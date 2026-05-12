# /// script
# requires-python = ">=3.12"
# dependencies = [
#   "requests",
#   "loguru",
# ]
# ///
"""
cite_rag.py — RAG 数据探索与引用检索
====================================
支持两种模式:
  1. 探索模式 (--queries): 从 queries.md 提取英文查询 → 检索 RAG → sources.json
  2. 引用模式 (--storyline): 从 storyline.md 的 [需要引用] 标记检索 (legacy)

用法:
  # 探索模式 (推荐, workflow Step 1)
  uv run cite_rag.py --queries data/short-videos/pnp/queries.md \
    --persona live-study-immigration \
    --output data/short-videos/pnp/sources.json

  # 引用模式 (legacy, 兼容旧 workflow)
  uv run cite_rag.py --storyline data/short-videos/pnp/storyline.md \
    --persona live-study-immigration \
    --output data/short-videos/pnp/sources.json

产出:
  sources.json — 去重后的 raw chunk 列表 (纯指针, 供 Agent 判断)
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

import requests
from loguru import logger


# ── 查询提取 ───────────────────────────────────────────────

CITATION_PATTERN = re.compile(r"\[需要引用[:：]\s*(.+?)\]")

# 分类前缀 → URL 基础映射
CATEGORY_URL_MAP = {
    "federal-ircc": "https://www.canada.ca",
    "ontario": "https://www.ontario.ca",
    "bc": "https://www.welcomebc.ca",
    "alberta": "https://www.alberta.ca",
}


def extract_queries(queries_path: Path) -> list[dict]:
    """从 queries.md / research.md 提取探索查询（Step 1 数据探索模式）。

    只解析 "## RAG 查询表" section 内的表格，忽略文件中其他表格
    （如"子弹提取"表），避免中文标题/层级引用被当作 RAG 查询。

    支持的表格格式:
      三列: | # | 主题 | RAG 查询 (英文) |
      两列: | # | RAG 查询 (英文) |
    """
    text = queries_path.read_text(encoding="utf-8")
    citations = []
    seen_queries = set()

    # ── 定位 "RAG 查询表" section ──
    # 匹配 ## RAG 查询表 / ## RAG查询表 / ## RAG Queries 等
    section_start = re.search(
        r"^##\s+RAG\s*查询表?",
        text,
        re.MULTILINE | re.IGNORECASE,
    )
    if section_start:
        section_text = text[section_start.end():]
        # section 到下一个 ## 或 --- 结束
        section_end = re.search(r"^(?:##\s|---)", section_text, re.MULTILINE)
        if section_end:
            section_text = section_text[:section_end.start()]
        logger.info(f"[Extract] Found 'RAG 查询表' section ({len(section_text)} chars)")
    else:
        # 向后兼容: 没有明确 section 标题时扫描全文
        section_text = text
        logger.warning("[Extract] No 'RAG 查询表' section found, scanning entire file")

    # ── 解析表格行 ──
    # 三列格式: | # | 主题/痛点 | RAG 查询 |
    table_3col = re.compile(r"\|\s*\d+\s*\|(.+?)\|(.+?)\|")
    for m in table_3col.finditer(section_text):
        col1 = m.group(1).strip()
        col2 = m.group(2).strip().strip('"')
        # 跳过表头
        if col1 in ("痛点问题", "断言", "主题", "...") or col2 in (
            "RAG 查询 (英文)", "RAG 查询建议 (必须英文)",
            "RAG 查询 (英文)", "...",
        ):
            continue
        # col2 是英文 query, col1 是中文描述
        query = col2 if col2 else col1
        if query and query not in seen_queries:
            seen_queries.add(query)
            citations.append({"claim": col1, "query": query})
            logger.info(f"  [Explore] {col1[:30]} → EN: {query[:60]}")

    if not citations:
        logger.warning(f"No queries found in {queries_path.name}")

    logger.info(f"[Extract] {len(citations)} exploration queries from {queries_path.name}")
    return citations


def extract_citations(storyline_path: Path) -> list[dict]:
    """从 storyline.md 提取引用需求（legacy 引用模式）。

    两个来源（优先级从高到低）:
      1. 引用需求清单表格 — 有英文 RAG 查询建议，最可靠
      2. [需要引用: ...] 内联标记 — 作为表格的补充
    """
    text = storyline_path.read_text(encoding="utf-8")
    citations = []
    seen_queries = set()

    # ── 来源 1: 解析引用需求清单表格 (权威来源) ──
    table_pattern = re.compile(
        r"\|\s*\d+\s*\|(.+?)\|(.+?)\|(.+?)\|"
    )
    for m in table_pattern.finditer(text):
        claim = m.group(1).strip()
        query = m.group(3).strip().strip('"')
        if not claim or claim in ("断言", "..."):
            continue
        if not query or query in ("...", "RAG 查询建议 (必须英文)"):
            continue
        if query not in seen_queries:
            seen_queries.add(query)
            citations.append({"claim": claim, "query": query})
            logger.info(f"  [Table] {claim[:30]} → EN: {query[:60]}")

    if citations:
        logger.info(f"[Table] Found {len(citations)} English queries from citation table")

    # ── 来源 2: 补充 [需要引用: ...] 内联标记 (仅当表格不存在时) ──
    if not citations:
        matches = CITATION_PATTERN.findall(text)
        for desc in matches:
            desc = desc.strip()
            if desc not in seen_queries:
                seen_queries.add(desc)
                logger.warning(f"  [Inline] No table found, using inline: {desc[:60]}")
                citations.append({"claim": desc, "query": desc})

    if not citations:
        logger.warning("No citations found in storyline (no table, no inline markers)")

    logger.info(f"[Extract] {len(citations)} citation needs from {storyline_path.name}")
    return citations


# ── URL 构建 ──────────────────────────────────────────────

def build_source_url(book_id: str, category: str) -> str:
    """从 book_id + category 构建完整 URL。"""
    base_url = CATEGORY_URL_MAP.get(category, "")
    if not base_url or not book_id:
        return ""

    # book_id 格式: "en/.../page-name/page-name"
    # 去掉末尾重复段: en/.../works/works → en/.../works
    parts = book_id.rsplit("/", 1)
    if len(parts) == 2 and parts[0].endswith(parts[1]):
        path = parts[0]
    else:
        path = book_id

    return f"{base_url}/{path}"


def build_md_path(book_id: str, category: str) -> str:
    """从 book_id + category 推算 MinerU 抽取的 .md 文件路径。

    MinerU 输出目录结构 (实际):
        data/mineru_output/{category}/{book_id}/auto/{last_segment}.md
    """
    if not book_id or not category:
        return ""

    dir_name = book_id.rstrip("/").rsplit("/", 1)[-1]
    return f"data/mineru_output/{category}/{book_id}/auto/{dir_name}.md"


# ── 纯检索 (无 rerank / 无 synthesis) ─────────────────────

def retrieve_chunks(api_url: str, persona: str, question: str, top_k: int = 10) -> list[dict]:
    """调用 /engine/consulting/retrieve 获取 raw BM25+Vector chunks。

    不经过 CrossEncoder rerank, 不经过 GPT 合成。
    返回 top_k 个 raw chunks, 每个包含:
      - book_id, category, page_number, snippet, score
      - vector_score, bm25_score, retrieval_source
    """
    url = f"{api_url}/engine/consulting/retrieve"
    payload = {"persona_slug": persona, "question": question, "top_k": top_k}
    logger.info(f"[Retrieve] Q: {question[:60]}...")
    resp = requests.post(url, json=payload, timeout=120)
    resp.raise_for_status()
    data = resp.json()
    return data.get("chunks", [])


# ── 全局去重 + 聚合 ──────────────────────────────────────

def deduplicate_chunks(all_chunks: list[dict]) -> list[dict]:
    """按 (book_id, page_number) 全局去重, 保留最高分。

    多个 query 可能命中同一 chunk, 去重后:
      - 保留最高 score 的那条
      - 合并所有命中该 chunk 的 query 列表
      - 避免 sources.json 中大量重复条目
    """
    groups: dict[tuple[str, int], dict] = {}

    for chunk in all_chunks:
        key = (chunk["book_id"], chunk["page_number"])
        if key not in groups:
            groups[key] = {
                **chunk,
                "queries": list(chunk.get("queries", [])),
            }
        else:
            existing = groups[key]
            # 保留更高分的 snippet/full_content
            if chunk["score"] > existing["score"]:
                existing["snippet"] = chunk["snippet"]
                existing["full_content"] = chunk.get("full_content", "")
                existing["score"] = chunk["score"]
                existing["vector_score"] = chunk.get("vector_score", 0)
                existing["bm25_score"] = chunk.get("bm25_score", 0)
                existing["retrieval_source"] = chunk.get("retrieval_source", "")
            # 合并 queries
            for q in chunk.get("queries", []):
                if q not in existing["queries"]:
                    existing["queries"].append(q)

    deduped = sorted(groups.values(), key=lambda c: c["score"], reverse=True)
    logger.info(f"[Dedup] {len(all_chunks)} raw chunks → {len(deduped)} unique (book_id, page)")
    return deduped


# ── 主流程 ────────────────────────────────────────────────

def find_citations(
    citations: list[dict],
    api_url: str,
    persona: str,
    top_k: int = 10,
) -> list[dict]:
    """为每个引用需求检索 raw chunks, 全局去重后返回。"""
    all_chunks: list[dict] = []

    for cit in citations:
        query = cit["query"]

        try:
            chunks = retrieve_chunks(api_url, persona, query, top_k)

            if chunks:
                logger.success(f"  ✅ {query[:50]} → {len(chunks)} chunks")
                for chunk in chunks:
                    # 附加来源信息
                    chunk["queries"] = [query]
                    chunk["source_url"] = build_source_url(
                        chunk.get("book_id", ""), chunk.get("category", ""),
                    )
                    chunk["md_path"] = build_md_path(
                        chunk.get("book_id", ""), chunk.get("category", ""),
                    )
                    all_chunks.append(chunk)
            else:
                logger.warning(f"  ❌ {query[:50]} → no chunks")

        except Exception as e:
            logger.error(f"  ⚠️ {query[:50]} → error: {e}")

    # 全局去重
    deduped = deduplicate_chunks(all_chunks)

    found_queries = set()
    for chunk in deduped:
        for q in chunk.get("queries", []):
            found_queries.add(q)

    all_queries = {c["query"] for c in citations}
    missing = all_queries - found_queries
    if missing:
        logger.warning("=" * 60)
        logger.warning("❌ 以下查询无法找到 RAG 数据，建议先入库再继续：")
        for q in missing:
            logger.warning(f"  ❌ {q}")
        logger.warning("=" * 60)

    logger.info(f"[Citations] {len(deduped)} unique chunks from {len(citations)} queries")
    return deduped


# ── CLI ────────────────────────────────────────────────────

def main():
    p = argparse.ArgumentParser(description="RAG 数据探索与引用检索")
    # 两种输入模式（二选一）
    group = p.add_mutually_exclusive_group(required=True)
    group.add_argument("--queries", type=Path, help="探索模式: queries.md 路径 (推荐)")
    group.add_argument("--storyline", type=Path, help="引用模式: storyline.md 路径 (legacy)")
    p.add_argument("--persona", default="live-study-immigration")
    p.add_argument("--output", type=Path, required=True, help="输出 sources.json")
    p.add_argument("--api-url", default="http://localhost:8001")
    p.add_argument("--top-k", type=int, default=10, help="每个 query 检索的 chunk 数 (默认 10)")
    args = p.parse_args()

    # 确定输入文件和模式
    if args.queries:
        input_path = args.queries
        mode = "探索"
    else:
        input_path = args.storyline
        mode = "引用"

    if not input_path.exists():
        logger.error(f"{input_path} not found")
        sys.exit(1)

    logger.info("=" * 50)
    logger.info(f"RAG 检索器 v3 (cite_rag.py) — {mode}模式")
    logger.info(f"模式: BM25+Vector 纯检索 (无 rerank, 无 synthesis)")
    logger.info(f"输入: {input_path}")
    logger.info(f"Top-K per query: {args.top_k}")
    logger.info("=" * 50)

    # 1. 提取查询
    if args.queries:
        citations = extract_queries(args.queries)
    else:
        citations = extract_citations(args.storyline)

    if not citations:
        logger.warning("No queries found in input file")
        args.output.write_text(json.dumps({"chunks": []}, ensure_ascii=False, indent=2))
        return

    # 2. 检索 + 去重
    chunks = find_citations(citations, args.api_url, args.persona, args.top_k)

    # 3. 输出 — 只保留有用字段 (纯指针, 供 Agent 判断)
    output_chunks = []
    for chunk in chunks:
        output_chunks.append({
            "book_id": chunk.get("book_id", ""),
            "category": chunk.get("category", ""),
            "page": chunk.get("page_number", 0),
            "source_url": chunk.get("source_url", ""),
            "md_path": chunk.get("md_path", ""),
            "snippet": chunk.get("snippet", ""),
            "score": chunk.get("score", 0),
            "vector_score": chunk.get("vector_score", 0),
            "bm25_score": chunk.get("bm25_score", 0),
            "retrieval_source": chunk.get("retrieval_source", ""),
            "queries": chunk.get("queries", []),
        })

    output = {
        "mode": mode,
        "input": str(input_path),
        "query_count": len(citations),
        "top_k_per_query": args.top_k,
        "unique_chunks": len(output_chunks),
        "chunks": output_chunks,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    logger.success(
        f"Done! {args.output} ({len(output_chunks)} unique chunks from {len(citations)} queries)"
    )


if __name__ == "__main__":
    main()
