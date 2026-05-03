"""benchmark — G7-08 端到端直播模拟 & 20 题压测。

对 /live 页面的后端接口进行 20 题自动化压测，记录：
- 首 token 延迟 (first token latency)
- 完整回答时间 (total latency)
- 回答质量评分 (自动: 有回答=1, 有来源=+1, 非空回答=+1, 长度适中=+1, 有免责声明=+1 → 1-5)
- 系统稳定性 (无崩溃)

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
    """Send a streaming query and measure timing metrics."""
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
# Quality auto-scorer
# ============================================================


def auto_score(result: dict) -> int:
    """Auto-score a result (1-5 scale).

    Criteria:
        1 point: Has any answer (not error)
        1 point: Has ≥ 1 source
        1 point: Answer length ≥ 50 chars
        1 point: Answer length ≤ 2000 chars (not runaway generation)
        1 point: Contains 免责声明 or ⚠️
    """
    score = 0
    if result["status"] == "ok" and result["answer"]:
        score += 1
    if len(result["sources"]) >= 1:
        score += 1
    if len(result["answer"]) >= 50:
        score += 1
    if 50 <= len(result["answer"]) <= 2000:
        score += 1
    if "⚠️" in result["answer"] or "仅供参考" in result["answer"]:
        score += 1
    return max(score, 1)  # minimum 1


# ============================================================
# Main benchmark
# ============================================================


def run_benchmark(rapid: bool = False):
    """Run 20-question benchmark."""
    questions = load_questions()
    logger.info("Loaded {} questions, mode={}", len(questions), "rapid" if rapid else "normal")

    results = []
    errors = 0

    for i, q in enumerate(questions, 1):
        logger.info(
            "[{}/{}] {} — {}",
            i, len(questions), q["id"], q["question"][:50],
        )
        result = stream_query(q["question"])
        score = auto_score(result)

        results.append({
            **q,
            "first_token_s": result["first_token_s"],
            "total_s": result["total_s"],
            "token_count": result["token_count"],
            "source_count": len(result["sources"]),
            "answer_len": len(result["answer"]),
            "quality_score": score,
            "error": result.get("error"),
            "answer_preview": result["answer"][:120],
        })

        if result["status"] == "error":
            errors += 1
            logger.warning("  ❌ Error: {}", result.get("error"))
        else:
            logger.info(
                "  ✅ first_token={:.1f}s total={:.1f}s score={}/5 sources={}",
                result["first_token_s"], result["total_s"],
                score, len(result["sources"]),
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
    avg_quality = (
        sum(r["quality_score"] for r in ok_results) / len(ok_results)
        if ok_results else 0
    )

    print("\n" + "=" * 70)
    print(f"  G7-08 端到端压测报告")
    print(f"  Persona: {PERSONA_SLUG}")
    print(f"  Questions: {total}")
    print(f"  Errors: {errors}")
    print(f"  Avg First Token: {avg_first_token:.1f}s")
    print(f"  Avg Total Time: {avg_total:.1f}s")
    print(f"  Avg Quality: {avg_quality:.1f}/5")
    print("=" * 70)

    # Per-question detail
    for r in results:
        status = "❌" if r.get("error") else "✅"
        print(
            f"  {status} [{r['id']}] "
            f"first={r['first_token_s']:.1f}s "
            f"total={r['total_s']:.1f}s "
            f"score={r['quality_score']}/5 "
            f"sources={r['source_count']} "
            f"tokens={r['token_count']} "
            f"— {r['question'][:40]}..."
        )

    # Gate checks
    g1_pass = sum(1 for r in ok_results if r["source_count"] >= 1) / total >= 0.9 if total > 0 else False
    g2_first = avg_first_token <= 2.0
    g2_total = avg_total <= 15.0
    g2_pass = g2_first and g2_total
    g4_pass = errors == 0

    print(f"\n  {'✅' if g1_pass else '❌'} G1 知识库覆盖率 ≥ 90%")
    print(f"  {'✅' if g2_first else '❌'} G2 首 token ≤ 2s (实际: {avg_first_token:.1f}s)")
    print(f"  {'✅' if g2_total else '❌'} G2 完整回答 ≤ 15s (实际: {avg_total:.1f}s)")
    print(f"  {'✅' if avg_quality >= 3.5 else '❌'} 平均质量 ≥ 3.5/5 (实际: {avg_quality:.1f})")
    print(f"  {'✅' if g4_pass else '❌'} G4 无崩溃 ({errors} errors)")

    # Save report
    output_dir = Path(__file__).parent / "results"
    output_dir.mkdir(exist_ok=True)
    report_path = output_dir / f"benchmark_{int(time.time())}.json"
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump({
            "persona": PERSONA_SLUG,
            "mode": "rapid" if rapid else "normal",
            "total": total,
            "errors": errors,
            "avg_first_token_s": avg_first_token,
            "avg_total_s": avg_total,
            "avg_quality": avg_quality,
            "gates": {
                "g1_coverage": g1_pass,
                "g2_first_token": g2_first,
                "g2_total_latency": g2_total,
                "g4_no_errors": g4_pass,
            },
            "results": results,
        }, f, ensure_ascii=False, indent=2)
    logger.info("Report saved to {}", report_path)

    all_pass = g1_pass and g2_pass and g4_pass and avg_quality >= 3.5
    return 0 if all_pass else 1


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="G7-08 Live QA Benchmark")
    parser.add_argument(
        "--rapid", action="store_true",
        help="Rapid-fire mode: minimal delay between questions",
    )
    args = parser.parse_args()
    sys.exit(run_benchmark(rapid=args.rapid))
