"""refresh_immigrate_canada.py — 以 immigrate-canada 为种子，BFS 探索 + 全量更新入库

三阶段:
  Phase 1: BFS 探索 immigrate-canada 子页面 → 独立 manifest
  Phase 2: Playwright 抓取全部 PDF (已有的跳过，--force 全部重抓)
  Phase 3: MinerU 解析 + ChromaDB 入库

用法:
    # 完整三阶段 (推荐过夜跑):
    $env:PYTHONIOENCODING='utf-8'; uv run python scripts/ingest/refresh_immigrate_canada.py

    # 只探索，不抓取不入库:
    $env:PYTHONIOENCODING='utf-8'; uv run python scripts/ingest/refresh_immigrate_canada.py --discover-only

    # 跳过探索，用已有 manifest 重新抓取+入库:
    $env:PYTHONIOENCODING='utf-8'; uv run python scripts/ingest/refresh_immigrate_canada.py --skip-discover

    # 跳过探索+抓取，只重新 MinerU+入库:
    $env:PYTHONIOENCODING='utf-8'; uv run python scripts/ingest/refresh_immigrate_canada.py --skip-discover --skip-crawl

    # 强制全部重新处理 (含已有 PDF):
    $env:PYTHONIOENCODING='utf-8'; uv run python scripts/ingest/refresh_immigrate_canada.py --force

    # dry-run 预览:
    $env:PYTHONIOENCODING='utf-8'; uv run python scripts/ingest/refresh_immigrate_canada.py --dry-run
"""
from __future__ import annotations

import argparse
import asyncio
import json
import sys
import time
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# ── 独立输出目录 ──
PERSONA = "federal-ircc-immigrate-update"
OUTPUT_DIR = PROJECT_ROOT / "data" / "crawled_web"
MANIFEST_DIR = OUTPUT_DIR / PERSONA
MANIFEST_PATH = MANIFEST_DIR / "manifest.json"

# ── ChromaDB/MinerU 仍复用 federal-ircc 的 category ──
INGEST_CATEGORY = "federal-ircc"
COLLECTION = "ca_federal"

# ── 种子 URL ──
SEED_URL = "https://www.canada.ca/en/immigration-refugees-citizenship/services/immigrate-canada.html"

# BFS 参数
BFS_DEPTH = 3
BFS_MAX_PAGES = 200

# ── 补充 URL: BFS 可能漏掉的关键页面 ──
# gc-subway 导航页、storyline 引用页、暂停/关闭项目页
_BASE = "https://www.canada.ca/en/immigration-refugees-citizenship"
SUPPLEMENTAL_URLS = [
    # === EE 核心子页面 (gc-subway 导航) ===
    f"{_BASE}/services/immigrate-canada/express-entry.html",
    f"{_BASE}/services/immigrate-canada/express-entry/works.html",
    f"{_BASE}/services/immigrate-canada/express-entry/who-can-apply.html",
    f"{_BASE}/services/immigrate-canada/express-entry/eligibility/federal-skilled-workers.html",
    f"{_BASE}/services/immigrate-canada/express-entry/eligibility/skilled-trades.html",
    f"{_BASE}/services/immigrate-canada/express-entry/eligibility/canadian-experience-class.html",
    f"{_BASE}/services/immigrate-canada/express-entry/check-score.html",
    f"{_BASE}/services/immigrate-canada/express-entry/check-score/crs-criteria.html",
    f"{_BASE}/services/immigrate-canada/express-entry/rounds-invitations.html",
    f"{_BASE}/services/immigrate-canada/express-entry/rounds-invitations/category-based-selection.html",
    f"{_BASE}/services/immigrate-canada/express-entry/create-profile.html",
    f"{_BASE}/services/immigrate-canada/express-entry/documents.html",
    f"{_BASE}/services/immigrate-canada/express-entry/apply-permanent-residence.html",
    # === AIP 大西洋 ===
    f"{_BASE}/services/immigrate-canada/atlantic-immigration.html",
    f"{_BASE}/services/immigrate-canada/atlantic-immigration/how-to-immigrate.html",
    f"{_BASE}/services/immigrate-canada/atlantic-immigration/hire-immigrant.html",
    # === RCIP/FCIP 社区试点 ===
    f"{_BASE}/services/immigrate-canada/rural-franco-pilots.html",
    f"{_BASE}/services/immigrate-canada/rural-franco-pilots/rural-immigration.html",
    f"{_BASE}/services/immigrate-canada/rural-franco-pilots/rural-immigration/eligibility/proof-funds.html",
    f"{_BASE}/services/immigrate-canada/rural-franco-pilots/rural-immigration/work-permit.html",
    f"{_BASE}/services/immigrate-canada/rural-franco-pilots/rural-immigration/permanent-residence.html",
    f"{_BASE}/services/immigrate-canada/rural-franco-pilots/franco-immigration.html",
    f"{_BASE}/services/immigrate-canada/rural-franco-pilots/franco-immigration/eligibility.html",
    f"{_BASE}/services/immigrate-canada/rural-franco-pilots/franco-immigration/work-permit.html",
    f"{_BASE}/services/immigrate-canada/rural-franco-pilots/franco-immigration/permanent-residence.html",
    f"{_BASE}/services/immigrate-canada/rural-franco-pilots/hire.html",
    # === Caregivers ===
    f"{_BASE}/services/immigrate-canada/caregivers.html",
    f"{_BASE}/services/immigrate-canada/caregivers/home-care-worker-immigration-pilots.html",
    # === PNP 省提名 ===
    f"{_BASE}/services/immigrate-canada/provincial-nominees.html",
    f"{_BASE}/services/immigrate-canada/provincial-nominees/express-entry.html",
    f"{_BASE}/services/immigrate-canada/provincial-nominees/non-express-entry.html",
    # === Family Sponsorship ===
    f"{_BASE}/services/immigrate-canada/family-sponsorship.html",
    f"{_BASE}/services/immigrate-canada/family-sponsorship/spouse-partner-children.html",
    f"{_BASE}/services/immigrate-canada/family-sponsorship/parents-grandparents.html",
    # === 暂停/关闭项目 (截图确认) ===
    f"{_BASE}/services/immigrate-canada/start-visa/about.html",
    f"{_BASE}/services/immigrate-canada/self-employed.html",
    f"{_BASE}/services/immigrate-canada/tr-pr-pathway.html",
    f"{_BASE}/services/immigrate-canada/gta-construction-workers.html",
    f"{_BASE}/services/immigrate-canada/humanitarian-colombia-haiti-venezuela.html",
    f"{_BASE}/services/immigrate-canada/ukraine-measures.html",  # Ukrainian nationals [Closed]
    f"{_BASE}/services/sudan2023.html",
    f"{_BASE}/services/sudan2023/pr-pathway.html",
    f"{_BASE}/services/refugees/economic-mobility-pathways-pilot.html",  # EMPP [Closed]
    f"{_BASE}/services/refugees/economic-mobility-pathways-pilot/immigrate.html",
    f"{_BASE}/services/refugees/economic-mobility-pathways-pilot/hire.html",
    # === storyline 引用的非 immigrate-canada 路径 ===
    f"{_BASE}/corporate/publications-manuals/annual-report-parliament-immigration-2025.html",
    f"{_BASE}/corporate/transparency/consultations/2026-consultation-express-entry-reforms.html",
    f"{_BASE}/news/2025/01/canada-launches-rural-and-francophone-community-immigration-pilots.html",
    f"{_BASE}/services/application/application-forms-guides/guide-0154-atlantic-immigration-program.html",
    f"{_BASE}/services/application/application-forms-guides/guide-5466-atlantic-immigration-pilot-program-atlantic-intermediate-skilled-program.html",
    f"{_BASE}/services/application/application-forms-guides/application-rural-northern-immigration.html",
    # === Medical doctors ===
    f"{_BASE}/services/immigrate-canada/medical-doctors.html",
    # === Special programs ===
    f"{_BASE}/services/immigrate-canada/hong-kong-residents-permanent-residence.html",
    f"{_BASE}/services/immigrate-canada/inadmissibility/trp-state-care.html",
]


# ══════════════════════════════════════════════════════════════════
#  Phase 1: BFS Discovery
# ══════════════════════════════════════════════════════════════════

async def phase1_discover(*, dry_run: bool = False) -> Path:
    """BFS 从 immigrate-canada 开始探索，输出独立 manifest。"""
    from engine_v2.crawling.web_crawler_v2 import discover_urls

    print("\n" + "=" * 70)
    print("PHASE 1: BFS Discovery")
    print(f"  Seed:      {SEED_URL}")
    print(f"  Depth:     {BFS_DEPTH}")
    print(f"  Max pages: {BFS_MAX_PAGES}")
    print(f"  Output:    {MANIFEST_DIR}/")
    print("=" * 70)

    if dry_run:
        print("  [DRY RUN] Would run BFS discovery")
        return MANIFEST_PATH

    # 清除旧 manifest，避免累积
    if MANIFEST_PATH.exists():
        MANIFEST_PATH.unlink()
        print("  [CLEAN] Deleted old manifest")

    # BFS 探索 — url_filter 限制在 /immigrate-canada 范围内
    SCOPE_PREFIX = "/en/immigration-refugees-citizenship/services/immigrate-canada"

    def _immigrate_filter(url: str) -> bool:
        from urllib.parse import urlparse
        path = urlparse(url).path
        return path.startswith(SCOPE_PREFIX)

    manifest_path = await discover_urls(
        seed_url=SEED_URL,
        persona_slug=PERSONA,
        max_depth=BFS_DEPTH,
        max_pages=BFS_MAX_PAGES,
        headless=True,
        output_dir=OUTPUT_DIR,
        url_filter=_immigrate_filter,
    )

    # 合并 supplemental URLs
    print(f"\n  Merging {len(SUPPLEMENTAL_URLS)} supplemental URLs...")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    existing_urls = set()
    for p in manifest["pages"]:
        existing_urls.add(p["url"].rstrip("/").replace(".html", ""))

    from engine_v2.crawling.web_crawler_v2 import _url_to_relpath, _normalize_url
    added = 0
    for url in SUPPLEMENTAL_URLS:
        norm = _normalize_url(url)
        key = norm.rstrip("/").replace(".html", "")
        if key not in existing_urls:
            existing_urls.add(key)
            relpath = _url_to_relpath(norm)
            manifest["pages"].append({"url": norm, "filename": relpath})
            added += 1

    manifest["total_urls"] = len(manifest["pages"])
    manifest["supplemental_added"] = added
    manifest["refreshed_at"] = datetime.now().isoformat()
    manifest_path.write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    print(f"  [OK] +{added} supplemental, total={manifest['total_urls']} URLs")
    print(f"  Manifest: {manifest_path}")
    return manifest_path


# ══════════════════════════════════════════════════════════════════
#  Phase 2: Crawl → PDF
# ══════════════════════════════════════════════════════════════════

async def phase2_crawl(manifest_path: Path, *, force: bool = False, dry_run: bool = False):
    """从 manifest 批量抓取 PDF。"""
    from engine_v2.crawling.web_crawler_v2 import save_pdfs_from_manifest

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    total = len(manifest.get("pages", []))

    print("\n" + "=" * 70)
    print("PHASE 2: Crawl -> PDF")
    print(f"  Manifest: {manifest_path}")
    print(f"  Pages:    {total}")
    print(f"  Force:    {force}")
    print("=" * 70)

    if dry_run:
        # 统计已有 PDF
        out_dir = manifest_path.parent
        existing = 0
        for page in manifest["pages"]:
            pdf = out_dir / f"{page['filename']}.pdf"
            if pdf.exists():
                existing += 1
        print(f"  [DRY RUN] Existing PDFs: {existing}/{total}")
        print(f"  [DRY RUN] Would crawl: {total - existing if not force else total}")
        return

    if force:
        # 删除所有已有 PDF 强制重抓
        out_dir = manifest_path.parent
        deleted = 0
        for page in manifest["pages"]:
            pdf = out_dir / f"{page['filename']}.pdf"
            if pdf.exists():
                pdf.unlink()
                deleted += 1
        print(f"  [FORCE] Deleted {deleted} existing PDFs")

    results = await save_pdfs_from_manifest(
        manifest_path=manifest_path,
        headless=True,
        delay_between=3.0,
    )

    saved = [r for r in results if r.success]
    failed = [r for r in results if not r.success]
    total_mb = sum(r.file_size for r in saved) / (1024 * 1024)

    print(f"\n  [OK] Saved: {len(saved)}/{len(results)} ({total_mb:.1f} MB)")
    if failed:
        print(f"  [WARN] Failed: {len(failed)}")
        for r in failed[:10]:
            print(f"    x {r.filename}: {r.error}")

    return results


# ══════════════════════════════════════════════════════════════════
#  Phase 3: MinerU + ChromaDB Ingest
# ══════════════════════════════════════════════════════════════════

async def phase3_ingest(manifest_path: Path, *, force: bool = False, dry_run: bool = False):
    """从 manifest 的 PDF 做 MinerU → ChromaDB 入库。"""
    from scripts.ingest.ingest_urls import (
        run_mineru, ingest_to_chroma, url_to_book_id,
    )

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    out_dir = manifest_path.parent
    pages = manifest.get("pages", [])

    print("\n" + "=" * 70)
    print("PHASE 3: MinerU + ChromaDB Ingest")
    print(f"  Category:   {INGEST_CATEGORY}")
    print(f"  Collection: {COLLECTION}")
    print(f"  Pages:      {len(pages)}")
    print(f"  Force:      {force}")
    print("=" * 70)

    if dry_run:
        has_pdf = sum(1 for p in pages if (out_dir / f"{p['filename']}.pdf").exists())
        print(f"  [DRY RUN] PDFs available: {has_pdf}/{len(pages)}")
        return

    results = []
    for i, page in enumerate(pages, 1):
        url = page["url"]
        filename = page["filename"]
        book_id = url_to_book_id(url)
        pdf_path = out_dir / f"{filename}.pdf"

        if not pdf_path.exists():
            # 也检查 federal-ircc 目录
            alt_pdf = OUTPUT_DIR / "federal-ircc" / f"{book_id}.pdf"
            if alt_pdf.exists():
                pdf_path = alt_pdf
            else:
                continue

        print(f"\n  [{i}/{len(pages)}] {url[55:80]}")

        # MinerU
        ok, md_path = run_mineru(pdf_path, INGEST_CATEGORY, book_id, force=force)
        if not ok:
            results.append({"book_id": book_id, "status": "mineru_failed"})
            continue

        # ChromaDB
        ok, nodes = ingest_to_chroma(INGEST_CATEGORY, book_id, COLLECTION)
        if not ok:
            results.append({"book_id": book_id, "status": "ingest_failed"})
            continue

        results.append({"book_id": book_id, "status": "success", "nodes": nodes})

    # Summary
    success = [r for r in results if r["status"] == "success"]
    failed = [r for r in results if r["status"] != "success"]
    total_nodes = sum(r.get("nodes", 0) for r in success)

    print(f"\n{'=' * 70}")
    print("INGEST SUMMARY")
    print(f"{'=' * 70}")
    print(f"  Success: {len(success)}/{len(results)}")
    print(f"  Total nodes: {total_nodes}")
    if failed:
        print(f"  Failed: {len(failed)}")
        for r in failed[:10]:
            print(f"    x {r['book_id']}: {r['status']}")


# ══════════════════════════════════════════════════════════════════
#  Main
# ══════════════════════════════════════════════════════════════════

async def run(args):
    t0 = time.time()

    # Phase 1: Discover
    if not args.skip_discover:
        manifest_path = await phase1_discover(dry_run=args.dry_run)
        if args.discover_only:
            print(f"\n  --discover-only, exiting.")
            return
    else:
        manifest_path = MANIFEST_PATH
        if not manifest_path.exists():
            print(f"[ERROR] Manifest not found: {manifest_path}")
            print(f"  Run without --skip-discover first.")
            return

    # Phase 2: Crawl
    if not args.skip_crawl:
        await phase2_crawl(manifest_path, force=args.force, dry_run=args.dry_run)

    # Phase 3: Ingest
    if not args.skip_ingest:
        await phase3_ingest(manifest_path, force=args.force, dry_run=args.dry_run)

    elapsed = time.time() - t0
    print(f"\n{'=' * 70}")
    print(f"ALL DONE ({elapsed / 60:.1f} min)")
    print(f"{'=' * 70}")


def main():
    p = argparse.ArgumentParser(
        description="Refresh immigrate-canada: BFS discover + crawl + ingest",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument("--force", action="store_true", help="Force re-process everything")
    p.add_argument("--dry-run", action="store_true", help="Preview only")
    p.add_argument("--discover-only", action="store_true", help="Only BFS discover, don't crawl/ingest")
    p.add_argument("--skip-discover", action="store_true", help="Skip BFS, use existing manifest")
    p.add_argument("--skip-crawl", action="store_true", help="Skip crawl, use existing PDFs")
    p.add_argument("--skip-ingest", action="store_true", help="Skip MinerU + ChromaDB")
    args = p.parse_args()

    from engine_v2.settings import init_settings
    init_settings()

    asyncio.run(run(args))


if __name__ == "__main__":
    main()
