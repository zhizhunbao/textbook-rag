"""Discover TD personal banking URLs.

BFS crawl from TD newcomer/banking/credit-card pages.
Category: bank-td, Collection: ca_bank_td.

Usage:
    uv run python scripts/crawl/discover_td.py
    uv run python scripts/crawl/discover_td.py --dry-run
    uv run python scripts/crawl/discover_td.py --supplemental-only
"""
import asyncio
import json
import sys
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

# ── Config ──
PERSONA = "bank-td"
MANIFEST_PATH = Path(__file__).resolve().parents[2] / "data" / "crawled_web" / PERSONA / "manifest.json"

# Phase 1: BFS seeds
BFS_SEEDS = [
    # Newcomer 专属页面
    "https://www.td.com/ca/en/personal-banking/solutions/new-to-canada",
    # 个人银行账户
    "https://www.td.com/ca/en/personal-banking/products/bank-accounts/",
    # 信用卡
    "https://www.td.com/ca/en/personal-banking/products/credit-cards/",
    # 学生
    "https://www.td.com/ca/en/personal-banking/solutions/student-banking",
]
BFS_DEPTH = 2
BFS_MAX_PAGES = 500

# Phase 1.5: Supplemental URLs
_BASE = "https://www.td.com/ca/en/personal-banking"
SUPPLEMENTAL_URLS = [
    # ── Newcomer ──
    f"{_BASE}/solutions/new-to-canada",
    # ── Bank Accounts ──
    f"{_BASE}/products/bank-accounts/",
    f"{_BASE}/products/bank-accounts/chequing-accounts/",
    f"{_BASE}/products/bank-accounts/savings-accounts/",
    f"{_BASE}/products/bank-accounts/every-day-chequing-account",
    f"{_BASE}/products/bank-accounts/unlimited-chequing-account",
    # ── Credit Cards ──
    f"{_BASE}/products/credit-cards/",
    f"{_BASE}/products/credit-cards/no-annual-fee/",
    f"{_BASE}/products/credit-cards/cash-back/",
    f"{_BASE}/products/credit-cards/rewards/",
    f"{_BASE}/products/credit-cards/low-interest/",
    f"{_BASE}/products/credit-cards/aeroplan/",
    # ── Students ──
    f"{_BASE}/solutions/student-banking",
    # ── Fees ──
    f"{_BASE}/products/bank-accounts/account-fees",
]


def _normalize_url(url: str) -> str:
    parsed = urlparse(url)
    return f"{parsed.scheme}://{parsed.netloc}{parsed.path}".rstrip("/")


async def run_bfs_discovery(headless: bool = True):
    """Discover TD pages via crawl4ai BFS."""
    from engine_v2.crawling.web_crawler_v2 import discover_urls

    print(f"\n{'='*60}")
    print(f"PHASE 1: BFS Discovery ({len(BFS_SEEDS)} seeds)")
    print(f"  PERSONA: {PERSONA}")
    print(f"{'='*60}")

    for i, url in enumerate(BFS_SEEDS):
        name = url.rstrip("/").split("/")[-1]
        print(f"\n[{i+1}/{len(BFS_SEEDS)}] {name}")

        def url_filter(u: str) -> bool:
            parsed = urlparse(u)
            return (
                parsed.netloc in ("www.td.com", "td.com")
                and "/personal-banking/" in parsed.path
            )

        try:
            manifest = await discover_urls(
                url, persona_slug=PERSONA,
                max_depth=BFS_DEPTH, max_pages=BFS_MAX_PAGES, headless=headless,
                url_filter=url_filter,
            )
            print(f"  -> Manifest: {manifest}")
        except Exception as e:
            print(f"  ERROR: {e}")


def merge_supplemental_into_manifest(dry_run: bool = False) -> int:
    """Merge SUPPLEMENTAL_URLS into manifest."""
    if not MANIFEST_PATH.exists():
        MANIFEST_PATH.parent.mkdir(parents=True, exist_ok=True)
        manifest = {
            "seed_urls": [str(u) for u in BFS_SEEDS],
            "persona": PERSONA,
            "discovered_at": datetime.now().isoformat(),
            "total_urls": 0,
            "pages": [],
        }
        MANIFEST_PATH.write_text(
            json.dumps(manifest, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        print(f"[CREATED] Empty manifest: {MANIFEST_PATH}")
    else:
        manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))

    existing_urls = {_normalize_url(p["url"]) for p in manifest["pages"]}

    new_pages = []
    for url in SUPPLEMENTAL_URLS:
        url_clean = _normalize_url(url)
        if url_clean not in existing_urls:
            path = urlparse(url_clean).path
            filename = path.lstrip("/").rstrip("/") or "index"
            new_pages.append({"url": url_clean, "filename": filename})

    print(f"\n{'='*60}")
    print(f"PHASE 1.5: Supplemental URLs")
    print(f"  Total supplemental: {len(SUPPLEMENTAL_URLS)}")
    print(f"  Already in manifest: {len(SUPPLEMENTAL_URLS) - len(new_pages)}")
    print(f"  New to add:          {len(new_pages)}")
    print(f"{'='*60}")

    if new_pages and not dry_run:
        manifest["pages"] = manifest["pages"] + new_pages
        manifest["total_urls"] = len(manifest["pages"])
        manifest["supplemental_at"] = datetime.now().isoformat()
        MANIFEST_PATH.write_text(
            json.dumps(manifest, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        print(f"[OK] Appended {len(new_pages)} supplemental URLs (total: {manifest['total_urls']})")
        for p in new_pages:
            print(f"  + {p['url']}")
    elif dry_run:
        print("[DRY RUN] Would add:")
        for p in new_pages:
            print(f"  {p['url']}")
    else:
        print("[OK] All supplemental URLs already in manifest")

    return len(new_pages)


async def main():
    import argparse
    parser = argparse.ArgumentParser(description="Discover TD personal banking URLs")
    parser.add_argument("--skip-bfs", action="store_true", help="Skip BFS phase")
    parser.add_argument("--supplemental-only", action="store_true", help="Only run supplemental merge")
    parser.add_argument("--visible", action="store_true", help="Show browser window (bypass anti-bot)")
    parser.add_argument("--dry-run", action="store_true", help="Preview only")
    args = parser.parse_args()

    if not args.supplemental_only and not args.skip_bfs:
        await run_bfs_discovery(headless=not args.visible)
    else:
        print("[SKIP] BFS discovery")

    merge_supplemental_into_manifest(dry_run=args.dry_run)

    print(f"\n{'='*60}")
    print("Discovery complete! Next steps:")
    print(f"{'='*60}")
    print(f"\n  # Step 1: 抓取 PDF")
    print(f"  uv run python scripts/crawl/crawler_cli.py batch data/crawled_web/{PERSONA}/manifest.json")
    print(f"\n  # Step 2-3: MinerU + ChromaDB")
    print(f"  uv run python scripts/ingest/batch_mineru.py --category {PERSONA}")
    print(f"  uv run python scripts/ingest/batch_ingest_vectors.py --category {PERSONA}")


if __name__ == "__main__":
    asyncio.run(main())
