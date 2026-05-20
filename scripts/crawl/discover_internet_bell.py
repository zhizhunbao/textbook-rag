"""Discover Bell Internet plan URLs.
Category: internet-bell, Collection: ca_internet_bell.
"""
import asyncio, json, sys
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

PERSONA = "internet-bell"
MANIFEST_PATH = Path(__file__).resolve().parents[2] / "data" / "crawled_web" / PERSONA / "manifest.json"
BFS_SEEDS = ["https://www.bell.ca/Bell_Internet"]
BFS_DEPTH = 2
BFS_MAX_PAGES = 200
SUPPLEMENTAL_URLS = [
    "https://www.bell.ca/Bell_Internet",
    "https://www.bell.ca/Bell_Internet/Internet_access",
    "https://www.bell.ca/Bell_Internet/Products/Fibe-Internet",
]

def _normalize_url(url):
    p = urlparse(url)
    return f"{p.scheme}://{p.netloc}{p.path}".rstrip("/")

async def run_bfs_discovery(headless=True):
    from engine_v2.crawling.web_crawler_v2 import discover_urls
    for i, url in enumerate(BFS_SEEDS):
        print(f"[{i+1}/{len(BFS_SEEDS)}] {url}")
        def url_filter(u):
            return urlparse(u).netloc in ("www.bell.ca", "bell.ca")
        try:
            await discover_urls(url, persona_slug=PERSONA, max_depth=BFS_DEPTH, max_pages=BFS_MAX_PAGES, headless=headless, url_filter=url_filter)
        except Exception as e:
            print(f"  ERROR: {e}")

def merge_supplemental_into_manifest(dry_run=False):
    if not MANIFEST_PATH.exists():
        MANIFEST_PATH.parent.mkdir(parents=True, exist_ok=True)
        manifest = {"seed_urls": BFS_SEEDS, "persona": PERSONA, "discovered_at": datetime.now().isoformat(), "total_urls": 0, "pages": []}
        MANIFEST_PATH.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
    else:
        manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    existing = {_normalize_url(p["url"]) for p in manifest["pages"]}
    new = [{"url": _normalize_url(u), "filename": urlparse(_normalize_url(u)).path.strip("/") or "index"} for u in SUPPLEMENTAL_URLS if _normalize_url(u) not in existing]
    if new and not dry_run:
        manifest["pages"] += new
        manifest["total_urls"] = len(manifest["pages"])
        MANIFEST_PATH.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"[OK] +{len(new)} URLs (total: {manifest['total_urls']})")
    else:
        print(f"[OK] {len(new)} new URLs" + (" [DRY]" if dry_run else ""))

async def main():
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("--skip-bfs", action="store_true")
    p.add_argument("--supplemental-only", action="store_true")
    p.add_argument("--visible", action="store_true")
    p.add_argument("--dry-run", action="store_true")
    a = p.parse_args()
    if not a.supplemental_only and not a.skip_bfs:
        await run_bfs_discovery(headless=not a.visible)
    merge_supplemental_into_manifest(dry_run=a.dry_run)

if __name__ == "__main__":
    asyncio.run(main())
