"""Batch runner — discover Internet ISP plan URLs (Bell, Rogers, TekSavvy).

Runs all discover_internet_*.py scripts in sequence:
    uv run python scripts/crawl/discover_internet.py --supplemental-only
"""
import asyncio, importlib, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

CARRIERS = [
    "bell",
    "rogers",
    "teksavvy",
]

HEADER = """
============================================================
INTERNET ISP DISCOVERY: {}
============================================================
""".format(", ".join(c.upper() for c in CARRIERS))


async def main():
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("--supplemental-only", action="store_true")
    p.add_argument("--visible", action="store_true")
    p.add_argument("--dry-run", action="store_true")
    a = p.parse_args()

    print(HEADER)

    for idx, carrier in enumerate(CARRIERS, 1):
        mod_name = f"discover_internet_{carrier}"
        print(f"\n{'─'*60}")
        print(f"[{idx}/{len(CARRIERS)}] {carrier.upper()}")
        print(f"{'─'*60}")

        mod = importlib.import_module(mod_name)

        if a.supplemental_only:
            print("  [SKIP] BFS discovery")
        else:
            await mod.run_bfs_discovery(headless=not a.visible)

        mod.merge_supplemental_into_manifest(dry_run=a.dry_run)

    print(f"\n{'='*60}")
    print("ALL DONE — next step:")
    for c in CARRIERS:
        print(f"  uv run python scripts/crawl/crawler_cli.py batch data/crawled_web/internet-{c}/manifest.json --visible")
    print(f"{'='*60}")


if __name__ == "__main__":
    asyncio.run(main())
