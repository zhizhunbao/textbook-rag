"""verify_knowledge — G7-01 知识库覆盖率验证脚本。

从 messages/zh/live.json 读取 20 道预设问题，逐一调用 Engine
consulting/query 接口，检查返回 chunks 的相关性。
输出覆盖率报告 + 缺失文档列表。

Usage:
    uv run python scripts/live_qa/verify_knowledge.py
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

# ── Windows UTF-8 stdout ──
if sys.platform == "win32" and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

import httpx
from loguru import logger

# ============================================================
# Config
# ============================================================

ENGINE_URL = "http://127.0.0.1:8001"
PERSONA_SLUG = "live-study-immigration"
TOP_K = 5
# Minimum number of retrieved chunks to consider a "hit"
MIN_CHUNKS_FOR_HIT = 1
# Minimum score for a chunk to count as relevant
MIN_RELEVANCE_SCORE = 0.01

# ============================================================
# Load questions from i18n JSON
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
LIVE_JSON = PROJECT_ROOT / "payload-v2" / "messages" / "zh" / "live.json"


def load_questions() -> list[dict]:
    """Load 20 preset questions from live.json, grouped by category."""
    with open(LIVE_JSON, encoding="utf-8") as f:
        data = json.load(f)

    questions_dict = data.get("questions", {})
    categories = data.get("categories", {})

    questions = []
    for key, text in questions_dict.items():
        # Determine category from key prefix
        if key.startswith("imm"):
            cat_key = "immigration"
        elif key.startswith("edu"):
            cat_key = "education"
        elif key.startswith("mix"):
            cat_key = "crossDomain"
        else:
            cat_key = "unknown"

        questions.append({
            "id": key,
            "category": categories.get(cat_key, cat_key),
            "category_key": cat_key,
            "question": text,
        })

    return questions


# ============================================================
# Query Engine
# ============================================================


def query_engine(question: str) -> dict:
    """Send a query to the consulting endpoint and return results."""
    url = f"{ENGINE_URL}/engine/consulting/query"
    payload = {
        "persona_slug": PERSONA_SLUG,
        "question": question,
        "top_k": TOP_K,
        "response_language": "zh",
    }

    start = time.perf_counter()
    resp = httpx.post(url, json=payload, timeout=60.0)
    elapsed = time.perf_counter() - start

    if resp.status_code != 200:
        return {
            "status": "error",
            "error": f"HTTP {resp.status_code}: {resp.text[:200]}",
            "latency_s": elapsed,
            "sources": [],
            "answer": "",
        }

    data = resp.json()
    return {
        "status": "ok",
        "latency_s": elapsed,
        "sources": data.get("sources", []),
        "answer": data.get("answer", ""),
        "stats": data.get("stats", {}),
    }


# ============================================================
# Main verification
# ============================================================


def verify():
    """Run coverage verification on all preset questions."""
    questions = load_questions()
    logger.info("Loaded {} questions from {}", len(questions), LIVE_JSON.name)

    results = []
    hits = 0
    misses = 0

    for i, q in enumerate(questions, 1):
        logger.info(
            "[{}/{}] {} — {}",
            i, len(questions), q["id"], q["question"][:50],
        )
        result = query_engine(q["question"])

        # Count relevant chunks
        relevant_chunks = [
            s for s in result["sources"]
            if s.get("score", 0) >= MIN_RELEVANCE_SCORE
        ]
        is_hit = len(relevant_chunks) >= MIN_CHUNKS_FOR_HIT
        if is_hit:
            hits += 1
        else:
            misses += 1

        results.append({
            **q,
            "is_hit": is_hit,
            "chunk_count": len(result["sources"]),
            "relevant_count": len(relevant_chunks),
            "latency_s": result["latency_s"],
            "top_source": (
                result["sources"][0].get("book_title", "—")
                if result["sources"]
                else "NO CHUNKS"
            ),
            "answer_preview": result["answer"][:100] if result["answer"] else "",
            "error": result.get("error"),
        })

        # Brief delay to avoid overwhelming the engine
        time.sleep(0.5)

    # ── Report ──
    total = len(questions)
    coverage = hits / total * 100 if total > 0 else 0
    avg_latency = (
        sum(r["latency_s"] for r in results) / total if total > 0 else 0
    )

    print("\n" + "=" * 70)
    print(f"  G7-01 知识库覆盖率验证报告")
    print(f"  Persona: {PERSONA_SLUG}")
    print(f"  Total Questions: {total}")
    print(f"  Hits: {hits} ({coverage:.0f}%)")
    print(f"  Misses: {misses}")
    print(f"  Average Latency: {avg_latency:.1f}s")
    print("=" * 70)

    # Detailed results by category
    for cat_key in ["immigration", "education", "crossDomain"]:
        cat_results = [r for r in results if r["category_key"] == cat_key]
        cat_hits = sum(1 for r in cat_results if r["is_hit"])
        cat_total = len(cat_results)
        cat_pct = cat_hits / cat_total * 100 if cat_total > 0 else 0
        print(f"\n  [{cat_key}] {cat_hits}/{cat_total} ({cat_pct:.0f}%)")
        for r in cat_results:
            status = "✅" if r["is_hit"] else "❌"
            print(
                f"    {status} {r['id']}: {r['question'][:40]}... "
                f"({r['relevant_count']} chunks, {r['latency_s']:.1f}s) "
                f"→ {r['top_source']}"
            )

    # Missed questions detail
    missed = [r for r in results if not r["is_hit"]]
    if missed:
        print(f"\n  ⚠️  未命中问题 ({len(missed)} 题):")
        for r in missed:
            print(f"    - [{r['id']}] {r['question']}")
            if r.get("error"):
                print(f"      Error: {r['error']}")

    # Gate check
    gate_pass = coverage >= 90
    print(f"\n  {'✅' if gate_pass else '❌'} G1 Gate: 覆盖率 {coverage:.0f}% "
          f"{'≥' if gate_pass else '<'} 90%")

    # Save JSON report
    output_dir = Path(__file__).parent / "results"
    output_dir.mkdir(exist_ok=True)
    report_path = output_dir / f"coverage_report_{int(time.time())}.json"
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump({
            "persona": PERSONA_SLUG,
            "total": total,
            "hits": hits,
            "misses": misses,
            "coverage_pct": coverage,
            "avg_latency_s": avg_latency,
            "gate_pass": gate_pass,
            "results": results,
        }, f, ensure_ascii=False, indent=2)
    logger.info("Report saved to {}", report_path)

    return 0 if gate_pass else 1


if __name__ == "__main__":
    sys.exit(verify())
