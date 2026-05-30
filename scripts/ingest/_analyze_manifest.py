"""Generate slim manifest with only the 31 URLs that need crawling."""
import json
import os
from pathlib import Path
from datetime import datetime

BASE_DIR = Path("data/crawled_web/federal-ircc")
UPDATE_DIR = Path("data/crawled_web/federal-ircc-immigrate-update")

m = json.loads(open(UPDATE_DIR / "manifest.json", "r", encoding="utf-8").read())

# The one page that changed (modified 5/27 > crawled 5/07)
CHANGED_URL = "https://www.canada.ca/en/immigration-refugees-citizenship/services/immigrate-canada.html"

need_crawl = []
for p in m["pages"]:
    fn = p["filename"]
    pdf = BASE_DIR / f"{fn}.pdf"
    if not pdf.exists():
        need_crawl.append(p)
    elif p["url"] == CHANGED_URL:
        need_crawl.append(p)

# Write slim manifest
slim = {
    "seed_url": CHANGED_URL,
    "persona_slug": "federal-ircc-immigrate-update",
    "total_urls": len(need_crawl),
    "created_at": datetime.now().isoformat(),
    "note": "Slim manifest: 30 new + 1 changed page",
    "pages": need_crawl,
}

out = UPDATE_DIR / "manifest_slim.json"
out.write_text(json.dumps(slim, indent=2, ensure_ascii=False), encoding="utf-8")

print(f"Slim manifest: {out}")
print(f"Total: {len(need_crawl)} URLs")
print()
for i, p in enumerate(need_crawl, 1):
    tag = "CHANGED" if p["url"] == CHANGED_URL else "NEW"
    short = p["url"].replace("https://www.canada.ca/en/immigration-refugees-citizenship/services/immigrate-canada/", "")
    print(f"  [{i:2d}] [{tag:7s}] {short}")
