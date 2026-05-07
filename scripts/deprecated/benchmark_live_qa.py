"""benchmark — G7-08 端到端直播模拟 & 20 题压测。

对 /live 页面的后端接口进行 20 题自动化压测，记录：
- 首 token 延迟 (first token latency)
- 完整回答时间 (total latency)
- 4 维质量评分 (retrieval / relevance / completeness / compliance, 0-100)
- 完整回答 + 来源详情（方便事后人工审核）
- 系统稳定性 (无崩溃)

4-dimensional weighted scoring (per question, 0-100 scale):
  - Retrieval (25%):   ≥1 source → 25 pts
  - Relevance (25%):   heuristic keyword/semantic match → 0-25 pts
  - Completeness (25%): answer length within 100-2000 chars → 0-25 pts
  - Compliance (25%):  disclaimer present + language match → 0-25 pts

Usage:
    uv run python scripts/live_qa/benchmark.py
    uv run python scripts/live_qa/benchmark.py --rapid  # 快速连续提问模式
"""

from __future__ import annotations

import argparse
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

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
LIVE_JSON = PROJECT_ROOT / "payload-v2" / "messages" / "zh" / "live.json"

# ============================================================
# Scoring weights (aligned with G4 benchmark)
# ============================================================

W_RETRIEVAL = 25
W_RELEVANCE = 25
W_COMPLETENESS = 25
W_COMPLIANCE = 25

_DISCLAIMER_MARKERS = ("免责声明", "Disclaimer", "disclaimer", "⚠️", "仅供参考")


# ============================================================
# Load questions
# ============================================================


def load_questions() -> list[dict]:
    """Load preset questions from live.json."""
    with open(LIVE_JSON, encoding="utf-8") as f:
        data = json.load(f)

    questions = []
    for key, text in data.get("questions", {}).items():
        if key.startswith("imm"):
            cat = "immigration"
        elif key.startswith("edu"):
            cat = "education"
        else:
            cat = "crossDomain"
        questions.append({"id": key, "category": cat, "question": text})
    return questions


# ============================================================
# Streaming query (measure first-token latency)
# ============================================================


def stream_query(question: str) -> dict:
    """Send a streaming query and measure timing metrics.

    Returns full answer text, complete source list, and timing data.
    """
    url = f"{ENGINE_URL}/engine/consulting/query/stream"
    payload = {
        "persona_slug": PERSONA_SLUG,
        "question": question,
        "top_k": TOP_K,
        "response_language": "zh",
    }

    start = time.perf_counter()
    first_token_time = None
    full_answer = ""
    sources = []
    error = None
    token_count = 0
    event_type = ""

    try:
        with httpx.stream(
            "POST", url, json=payload, timeout=120.0,
        ) as resp:
            if resp.status_code != 200:
                return {
                    "status": "error",
                    "error": f"HTTP {resp.status_code}",
                    "first_token_s": 0,
                    "total_s": 0,
                    "answer": "",
                    "sources": [],
                    "token_count": 0,
                }

            for line in resp.iter_lines():
                if not line:
                    continue

                if line.startswith("event: "):
                    event_type = line[7:].strip()
                    continue

                if line.startswith("data: "):
                    data_str = line[6:]
                    try:
                        data = json.loads(data_str)
                    except json.JSONDecodeError:
                        continue

                    if event_type == "token":
                        if first_token_time is None:
                            first_token_time = time.perf_counter() - start
                        full_answer += data.get("t", "")
                        token_count += 1

                    elif event_type == "retrieval_done":
                        sources = data.get("sources", [])

                    elif event_type == "done":
                        full_answer = data.get("answer", full_answer)
                        sources = data.get("sources", sources)

                    elif event_type == "error":
                        error = data.get("message", "Unknown error")

    except Exception as e:
        error = str(e)

    total_time = time.perf_counter() - start

    return {
        "status": "error" if error else "ok",
        "error": error,
        "first_token_s": first_token_time or total_time,
        "total_s": total_time,
        "answer": full_answer,
        "sources": sources,
        "token_count": token_count,
    }


# ============================================================
# 4-dimensional scorer (aligned with g4_benchmark.py)
# ============================================================


def score_question(
    answer: str, sources: list[dict], question: str,
) -> dict:
    """Score a question response using 4 weighted dimensions (0-100).

    Dimensions:
        1. Retrieval (25 pts): Has ≥1 source?
        2. Relevance (25 pts): Heuristic keyword overlap between Q and A.
        3. Completeness (25 pts): Answer length in ideal band (100-2000 chars).
        4. Compliance (25 pts): Disclaimer present + language consistency.
    """
    # 1. Retrieval: has sources?
    retrieval = W_RETRIEVAL if len(sources) >= 1 else 0

    # 2. Relevance: heuristic keyword match
    cjk_q = [ch for ch in question if '\u4e00' <= ch <= '\u9fff']
    if cjk_q:
        matched = sum(1 for ch in cjk_q if ch in answer)
        relevance_ratio = matched / max(len(cjk_q), 1)
    else:
        q_words = set(question.lower().split())
        a_words = set(answer.lower().split())
        stopwords = {
            "the", "a", "an", "is", "are", "in", "to", "of",
            "and", "for", "what", "how", "can", "do", "i", "my",
        }
        common = q_words & a_words - stopwords
        relevance_ratio = len(common) / max(len(q_words), 1)

    relevance = int(min(relevance_ratio * 2, 1.0) * W_RELEVANCE)

    # 3. Completeness: answer length band
    alen = len(answer)
    if 100 <= alen <= 2000:
        completeness = W_COMPLETENESS
    elif 50 <= alen < 100:
        completeness = int(W_COMPLETENESS * 0.6)
    elif alen > 2000:
        completeness = int(W_COMPLETENESS * 0.8)  # too verbose but ok
    else:
        completeness = int(W_COMPLETENESS * 0.3)

    # 4. Compliance: disclaimer + language consistency
    has_disclaimer = any(m in answer for m in _DISCLAIMER_MARKERS)
    # Chinese question → answer should contain CJK
    q_is_zh = sum(1 for ch in question if '\u4e00' <= ch <= '\u9fff') > len(question) * 0.2
    if q_is_zh:
        a_cjk = sum(1 for ch in answer if '\u4e00' <= ch <= '\u9fff')
        lang_match = a_cjk > 20
    else:
        lang_match = True

    compliance = 0
    if has_disclaimer:
        compliance += int(W_COMPLIANCE * 0.6)
    if lang_match:
        compliance += int(W_COMPLIANCE * 0.4)

    total = retrieval + relevance + completeness + compliance
    return {
        "retrieval": retrieval,
        "relevance": relevance,
        "completeness": completeness,
        "compliance": compliance,
        "total": total,
    }


# ============================================================
# Source summary (for JSON report readability)
# ============================================================


def _summarize_source(src: dict) -> dict:
    """Extract key fields from a source dict for the report."""
    return {
        "book_title": src.get("book_title", ""),
        "page_number": src.get("page_number"),
        "score": src.get("score"),
        "retrieval_origin": src.get("retrieval_origin", ""),
        "snippet": (src.get("full_content") or src.get("snippet") or "")[:300],
    }


# ============================================================
# Main benchmark
# ============================================================


def run_benchmark(rapid: bool = False):
    """Run 20-question benchmark with 4-dimensional scoring."""
    questions = load_questions()
    logger.info(
        "Loaded {} questions, mode={}", len(questions), "rapid" if rapid else "normal",
    )

    results = []
    errors = 0

    for i, q in enumerate(questions, 1):
        logger.info(
            "[{}/{}] {} — {}",
            i, len(questions), q["id"], q["question"][:50],
        )
        result = stream_query(q["question"])
        scores = score_question(result["answer"], result["sources"], q["question"])

        entry = {
            **q,
            "first_token_s": result["first_token_s"],
            "total_s": result["total_s"],
            "token_count": result["token_count"],
            "source_count": len(result["sources"]),
            "answer_len": len(result["answer"]),
            "scores": scores,
            "error": result.get("error"),
            # Full data for post-hoc review
            "answer_full": result["answer"],
            "sources_detail": [_summarize_source(s) for s in result["sources"]],
        }
        results.append(entry)

        if result["status"] == "error":
            errors += 1
            logger.warning("  ❌ Error: {}", result.get("error"))
        else:
            logger.info(
                "  ✅ score={}/100 (R={} Rv={} C={} Cm={}) "
                "first={:.1f}s total={:.1f}s sources={}",
                scores["total"],
                scores["retrieval"], scores["relevance"],
                scores["completeness"], scores["compliance"],
                result["first_token_s"], result["total_s"],
                len(result["sources"]),
            )

        # Delay between questions (skip in rapid mode)
        if not rapid and i < len(questions):
            time.sleep(2.0)
        elif rapid:
            time.sleep(0.3)

    # ── Report ──
    total = len(results)
    ok_results = [r for r in results if not r.get("error")]

    avg_first_token = (
        sum(r["first_token_s"] for r in ok_results) / len(ok_results)
        if ok_results else 0
    )
    avg_total = (
        sum(r["total_s"] for r in ok_results) / len(ok_results)
        if ok_results else 0
    )
    avg_score = (
        sum(r["scores"]["total"] for r in ok_results) / len(ok_results)
        if ok_results else 0
    )
    min_score = min((r["scores"]["total"] for r in ok_results), default=0)
    max_score = max((r["scores"]["total"] for r in ok_results), default=0)

    # Per-dimension averages
    dim_avgs = {}
    for dim in ("retrieval", "relevance", "completeness", "compliance"):
        dim_avgs[dim] = (
            sum(r["scores"][dim] for r in ok_results) / len(ok_results)
            if ok_results else 0
        )

    print("\n" + "=" * 70)
    print(f"  G7-08 端到端压测报告 (4 维评分)")
    print(f"  Persona: {PERSONA_SLUG}")
    print(f"  Questions: {total}")
    print(f"  Errors: {errors}")
    print(f"  Avg Score: {avg_score:.1f}/100 (min={min_score}, max={max_score})")
    print(f"  Avg First Token: {avg_first_token:.1f}s")
    print(f"  Avg Total Time: {avg_total:.1f}s")
    print("=" * 70)

    # Dimension breakdown
    print(f"\n  Dimension Breakdown (avg of /{W_RETRIEVAL} each):")
    for dim, avg_val in dim_avgs.items():
        bar_len = int(avg_val / 25 * 20)
        bar = "█" * bar_len + "░" * (20 - bar_len)
        print(f"    {dim:<14} {bar} {avg_val:.1f}/{W_RETRIEVAL}")

    # Per-question detail
    print(f"\n  Per-question scores:")
    print(f"  {'ID':<8} {'Score':>5} {'R':>3} {'Rv':>3} {'C':>3} {'Cm':>3} "
          f"{'1st':>5} {'Tot':>5} {'Src':>3} Question")
    print(f"  {'-'*8} {'-'*5} {'-'*3} {'-'*3} {'-'*3} {'-'*3} "
          f"{'-'*5} {'-'*5} {'-'*3} {'-'*30}")
    for r in results:
        status = "❌" if r.get("error") else "  "
        s = r["scores"]
        print(
            f"  {status}{r['id']:<6} {s['total']:>5} "
            f"{s['retrieval']:>3} {s['relevance']:>3} "
            f"{s['completeness']:>3} {s['compliance']:>3} "
            f"{r['first_token_s']:>5.1f} {r['total_s']:>5.1f} "
            f"{r['source_count']:>3} {r['question'][:30]}..."
        )

    # Gate checks
    coverage = (
        sum(1 for r in ok_results if r["source_count"] >= 1) / total
        if total > 0 else 0
    )
    g1_pass = coverage >= 0.9
    g2_first = avg_first_token <= 2.0
    g2_total = avg_total <= 15.0
    g4_pass = errors == 0
    quality_pass = avg_score >= 75

    print(f"\n  Gate Results:")
    print(f"  {'✅' if g1_pass else '❌'} G1 知识库覆盖率 ≥ 90% (实际: {coverage*100:.0f}%)")
    print(f"  {'✅' if g2_first else '❌'} G2 首 token ≤ 2s (实际: {avg_first_token:.1f}s)")
    print(f"  {'✅' if g2_total else '❌'} G2 完整回答 ≤ 15s (实际: {avg_total:.1f}s)")
    print(f"  {'✅' if quality_pass else '❌'} 质量 ≥ 75/100 (实际: {avg_score:.1f})")
    print(f"  {'✅' if g4_pass else '❌'} G4 无崩溃 ({errors} errors)")

    # Save report
    output_dir = Path(__file__).parent / "results"
    output_dir.mkdir(exist_ok=True)
    report_path = output_dir / f"benchmark_{int(time.time())}.json"
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump({
            "version": "g7-v2",
            "persona": PERSONA_SLUG,
            "mode": "rapid" if rapid else "normal",
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
            "total": total,
            "errors": errors,
            "avg_score": round(avg_score, 1),
            "min_score": min_score,
            "max_score": max_score,
            "avg_first_token_s": round(avg_first_token, 2),
            "avg_total_s": round(avg_total, 2),
            "dimension_averages": {
                k: round(v, 1) for k, v in dim_avgs.items()
            },
            "gates": {
                "g1_coverage": g1_pass,
                "g2_first_token": g2_first,
                "g2_total_latency": g2_total,
                "g4_no_errors": g4_pass,
                "quality_75": quality_pass,
            },
            "results": results,
        }, f, ensure_ascii=False, indent=2)
    logger.info("Report saved to {}", report_path)

    all_pass = g1_pass and g2_total and g4_pass and quality_pass
    return 0 if all_pass else 1


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="G7-08 Live QA Benchmark")
    parser.add_argument(
        "--rapid", action="store_true",
        help="Rapid-fire mode: minimal delay between questions",
    )
    args = parser.parse_args()
    sys.exit(run_benchmark(rapid=args.rapid))
