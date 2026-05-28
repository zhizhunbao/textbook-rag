"""Discover ESDC (Employment and Social Development Canada) URLs.

ESDC is Canada's largest federal department, managing:
  - EI (Employment Insurance) — regular, sickness, maternity, parental, fishing, etc.
  - CPP (Canada Pension Plan) — retirement, disability, survivor, death benefits
  - OAS (Old Age Security) — OAS pension, GIS, Allowance, Allowance for Survivor
  - SIN (Social Insurance Number) — application, replacement, update
  - RESP / CESG / CLB — education savings programs
  - Student Financial Aid — Canada Student Loans, grants
  - Labour Standards — federal labour code, workplace safety, hours, wages
  - Accessibility — Accessible Canada Act
  - Homelessness — Reaching Home strategy
  - Service Canada — service centres, passport services (shared with IRCC)

BFS crawl + supplemental URL merge for comprehensive coverage.

Usage:
    uv run python scripts/crawl/discover_esdc.py
    uv run python scripts/crawl/discover_esdc.py --dry-run
    uv run python scripts/crawl/discover_esdc.py --skip-bfs
    uv run python scripts/crawl/discover_esdc.py --supplemental-only
    uv run python scripts/crawl/discover_esdc.py --skip-news
"""
import asyncio
import json
import sys
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

# ── Config ──
PERSONA = "federal-esdc"
MANIFEST_PATH = Path(__file__).parent.parent.parent / "data" / "crawled_web" / PERSONA / "manifest.json"

# ════════════════════════════════════════════════════════════════════════════════
# Phase 1: BFS seeds — ESDC 各主要服务枢纽页
# ════════════════════════════════════════════════════════════════════════════════
BFS_SEEDS = [
    # ── EI 就业保险 ──
    "https://www.canada.ca/en/services/benefits/ei.html",
    # ── CPP 加拿大养老金 ──
    "https://www.canada.ca/en/services/benefits/publicpensions/cpp.html",
    # ── OAS 老年保障金 ──
    "https://www.canada.ca/en/services/benefits/publicpensions/cpp/old-age-security.html",
    # ── SIN 社会保险号 ──
    "https://www.canada.ca/en/employment-social-development/services/sin.html",
    # ── 教育储蓄 (RESP, CESG, CLB) ──
    "https://www.canada.ca/en/services/benefits/education/education-savings.html",
    # ── 学生贷款和助学金 ──
    "https://www.canada.ca/en/services/benefits/education/student-aid.html",
    # ── 联邦劳动标准 ──
    "https://www.canada.ca/en/services/jobs/workplace/federal-labour-standards.html",
    # ── 工作场所健康与安全 ──
    "https://www.canada.ca/en/services/jobs/workplace/health-safety.html",
    # ── 无障碍 (Accessible Canada Act) ──
    "https://www.canada.ca/en/employment-social-development/programs/accessible-canada.html",
    # ── 住房和无家可归 ──
    "https://www.canada.ca/en/employment-social-development/programs/homelessness.html",
    # ── ESDC 机构总页面 ──
    "https://www.canada.ca/en/employment-social-development.html",
    # ── Service Canada ──
    "https://www.canada.ca/en/employment-social-development/corporate/portfolio/service-canada.html",
]
BFS_DEPTH = 3
BFS_MAX_PAGES = 150


# ════════════════════════════════════════════════════════════════════════════════
# Phase 1.5: Supplemental URLs — BFS 可能漏掉的关键子页面
# ════════════════════════════════════════════════════════════════════════════════

# ── 常用基础路径 ──
_ESDC = "https://www.canada.ca/en/employment-social-development"
_BENEFITS = "https://www.canada.ca/en/services/benefits"
_JOBS = "https://www.canada.ca/en/services/jobs"
_CRA_RESP = "https://www.canada.ca/en/revenue-agency/services/tax/individuals/topics/registered-education-savings-plans-resps"
_SERVICE_CA = "https://www.canada.ca/en/employment-social-development/corporate/portfolio/service-canada"

SUPPLEMENTAL_URLS = [
    # ══════════════════════════════════════════════════════════════════════
    # EI (Employment Insurance / 就业保险) — 子页面
    # ══════════════════════════════════════════════════════════════════════
    f"{_BENEFITS}/ei.html",
    f"{_BENEFITS}/ei/eligibility.html",
    f"{_BENEFITS}/ei/ei-regular-benefit.html",
    f"{_BENEFITS}/ei/ei-regular-benefit/apply.html",
    f"{_BENEFITS}/ei/ei-regular-benefit/while-receiving.html",
    f"{_BENEFITS}/ei/ei-sickness.html",
    f"{_BENEFITS}/ei/ei-sickness/apply.html",
    f"{_BENEFITS}/ei/ei-maternity-parental.html",
    f"{_BENEFITS}/ei/ei-maternity-parental/apply.html",
    f"{_BENEFITS}/ei/ei-maternity-parental/eligibility.html",
    f"{_BENEFITS}/ei/ei-compassionate.html",
    f"{_BENEFITS}/ei/ei-family-supplement.html",
    f"{_BENEFITS}/ei/ei-fishing.html",
    f"{_BENEFITS}/ei/ei-self-employed-workers.html",
    f"{_BENEFITS}/ei/ei-internet-reporting.html",
    f"{_BENEFITS}/ei/ei-reconsideration.html",
    f"{_BENEFITS}/ei/cerb-application.html",
    f"{_BENEFITS}/ei/ei-employers.html",
    f"{_BENEFITS}/ei/ei-employers/responsibilities-employers.html",
    f"{_BENEFITS}/ei/ei-employers/roe.html",

    # ══════════════════════════════════════════════════════════════════════
    # CPP (Canada Pension Plan / 加拿大养老金计划) — 子页面
    # ══════════════════════════════════════════════════════════════════════
    f"{_BENEFITS}/publicpensions/cpp.html",
    f"{_BENEFITS}/publicpensions/cpp/retirement-pension.html",
    f"{_BENEFITS}/publicpensions/cpp/retirement-pension/apply.html",
    f"{_BENEFITS}/publicpensions/cpp/retirement-pension/eligibility.html",
    f"{_BENEFITS}/publicpensions/cpp/cpp-disability-benefit.html",
    f"{_BENEFITS}/publicpensions/cpp/cpp-disability-benefit/apply.html",
    f"{_BENEFITS}/publicpensions/cpp/cpp-survivor-pension.html",
    f"{_BENEFITS}/publicpensions/cpp/cpp-death-benefit.html",
    f"{_BENEFITS}/publicpensions/cpp/cpp-childrens-benefit.html",
    f"{_BENEFITS}/publicpensions/cpp/contributions.html",
    f"{_BENEFITS}/publicpensions/cpp/cpp-post-retirement-disability-benefit.html",
    f"{_BENEFITS}/publicpensions/cpp/statement-contributions.html",
    f"{_BENEFITS}/publicpensions/cpp/child-rearing-provision.html",
    f"{_BENEFITS}/publicpensions/cpp/credit-splitting.html",
    f"{_BENEFITS}/publicpensions/cpp/share-cpp-retirement-pensions.html",

    # ══════════════════════════════════════════════════════════════════════
    # OAS (Old Age Security / 老年保障金) — 子页面
    # ══════════════════════════════════════════════════════════════════════
    f"{_BENEFITS}/publicpensions/cpp/old-age-security.html",
    f"{_BENEFITS}/publicpensions/cpp/old-age-security/eligibility.html",
    f"{_BENEFITS}/publicpensions/cpp/old-age-security/benefit-amount.html",
    f"{_BENEFITS}/publicpensions/cpp/old-age-security/recovery-tax.html",
    f"{_BENEFITS}/publicpensions/cpp/old-age-security/guaranteed-income-supplement.html",
    f"{_BENEFITS}/publicpensions/cpp/old-age-security/guaranteed-income-supplement/apply.html",
    f"{_BENEFITS}/publicpensions/cpp/old-age-security/guaranteed-income-supplement/eligibility.html",
    f"{_BENEFITS}/publicpensions/cpp/old-age-security/guaranteed-income-supplement/benefit-amount.html",
    f"{_BENEFITS}/publicpensions/cpp/old-age-security/allowance/eligibility.html",
    f"{_BENEFITS}/publicpensions/cpp/old-age-security/allowance-survivor/eligibility.html",

    # ══════════════════════════════════════════════════════════════════════
    # SIN (Social Insurance Number / 社会保险号) — 子页面
    # ══════════════════════════════════════════════════════════════════════
    f"{_ESDC}/services/sin.html",
    f"{_ESDC}/services/sin/apply.html",
    f"{_ESDC}/services/sin/reports/statistics.html",
    f"{_ESDC}/services/sin/protection.html",

    # ══════════════════════════════════════════════════════════════════════
    # 教育储蓄 (RESP, CESG, CLB) — ESDC + CRA 子页面
    # ══════════════════════════════════════════════════════════════════════
    f"{_BENEFITS}/education/education-savings.html",
    f"{_ESDC}/services/student-financial-aid/education-savings/resp.html",
    f"{_ESDC}/services/student-financial-aid/education-savings/cesg.html",
    f"{_ESDC}/services/student-financial-aid/education-savings/clb.html",
    # CRA 侧 RESP 子页面（含具体规则）
    f"{_CRA_RESP}/canada-education-savings-programs-cesp/canada-education-savings-grant-cesg.html",
    f"{_CRA_RESP}/canada-education-savings-programs-cesp/canada-learning-bond.html",
    f"{_CRA_RESP}/canada-education-savings-programs-cesp.html",
    f"{_CRA_RESP}/resp-works.html",
    f"{_CRA_RESP}/resp-contributions.html",
    f"{_CRA_RESP}/payments-resp.html",

    # ══════════════════════════════════════════════════════════════════════
    # Student Aid / 学生贷款和助学金 — 子页面
    # ══════════════════════════════════════════════════════════════════════
    f"{_BENEFITS}/education/student-aid.html",
    f"{_BENEFITS}/education/student-aid/grants-loans.html",
    f"{_BENEFITS}/education/student-aid/grants-loans/repay-student-loan.html",
    f"{_BENEFITS}/education/student-aid/grants-loans/apply.html",

    # ══════════════════════════════════════════════════════════════════════
    # 联邦劳动标准 (Federal Labour Standards)
    # ══════════════════════════════════════════════════════════════════════
    f"{_JOBS}/workplace/federal-labour-standards.html",
    f"{_JOBS}/workplace/federal-labour-standards/hours.html",
    f"{_JOBS}/workplace/federal-labour-standards/leaves.html",
    f"{_JOBS}/workplace/federal-labour-standards/vacations.html",
    f"{_JOBS}/workplace/federal-labour-standards/pay.html",
    f"{_JOBS}/workplace/federal-labour-standards/termination.html",
    f"{_JOBS}/workplace/federal-labour-standards/complaint.html",
    f"{_JOBS}/workplace/federal-labour-standards/wages.html",

    # ══════════════════════════════════════════════════════════════════════
    # 工作场所健康与安全 (Workplace Health & Safety)
    # ══════════════════════════════════════════════════════════════════════
    f"{_JOBS}/workplace/health-safety.html",
    f"{_JOBS}/workplace/health-safety/committees.html",
    f"{_JOBS}/workplace/health-safety/harassment.html",
    f"{_JOBS}/workplace/health-safety/reporting.html",

    # ══════════════════════════════════════════════════════════════════════
    # 无障碍 (Accessible Canada Act)
    # ══════════════════════════════════════════════════════════════════════
    f"{_ESDC}/programs/accessible-canada.html",
    f"{_ESDC}/programs/accessible-canada/act-summary.html",
    f"{_ESDC}/programs/accessible-canada/regulations-summary.html",

    # ══════════════════════════════════════════════════════════════════════
    # 住房与无家可归 (Homelessness / Reaching Home)
    # ══════════════════════════════════════════════════════════════════════
    f"{_ESDC}/programs/homelessness.html",
    f"{_ESDC}/programs/homelessness/resources.html",
    f"{_ESDC}/programs/homelessness/directives.html",

    # ══════════════════════════════════════════════════════════════════════
    # Service Canada — 服务中心、护照等
    # ══════════════════════════════════════════════════════════════════════
    f"{_SERVICE_CA}.html",
    f"{_SERVICE_CA}/overview.html",

    # ══════════════════════════════════════════════════════════════════════
    # 其他 ESDC benefits — 残障 / 家庭
    # ══════════════════════════════════════════════════════════════════════
    f"{_BENEFITS}/disability.html",
    f"{_BENEFITS}/disability/savings.html",
    f"{_BENEFITS}/family.html",
]


def _normalize_url(url: str) -> str:
    parsed = urlparse(url)
    return f"{parsed.scheme}://{parsed.netloc}{parsed.path}".rstrip("/")


# ════════════════════════════════════════════════════════════════════════════════
# Phase 1: BFS Discovery
# ════════════════════════════════════════════════════════════════════════════════

async def run_bfs_discovery():
    """Discover ESDC pages via crawl4ai BFS."""
    from engine_v2.crawling.web_crawler_v2 import discover_urls

    print(f"\n{'='*60}")
    print(f"PHASE 1: BFS Discovery ({len(BFS_SEEDS)} seeds)")
    print(f"  PERSONA: {PERSONA}")
    print(f"  MANIFEST: {MANIFEST_PATH}")
    print(f"{'='*60}")

    for i, url in enumerate(BFS_SEEDS):
        name = url.rstrip("/").split("/")[-1].replace(".html", "")
        print(f"\n[{i+1}/{len(BFS_SEEDS)}] {name}")

        # URL filter: 保留 ESDC 相关路径
        def url_filter(u: str) -> bool:
            path = urlparse(u).path
            return (
                # ESDC 部门页面
                path.startswith("/en/employment-social-development/")
                # Benefits 大类（EI、CPP、OAS、education 等）
                or path.startswith("/en/services/benefits/")
                # Jobs/workplace 大类（劳动标准、健康安全等）
                or path.startswith("/en/services/jobs/workplace/")
                # CRA 的 RESP 相关页面
                or (
                    path.startswith("/en/revenue-agency/")
                    and "registered-education-savings-plans" in path
                )
            )

        try:
            manifest = await discover_urls(
                url, persona_slug=PERSONA,
                max_depth=BFS_DEPTH, max_pages=BFS_MAX_PAGES,
                url_filter=url_filter,
            )
            print(f"  -> Manifest: {manifest}")
        except Exception as e:
            print(f"  ERROR: {e}")


# ════════════════════════════════════════════════════════════════════════════════
# Phase 1.5: Supplemental merge
# ════════════════════════════════════════════════════════════════════════════════

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
        manifest["esdc_supplemental_at"] = datetime.now().isoformat()
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


# ════════════════════════════════════════════════════════════════════════════════
# Phase 2: News Discovery
# ════════════════════════════════════════════════════════════════════════════════

NEWS_SEARCH_URL = "https://www.canada.ca/en/news/advanced-news-search/news-results.html"
# ESDC has multiple department identifiers in the news search
NEWS_DEPT = "departmentofemploymentandsocialdevelopment"
NEWS_TYPES = ["newsreleases", "backgrounders", "statements"]
NEWS_PER_PAGE = 10
NEWS_YEAR_MIN = 2024


async def discover_news_urls(year_min: int = NEWS_YEAR_MIN) -> list[dict]:
    """Paginate through GC Advanced News Search to collect ESDC news URLs."""
    from playwright.async_api import async_playwright

    all_urls: list[dict] = []
    seen: set[str] = set()

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()

        for news_type in NEWS_TYPES:
            start_date = f"{year_min}-01-01"
            idx = 0
            empty_pages = 0

            print(f"\n--- {news_type} ---")

            while empty_pages < 2:
                url = (f"{NEWS_SEARCH_URL}?typ={news_type}"
                       f"&dprtmnt={NEWS_DEPT}&start={start_date}&end=&idx={idx}")
                try:
                    await page.goto(url, wait_until="networkidle", timeout=30000)
                    await page.wait_for_timeout(1500)
                except Exception as e:
                    print(f"  [ERROR] idx={idx}: {e}")
                    break

                links = await page.eval_on_selector_all(
                    'a[href*="/employment-social-development/news/"]',
                    """elements => elements.map(el => ({
                        url: el.href,
                        text: el.textContent.trim().substring(0, 150)
                    }))"""
                )

                new_count = 0
                for link in links:
                    url_clean = link["url"].split("?")[0].split("#")[0]
                    if url_clean.endswith("/news.html") or url_clean.endswith("/archives.html"):
                        continue
                    if url_clean not in seen:
                        seen.add(url_clean)
                        all_urls.append({"url": url_clean, "text": link["text"]})
                        new_count += 1

                page_num = idx // NEWS_PER_PAGE + 1
                print(f"  Page {page_num} (idx={idx}): +{new_count} new (total: {len(all_urls)})")

                if new_count == 0:
                    empty_pages += 1
                else:
                    empty_pages = 0

                idx += NEWS_PER_PAGE

        await browser.close()

    print(f"\nTotal unique news URLs: {len(all_urls)}")
    return all_urls


def merge_news_into_manifest(news_urls: list[dict], dry_run: bool = False) -> int:
    """Merge news URLs into manifest, prepending for priority crawling."""
    if not MANIFEST_PATH.exists():
        print(f"[ERROR] Manifest not found: {MANIFEST_PATH}")
        return 0

    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    existing_urls = {p["url"] for p in manifest["pages"]}

    new_pages = []
    for item in news_urls:
        if item["url"] not in existing_urls:
            path = urlparse(item["url"]).path
            filename = path.lstrip("/").rstrip("/").replace(".html", "")
            new_pages.append({"url": item["url"], "filename": filename})

    print(f"\n{'='*60}")
    print(f"News URLs discovered: {len(news_urls)}")
    print(f"Already in manifest:  {len(news_urls) - len(new_pages)}")
    print(f"New to add:           {len(new_pages)}")
    print(f"{'='*60}")

    if new_pages and not dry_run:
        manifest["pages"] = new_pages + manifest["pages"]
        manifest["total_urls"] = len(manifest["pages"])
        manifest["news_updated_at"] = datetime.now().isoformat()
        MANIFEST_PATH.write_text(
            json.dumps(manifest, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        print(f"[OK] Prepended {len(new_pages)} news URLs (total: {manifest['total_urls']})")
    elif dry_run:
        print("[DRY RUN] Would add:")
        for p in new_pages[:20]:
            print(f"  {p['url']}")
        if len(new_pages) > 20:
            print(f"  ... and {len(new_pages) - 20} more")

    return len(new_pages)


# ════════════════════════════════════════════════════════════════════════════════
# Main
# ════════════════════════════════════════════════════════════════════════════════

async def main():
    import argparse
    parser = argparse.ArgumentParser(
        description="Discover ESDC URLs (EI, CPP, OAS, SIN, RESP, Labour, etc.)"
    )
    parser.add_argument("--skip-bfs", action="store_true", help="Skip BFS phase")
    parser.add_argument("--skip-news", action="store_true", help="Skip news phase")
    parser.add_argument("--skip-supplemental", action="store_true", help="Skip supplemental phase")
    parser.add_argument("--supplemental-only", action="store_true", help="Only run supplemental merge")
    parser.add_argument("--news-year-min", type=int, default=NEWS_YEAR_MIN, help="News start year")
    parser.add_argument("--dry-run", action="store_true", help="Preview only")
    args = parser.parse_args()

    # Phase 1: BFS
    if not args.supplemental_only:
        if not args.skip_bfs:
            await run_bfs_discovery()
        else:
            print("[SKIP] BFS discovery")

    # Phase 1.5: Supplemental
    if not args.skip_supplemental:
        merge_supplemental_into_manifest(dry_run=args.dry_run)
    else:
        print("[SKIP] Supplemental merge")

    # Phase 2: News
    if not args.supplemental_only:
        if not args.skip_news:
            print(f"\n{'='*60}")
            print(f"PHASE 2: News Discovery (>= {args.news_year_min})")
            print(f"{'='*60}")
            news = await discover_news_urls(year_min=args.news_year_min)
            merge_news_into_manifest(news, dry_run=args.dry_run)
        else:
            print("[SKIP] News discovery")

    # ── Summary & next steps ──
    if MANIFEST_PATH.exists():
        manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
        total = manifest.get("total_urls", 0)
    else:
        total = "?"

    print(f"\n{'='*60}")
    print(f"Discovery complete! Total URLs: {total}")
    print(f"{'='*60}")
    print()
    print("  # Step 1: Save PDFs")
    print(f"  uv run python scripts/crawl/crawler_cli.py batch data/crawled_web/{PERSONA}/manifest.json")
    print()
    print("  # Step 2: MinerU parse")
    print(f"  uv run python scripts/ingest/batch_mineru.py --category {PERSONA}")
    print()
    print("  # Step 3: Ingest to ChromaDB")
    print(f"  uv run python scripts/ingest/batch_ingest_vectors.py --category {PERSONA}")


if __name__ == "__main__":
    asyncio.run(main())
