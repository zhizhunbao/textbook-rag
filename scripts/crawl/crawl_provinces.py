"""
Batch Provincial Nominee Program (PNP) Crawler — All provinces & territories.

Usage:
  uv run python scripts/crawl/crawl_provinces.py                 # All provinces
  uv run python scripts/crawl/crawl_provinces.py --only on bc ab # Specific ones
  uv run python scripts/crawl/crawl_provinces.py --list          # Show config
  uv run python scripts/crawl/crawl_provinces.py --resume        # Skip already-crawled

Crawls each province's official PNP website into:
  data/crawled_web/prov-{slug}/manifest.json + *.pdf

Designed for overnight/unattended execution.
"""
import argparse
import asyncio
import json
import re
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Callable
from urllib.parse import urlparse

sys.path.insert(0, ".")
from engine_v2.settings import *  # noqa
from engine_v2.crawling.web_crawler_v2 import (
    discover_urls,
    save_pdfs_from_manifest,
)

# ╔══════════════════════════════════════════════════════════════════════════════╗
# ║  URL Filter Factories — per-province path scope control                    ║
# ╚══════════════════════════════════════════════════════════════════════════════╝

def _make_path_filter(
    *,
    include_prefixes: list[str] | None = None,
    exclude_prefixes: list[str] | None = None,
    exclude_patterns: list[str] | None = None,
) -> Callable[[str], bool]:
    """Create a URL filter based on path prefix inclusion/exclusion rules.

    Args:
        include_prefixes: If set, path must start with one of these.
        exclude_prefixes: Path must NOT start with any of these.
        exclude_patterns: Regex patterns — path must NOT match any.
    """
    compiled_patterns = [re.compile(p) for p in (exclude_patterns or [])]

    def _filter(url: str) -> bool:
        path = urlparse(url).path

        # Include check: path must start with at least one prefix
        if include_prefixes:
            if not any(path.startswith(pfx) for pfx in include_prefixes):
                return False

        # Exclude check: path must NOT start with any excluded prefix
        if exclude_prefixes:
            if any(path.startswith(pfx) for pfx in exclude_prefixes):
                return False

        # Regex exclude check
        if compiled_patterns:
            if any(pat.search(path) for pat in compiled_patterns):
                return False

        return True

    return _filter


# ── Ontario-specific keyword filter ──────────────────────────────────────────
# ontario.ca /page/ is a catch-all for every government topic.
# We only want OINP-related content, so require immigration keywords in the path.
_ONTARIO_KEYWORDS = {
    "oinp", "immigr", "nominee", "express-entry", "pnp",
    "employer-job-offer", "graduate-stream", "skilled-trades",
    "human-capital", "french-speaking", "tech-draw",
    "regional-immigration", "redi-pilot", "e-filing",
    "employer-portal", "representative", "contravention",
    "document-checklist", "expression-interest",
    # removed: "extra-provincial-corporation" — matches non-immigration business pages
}

def _ontario_filter(url: str) -> bool:
    """Ontario.ca: only keep URLs with immigration-related keywords."""
    path = urlparse(url).path.lower()
    # Must be under /page/ or /document/
    if not (path.startswith("/page/") or path.startswith("/document/")):
        return False
    # Exclude French, archive, government org pages
    if any(x in path for x in ("/lois/", "/archive/")):
        return False
    # Must contain at least one immigration keyword
    return any(kw in path for kw in _ONTARIO_KEYWORDS)

# ╔══════════════════════════════════════════════════════════════════════════════╗
# ║  Provincial PNP Configuration — Official URLs from canada.ca               ║
# ╚══════════════════════════════════════════════════════════════════════════════╝

@dataclass
class ProvinceConfig:
    slug: str                          # prov-{slug} directory name
    name: str                          # Human-readable province name
    seed_urls: list                    # Official PNP entry page(s)
    max_depth: int = 3                 # BFS depth
    max_pages: int = 150               # Max pages per seed
    static_urls: list | None = None    # URLs injected directly into manifest (skip BFS)
    delay_override: float | None = None  # Per-province delay (overrides --delay)
    url_filter: Callable | None = None # Custom URL filter

PROVINCES = [
    # ── Big 4 (highest immigration volume) ──────────────────────────────────
    ProvinceConfig(
        slug="ontario",
        name="Ontario (OINP)",
        seed_urls=[
            "https://www.ontario.ca/page/ontario-immigrant-nominee-program-oinp",
        ],
        # Direct manifest injection — these won't go through BFS (avoids law cross-references)
        static_urls=[
            "https://www.ontario.ca/laws/statute/15o08",  # Ontario Immigration Act, 2015
        ],
        max_depth=3,
        max_pages=150,
        delay_override=15.0,  # Ontario.ca Radware WAF blocks after ~14 reqs at 8s
        # Ontario.ca: /page/ is too broad (includes all gov topics).
        # Use keyword filter: URL must contain immigration-related terms.
        url_filter=_ontario_filter,
    ),
    ProvinceConfig(
        slug="quebec",
        name="Quebec (PQI / PRTQ)",
        seed_urls=[
            # Quebec has its own immigration system (not PNP)
            "https://www.quebec.ca/en/immigration",
        ],
        max_depth=3,
        max_pages=150,
        # quebec.ca: keep immigration + education (study-quebec) paths
        url_filter=_make_path_filter(
            include_prefixes=["/en/immigration/", "/en/education/study-quebec", "/en/education/learn-french"],
        ),
    ),
    ProvinceConfig(
        slug="bc",
        name="British Columbia (BC PNP)",
        seed_urls=[
            "https://www.welcomebc.ca/immigrate-to-b-c/about-the-bc-provincial-nominee-program",
        ],
        max_depth=3,
        max_pages=150,
        # WelcomeBC: keep immigration-related paths
        url_filter=_make_path_filter(
            include_prefixes=["/immigrate-to-b-c/", "/work-or-study-in-b-c/", "/resources-for/"],
        ),
    ),
    ProvinceConfig(
        slug="alberta",
        name="Alberta (AAIP)",
        seed_urls=[
            "https://www.alberta.ca/alberta-advantage-immigration-program",
            "https://www.alberta.ca/aaip-application-streams",
            "https://www.alberta.ca/immigration",
        ],
        max_depth=3,
        max_pages=150,
        # Alberta.ca uses flat URL patterns: /aaip-*, /tourism-and-hospitality-stream, etc.
        url_filter=_make_path_filter(
            include_prefixes=[
                "/alberta-advantage-immigration-program",
                "/aaip-",
                "/immigration",
                "/immigrate-to-alberta",
                "/moving-to-alberta",
                "/rural-renewal-stream",
                "/tourism-and-hospitality-stream",
                "/dedicated-health-care-pathway",
                "/job-offer-and-employer-requirements",
                "/contact-opportunity-alberta",
            ],
        ),
    ),
    ProvinceConfig(
        slug="manitoba",
        name="Manitoba (MPNP)",
        seed_urls=[
            "https://immigratemanitoba.com/immigrate/",
        ],
        max_depth=3,
        max_pages=150,
    ),
    # ── Atlantic Provinces ──────────────────────────────────────────────────
    ProvinceConfig(
        slug="nova-scotia",
        name="Nova Scotia (NSNP)",
        seed_urls=[
            "https://liveinnovascotia.com/",
        ],
        max_depth=3,
        max_pages=150,
    ),
    ProvinceConfig(
        slug="new-brunswick",
        name="New Brunswick (NBPNP)",
        seed_urls=[
            "https://www2.gnb.ca/content/gnb/en/corporate/promo/immigration/immigrating-to-nb/nb-immigration-program-streams.html",
        ],
        max_depth=3,
        max_pages=150,
        # GNB: stay within immigration content
        url_filter=_make_path_filter(
            include_prefixes=["/content/gnb/en/corporate/promo/immigration/"],
        ),
    ),
    ProvinceConfig(
        slug="newfoundland",
        name="Newfoundland & Labrador (NLPNP)",
        seed_urls=[
            # BFS disabled — gov.nl.ca returns maintenance page to headless browsers.
            # All URLs injected as static_urls instead.
        ],
        max_depth=0,
        max_pages=0,
        static_urls=[
            # ── PNP Overview ──
            "https://www.gov.nl.ca/immigration/immigrating-to-newfoundland-and-labrador/provincial-nominee-program/overview/",
            "https://www.gov.nl.ca/immigration/immigrating-to-newfoundland-and-labrador/",
            "https://www.gov.nl.ca/immigration/",
            # ── PNP Applicant Streams ──
            "https://www.gov.nl.ca/immigration/immigrating-to-newfoundland-and-labrador/provincial-nominee-program/applicants/overview/",
            "https://www.gov.nl.ca/immigration/immigrating-to-newfoundland-and-labrador/provincial-nominee-program/applicants/skilled-worker/",
            "https://www.gov.nl.ca/immigration/immigrating-to-newfoundland-and-labrador/provincial-nominee-program/applicants/express-entry-skilled-worker/",
            "https://www.gov.nl.ca/immigration/immigrating-to-newfoundland-and-labrador/provincial-nominee-program/applicants/international-graduate/",
            "https://www.gov.nl.ca/immigration/immigrating-to-newfoundland-and-labrador/provincial-nominee-program/applicants/using-representatives-and-consultants/",
            "https://www.gov.nl.ca/immigration/immigrating-to-newfoundland-and-labrador/provincial-nominee-program/applicants/disclaimer/",
            # ── PNP Employers ──
            "https://www.gov.nl.ca/immigration/immigrating-to-newfoundland-and-labrador/provincial-nominee-program/employers/overview/",
            "https://www.gov.nl.ca/immigration/immigrating-to-newfoundland-and-labrador/provincial-nominee-program/employers/employer-criteria/",
            "https://www.gov.nl.ca/immigration/job-vacancy-assessment/",
            # ── PNP Entrepreneurs ──
            "https://www.gov.nl.ca/immigration/immigrating-to-newfoundland-and-labrador/provincial-nominee-program/entrepreneurs/international-entrepreneur/overview/",
            "https://www.gov.nl.ca/immigration/immigrating-to-newfoundland-and-labrador/provincial-nominee-program/entrepreneurs/international-entrepreneur/eligibility-criteria/",
            "https://www.gov.nl.ca/immigration/immigrating-to-newfoundland-and-labrador/provincial-nominee-program/entrepreneurs/international-graduate-entrepreneur/overview/",
            "https://www.gov.nl.ca/immigration/immigrating-to-newfoundland-and-labrador/provincial-nominee-program/entrepreneurs/international-graduate-entrepreneur/eligibility-criteria/",
            # ── Expression of Interest ──
            "https://www.gov.nl.ca/immigration/expression-of-interest-model-overview/",
            "https://www.gov.nl.ca/immigration/expression-of-interest-model-faqs/",
            "https://www.gov.nl.ca/immigration/expression-of-interest-model-prioritization-criteria/",
            "https://www.gov.nl.ca/immigration/invitations-to-apply-updates/",
            # ── Atlantic Immigration Program ──
            "https://www.gov.nl.ca/immigration/immigrating-to-newfoundland-and-labrador/atlantic-immigration-program/overview/",
            "https://www.gov.nl.ca/immigration/immigrating-to-newfoundland-and-labrador/atlantic-immigration-program/workers/",
            "https://www.gov.nl.ca/immigration/immigrating-to-newfoundland-and-labrador/atlantic-immigration-program/employers/",
            "https://www.gov.nl.ca/immigration/immigrating-to-newfoundland-and-labrador/atlantic-immigration-program/designated-employers/",
            "https://www.gov.nl.ca/immigration/immigrating-to-newfoundland-and-labrador/atlantic-immigration-program/using-representatives-and-consultants/",
            "https://www.gov.nl.ca/immigration/de-designation/",
            # ── Program Policies ──
            "https://www.gov.nl.ca/immigration/program-policies-and-procedures/",
            "https://www.gov.nl.ca/immigration/general-policies-2/",
            "https://www.gov.nl.ca/immigration/job-vacancy-assessment-2/",
            "https://www.gov.nl.ca/immigration/skilled-workers-category/",
            "https://www.gov.nl.ca/immigration/express-entry-skilled-worker-category/",
            "https://www.gov.nl.ca/immigration/international-graduate-category/",
            "https://www.gov.nl.ca/immigration/in-canada-refugee-claimants/",
            "https://www.gov.nl.ca/immigration/excluded-positions/",
            # ── Settlement & Other ──
            "https://www.gov.nl.ca/immigration/settlement-and-other-resources/overview/",
            "https://www.gov.nl.ca/immigration/newfoundland-and-labrador-settlement-and-integration-program/",
            "https://www.gov.nl.ca/immigration/contact-us/",
            "https://www.gov.nl.ca/immigration/mandate/",
        ],
        url_filter=_make_path_filter(
            include_prefixes=["/immigration/"],
        ),
    ),
    ProvinceConfig(
        slug="pei",
        name="Prince Edward Island (PEI PNP)",
        seed_urls=[
            "https://www.princeedwardisland.ca/en/topic/immigrate-to-pei-as-a-worker",
        ],
        max_depth=3,
        max_pages=150,
        url_filter=_make_path_filter(
            include_prefixes=[
                "/en/topic/immigrate",
                "/en/topic/pei-pnp",
                "/en/information/pei-pnp",
                "/en/topic/work-in-pei",
            ],
        ),
    ),
    # ── Prairie ─────────────────────────────────────────────────────────────
    ProvinceConfig(
        slug="saskatchewan",
        name="Saskatchewan (SINP)",
        seed_urls=[
            "https://www.saskatchewan.ca/residents/moving-to-saskatchewan/live-in-saskatchewan/by-immigrating/saskatchewan-immigrant-nominee-program",
        ],
        max_depth=3,
        max_pages=150,
        url_filter=_make_path_filter(
            include_prefixes=[
                "/residents/moving-to-saskatchewan/",
            ],
        ),
    ),
    # ── Territories ─────────────────────────────────────────────────────────
    ProvinceConfig(
        slug="yukon",
        name="Yukon (YNP)",
        seed_urls=[
            "https://yukon.ca/en/immigration/apply-immigrate-yukon/immigrate-yukon",
        ],
        max_depth=3,
        max_pages=150,
        url_filter=_make_path_filter(
            include_prefixes=["/en/immigration/"],
        ),
    ),
    ProvinceConfig(
        slug="nwt",
        name="Northwest Territories (NTNP)",
        seed_urls=[
            "https://www.immigratenwt.ca/immigrate-here",
        ],
        max_depth=3,
        max_pages=150,
    ),
]

PROVINCE_MAP = {p.slug: p for p in PROVINCES}

# ── Log ──────────────────────────────────────────────────────────────────────

LOG_DIR = Path("data/crawled_web")
GLOBAL_LOG = LOG_DIR / "_provinces_crawl.log"

def _log(msg: str):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line)
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    with open(GLOBAL_LOG, "a", encoding="utf-8") as f:
        f.write(line + "\n")


# ╔══════════════════════════════════════════════════════════════════════════════╗
# ║  Crawl Runner                                                               ║
# ╚══════════════════════════════════════════════════════════════════════════════╝

async def crawl_province(prov: ProvinceConfig, *, delay: float = 3.0, headless: bool = True) -> dict:
    """Crawl a single province: discover URLs → save PDFs."""
    persona = f"prov-{prov.slug}"
    effective_delay = prov.delay_override or delay
    _log(f"\n{'='*60}")
    _log(f"PROVINCE: {prov.name}")
    _log(f"  Persona: {persona}")
    _log(f"  Seeds:   {len(prov.seed_urls)}")
    for u in prov.seed_urls:
        _log(f"           {u}")
    _log(f"  Depth:   {prov.max_depth}, Max: {prov.max_pages}")
    _log(f"  Delay:   {effective_delay}s {'(override)' if prov.delay_override else '(default)'}")
    _log(f"  Filter:  {'✓ custom' if prov.url_filter else '✗ none'}")
    _log(f"{'='*60}")

    t0 = time.time()
    result = {"province": prov.name, "slug": persona, "status": "ok", "pages": 0, "saved": 0, "failed": 0}

    # Phase 1: Discover (skip if manifest already exists)
    manifest_path = LOG_DIR / persona / "manifest.json"
    if manifest_path.exists():
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        total = manifest.get("total_urls", 0)
        _log(f"  [SKIP] manifest.json already exists ({total} URLs) — skipping discovery")
    else:
        for i, seed_url in enumerate(prov.seed_urls, 1):
            _log(f"  [DISCOVER {i}/{len(prov.seed_urls)}] {seed_url}")
            try:
                manifest_path = await discover_urls(
                    seed_url=seed_url,
                    persona_slug=persona,
                    max_depth=prov.max_depth,
                    max_pages=prov.max_pages,
                    headless=headless,
                    url_filter=prov.url_filter,
                )
                manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
                total = manifest.get("total_urls", 0)
                _log(f"    → {total} URLs discovered")
            except Exception as e:
                _log(f"    [ERROR] Discovery failed: {e}")
                result["status"] = "partial"
                continue

    # Inject static_urls into manifest (skip BFS)
    manifest_path = LOG_DIR / persona / "manifest.json"
    if prov.static_urls:
        # Create empty manifest if it doesn't exist (static-only provinces)
        if not manifest_path.exists():
            manifest_path.parent.mkdir(parents=True, exist_ok=True)
            manifest_path.write_text(json.dumps({
                "seed_urls": prov.seed_urls,
                "persona": persona,
                "total_urls": 0,
                "pages": [],
            }, indent=2, ensure_ascii=False), encoding="utf-8")
            _log(f"  [STATIC] Created empty manifest for static-only province")
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        if manifest.get("pages") is None:
            manifest["pages"] = []
        existing_urls = {p["url"] for p in manifest.get("pages", [])}
        added = 0
        for surl in prov.static_urls:
            if surl not in existing_urls:
                from engine_v2.crawling.web_crawler import _url_to_filename
                manifest["pages"].append({"url": surl, "filename": _url_to_filename(surl)})
                added += 1
        if added:
            manifest["total_urls"] = len(manifest["pages"])
            manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
            _log(f"  [STATIC] Injected {added} static URLs into manifest")

    # Phase 2: Save PDFs
    if not manifest_path.exists():
        _log(f"  [ERROR] No manifest found for {persona}")
        result["status"] = "error"
        return result

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    result["pages"] = len(manifest.get("pages", []))
    _log(f"  [BATCH] Saving {result['pages']} pages as PDF...")

    try:
        results = await save_pdfs_from_manifest(
            manifest_path=manifest_path,
            headless=headless,
            delay_between=effective_delay,
        )
        result["saved"] = sum(1 for r in results if r.success)
        result["failed"] = sum(1 for r in results if not r.success)
    except Exception as e:
        _log(f"  [ERROR] Batch save crashed: {e}")
        result["status"] = "error"

    elapsed = time.time() - t0
    result["time_min"] = round(elapsed / 60, 1)
    _log(f"  DONE: {result['saved']}/{result['pages']} saved, {result['failed']} failed ({result['time_min']} min)")
    return result


async def main_crawl(provinces: list[ProvinceConfig], *, delay: float = 2.0, resume: bool = False, headless: bool = True):
    """Crawl all specified provinces sequentially."""
    _log("\n" + "█" * 60)
    _log(f"PROVINCIAL PNP BATCH CRAWL — {len(provinces)} provinces")
    _log(f"  Resume mode: {resume}")
    _log("█" * 60)

    t0 = time.time()
    results = []

    for i, prov in enumerate(provinces, 1):
        persona = f"prov-{prov.slug}"

        # Skip if resume mode and manifest has saved pages
        if resume:
            mpath = LOG_DIR / persona / "manifest.json"
            if mpath.exists():
                try:
                    m = json.loads(mpath.read_text(encoding="utf-8"))
                    saved_count = sum(1 for p in m.get("pages", []) if p.get("status") == "saved")
                    if saved_count > 0:
                        _log(f"\n[{i}/{len(provinces)}] SKIP {prov.name} (already has {saved_count} saved pages)")
                        results.append({
                            "province": prov.name, "slug": persona,
                            "status": "skipped", "pages": saved_count,
                        })
                        continue
                except Exception:
                    pass

        _log(f"\n[{i}/{len(provinces)}] Starting {prov.name}...")
        r = await crawl_province(prov, delay=delay, headless=headless)
        results.append(r)

    # ── Final Summary ────────────────────────────────────────────────────────
    total_elapsed = time.time() - t0
    _log("\n\n" + "█" * 60)
    _log("BATCH CRAWL SUMMARY")
    _log("█" * 60)
    _log(f"{'Province':<30} {'Status':<10} {'Pages':<8} {'Saved':<8} {'Failed':<8} {'Time'}")
    _log("-" * 80)
    for r in results:
        _log(f"{r.get('province','?'):<30} {r.get('status','?'):<10} {r.get('pages',0):<8} {r.get('saved',0):<8} {r.get('failed',0):<8} {r.get('time_min','—')} min")
    _log("-" * 80)
    _log(f"Total time: {total_elapsed/60:.1f} min")
    _log(f"Log: {GLOBAL_LOG}")


# ╔══════════════════════════════════════════════════════════════════════════════╗
# ║  CLI                                                                         ║
# ╚══════════════════════════════════════════════════════════════════════════════╝

def cli():
    parser = argparse.ArgumentParser(
        description="Batch crawl all Canadian provincial PNP websites",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  uv run python scripts/crawl/crawl_provinces.py                   # All provinces
  uv run python scripts/crawl/crawl_provinces.py --only on bc ab   # Ontario, BC, Alberta
  uv run python scripts/crawl/crawl_provinces.py --resume           # Skip done ones
  uv run python scripts/crawl/crawl_provinces.py --list             # Show config
        """,
    )
    parser.add_argument("--only", nargs="+", metavar="SLUG",
                        help="Only crawl these provinces (slugs: on, qc, bc, ab, mb, ns, nb, nl, pei, sk, yk, nwt)")
    parser.add_argument("--resume", action="store_true",
                        help="Skip provinces that already have saved pages")
    parser.add_argument("--delay", type=float, default=2.0,
                        help="Delay between pages in seconds (default: 2.0)")
    parser.add_argument("--no-headless", action="store_true",
                        help="Show browser window (for manual CAPTCHA solving)")
    parser.add_argument("--list", action="store_true",
                        help="List all configured provinces and exit")

    args = parser.parse_args()

    if args.list:
        print(f"\n{'Slug':<15} {'Name':<35} {'Depth':<6} {'Max':<6} {'Filter':<8} Seed URL")
        print("-" * 120)
        for p in PROVINCES:
            filt = "✓" if p.url_filter else "—"
            for u in p.seed_urls:
                print(f"{p.slug:<15} {p.name:<35} {p.max_depth:<6} {p.max_pages:<6} {filt:<8} {u}")
        return

    # Filter provinces
    SLUG_ALIASES = {
        "on": "ontario", "ontario": "ontario",
        "qc": "quebec", "quebec": "quebec",
        "bc": "bc",
        "ab": "alberta", "alberta": "alberta",
        "mb": "manitoba", "manitoba": "manitoba",
        "ns": "nova-scotia", "nova-scotia": "nova-scotia",
        "nb": "new-brunswick", "new-brunswick": "new-brunswick",
        "nl": "newfoundland", "newfoundland": "newfoundland",
        "pei": "pei",
        "sk": "saskatchewan", "saskatchewan": "saskatchewan",
        "yk": "yukon", "yukon": "yukon",
        "nwt": "nwt",
    }

    if args.only:
        selected = []
        for s in args.only:
            slug = SLUG_ALIASES.get(s.lower())
            if slug and slug in PROVINCE_MAP:
                selected.append(PROVINCE_MAP[slug])
            else:
                print(f"[WARN] Unknown slug: {s} — available: {', '.join(sorted(set(SLUG_ALIASES.values())))}")
        if not selected:
            print("No valid provinces selected!")
            return
        provinces = selected
    else:
        provinces = PROVINCES

    asyncio.run(main_crawl(provinces, delay=args.delay, resume=args.resume, headless=not args.no_headless))


if __name__ == "__main__":
    cli()
