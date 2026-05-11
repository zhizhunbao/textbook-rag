"""
diagnose_rag_quality.py — RAG 检索质量诊断 & 优化工具
=====================================================
三层诊断:
  1. ChromaDB 层: 检查 collection 状态、book_id 覆盖、chunk 数量
  2. 向量检索层: 直接查 ChromaDB 对比 query 命中率
  3. Engine API 层: 通过 /engine/consulting/query 测试最终检索效果

所有执行过程输出到 --output 日志文件 (默认 rag_report.log)。

用法:
  uv run python scripts/diag/diagnose_rag_quality.py
  uv run python scripts/diag/diagnose_rag_quality.py --collection ca_federal
  uv run python scripts/diag/diagnose_rag_quality.py --queries-file data/short-videos/ee-crs-scoring/storyline.md
"""
from __future__ import annotations

import argparse
import re
import sys
from collections import Counter
from datetime import datetime
from pathlib import Path

from loguru import logger

# ── Config ──
PROJECT_ROOT = Path(__file__).parent.parent.parent
CHROMA_DIR = PROJECT_ROOT / "data" / "chroma_persist"
ENGINE_API = "http://localhost:8001"
DEFAULT_COLLECTION = "ca_federal"
DEFAULT_PERSONA = "live-study-immigration"

# EE CRS 视频需要的核心 book_ids (期望在 ChromaDB 中存在)
# collection: 数据所在的 ChromaDB collection (默认 DEFAULT_COLLECTION)
EXPECTED_BOOK_IDS = {
    "crs-criteria": {
        "pattern": "check-score/crs-criteria",
        "description": "CRS 打分标准详情页",
        "test_queries": [
            "CRS criteria age education language points table",
            "CRS points per factor with or without spouse",
        ],
    },
    "check-score": {
        "pattern": "check-score/check-score",
        "description": "Express Entry 分数查看页",
        "test_queries": ["Express Entry check your CRS score"],
    },
    "ee-rounds-123": {
        "pattern": "ee_rounds",  # 接受 123 或 4，都是 EE 轮次数据
        "collection": "ca_federal_data",
        "description": "EE 轮次数据 — 已迁移到 ca_federal_data",
        "test_queries": ["Express Entry invitation round CRS cut-off score number of invitations issued"],
    },
    "ee-rounds-4": {
        "pattern": "ee_rounds_4_en",
        "collection": "ca_federal_data",
        "description": "EE 轮次详细 Ministerial Instructions (4) — 已迁移到 ca_federal_data",
        "test_queries": ["Express Entry ministerial instructions round details"],
    },
    "express-entry-rounds": {
        "pattern": "rounds-invitations",  # 实际 book_id 用的是 rounds-invitations
        "description": "EE 轮次邀请页面",
        "test_queries": ["Express Entry rounds of invitations"],
    },
}

# cite_rag.py 的引用标记格式
CITATION_PATTERN = re.compile(r"\[需要引用[:：]\s*(.+?)\]")

# 从 storyline 表格提取英文 query
TABLE_PATTERN = re.compile(r"\|\s*\w+\s*\|(.+?)\|(.+?)\|(.+?)\|")


def get_chroma_client():
    """获取 ChromaDB PersistentClient。"""
    import chromadb
    return chromadb.PersistentClient(
        path=str(CHROMA_DIR),
        settings=chromadb.Settings(anonymized_telemetry=False),
    )


# ═════════════════════════════════════════════════════════════
#  Phase 1: ChromaDB 层诊断
# ═════════════════════════════════════════════════════════════

def _get_all_collections(default_collection: str) -> set[str]:
    """从 EXPECTED_BOOK_IDS 收集所有需要检查的 collection 名称。"""
    cols = {default_collection}
    for config in EXPECTED_BOOK_IDS.values():
        if "collection" in config:
            cols.add(config["collection"])
    return cols


def _scan_book_ids(col) -> Counter:
    """分批扫描 collection 中所有 book_id 及计数。"""
    total = col.count()
    counts: Counter = Counter()
    batch_size = 10000
    offset = 0
    while offset < total:
        r = col.get(limit=batch_size, offset=offset, include=["metadatas"])
        if not r["ids"]:
            break
        for m in r["metadatas"]:
            counts[m.get("book_id", "unknown")] += 1
        offset += len(r["ids"])
    return counts


def phase1_chroma_status(collection_name: str) -> dict:
    """检查 ChromaDB collection 状态和 book_id 覆盖 (支持多 collection)。"""
    logger.info("=" * 60)
    logger.info("PHASE 1: ChromaDB 层诊断")
    logger.info("=" * 60)

    client = get_chroma_client()

    # 扫描所有涉及的 collection
    all_cols = _get_all_collections(collection_name)
    col_book_ids: dict[str, Counter] = {}  # collection → book_id counts
    total_chunks = 0

    for cname in sorted(all_cols):
        try:
            col = client.get_collection(cname)
        except Exception:
            logger.error(f"  ❌ Collection '{cname}' does not exist")
            col_book_ids[cname] = Counter()
            continue
        cnt = col.count()
        total_chunks += cnt
        counts = _scan_book_ids(col)
        col_book_ids[cname] = counts
        logger.info(f"  Collection: {cname} — {cnt} chunks, {len(counts)} book_ids")

    # 检查期望的 book_ids
    logger.info("  --- 期望 book_id 覆盖检查 ---")
    found_books = {}
    missing_books = {}

    for name, config in EXPECTED_BOOK_IDS.items():
        pattern = config["pattern"]
        target_col = config.get("collection", collection_name)
        counts = col_book_ids.get(target_col, Counter())
        matches = [
            (bid, cnt)
            for bid, cnt in counts.items()
            if pattern in bid
        ]
        if matches:
            for bid, cnt in matches:
                logger.success(f"  ✅ {name}: {bid} ({cnt} chunks) [{target_col}]")
                found_books[name] = {"book_id": bid, "chunks": cnt, "collection": target_col}
        else:
            logger.error(f"  ❌ {name}: NOT FOUND in '{target_col}' (pattern: '{pattern}')")
            missing_books[name] = config

    return {
        "total": total_chunks,
        "book_ids": sum(len(c) for c in col_book_ids.values()),
        "found": found_books,
        "missing": missing_books,
    }


# ═════════════════════════════════════════════════════════════
#  Phase 2: 向量检索层诊断
# ═════════════════════════════════════════════════════════════

def phase2_vector_retrieval(collection_name: str) -> list[dict]:
    """直接查 ChromaDB 向量，测试每个 query 的命中率 (支持多 collection)。"""
    logger.info("")
    logger.info("=" * 60)
    logger.info("PHASE 2: 向量检索层诊断 (直接 ChromaDB)")
    logger.info("=" * 60)

    client = get_chroma_client()
    # 缓存已打开的 collection
    _col_cache: dict[str, object] = {}

    def _get_col(cname: str):
        if cname not in _col_cache:
            _col_cache[cname] = client.get_collection(cname)
        return _col_cache[cname]

    results = []
    for name, config in EXPECTED_BOOK_IDS.items():
        pattern = config["pattern"]
        target_col = config.get("collection", collection_name)
        col = _get_col(target_col)

        for query in config["test_queries"]:
            r = col.query(
                query_texts=[query],
                n_results=5,
                include=["metadatas", "distances", "documents"],
            )

            hits = []
            target_hit = False
            for i, (meta, dist, doc) in enumerate(
                zip(r["metadatas"][0], r["distances"][0], r["documents"][0])
            ):
                bid = meta.get("book_id", "?")
                page = meta.get("page_number", "?")
                hit = pattern in bid
                if hit:
                    target_hit = True
                hits.append({
                    "rank": i + 1,
                    "book_id": bid,
                    "page": page,
                    "distance": round(dist, 4),
                    "is_target": hit,
                    "snippet": doc[:100] if doc else "",
                })

            if target_hit:
                logger.success(f"  [HIT]  Q: {query[:50]} [{target_col}]")
            else:
                logger.warning(f"  [MISS] Q: {query[:50]} [{target_col}]")
            logger.info(f"          Target: {pattern}")
            for h in hits[:3]:
                marker = "→" if h["is_target"] else " "
                logger.info(f"    {marker} [{h['rank']}] dist={h['distance']:.4f} "
                            f"book={h['book_id']} p={h['page']}")

            results.append({
                "name": name,
                "query": query,
                "target_pattern": pattern,
                "target_collection": target_col,
                "target_hit": target_hit,
                "top_hit_book": hits[0]["book_id"] if hits else "",
                "top_hit_dist": hits[0]["distance"] if hits else 999,
            })

    # 汇总
    total_q = len(results)
    hit_q = sum(1 for r in results if r["target_hit"])
    logger.info(f"  --- 命中率: {hit_q}/{total_q} ({hit_q/max(total_q,1):.0%}) ---")
    return results


# ═════════════════════════════════════════════════════════════
#  Phase 3: Engine API 层诊断
# ═════════════════════════════════════════════════════════════

def phase3_engine_api(
    api_url: str,
    persona: str,
    queries: list[str] | None = None,
    label: str = "PHASE 3",
) -> list[dict]:
    """通过 Engine API 测试最终检索效果。"""
    logger.info("")
    logger.info("=" * 60)
    logger.info(f"{label}: Engine API 层诊断")
    logger.info("=" * 60)

    import requests

    if not queries:
        queries = []
        for config in EXPECTED_BOOK_IDS.values():
            queries.extend(config["test_queries"])

    # 先检查 API 是否可用
    try:
        requests.get(f"{api_url}/health", timeout=5)
        logger.success(f"  Engine API: {api_url} ✅")
    except Exception:
        logger.error(f"  Engine API: {api_url} ❌ 不可用，跳过")
        return []

    results = []
    for query in queries:
        try:
            resp = requests.post(
                f"{api_url}/engine/consulting/query",
                json={"persona_slug": persona, "question": query, "top_k": 5},
                timeout=120,
            )
            resp.raise_for_status()
            data = resp.json()
            sources = data.get("sources", [])
            answer = data.get("answer", "")

            logger.info(f"  Q: {query[:60]}")
            logger.info(f"  Sources: {len(sources)}")
            for i, src in enumerate(sources[:3]):
                bid = src.get("book_id", "?")
                score = src.get("score", 0)
                logger.info(f"    [{i+1}] score={score:.4f} book={bid}")

            # Check answer quality
            no_data = any(
                phrase in answer.lower()
                for phrase in ["does not contain", "no information", "not found"]
            )
            if no_data:
                logger.warning(f"  ⚠️ Answer 暗示数据缺失")
            else:
                logger.success(f"  Answer OK")

            results.append({
                "query": query,
                "source_count": len(sources),
                "top_book": sources[0].get("book_id", "") if sources else "",
                "top_score": sources[0].get("score", 0) if sources else 0,
                "no_data_flag": no_data,
                "answer_preview": answer[:150],
            })
        except Exception as e:
            logger.error(f"  Q: {query[:50]}... ❌ Error: {e}")
            results.append({"query": query, "error": str(e)})

    return results


# ═════════════════════════════════════════════════════════════
#  Phase 4: 从 storyline 提取引用需求测试 (使用英文 query)
# ═════════════════════════════════════════════════════════════

def phase4_storyline_queries(
    storyline_path: Path,
    api_url: str,
    persona: str,
) -> list[dict]:
    """从 storyline.md 提取引用需求，优先使用英文 query 测试 Engine API。"""
    if not storyline_path.exists():
        logger.error(f"  ❌ {storyline_path} not found")
        return []

    text = storyline_path.read_text(encoding="utf-8")

    # 先解析表格获取英文 query 映射 (多种索引方式)
    claim_to_query: dict[str, str] = {}  # 中文断言 → 英文 query
    query_text_to_query: dict[str, str] = {}  # 英文 inline text → 英文 query
    for m in TABLE_PATTERN.finditer(text):
        claim = m.group(1).strip()
        query_suggestion = m.group(3).strip().strip('"')
        if claim and claim not in ("断言", "...") and query_suggestion and query_suggestion != "...":
            claim_to_query[claim] = query_suggestion
            # 也用 query_suggestion 本身做 key（inline 标记可能直接就是英文）
            query_text_to_query[query_suggestion] = query_suggestion

    # 提取内联标记
    claims = CITATION_PATTERN.findall(text)
    claims = list(dict.fromkeys(claims))  # deduplicate

    # 构建英文 query 列表
    queries = []
    matched = 0
    for claim in claims:
        claim = claim.strip()
        # 1) 先在中文断言列匹配
        eng_query = claim_to_query.get(claim)
        # 2) 再在英文 query suggestion 列匹配（inline 标记本身就是英文时）
        if not eng_query:
            eng_query = query_text_to_query.get(claim)
        # 3) 回退: 直接使用 inline 文本
        if not eng_query:
            eng_query = claim
            logger.warning(f"  [WARN] No table match for: {claim}")
        else:
            matched += 1
        queries.append(eng_query)

    logger.info(f"  Storyline: {storyline_path.name}")
    logger.info(f"  引用需求: {len(queries)}")
    logger.info(f"  表格匹配: {matched}/{len(queries)}")

    return phase3_engine_api(api_url, persona, queries, label="PHASE 4 (Storyline)")


# ═════════════════════════════════════════════════════════════
#  汇总报告
# ═════════════════════════════════════════════════════════════

def generate_report(
    chroma_status: dict,
    vector_results: list[dict],
    api_results: list[dict],
    storyline_results: list[dict],
) -> dict:
    """汇总报告 (写入日志)。"""
    logger.info("")
    logger.info("=" * 60)
    logger.info("SUMMARY REPORT")
    logger.info("=" * 60)

    report = {
        "chroma": {
            "total_chunks": chroma_status["total"],
            "unique_books": chroma_status["book_ids"],
            "expected_found": len(chroma_status["found"]),
            "expected_missing": len(chroma_status["missing"]),
            "missing_books": list(chroma_status["missing"].keys()),
        },
        "vector_retrieval": {
            "total_queries": len(vector_results),
            "target_hits": sum(1 for r in vector_results if r.get("target_hit")),
        },
        "engine_api": {
            "total_queries": len(api_results),
            "no_data_flags": sum(1 for r in api_results if r.get("no_data_flag")),
        },
        "storyline": {
            "total_claims": len(storyline_results),
            "no_data_flags": sum(1 for r in storyline_results if r.get("no_data_flag")),
        },
    }

    # 汇总
    logger.info(f"  ChromaDB:")
    logger.info(f"    Total chunks:   {report['chroma']['total_chunks']}")
    logger.info(f"    Expected books: {report['chroma']['expected_found']}/{report['chroma']['expected_found'] + report['chroma']['expected_missing']}")
    if report["chroma"]["missing_books"]:
        logger.error(f"    ❌ Missing: {', '.join(report['chroma']['missing_books'])}")

    hit_rate = (
        report["vector_retrieval"]["target_hits"]
        / max(report["vector_retrieval"]["total_queries"], 1)
    )
    logger.info(f"  向量检索: {report['vector_retrieval']['target_hits']}/{report['vector_retrieval']['total_queries']} ({hit_rate:.0%})")
    logger.info(f"  Engine API: {report['engine_api']['total_queries']} queries, {report['engine_api']['no_data_flags']} data gaps")

    if storyline_results:
        logger.info(f"  Storyline: {report['storyline']['total_claims']} claims, {report['storyline']['no_data_flags']} data gaps")

    # 判定
    logger.info("")
    passed = True
    if report["chroma"]["missing_books"]:
        logger.error("  FAIL: 缺失 book_ids — " + ", ".join(report["chroma"]["missing_books"]))
        passed = False
    if hit_rate < 0.5:
        logger.error(f"  FAIL: 向量命中率 {hit_rate:.0%} < 50%")
        passed = False
    if report["engine_api"]["no_data_flags"] > 0:
        logger.error(f"  FAIL: Engine API {report['engine_api']['no_data_flags']} queries 数据缺失")
        passed = False
    if report["storyline"]["no_data_flags"] > 0:
        logger.error(f"  FAIL: Storyline {report['storyline']['no_data_flags']} claims 数据缺失")
        passed = False

    if passed:
        logger.success("  ✅ QUALITY GATE PASSED — 可以继续生成 sources.json")
    else:
        logger.error("  ❌ QUALITY GATE FAILED — 需要修复后重试")

    return report


# ═════════════════════════════════════════════════════════════
#  CLI
# ═════════════════════════════════════════════════════════════

def setup_logging(log_path: Path) -> None:
    """配置 loguru: 同时输出到 console 和 log 文件。"""
    # 移除默认 handler
    logger.remove()
    # Console: 简洁格式
    logger.add(sys.stderr, format="{message}", level="INFO")
    # File: 详细格式
    log_path.parent.mkdir(parents=True, exist_ok=True)
    logger.add(
        str(log_path),
        format="{time:YYYY-MM-DD HH:mm:ss} | {level:<8} | {message}",
        level="DEBUG",
        mode="w",  # 每次覆盖
        encoding="utf-8",
    )
    logger.info(f"Log file: {log_path}")


def main():
    p = argparse.ArgumentParser(
        description="RAG 检索质量诊断 & 优化",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument("--collection", default=DEFAULT_COLLECTION)
    p.add_argument("--api-url", default=ENGINE_API)
    p.add_argument("--persona", default=DEFAULT_PERSONA)
    p.add_argument("--queries-file", type=Path, help="storyline.md 路径")
    p.add_argument("--output", type=Path, help="日志输出路径 (.log)")
    p.add_argument("--skip-api", action="store_true", help="跳过 Engine API 测试")
    p.add_argument("--phase", type=int, help="只跑某一阶段 (1/2/3/4)")
    args = p.parse_args()

    # 日志路径: 默认放在 storyline 同目录
    if args.output:
        log_path = args.output.with_suffix(".log") if args.output.suffix != ".log" else args.output
    elif args.queries_file:
        log_path = args.queries_file.parent / "rag_report.log"
    else:
        log_path = Path("rag_report.log")

    setup_logging(log_path)

    logger.info("=" * 60)
    logger.info("RAG 检索质量诊断工具")
    logger.info(f"Time: {datetime.now().isoformat()}")
    logger.info("=" * 60)

    # Phase 1
    chroma_status = {"total": 0, "book_ids": 0, "found": {}, "missing": {}}
    if not args.phase or args.phase == 1:
        chroma_status = phase1_chroma_status(args.collection)

    # Phase 2
    vector_results = []
    if not args.phase or args.phase == 2:
        vector_results = phase2_vector_retrieval(args.collection)

    # Phase 3
    api_results = []
    if (not args.phase or args.phase == 3) and not args.skip_api:
        api_results = phase3_engine_api(args.api_url, args.persona)

    # Phase 4
    storyline_results = []
    if args.queries_file and (not args.phase or args.phase == 4):
        storyline_results = phase4_storyline_queries(
            args.queries_file, args.api_url, args.persona
        )

    # Report
    generate_report(chroma_status, vector_results, api_results, storyline_results)

    logger.info("")
    logger.info("=" * 60)
    logger.info("DONE")
    logger.info("=" * 60)


if __name__ == "__main__":
    main()
