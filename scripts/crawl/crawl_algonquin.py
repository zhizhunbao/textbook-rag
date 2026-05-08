"""
Algonquin College Program Crawler
爬取亚岗昆学院所有项目，保存为 PDF 用于 MinerU → ChromaDB 管道。

逻辑和 crawler_cli.py / crawl_provinces.py 完全一致：
  Phase 1: discover_urls() — BFS via crawl4ai → manifest.json
  Phase 2: save_pdfs_from_manifest() — Playwright page.pdf() per URL

Usage:
  cd textbook-rag
  uv run python scripts/crawl/crawl_algonquin.py
  uv run python scripts/crawl/crawl_algonquin.py --resume      # 跳过已保存的 PDF
  uv run python scripts/crawl/crawl_algonquin.py --list        # 显示配置

Output:
  data/crawled_web/algonquin-programs/
    manifest.json       — URL index
    *.pdf               — Full-page PDFs of each program page
"""
import argparse
import asyncio
import json
import re
import sys
import time
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse

sys.path.insert(0, ".")
from engine_v2.settings import *  # noqa
from engine_v2.crawling import (
    discover_urls,
    save_pdfs_from_manifest,
)

# ╔══════════════════════════════════════════════════════════════════════════════╗
# ║  URL Filter — keep only program pages, skip noise                            ║
# ╚══════════════════════════════════════════════════════════════════════════════╝

# Algonquin site has a LOT of pages (news, events, employee portals, etc.)
# We only want /program/ pages and closely related content.
_KEEP_PREFIXES = [
    "/program/",           # Individual program pages
    "/future-students/",   # Future students hub (programs, courses)
    "/international/",     # International student info (PGWP, fees, etc.)
    "/fee-estimator",      # Tuition fee estimator tool
    "/ro/",                # Registrar's Office (fees, policies)
    "/coop-career-centre/", # Co-op & career centre (co-op fees, etc.)
    "/financial-aid/",      # Financial aid, scholarships, OSAP, bursaries
]

_EXCLUDE_PATTERNS = [
    r"/employees?/",           # Employee portal
    r"/alumni/",               # Alumni
    r"/foundation/",           # Giving/Foundation
    r"/careers?/",             # Job postings
    r"/news/",                 # News articles
    r"/events?/",              # Events
    r"/myac",                  # My AC portal
    r"/library/",              # Library
    r"/maps?/",                # Campus maps
    r"/policies/",             # Policies
    r"/corporate/",            # Corporate pages
    r"/a-z/",                  # Site index
    r"/accessibility",         # Accessibility
    r"/research/",             # Research
    r"/pembroke/",             # Pembroke campus — not needed
    r"/student-experience",    # Student testimonial/marketing pages
    r"/hs-testimonials",       # Health studies testimonials
    r"/contact/?$",            # Contact sub-pages
    r"/campus-tours",          # Campus tour marketing pages
    r"/prc-orientation",       # Orientation sub-pages
    r"/assumption-risk",       # Risk release forms
]

_compiled_excludes = [re.compile(p) for p in _EXCLUDE_PATTERNS]


def _algonquin_filter(url: str) -> bool:
    """Keep program-related pages, filter out noise."""
    path = urlparse(url).path.lower()

    # Exclude noise first (takes priority)
    if any(pat.search(path) for pat in _compiled_excludes):
        return False

    # Keep individual program pages (main program pages only)
    if "/program/" in path:
        return True

    # Check include prefixes
    if not any(path.startswith(pfx) for pfx in _KEEP_PREFIXES):
        return False

    return True


# ╔══════════════════════════════════════════════════════════════════════════════╗
# ║  Configuration                                                               ║
# ╚══════════════════════════════════════════════════════════════════════════════╝

PERSONA = "algonquin-programs"
SEED_URLS = [
    "https://www.algonquincollege.com/future-students/programs/",
]
MAX_DEPTH = 3
MAX_PAGES = 300  # Algonquin has ~200 programs
DEFAULT_DELAY = 2.0

# Static URLs: pages that BFS won't discover from the programs listing
# but contain valuable content for the RAG knowledge base.
STATIC_URLS = [
    # ── Fees & Payment ──
    "https://www.algonquincollege.com/ro/pay/fee-estimator/",
    "https://www.algonquincollege.com/ro/pay/payment-options/",
    "https://www.algonquincollege.com/ro/pay/",
    "https://www.algonquincollege.com/ro/apprenticeships/apprenticeship-fees/",
    "https://www.algonquincollege.com/coop-career-centre/co-op-fees/",
    # ── Admissions ──
    "https://www.algonquincollege.com/ro/admissions/",
    "https://www.algonquincollege.com/ro/plan-getting-accepted-into-college/day-time-programs/",
    # ── Financial Aid, Scholarships & Bursaries ──
    "https://www.algonquincollege.com/financial-aid/",
    "https://www.algonquincollege.com/financial-aid/home/osap/",
    "https://www.algonquincollege.com/financial-aid/submit-osap-documents/",
    "https://www.algonquincollege.com/financial-aid/home/osap/grant-only-funding/",
    "https://www.algonquincollege.com/financial-aid/home/osap/fasa-deadlines/",
    "https://www.algonquincollege.com/financial-aid/part-time-students-ontario/",
    "https://www.algonquincollege.com/financial-aid/out-of-province-students/",
    "https://www.algonquincollege.com/financial-aid/academic-probation/",
    "https://www.algonquincollege.com/financial-aid/awards-bursaries-scholarships/",
    "https://www.algonquincollege.com/financial-aid/awards/",
    "https://www.algonquincollege.com/financial-aid/how-to-apply-for-bursaries/",
    "https://www.algonquincollege.com/financial-aid/resources/",
    "https://www.algonquincollege.com/financial-aid/resources/budgeting-basics/",
    "https://www.algonquincollege.com/financial-aid/resources/emergency-funding/",
    "https://www.algonquincollege.com/financial-aid/work-study-programs/",
    "https://www.algonquincollege.com/financial-aid/resources/faq/",
    "https://www.algonquincollege.com/financial-aid/contact-us/",
    # ── International Students ──
    "https://www.algonquincollege.com/international/",
]

LOG_DIR = Path("data/crawled_web")


# ── Helpers ──────────────────────────────────────────────────────────────────

def _url_to_filename(url: str) -> str:
    """Convert URL to a relative filename path (mirrors site structure)."""
    parsed = urlparse(url)
    path = parsed.path.strip("/")
    if not path:
        path = "index"
    return path


def _inject_static_urls(manifest_path: Path):
    """Inject STATIC_URLS into manifest.json if not already present."""
    if not manifest_path.exists():
        return

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    pages = manifest.get("pages", [])
    existing_urls = {p.get("url", "").rstrip("/").lower() for p in pages}

    added = 0
    for url in STATIC_URLS:
        norm = url.rstrip("/").lower()
        if norm in existing_urls:
            continue
        pages.append({
            "url": url.rstrip("/"),
            "filename": _url_to_filename(url),
        })
        existing_urls.add(norm)
        added += 1

    if added > 0:
        manifest["pages"] = pages
        manifest["total_urls"] = len(pages)
        manifest_path.write_text(
            json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8"
        )
        _log(f"  [STATIC] Injected {added} static URLs → {len(pages)} total")
    else:
        _log(f"  [STATIC] All {len(STATIC_URLS)} static URLs already present")


# ── Logging ──────────────────────────────────────────────────────────────────

def _log(msg: str):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line)
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    log_file = LOG_DIR / PERSONA / "crawl.log"
    log_file.parent.mkdir(parents=True, exist_ok=True)
    with open(log_file, "a", encoding="utf-8") as f:
        f.write(line + "\n")


# ╔══════════════════════════════════════════════════════════════════════════════╗
# ║  Crawl Runner                                                               ║
# ╚══════════════════════════════════════════════════════════════════════════════╝

async def run_crawl(*, delay: float = DEFAULT_DELAY):
    """Full pipeline: discover_urls() → save_pdfs_from_manifest()."""
    _log("=" * 60)
    _log(f"ALGONQUIN COLLEGE CRAWL")
    _log(f"  Persona: {PERSONA}")
    _log(f"  Seeds:   {len(SEED_URLS)}")
    for u in SEED_URLS:
        _log(f"           {u}")
    _log(f"  Depth:   {MAX_DEPTH}, Max: {MAX_PAGES}")
    _log(f"  Delay:   {delay}s")
    _log("=" * 60)

    t0 = time.time()

    # ── Phase 1: BFS Discovery → manifest.json ──
    manifest_path = LOG_DIR / PERSONA / "manifest.json"
    if manifest_path.exists():
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        total = manifest.get("total_urls", 0)
        _log(f"\n[SKIP] manifest.json already exists ({total} URLs) — skipping discovery")
    else:
        for i, seed_url in enumerate(SEED_URLS, 1):
            _log(f"\n[DISCOVER {i}/{len(SEED_URLS)}] {seed_url}")
            try:
                manifest_path = await discover_urls(
                    seed_url=seed_url,
                    persona_slug=PERSONA,
                    max_depth=MAX_DEPTH,
                    max_pages=MAX_PAGES,
                    headless=True,
                    url_filter=_algonquin_filter,
                )
                manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
                total = manifest.get("total_urls", 0)
                _log(f"  → {total} URLs discovered")
            except Exception as e:
                _log(f"  [ERROR] Discovery failed: {e}")
                continue

    # ── Phase 1b: Inject static URLs into manifest ──
    _inject_static_urls(manifest_path)

    # ── Phase 2: Save PDFs ──
    if not manifest_path.exists():
        _log("[ERROR] No manifest.json found, aborting")
        return

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    total_urls = len(manifest.get("pages", []))
    _log(f"\n[BATCH] Saving {total_urls} pages as PDF (delay={delay}s)")

    try:
        results = await save_pdfs_from_manifest(
            manifest_path=manifest_path,
            headless=True,
            delay_between=delay,
            # pre_pdf_js now handled by Algonquin site profile
            # (engine_v2/crawling/sites/algonquin.py)
        )
    except Exception as e:
        _log(f"[ERROR] Batch save crashed: {e}")
        results = []

    # ── Summary ──
    elapsed = time.time() - t0
    saved = [r for r in results if r.success]
    failed = [r for r in results if not r.success]
    total_mb = sum(r.file_size for r in saved) / (1024 * 1024) if saved else 0

    _log("\n" + "=" * 60)
    _log("CRAWL COMPLETE")
    _log(f"  Time:    {elapsed/60:.1f} min")
    _log(f"  Saved:   {len(saved)}/{len(results)} pages ({total_mb:.1f} MB)")
    _log(f"  Failed:  {len(failed)}")
    if failed:
        for r in failed:
            reason = (r.error or "unknown")[:80]
            _log(f"    ✗ {r.filename}: {reason}")
    _log("=" * 60)


# ╔══════════════════════════════════════════════════════════════════════════════╗
# ║  CLI                                                                         ║
# ╚══════════════════════════════════════════════════════════════════════════════╝

def cli():
    parser = argparse.ArgumentParser(
        description="Crawl Algonquin College programs → manifest.json + PDFs",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  uv run python scripts/crawl/crawl_algonquin.py
  uv run python scripts/crawl/crawl_algonquin.py --delay 3
  uv run python scripts/crawl/crawl_algonquin.py --list
        """,
    )
    parser.add_argument("--delay", type=float, default=DEFAULT_DELAY,
                        help=f"Delay between pages (default: {DEFAULT_DELAY}s)")
    parser.add_argument("--list", action="store_true",
                        help="Show configuration and exit")

    args = parser.parse_args()

    if args.list:
        print(f"\nPersona:  {PERSONA}")
        print(f"Depth:    {MAX_DEPTH}")
        print(f"Max:      {MAX_PAGES}")
        print(f"Delay:    {args.delay}s")
        print(f"Filter:   ✓ algonquin_filter")
        print(f"Seeds:")
        for u in SEED_URLS:
            print(f"  {u}")
        return

    asyncio.run(run_crawl(delay=args.delay))


if __name__ == "__main__":
    cli()
