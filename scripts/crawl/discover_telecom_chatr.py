"""Discover Chatr Wireless plan URLs.

BFS crawl from Chatr plan/BYOD pages.
Category: telecom-chatr, Collection: ca_telecom_chatr.
Network: Rogers (Budget tier)

Usage:
    uv run python scripts/crawl/discover_chatr.py
    uv run python scripts/crawl/discover_chatr.py --dry-run
    uv run python scripts/crawl/discover_chatr.py --supplemental-only
"""
import asyncio
import json
import sys
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

PERSONA = "telecom-chatr"
MANIFEST_PATH = Path(__file__).resolve().parents[2] / "data" / "crawled_web" / PERSONA / "manifest.json"

BFS_SEEDS = [
    "https://www.chatrwireless.com",
]
BFS_DEPTH = 2
BFS_MAX_PAGES = 200
SUPPLEMENTAL_URLS = [
    "https://www.chatrwireless.com",
    "https://www.chatrwireless.com/plans",
    "https://www.chatrwireless.com/phones",
    "https://www.chatrwireless.com/why-chatr",
    "https://www.chatrwireless.com/coverage",
    "https://www.chatrwireless.com/top-up",
    "https://www.chatrwireless.com/support",
    "https://www.chatrwireless.com/stores",
]


def _normalize_url(url: str) -> str:
    parsed = urlparse(url)
    return f"{parsed.scheme}://{parsed.netloc}{parsed.path}".rstrip("/")


async def run_bfs_discovery(headless: bool = True):
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
            return parsed.netloc in ("www.chatrwireless.com", "chatrwireless.com")
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
    if not MANIFEST_PATH.exists():
        MANIFEST_PATH.parent.mkdir(parents=True, exist_ok=True)
        manifest = {
            "seed_urls": [str(u) for u in BFS_SEEDS],
            "persona": PERSONA,
            "discovered_at": datetime.now().isoformat(),
            "total_urls": 0, "pages": [],
        }
        MANIFEST_PATH.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"[CREATED] Empty manifest: {MANIFEST_PATH}")
    else:
        manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))

    existing_urls = {_normalize_url(p["url"]) for p in manifest["pages"]}
    new_pages = []
    for url in SUPPLEMENTAL_URLS:
        url_clean = _normalize_url(url)
        if url_clean not in existing_urls:
            path = urlparse(url_clean).path
            new_pages.append({"url": url_clean, "filename": path.lstrip("/").rstrip("/") or "index"})

    print(f"\n{'='*60}")
    print(f"PHASE 1.5: Supplemental URLs")
    print(f"  Total: {len(SUPPLEMENTAL_URLS)}, Already: {len(SUPPLEMENTAL_URLS) - len(new_pages)}, New: {len(new_pages)}")
    print(f"{'='*60}")

    if new_pages and not dry_run:
        manifest["pages"] += new_pages
        manifest["total_urls"] = len(manifest["pages"])
        manifest["supplemental_at"] = datetime.now().isoformat()
        MANIFEST_PATH.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"[OK] Appended {len(new_pages)} URLs (total: {manifest['total_urls']})")
        for p in new_pages:
            print(f"  + {p['url']}")
    elif dry_run:
        for p in new_pages:
            print(f"  [DRY] {p['url']}")
    else:
        print("[OK] All supplemental URLs already in manifest")
    return len(new_pages)


async def main():
    import argparse
    parser = argparse.ArgumentParser(description="Discover Chatr Wireless URLs")
    parser.add_argument("--skip-bfs", action="store_true")
    parser.add_argument("--supplemental-only", action="store_true")
    parser.add_argument("--visible", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    if not args.supplemental_only and not args.skip_bfs:
        await run_bfs_discovery(headless=not args.visible)
    else:
        print("[SKIP] BFS discovery")
    merge_supplemental_into_manifest(dry_run=args.dry_run)

    print(f"\nNext: uv run python scripts/crawl/crawler_cli.py batch data/crawled_web/{PERSONA}/manifest.json")


if __name__ == "__main__":
    asyncio.run(main())
