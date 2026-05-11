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
    """从 storyline.md 提取所有 [需要引用: ...] 标记。

    优先使用引用需求清单表格中的英文 RAG 查询建议作为 query,
    因为 ChromaDB 中的数据全部是英文, 中文查询会导致向量命中率极低。
    """
    text = storyline_path.read_text(encoding="utf-8")

    # ── Step 1: 先解析引用需求清单表格, 建立 claim → English query 映射 ──
    table_pattern = re.compile(
        r"\|\s*\d+\s*\|(.+?)\|(.+?)\|(.+?)\|"
    )
    claim_to_query: dict[str, str] = {}
    for m in table_pattern.finditer(text):
        claim = m.group(1).strip()
        query_suggestion = m.group(3).strip().strip('"')
        if claim and claim not in ("断言", "...") and query_suggestion and query_suggestion != "...":
            claim_to_query[claim] = query_suggestion

    if claim_to_query:
        logger.info(f"[Table] Found {len(claim_to_query)} English query mappings")

    # ── Step 2: 提取 [需要引用: ...] 内联标记 ──
    matches = CITATION_PATTERN.findall(text)

    citations = []
    seen = set()
    def _is_english(s: str) -> bool:
        """判断字符串是否主要是英文 (ASCII 占比 > 80%)。"""
        if not s:
            return False
        ascii_count = sum(1 for c in s if ord(c) < 128)
        return ascii_count / len(s) > 0.8

    for desc in matches:
        desc = desc.strip()
        if desc not in seen:
            seen.add(desc)
            # 优先用表格中的英文 query, 否则用 claim 本身
            english_query = claim_to_query.get(desc, "")
            if not english_query:
                if _is_english(desc):
                    # 内联标记本身就是英文，直接用
                    logger.info(f"  [EN] Using inline English query: {desc[:60]}")
                else:
                    logger.warning(f"  [WARN] No English query for: {desc} — using Chinese (低命中率)")
            citations.append({
                "claim": desc,
                "query": english_query or desc,
            })

    # ── Step 3: 补充表格中有但内联标记没覆盖的 claim ──
    for claim, query in claim_to_query.items():
        if claim not in seen:
            seen.add(claim)
            citations.append({"claim": claim, "query": query})

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


def build_md_path(source: dict) -> str:
    """从 RAG source 元数据推算 MinerU 抽取的 .md 文件路径。

    MinerU 输出目录结构 (实际):
        data/mineru_output/{category}/{book_id}/auto/{last_segment}.md

    book_id 是完整路径 (如 "en/immigration-refugees-citizenship/.../crs-criteria/crs-criteria")，
    保留完整路径作为目录，取最后一段作为文件名。
    """
    book_id = source.get("book_id", "")
    category = source.get("category", "")
    if not book_id or not category:
        return ""

    # book_id 包含完整目录结构，最后一段是文件名
    dir_name = book_id.rstrip("/").rsplit("/", 1)[-1]
    return f"data/mineru_output/{category}/{book_id}/auto/{dir_name}.md"


def extract_md_context(
    md_path: str,
    snippet: str,
    context_chars: int = 1500,
) -> str:
    """从 MinerU .md 文件中提取 snippet 周围的完整段落上下文。

    策略:
      1. 在 .md 文件中搜索 snippet 的前 40 个字符
      2. 找到后向两侧扩展到段落边界 (空行)
      3. 返回最多 context_chars 字符的上下文
      4. 找不到则返回空字符串
    """
    from pathlib import Path

    # 解析为绝对路径 (相对于 cwd, 即项目根目录)
    abs_path = Path.cwd() / md_path
    if not abs_path.exists():
        return ""

    try:
        text = abs_path.read_text(encoding="utf-8")
    except Exception:
        return ""

    # 多策略搜索 snippet 在 .md 文件中的位置
    snippet_clean = snippet.strip()
    if not snippet_clean:
        return ""

    pos = -1

    # 策略 1: 前 40 字符精确匹配
    pos = text.find(snippet_clean[:40])

    # 策略 2: 前 20 字符
    if pos == -1:
        pos = text.find(snippet_clean[:20])

    # 策略 3: 去掉表格管道符，提取关键短语搜索
    if pos == -1:
        # "| one or more under CLB 9 |" → "one or more under CLB 9"
        cleaned = snippet_clean.replace("|", " ").strip()
        # 取第一个有意义的短语 (>10 字符)
        for phrase in cleaned.split("  "):
            phrase = phrase.strip()
            if len(phrase) > 10:
                pos = text.find(phrase[:30])
                if pos != -1:
                    break

    # 策略 4: 用 snippet 中最长的连续英文词组搜索
    if pos == -1:
        import re as _re
        words = _re.findall(r'[A-Za-z][A-Za-z\s]{8,30}', snippet_clean)
        for w in sorted(words, key=len, reverse=True):
            pos = text.find(w.strip())
            if pos != -1:
                break

    if pos == -1:
        return ""

    # 向两侧扩展到段落边界 (连续两个换行符)
    half = context_chars // 2
    start = max(0, pos - half)
    end = min(len(text), pos + half)

    # 向前找段落开头 (空行 or 文档开头)
    para_start = text.rfind("\n\n", 0, start)
    if para_start != -1:
        start = para_start + 2  # 跳过空行本身

    # 向后找段落结尾
    para_end = text.find("\n\n", end)
    if para_end != -1:
        end = para_end

    context = text[start:end].strip()
    if len(context) > context_chars:
        context = context[:context_chars] + "..."

    return context


# ── 质量验证 ───────────────────────────────────────────────

def validate_source(source: dict, url: str, answer: str) -> tuple[bool, list[str]]:
    """验证 RAG 返回的 source 质量，返回 (is_ok, warnings)。

    检查:
      1. URL 完整性 — book_id 必须包含 / 才能拼出有效 URL
      2. 数据时效 — snippet/answer 中的年份不能比当前年份早 >1 年
      3. 内容相关性 — answer 不能包含"does not contain"等无数据短语
      4. 空白内容 — snippet 不能是空模板（如 "Date and time: ."）
    """
    warnings = []
    book_id = source.get("book_id", "")

    # Check 1: URL 完整性
    if "/" not in book_id:
        warnings.append(f"book_id 无完整路径 ('{book_id}')，URL 可能无效")

    if not url or url.count("/") < 4:
        warnings.append(f"URL 不完整: {url}")

    # Check 2: 数据时效
    from datetime import datetime
    current_year = datetime.now().year
    snippet = source.get("snippet", "")
    combined_text = f"{snippet} {answer}"
    year_pattern = re.compile(r"\b(20\d{2})\b")
    years_found = [int(y) for y in year_pattern.findall(combined_text)]
    if years_found:
        max_year = max(years_found)
        if current_year - max_year > 1:
            warnings.append(
                f"数据可能过时: 最新年份 {max_year}，当前 {current_year}"
            )

    # Check 3: 内容相关性
    no_data_phrases = [
        "does not contain",
        "do not contain",
        "no information",
        "not found in",
        "not available",
        "unable to find",
        "no relevant",
    ]
    answer_lower = answer.lower()
    for phrase in no_data_phrases:
        if phrase in answer_lower:
            warnings.append(f"RAG 回答暗示数据缺失: '{phrase}'")
            break

    # Check 4: 空白内容检测
    # 动态加载页面截取后常见: "Date and time: . CRS score: ."
    blank_indicators = [
        ":      ",   # 大量空白 = 动态加载未渲染
        ":   \n",
    ]
    for indicator in blank_indicators:
        if indicator in snippet:
            warnings.append("snippet 包含空白字段，可能是动态页面未渲染")
            break

    is_ok = len(warnings) == 0
    return is_ok, warnings

# ── 主流程 ────────────────────────────────────────────────

def find_citations(
    citations: list[dict],
    api_url: str,
    persona: str,
    top_k: int = 10,
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
                best = sources[0]  # Engine API 排序最高的
                url = build_source_url(best)
                md_path = build_md_path(best)
                snippet = best.get("snippet", "")

                # ── 从 .md 文件提取完整上下文 ──
                source_context = extract_md_context(md_path, snippet)

                # ── 质量验证 ──
                is_ok, warnings = validate_source(best, url, answer)

                entry = {
                    "claim": claim,
                    "query": query,
                    "source_url": url,
                    "source_title": best.get("book_title", ""),
                    "source_text": snippet[:300],
                    "source_context": source_context or "",
                    "page": best.get("page_number", 0),
                    "category": best.get("category", ""),
                    "book_id": best.get("book_id", ""),
                    "md_path": md_path,
                    "score": round(best.get("score", 0), 4),
                    "answer_excerpt": answer[:200],
                }

                if is_ok:
                    entry["status"] = "found"
                    results.append(entry)
                    logger.success(f"  ✅ {claim[:30]} → {url[:60]}")
                else:
                    # low_quality 仍视为可用引用 (数据已入库, Engine API 有回答)
                    # 只附加警告信息, 不阻断 pipeline
                    entry["status"] = "found"
                    entry["warnings"] = warnings
                    results.append(entry)
                    logger.warning(f"  ⚠️ {claim[:30]} → {url[:60]} (有警告)")
                    for w in warnings:
                        logger.warning(f"     - {w}")
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
    with_warnings = sum(1 for r in results if r["status"] == "found" and r.get("warnings"))
    not_found = sum(1 for r in results if r["status"] in ("not_found", "error"))

    if with_warnings:
        logger.info(f"[Citations] {found} ✅ found ({with_warnings} with warnings), {not_found} ❌ missing")
    else:
        logger.info(f"[Citations] {found} ✅ found, {not_found} ❌ missing")

    # ── 真正缺数据才告警 (only not_found / error) ──
    missing = [r for r in results if r["status"] in ("not_found", "error")]
    if missing:
        logger.warning("=" * 60)
        logger.warning("❌ 以下论点无法找到 RAG 数据，建议先入库再继续：")
        for r in missing:
            logger.warning(f"  ❌ {r['claim']}")
        logger.warning("")
        logger.warning("👉 用 ingest_urls.py 入库缺失页面：")
        logger.warning('   uv run python scripts/ingest/ingest_urls.py \\')
        logger.warning('     --category federal-ircc --collection ca_federal --force \\')
        logger.warning('     "https://www.canada.ca/en/..."')
        logger.warning("=" * 60)
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
