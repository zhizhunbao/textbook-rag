# /// script
# requires-python = ">=3.12"
# dependencies = [
#   "requests",
#   "loguru",
# ]
# ///
"""
cite_rag.py — 从 storyline.md 的引用标记查找 RAG 来源 URL
============================================================
提取 [需要引用: ...] 标记 → 精确查 RAG → 返回 sources.json

用法:
  uv run cite_rag.py --storyline data/short-videos/crs/storyline.md \
    --persona live-study-immigration \
    --output data/short-videos/crs/sources.json

产出:
  sources.json — 引用需求 → 来源 URL 映射
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

import requests
from loguru import logger


# ── 引用标记提取 ───────────────────────────────────────────

CITATION_PATTERN = re.compile(r"\[需要引用[:：]\s*(.+?)\]")

# 分类前缀 → URL 基础映射
CATEGORY_URL_MAP = {
    "federal-ircc": "https://www.canada.ca",
    "ontario": "https://www.ontario.ca",
    "bc": "https://www.welcomebc.ca",
    "alberta": "https://www.alberta.ca",
}


def extract_citations(storyline_path: Path) -> list[dict]:
    """从 storyline.md 提取所有 [需要引用: ...] 标记。"""
    text = storyline_path.read_text(encoding="utf-8")
    matches = CITATION_PATTERN.findall(text)

    citations = []
    seen = set()
    for desc in matches:
        desc = desc.strip()
        if desc not in seen:
            seen.add(desc)
            citations.append({"claim": desc, "query": desc})
    
    # 也从引用需求清单表格中提取 (如果有)
    # 匹配 | N | 断言 | 引用类型 | RAG查询建议 | 的格式
    table_pattern = re.compile(
        r"\|\s*\d+\s*\|(.+?)\|(.+?)\|(.+?)\|"
    )
    for m in table_pattern.finditer(text):
        claim = m.group(1).strip()
        query_suggestion = m.group(3).strip()
        if claim and claim not in seen and claim != "断言" and claim != "...":
            seen.add(claim)
            citations.append({
                "claim": claim,
                "query": query_suggestion if query_suggestion != "..." else claim,
            })

    logger.info(f"[Extract] {len(citations)} citation needs from {storyline_path.name}")
    return citations


# ── RAG 查询 ──────────────────────────────────────────────

def query_rag(api_url: str, persona: str, question: str, top_k: int = 5) -> dict:
    """调用 consulting /query API 获取来源。"""
    url = f"{api_url}/engine/consulting/query"
    payload = {"persona_slug": persona, "question": question, "top_k": top_k}
    logger.info(f"[RAG] Q: {question[:60]}...")
    resp = requests.post(url, json=payload, timeout=120)
    resp.raise_for_status()
    return resp.json()


def build_source_url(source: dict) -> str:
    """从 RAG source 元数据构建完整 URL。"""
    book_id = source.get("book_id", "")
    category = source.get("category", "")

    # 从 category 获取基础 URL
    base_url = CATEGORY_URL_MAP.get(category, "")
    if not base_url or not book_id:
        # 尝试从 book_title 推断
        title = source.get("book_title", "")
        if "canada.ca" in title.lower():
            base_url = "https://www.canada.ca"
        else:
            return ""

    # book_id 格式: "en/.../page-name/page-name"
    # 去掉末尾重复段: en/.../works/works → en/.../works
    parts = book_id.rsplit("/", 1)
    if len(parts) == 2 and parts[0].endswith(parts[1]):
        path = parts[0]
    else:
        path = book_id

    return f"{base_url}/{path}"


# ── 主流程 ────────────────────────────────────────────────

def find_citations(
    citations: list[dict],
    api_url: str,
    persona: str,
    top_k: int = 5,
) -> list[dict]:
    """为每个引用需求查找 RAG 来源。"""
    results = []

    for cit in citations:
        claim = cit["claim"]
        query = cit["query"]

        try:
            rag_result = query_rag(api_url, persona, query, top_k)
            sources = rag_result.get("sources", [])
            answer = rag_result.get("answer", "")

            if sources:
                best = sources[0]  # 取最高分来源
                url = build_source_url(best)
                results.append({
                    "claim": claim,
                    "query": query,
                    "source_url": url,
                    "source_title": best.get("book_title", ""),
                    "source_text": best.get("snippet", "")[:300],
                    "page": best.get("page_number", 0),
                    "category": best.get("category", ""),
                    "score": round(best.get("score", 0), 4),
                    "answer_excerpt": answer[:200],
                    "status": "found",
                })
                logger.success(f"  ✅ {claim[:30]} → {url[:60]}")
            else:
                results.append({
                    "claim": claim,
                    "query": query,
                    "source_url": "",
                    "source_title": "",
                    "source_text": "",
                    "status": "not_found",
                })
                logger.warning(f"  ❌ {claim[:30]} → no sources")

        except Exception as e:
            logger.error(f"  ⚠️ {claim[:30]} → error: {e}")
            results.append({
                "claim": claim,
                "query": query,
                "source_url": "",
                "status": "error",
                "error": str(e),
            })

    found = sum(1 for r in results if r["status"] == "found")
    logger.info(f"[Citations] {found}/{len(results)} found")
    return results


# ── CLI ────────────────────────────────────────────────────

def main():
    p = argparse.ArgumentParser(description="从 storyline 引用标记查找 RAG 来源 URL")
    p.add_argument("--storyline", type=Path, required=True, help="storyline.md 路径")
    p.add_argument("--persona", default="live-study-immigration")
    p.add_argument("--output", type=Path, required=True, help="输出 sources.json")
    p.add_argument("--api-url", default="http://localhost:8001")
    p.add_argument("--top-k", type=int, default=5)
    args = p.parse_args()

    if not args.storyline.exists():
        logger.error(f"{args.storyline} not found")
        sys.exit(1)

    logger.info("=" * 50)
    logger.info("RAG 引用查找器 (cite_rag.py)")
    logger.info(f"Storyline: {args.storyline}")
    logger.info("=" * 50)

    # 1. 提取引用需求
    citations = extract_citations(args.storyline)
    if not citations:
        logger.warning("No [需要引用] markers found in storyline")
        args.output.write_text(json.dumps({"citations": []}, ensure_ascii=False, indent=2))
        return

    # 2. 查找来源
    results = find_citations(citations, args.api_url, args.persona, args.top_k)

    # 3. 输出
    output = {
        "storyline": str(args.storyline),
        "total": len(results),
        "found": sum(1 for r in results if r["status"] == "found"),
        "citations": results,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    logger.success(f"Done! {args.output} ({output['found']}/{output['total']} found)")


if __name__ == "__main__":
    main()
