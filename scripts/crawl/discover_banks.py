"""Discover all Big-5 Canadian bank personal banking URLs.

Batch runner that sequentially calls each bank's discover script.
Designed to run unattended — safe to leave overnight.

Usage:
    uv run python scripts/crawl/discover_banks.py
    uv run python scripts/crawl/discover_banks.py --dry-run
    uv run python scripts/crawl/discover_banks.py --supplemental-only
    uv run python scripts/crawl/discover_banks.py --banks bmo td     # subset only
"""
import asyncio
import importlib
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

# ── Bank modules (import path relative to scripts/crawl/) ──
BANK_MODULES = {
    "bmo": "scripts.crawl.discover_bmo",
    "rbc": "scripts.crawl.discover_rbc",
    "td": "scripts.crawl.discover_td",
    "scotiabank": "scripts.crawl.discover_scotiabank",
    "cibc": "scripts.crawl.discover_cibc",
}


async def main():
    import argparse
    parser = argparse.ArgumentParser(description="Discover all Big-5 bank URLs")
    parser.add_argument("--banks", nargs="+", choices=list(BANK_MODULES.keys()),
                        default=list(BANK_MODULES.keys()),
                        help="Which banks to crawl (default: all)")
    parser.add_argument("--skip-bfs", action="store_true", help="Skip BFS phase for all banks")
    parser.add_argument("--supplemental-only", action="store_true", help="Only run supplemental merge")
    parser.add_argument("--visible", action="store_true", help="Show browser window (bypass anti-bot)")
    parser.add_argument("--dry-run", action="store_true", help="Preview only")
    args = parser.parse_args()

    total_t0 = time.time()

    print("=" * 60)
    print(f"BIG-5 BANK DISCOVERY: {', '.join(b.upper() for b in args.banks)}")
    print("=" * 60)

    for i, bank in enumerate(args.banks, 1):
        mod_name = BANK_MODULES[bank]
        print(f"\n{'─'*60}")
        print(f"[{i}/{len(args.banks)}] {bank.upper()}")
        print(f"{'─'*60}")

        t0 = time.time()

        # Dynamic import
        mod = importlib.import_module(mod_name)

        # Phase 1: BFS
        if not args.supplemental_only and not args.skip_bfs:
            try:
                await mod.run_bfs_discovery(headless=not args.visible)
            except Exception as e:
                print(f"  [ERROR] BFS failed for {bank}: {e}")
        else:
            print("  [SKIP] BFS discovery")

        # Phase 1.5: Supplemental
        mod.merge_supplemental_into_manifest(dry_run=args.dry_run)

        elapsed = time.time() - t0
        print(f"  [{bank.upper()}] Done in {elapsed:.1f}s")

    total_elapsed = time.time() - total_t0

    print(f"\n{'='*60}")
    print(f"ALL BANKS COMPLETE ({total_elapsed/60:.1f} min)")
    print(f"{'='*60}")
    print()
    print("Next steps:")
    for bank in args.banks:
        persona = f"bank-{bank}"
        print(f"  uv run python scripts/crawl/crawler_cli.py batch data/crawled_web/{persona}/manifest.json")
    print()
    print("Then ingest:")
    for bank in args.banks:
        persona = f"bank-{bank}"
        print(f"  uv run python scripts/ingest/batch_mineru.py --category {persona}")
        print(f"  uv run python scripts/ingest/batch_ingest_vectors.py --category {persona}")


if __name__ == "__main__":
    asyncio.run(main())
