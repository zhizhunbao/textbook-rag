"""Discover FCAC (Financial Consumer Agency of Canada) URLs.

BFS crawl from FCAC service pages to discover banking/finance related pages.
独立 category: federal-fcac，独立 collection: ca_fcac。

Usage:
    uv run python scripts/crawl/discover_fcac.py
    uv run python scripts/crawl/discover_fcac.py --dry-run
    uv run python scripts/crawl/discover_fcac.py --skip-bfs          # supplemental only
    uv run python scripts/crawl/discover_fcac.py --supplemental-only
"""
import asyncio
import json
import sys
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

# ── Config ──
PERSONA = "federal-fcac"
MANIFEST_PATH = Path(__file__).parent.parent.parent / "data" / "crawled_web" / PERSONA / "manifest.json"

# Phase 1: BFS seeds
BFS_SEEDS = [
    # FCAC Banking 主页（索引页，含所有银行相关子链接）
    "https://www.canada.ca/en/financial-consumer-agency/services/banking.html",
    # FCAC Mortgages（房贷相关）
    "https://www.canada.ca/en/financial-consumer-agency/services/mortgages.html",
    # FCAC Loans（贷款相关）
    "https://www.canada.ca/en/financial-consumer-agency/services/loans.html",
]
BFS_DEPTH = 2
BFS_MAX_PAGES = 100

# Phase 1.5: Supplemental URLs — 已确认真实存在的页面
_FCAC = "https://www.canada.ca/en/financial-consumer-agency/services/banking"
SUPPLEMENTAL_URLS = [
    # ── FCAC Banking 子页面（从 banking.html 索引页提取的真实链接） ──
    f"{_FCAC}/choosing-financial-institution.html",
    f"{_FCAC}/opening-bank-account.html",
    f"{_FCAC}/bank-accounts.html",
    f"{_FCAC}/transferring-products-services.html",
    f"{_FCAC}/choosing-products.html",
    f"{_FCAC}/online-banking.html",
    f"{_FCAC}/deposit-insurance.html",
    f"{_FCAC}/atm-fees.html",
    f"{_FCAC}/preauthorized-debit.html",
    f"{_FCAC}/cashing-cheques.html",
    f"{_FCAC}/cashing-government-cheque.html",
    f"{_FCAC}/using-debit.html",
    f"{_FCAC}/right-of-offset.html",
    f"{_FCAC}/overdraft-protection.html",
    f"{_FCAC}/risks-banking-fintech-apps.html",
    f"{_FCAC}/depositing-cheque-with-mobile.html",
    f"{_FCAC}/open-banking.html",
    # ── FCAC 其他金融服务 ──
    "https://www.canada.ca/en/financial-consumer-agency/services/mortgages.html",
    "https://www.canada.ca/en/financial-consumer-agency/services/loans.html",
    "https://www.canada.ca/en/financial-consumer-agency/services/complaints.html",
    # ── FCAC 消费者权益保护 ──
    "https://www.canada.ca/en/financial-consumer-agency/corporate/protecting-financial-consumers.html",
]


def _normalize_url(url: str) -> str:
    parsed = urlparse(url)
    return f"{parsed.scheme}://{parsed.netloc}{parsed.path}".rstrip("/")


# ── Phase 1: BFS ──

async def run_bfs_discovery():
    """Discover FCAC pages via crawl4ai BFS."""
    from engine_v2.crawling.web_crawler_v2 import discover_urls

    print(f"\n{'='*60}")
    print(f"PHASE 1: BFS Discovery ({len(BFS_SEEDS)} seeds)")
    print(f"  PERSONA: {PERSONA}")
    print(f"  MANIFEST: {MANIFEST_PATH}")
    print(f"{'='*60}")

    for i, url in enumerate(BFS_SEEDS):
        name = url.rstrip("/").split("/")[-1].replace(".html", "")
        print(f"\n[{i+1}/{len(BFS_SEEDS)}] {name}")

        # URL filter: 只保留 FCAC 路径下的页面
        def url_filter(u: str) -> bool:
            path = urlparse(u).path
            return path.startswith("/en/financial-consumer-agency/")

        try:
            manifest = await discover_urls(
                url, persona_slug=PERSONA,
                max_depth=BFS_DEPTH, max_pages=BFS_MAX_PAGES,
                url_filter=url_filter,
            )
            print(f"  -> Manifest: {manifest}")
        except Exception as e:
            print(f"  ERROR: {e}")


# ── Phase 1.5: Supplemental merge ──

def merge_supplemental_into_manifest(dry_run: bool = False) -> int:
    """Merge SUPPLEMENTAL_URLS into manifest."""
    if not MANIFEST_PATH.exists():
        # 如果 manifest 不存在，创建一个空的
        MANIFEST_PATH.parent.mkdir(parents=True, exist_ok=True)
        manifest = {
            "seed_urls": [],
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
            filename = path.lstrip("/").rstrip("/").replace(".html", "")
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
        manifest["fcac_supplemental_at"] = datetime.now().isoformat()
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


# ── Main ──

async def main():
    import argparse
    parser = argparse.ArgumentParser(description="Discover FCAC banking URLs")
    parser.add_argument("--skip-bfs", action="store_true", help="Skip BFS phase")
    parser.add_argument("--supplemental-only", action="store_true", help="Only run supplemental merge")
    parser.add_argument("--dry-run", action="store_true", help="Preview only")
    args = parser.parse_args()

    # Phase 1: BFS
    if not args.supplemental_only and not args.skip_bfs:
        await run_bfs_discovery()
    else:
        print("[SKIP] BFS discovery")

    # Phase 1.5: Supplemental
    merge_supplemental_into_manifest(dry_run=args.dry_run)

    print(f"\n{'='*60}")
    print("Discovery complete! Next steps:")
    print(f"{'='*60}")
    print()
    print("  # Step 1: 抓取 PDF")
    print(f"  uv run python scripts/crawl/crawler_cli.py batch data/crawled_web/{PERSONA}/manifest.json")
    print()
    print("  # Step 2: MinerU 解析 + 入库")
    print(f"  # category={PERSONA}, collection=ca_fcac")
    print(f"  uv run python scripts/ingest/ingest_urls.py \\")
    print(f"    --category {PERSONA} --collection ca_fcac --force \\")
    print(f"    <URLs from manifest>")


if __name__ == "__main__":
    asyncio.run(main())
