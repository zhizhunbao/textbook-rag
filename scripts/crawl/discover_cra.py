"""Discover CRA (Canada Revenue Agency) URLs.

BFS crawl from CRA individual tax & registered plan pages to discover
RRSP, TFSA, HBP, LLP and related tax content.
独立 category: federal-cra，独立 collection: ca_cra。

Usage:
    uv run python scripts/crawl/discover_cra.py
    uv run python scripts/crawl/discover_cra.py --dry-run
    uv run python scripts/crawl/discover_cra.py --skip-bfs          # supplemental only
    uv run python scripts/crawl/discover_cra.py --supplemental-only
"""
import asyncio
import json
import sys
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

# ── Config ──
PERSONA = "federal-cra"
MANIFEST_PATH = Path(__file__).parent.parent.parent / "data" / "crawled_web" / PERSONA / "manifest.json"

# Phase 1: BFS seeds — CRA 主要税务服务枢纽页
BFS_SEEDS = [
    # RRSP 及相关计划总枢纽 (2025 新 URL 结构: rrsps-related-plans)
    "https://www.canada.ca/en/revenue-agency/services/tax/individuals/topics/rrsps-related-plans.html",
    # TFSA 总枢纽
    "https://www.canada.ca/en/revenue-agency/services/tax/individuals/topics/tax-free-savings-account.html",
    # 个人所得税率
    "https://www.canada.ca/en/revenue-agency/services/tax/individuals/frequently-asked-questions-individuals/canadian-income-tax-rates-individuals-current-previous-years.html",
]
BFS_DEPTH = 2
BFS_MAX_PAGES = 100

# Phase 1.5: Supplemental URLs — CRA RRSP 相关子页面（BFS 可能漏掉的 gc-subway 导航页）
_CRA_RRSP = "https://www.canada.ca/en/revenue-agency/services/tax/individuals/topics/rrsps-related-plans"
_CRA_TFSA = "https://www.canada.ca/en/revenue-agency/services/tax/individuals/topics/tax-free-savings-account"
_CRA_FORMS = "https://www.canada.ca/en/revenue-agency/services/forms-publications/forms"

SUPPLEMENTAL_URLS = [
    # ── RRSP 核心页面 ──
    f"{_CRA_RRSP}.html",
    f"{_CRA_RRSP}/registered-retirement-savings-plan-rrsp.html",
    # ── RRSP 存款 (Contributing) ──
    f"{_CRA_RRSP}/contributing-a-rrsp-prpp.html",
    f"{_CRA_RRSP}/contributing-a-rrsp-prpp/contributions-affect-your-rrsp-prpp-deduction-limit.html",
    f"{_CRA_RRSP}/contributing-a-rrsp-prpp/what-happens-you-over-contribute.html",
    f"{_CRA_RRSP}/contributing-a-rrsp-prpp/making-withdrawals.html",
    # ── RRSP 提款 (Withdrawing) ──
    f"{_CRA_RRSP}/withdrawing-funds-a-rrsp.html",
    # ── Spousal / Common-law RRSP ──
    f"{_CRA_RRSP}/setting-a-spousal-common-law-partner-rrsp.html",
    # ── RRSP 71 岁到期选项 ──
    f"{_CRA_RRSP}/options-your-rrsp-when-you-turn-71.html",
    # ── Home Buyers' Plan (HBP) ──
    f"{_CRA_RRSP}/home-buyers-plan-hbp.html",
    f"{_CRA_RRSP}/home-buyers-plan-hbp/participate-home-buyers-plan.html",
    f"{_CRA_RRSP}/home-buyers-plan-hbp/repay-funds-withdrawn-rrsp-under-home-buyers-plan.html",
    # ── Lifelong Learning Plan (LLP) ──
    f"{_CRA_RRSP}/lifelong-learning-plan.html",
    f"{_CRA_RRSP}/lifelong-learning-plan/participate-lifelong-learning-plan.html",
    f"{_CRA_RRSP}/lifelong-learning-plan/repay-funds-withdrawn-rrsp-under-lifelong-learning-plan.html",
    # ── RRIF (Registered Retirement Income Fund) ──
    f"{_CRA_RRSP}/registered-retirement-income-fund-rrif.html",
    # ── RRSP 死亡/反避税规则 ──
    f"{_CRA_RRSP}/death-a-rrsp-annuitant.html",
    f"{_CRA_RRSP}/anti-avoidance-rules.html",
    # ── TFSA 核心页面（已有，但补充完整） ──
    f"{_CRA_TFSA}.html",
    f"{_CRA_TFSA}/opening.html",
    f"{_CRA_TFSA}/contributing.html",
    f"{_CRA_TFSA}/contributing/calculate-room.html",
    f"{_CRA_TFSA}/contributing/overcontribute.html",
    f"{_CRA_TFSA}/withdraw.html",
    f"{_CRA_TFSA}/transfer.html",
    f"{_CRA_TFSA}/death-of-holder.html",
    f"{_CRA_TFSA}/non-resident.html",
    f"{_CRA_TFSA}/what.html",
    f"{_CRA_TFSA}/owing-tax.html",
    f"{_CRA_TFSA}/owing-tax/pay.html",
    # ── 常用表格 ──
    f"{_CRA_FORMS}/t1213.html",           # T1213 减税申请
    f"{_CRA_FORMS}/t1-ovp.html",          # T1-OVP 超额缴税表
    f"{_CRA_FORMS}/t3012a.html",          # T3012A 未扣除额退款
    f"{_CRA_FORMS}/t746.html",            # T746 RRSP 提款计算
]


def _normalize_url(url: str) -> str:
    parsed = urlparse(url)
    return f"{parsed.scheme}://{parsed.netloc}{parsed.path}".rstrip("/")


# ── Phase 1: BFS ──

async def run_bfs_discovery():
    """Discover CRA pages via crawl4ai BFS."""
    from engine_v2.crawling.web_crawler_v2 import discover_urls

    print(f"\n{'='*60}")
    print(f"PHASE 1: BFS Discovery ({len(BFS_SEEDS)} seeds)")
    print(f"  PERSONA: {PERSONA}")
    print(f"  MANIFEST: {MANIFEST_PATH}")
    print(f"{'='*60}")

    for i, url in enumerate(BFS_SEEDS):
        name = url.rstrip("/").split("/")[-1].replace(".html", "")
        print(f"\n[{i+1}/{len(BFS_SEEDS)}] {name}")

        # URL filter: 只保留 CRA 路径下的页面
        def url_filter(u: str) -> bool:
            path = urlparse(u).path
            return path.startswith("/en/revenue-agency/")

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
        manifest["cra_supplemental_at"] = datetime.now().isoformat()
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
    parser = argparse.ArgumentParser(description="Discover CRA tax & registered plan URLs")
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
    print("  # Step 2: MinerU 解析")
    print(f"  uv run python scripts/ingest/batch_mineru.py --category {PERSONA}")
    print()
    print("  # Step 3: 入库 ChromaDB")
    print(f"  uv run python scripts/ingest/batch_ingest.py --category {PERSONA}")


if __name__ == "__main__":
    asyncio.run(main())
