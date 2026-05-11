
"""
ingest_urls.py — 一条龙管线：URL → 抓取 → MinerU → ChromaDB → 验证
=====================================================================
用法:
  # 普通 URL 抓取入库:
  uv run scripts/ingest/ingest_urls.py "https://..." --category federal-ircc

  # EE 轮次数据 (JSON 动态加载，特殊处理):
  uv run scripts/ingest/ingest_urls.py --ee-rounds --category federal-ircc

  # 只验证:
  uv run scripts/ingest/ingest_urls.py --verify-only --verify-query "CRS score"
"""
from __future__ import annotations

import argparse
import asyncio
import json
import re
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse

from loguru import logger

# ── Paths ──
PROJECT_ROOT = Path(__file__).parent.parent.parent
CRAWLED_WEB_DIR = PROJECT_ROOT / "data" / "crawled_web"
MINERU_DIR = PROJECT_ROOT / "data" / "mineru_output"


# ═══════════════════════════════════════════════════════════════════
#  Helpers
# ═══════════════════════════════════════════════════════════════════

def url_to_book_id(url: str) -> str:
    """从 URL 推导 book_id (与 batch_mineru.py 的 _unique_short_name 一致)。

    https://www.canada.ca/en/ircc/services/study-canada.html
    → en/ircc/services/study-canada
    """
    parsed = urlparse(url)
    path = parsed.path.strip("/")
    # 去掉 .html/.htm 后缀
    path = re.sub(r"\.(html?|asp|php)$", "", path, flags=re.IGNORECASE)
    # 清理特殊字符
    segments = path.split("/")
    clean = []
    for seg in segments:
        seg = re.sub(r"[^\w\-]", "-", seg).strip("-")
        if seg:
            clean.append(seg)
    return "/".join(clean) if clean else "index"


def url_to_pdf_filename(url: str) -> str:
    """URL → 扁平文件名 (用 -- 替代 /)。"""
    return url_to_book_id(url).replace("/", "--")


def book_id_to_md_path(category: str, book_id: str) -> Path:
    """推算 MinerU 输出的 .md 路径。"""
    last_seg = book_id.rstrip("/").rsplit("/", 1)[-1]
    return MINERU_DIR / category / book_id / last_seg / "auto" / f"{last_seg}.md"


# ═══════════════════════════════════════════════════════════════════
#  EE Rounds 特殊管线: JSON 下载 → 转换 → MinerU → Ingest
#  两个 JSON 各自独立生成 PDF → 独立入库
# ═══════════════════════════════════════════════════════════════════

EE_JSON_URLS = [
    "https://www.canada.ca/content/dam/ircc/documents/json/ee_rounds_123_en.json",
    "https://www.canada.ca/content/dam/ircc/documents/json/ee_rounds_4_en.json",
]
EE_BOOK_IDS = [
    "content/dam/ircc/documents/json/ee_rounds_123_en",
    "content/dam/ircc/documents/json/ee_rounds_4_en",
]


async def run_ee_rounds_pipeline(category: str, collection: str, force: bool = False) -> dict:
    """EE 轮次数据特殊管线: 下载 JSON → 各自转 PDF → MinerU → Ingest。"""
    import httpx

    ircc_dir = CRAWLED_WEB_DIR / category
    json_dir = ircc_dir / "content" / "dam" / "ircc" / "documents" / "json"
    json_dir.mkdir(parents=True, exist_ok=True)

    # Step 0: 下载最新 JSON
    print("\n  Step 0: 下载最新 EE Rounds JSON")
    for url in EE_JSON_URLS:
        fname = url.rsplit("/", 1)[-1]
        out = json_dir / fname
        try:
            async with httpx.AsyncClient(follow_redirects=True, timeout=30) as client:
                resp = await client.get(url)
                resp.raise_for_status()
                out.write_bytes(resp.content)
                logger.success("  [OK] {} ({:.1f} KB)", fname, len(resp.content) / 1024)
        except Exception as e:
            logger.error("  [FAIL] Download {}: {}", url, e)
            return {"book_ids": EE_BOOK_IDS, "status": "download_failed", "error": str(e)}

    # Step 1: JSON → PDF (两个独立 PDF)
    print("\n  Step 1: build_ee_rounds.py (two PDFs)")
    converter = PROJECT_ROOT / "scripts" / "crawl" / "build_ee_rounds.py"
    result = subprocess.run(
        ["uv", "run", "python", str(converter)],
        capture_output=False, text=True, timeout=300,
        cwd=str(PROJECT_ROOT),
    )
    if result.returncode != 0:
        return {"book_ids": EE_BOOK_IDS, "status": "convert_failed"}

    # Step 2 & 3: 每个 book_id 独立 MinerU + Ingest
    results = []
    for book_id in EE_BOOK_IDS:
        pdf_path = ircc_dir / f"{book_id}.pdf"
        if not pdf_path.exists():
            logger.warning("  [SKIP] PDF not found: {}", book_id)
            results.append({"book_id": book_id, "status": "pdf_not_found"})
            continue

        print(f"\n  Step 2: MinerU → Markdown ({book_id.rsplit('/', 1)[-1]})")
        md_path = book_id_to_md_path(category, book_id)
        if force or not md_path.exists() or md_path.stat().st_size < 50:
            ok, md_path = run_mineru(pdf_path, category, book_id)
            if not ok:
                results.append({"book_id": book_id, "status": "mineru_failed"})
                continue
        else:
            logger.info("  [SKIP] MinerU output exists")

        print(f"\n  Step 3: Ingest → ChromaDB ({book_id.rsplit('/', 1)[-1]})")
        ok, nodes = ingest_to_chroma(category, book_id, collection)
        if not ok:
            results.append({"book_id": book_id, "status": "ingest_failed"})
            continue

        results.append({"book_id": book_id, "status": "success", "nodes": nodes})

    # 汇总: 任一成功即视为整体成功
    all_ok = any(r["status"] == "success" for r in results)
    return {"book_ids": EE_BOOK_IDS, "status": "success" if all_ok else "failed", "results": results}

# ═══════════════════════════════════════════════════════════════════
#  Step 1: Crawl URL → PDF
# ═══════════════════════════════════════════════════════════════════

async def crawl_url(url: str, category: str, *, force: bool = False, wait_for_js_ms: int = 0) -> tuple[bool, Path | None]:
    """用 Playwright 把 URL 截取为 PDF。

    PDF 保存在 data/crawled_web/{category}/{relpath}.pdf
    wait_for_js_ms: 额外等待 JS 渲染时间 (动态页面如 rounds-invitations)
    """
    book_id = url_to_book_id(url)
    out_dir = CRAWLED_WEB_DIR / category
    pdf_path = out_dir / f"{book_id}.pdf"

    # 已存在就跳过 (除非 force)
    if not force and pdf_path.exists() and pdf_path.stat().st_size > 1000:
        logger.info("  [SKIP] PDF already exists: {} ({:.1f} KB)",
                     pdf_path.name, pdf_path.stat().st_size / 1024)
        return True, pdf_path

    pdf_path.parent.mkdir(parents=True, exist_ok=True)
    logger.info("  [CRAWL] {} → {}", url[:80], pdf_path)

    try:
        sys.path.insert(0, str(PROJECT_ROOT))
        from engine_v2.crawling.web_crawler_v2 import _save_single_pdf
        result = await _save_single_pdf(url, pdf_path, headless=True)
        if result.success:
            logger.success("  [OK] Saved {:.1f} KB", result.file_size / 1024)
            return True, pdf_path
        else:
            logger.error("  [FAIL] Crawl failed: {}", result.error)
            return False, None
    except Exception as e:
        logger.error("  [FAIL] Crawl exception: {}", e)
        return False, None


# ═══════════════════════════════════════════════════════════════════
#  Step 2: MinerU → Markdown
# ═══════════════════════════════════════════════════════════════════

def run_mineru(pdf_path: Path, category: str, book_id: str) -> tuple[bool, Path | None]:
    """对单个 PDF 执行 MinerU 解析。"""
    out_dir = MINERU_DIR / category / book_id
    md_path = book_id_to_md_path(category, book_id)

    # 已解析就跳过
    if md_path.exists() and md_path.stat().st_size > 50:
        logger.info("  [SKIP] MinerU output exists: {} ({:.1f} KB)",
                     md_path.name, md_path.stat().st_size / 1024)
        return True, md_path

    out_dir.parent.mkdir(parents=True, exist_ok=True)
    logger.info("  [MINERU] {} → {}", pdf_path.name, out_dir)

    cmd = ["uv", "run", "mineru", "-p", str(pdf_path), "-o", str(out_dir), "-b", "pipeline"]
    try:
        result = subprocess.run(cmd, capture_output=False, text=True)
        if result.returncode == 0 and md_path.exists():
            logger.success("  [OK] MinerU done: {:.1f} KB", md_path.stat().st_size / 1024)
            return True, md_path
        else:
            logger.error("  [FAIL] MinerU exit code: {}", result.returncode)
            return False, None
    except Exception as e:
        logger.error("  [FAIL] MinerU exception: {}", e)
        return False, None


# ═══════════════════════════════════════════════════════════════════
#  Step 3: Ingest → ChromaDB (增量 — 只入库指定 book)
# ═══════════════════════════════════════════════════════════════════

_engine_initialized = False


def _ensure_engine_initialized():
    """懒初始化 engine_v2 settings (只跑一次)。"""
    global _engine_initialized
    if not _engine_initialized:
        sys.path.insert(0, str(PROJECT_ROOT))
        from engine_v2.settings import init_settings
        init_settings()
        _engine_initialized = True


def ingest_to_chroma(
    category: str, book_id: str, collection_name: str,
) -> tuple[bool, int]:
    """将单个 book 的 MinerU 输出增量 ingest 到 ChromaDB。

    只处理指定的 book_id，不删旧 collection、不全量重建。
    """
    logger.info("  [INGEST] {}/{} → {}", category, book_id, collection_name)

    try:
        _ensure_engine_initialized()

        from engine_v2.ingestion.pipeline import get_vector_store
        from engine_v2.readers.mineru_reader import MinerUReader
        from engine_v2.ingestion.transformations import BBoxNormalizer
        from llama_index.core.ingestion import IngestionPipeline
        from llama_index.core.settings import Settings

        # 1. 读取 MinerU 输出
        reader = MinerUReader(MINERU_DIR)
        documents = reader.load_data(book_dir_name=book_id, category=category)
        if not documents:
            logger.error("  [FAIL] No documents found for {}/{}", category, book_id)
            return False, 0
        logger.info("  [DOCS] {} documents loaded", len(documents))

        # 2. 增量写入 ChromaDB (不删旧 collection，追加/覆盖)
        vector_store = get_vector_store(collection_name=collection_name)
        pipeline = IngestionPipeline(
            transformations=[
                BBoxNormalizer(),
                Settings.embed_model,
            ],
            vector_store=vector_store,
        )
        nodes = pipeline.run(documents=documents, show_progress=True)
        logger.success("  [OK] Ingest done — {} nodes", len(nodes))
        return True, len(nodes)

    except Exception as e:
        logger.error("  [FAIL] Ingest exception: {}", e)
        import traceback
        traceback.print_exc()
        return False, 0


# ═══════════════════════════════════════════════════════════════════
#  Step 4: Verify → 查询 RAG 确认数据可检索
# ═══════════════════════════════════════════════════════════════════

def verify_rag(query: str, persona: str, api_url: str) -> dict:
    """查询 RAG API 验证数据是否可检索。"""
    import httpx

    logger.info("  [VERIFY] Query: '{}'", query[:60])
    url = f"{api_url}/engine/consulting/query"
    payload = {"persona_slug": persona, "question": query, "top_k": 3}

    try:
        resp = httpx.post(url, json=payload, timeout=120)
        resp.raise_for_status()
        data = resp.json()
        sources = data.get("sources", [])
        answer = data.get("answer", "")

        if sources:
            logger.success("  [OK] {} sources found", len(sources))
            for i, src in enumerate(sources[:3], 1):
                book = src.get("book_id", "?")
                page = src.get("page_number", "?")
                score = src.get("score", 0)
                snippet = src.get("snippet", "")[:80]
                logger.info("    [{}] book={}, page={}, score={:.4f}", i, book, page, score)
                logger.info("        {}", snippet)
        else:
            logger.warning("  [WARN] No sources found!")

        return {
            "query": query,
            "source_count": len(sources),
            "answer_preview": answer[:200],
            "sources": [
                {
                    "book_id": s.get("book_id", ""),
                    "page": s.get("page_number", 0),
                    "score": round(s.get("score", 0), 4),
                    "snippet": s.get("snippet", "")[:200],
                }
                for s in sources[:5]
            ],
        }
    except Exception as e:
        logger.error("  [FAIL] RAG verify failed: {}", e)
        return {"query": query, "error": str(e)}


# ═══════════════════════════════════════════════════════════════════
#  Main: 一条龙
# ═══════════════════════════════════════════════════════════════════

async def run_pipeline(args):
    """执行完整管线。"""
    urls = args.urls or []
    category = args.category
    collection = args.collection
    dry_run = args.dry_run
    verify_only = args.verify_only
    persona = args.persona
    api_url = args.api_url
    ee_rounds = args.ee_rounds
    force = args.force

    # ── 规划 ──
    plan = []
    for url in urls:
        book_id = url_to_book_id(url)
        pdf_path = CRAWLED_WEB_DIR / category / f"{book_id}.pdf"
        md_path = book_id_to_md_path(category, book_id)
        plan.append({
            "url": url,
            "book_id": book_id,
            "pdf_exists": pdf_path.exists(),
            "md_exists": md_path.exists(),
            "pdf_path": str(pdf_path),
            "md_path": str(md_path),
        })

    print("=" * 70)
    print(f"一条龙管线: URL → Crawl → MinerU → ChromaDB → Verify")
    print(f"=" * 70)
    print(f"  Category:   {category}")
    print(f"  Collection: {collection}")
    print(f"  URLs:       {len(urls)}")
    print()
    for i, p in enumerate(plan, 1):
        pdf_tag = "✅" if p["pdf_exists"] else "❌"
        md_tag = "✅" if p["md_exists"] else "❌"
        print(f"  [{i}] {p['url'][:80]}")
        print(f"      book_id: {p['book_id']}")
        print(f"      PDF {pdf_tag}  MD {md_tag}")
    print()

    if dry_run:
        print("  --dry-run mode, exiting.")
        return

    # ── EE Rounds 特殊管线 ──
    if ee_rounds and not verify_only and not dry_run:
        print(f"\n{'─' * 70}")
        print("[EE-ROUNDS] JSON 动态数据特殊管线")
        print(f"{'─' * 70}")
        ee_result = await run_ee_rounds_pipeline(category, collection, force=force)
        if ee_result["status"] == "success":
            for r in ee_result.get("results", []):
                status = "✅" if r["status"] == "success" else "❌"
                nodes = r.get("nodes", "?")
                print(f"  {status} {r['book_id']} ({nodes} nodes)")
        else:
            print(f"  ❌ EE pipeline — {ee_result['status']}")

    if verify_only:
        print("  --verify-only mode, skipping crawl/mineru/ingest.")
    else:
        # ── Step 1-3: 逐个 URL 处理 ──
        results = []
        for i, p in enumerate(plan, 1):
            url = p["url"]
            book_id = p["book_id"]
            print(f"\n{'─' * 70}")
            print(f"[{i}/{len(plan)}] {url[:80]}")
            print(f"{'─' * 70}")

            # Step 1: Crawl
            print(f"\n  Step 1: Crawl → PDF")
            ok, pdf_path = await crawl_url(url, category, force=force, wait_for_js_ms=getattr(args, 'wait_js', 0))
            if not ok or pdf_path is None:
                results.append({"url": url, "book_id": book_id, "status": "crawl_failed"})
                continue

            # Step 2: MinerU
            print(f"\n  Step 2: MinerU → Markdown")
            ok, md_path = run_mineru(pdf_path, category, book_id)
            if not ok:
                results.append({"url": url, "book_id": book_id, "status": "mineru_failed"})
                continue

            # Step 3: Ingest
            print(f"\n  Step 3: Ingest → ChromaDB ({collection})")
            ok, node_count = ingest_to_chroma(category, book_id, collection)
            if not ok:
                results.append({"url": url, "book_id": book_id, "status": "ingest_failed"})
                continue

            results.append({
                "url": url,
                "book_id": book_id,
                "status": "success",
                "nodes": node_count,
                "md_path": str(md_path),
            })

        # ── 小结 ──
        print(f"\n{'═' * 70}")
        print("INGEST SUMMARY")
        print(f"{'═' * 70}")
        success = [r for r in results if r["status"] == "success"]
        failed = [r for r in results if r["status"] != "success"]
        for r in success:
            print(f"  ✅ {r['book_id']} ({r['nodes']} nodes)")
        for r in failed:
            print(f"  ❌ {r['book_id']} — {r['status']}")
        print(f"\n  Success: {len(success)}/{len(results)}")

    # ── Step 4: Verify ──
    verify_queries = args.verify_query or []
    if verify_queries:
        print(f"\n{'═' * 70}")
        print("VERIFY: RAG 检索验证")
        print(f"{'═' * 70}")
        verify_results = []
        for q in verify_queries:
            vr = verify_rag(q, persona, api_url)
            verify_results.append(vr)

        # 统计缺失
        missing = [vr for vr in verify_results if vr.get("source_count", 0) == 0]
        if missing:
            print(f"\n  ⚠️ 以下查询未找到 RAG 数据，建议补充抓取:")
            for m in missing:
                print(f"    - {m['query']}")
        else:
            print(f"\n  ✅ 所有 {len(verify_queries)} 条查询都找到了数据")

    print(f"\n{'═' * 70}")
    print("DONE")
    print(f"{'═' * 70}")


# ═══════════════════════════════════════════════════════════════════
#  CLI
# ═══════════════════════════════════════════════════════════════════

def main():
    p = argparse.ArgumentParser(
        description="一条龙管线: URL → 抓取 → MinerU → ChromaDB → 验证",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument("urls", nargs="*", help="要抓取的 URL 列表")
    p.add_argument("--category", default="federal-ircc", help="数据分类 (default: federal-ircc)")
    p.add_argument("--collection", default="ca_federal", help="ChromaDB collection (default: ca_federal)")
    p.add_argument("--persona", default="live-study-immigration", help="RAG persona slug")
    p.add_argument("--api-url", default="http://localhost:8001", help="Engine API URL")
    p.add_argument("--verify-query", action="append", help="验证查询 (可多次使用)")
    p.add_argument("--verify-only", action="store_true", help="只验证，不抓取/入库")
    p.add_argument("--ee-rounds", action="store_true", help="EE轮次数据 (JSON动态加载特殊处理)")
    p.add_argument("--force", action="store_true", help="强制重新处理 (不跳过已有数据)")
    p.add_argument("--wait-js", type=int, default=0, help="等待 JS 渲染时间(ms)，动态页面用 (如 10000)")
    p.add_argument("--dry-run", action="store_true", help="只显示计划，不执行")
    args = p.parse_args()

    if not args.urls and not args.verify_only and not args.ee_rounds:
        p.error("至少传入一个 URL 或使用 --verify-only")

    asyncio.run(run_pipeline(args))


if __name__ == "__main__":
    main()
