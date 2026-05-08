"""g4_benchmark — Sprint G4 quality assessment: 10 P0 personas × 10 questions.

Reads data/eval/g4-p0-test-questions.json and evaluates each persona via
the /engine/consulting/query endpoint (non-streaming for simplicity).

4-dimensional weighted scoring (per question, 0-100 scale):
  - Retrieval (25%):   ≥1 source → 25 pts
  - Relevance (25%):   heuristic keyword/semantic match → 0-25 pts
  - Completeness (25%): answer length within 100-3000 chars → 0-25 pts
  - Compliance (25%):  disclaimer present + language match → 0-25 pts

Cross-domain questions (type=cross-domain) are evaluated differently:
  - Did the system redirect/refuse appropriately? (50%)
  - Did it mention the correct target persona? (50%)

Outputs per-persona scores and overall pass/fail (target: ≥ 75).

Usage:
    uv run python scripts/eval/g4_benchmark.py
    uv run python scripts/eval/g4_benchmark.py --personas edu-school-planning imm-pathways
    uv run python scripts/eval/g4_benchmark.py --dry-run
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
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
DATASET_PATH = PROJECT_ROOT / "data" / "eval" / "g4-p0-test-questions.json"
RESULTS_DIR = PROJECT_ROOT / "data" / "eval" / "results"
TOP_K = 5
QUERY_TIMEOUT = 120.0

# ============================================================
# Scoring weights
# ============================================================
W_RETRIEVAL = 25
W_RELEVANCE = 25
W_COMPLETENESS = 25
W_COMPLIANCE = 25

# ============================================================
# Load dataset
# ============================================================


def load_dataset(
    filter_personas: list[str] | None = None,
) -> list[dict]:
    """Load the G4 test dataset, optionally filtering by persona slugs."""
    with open(DATASET_PATH, encoding="utf-8") as f:
        data = json.load(f)

    personas = data["personas"]
    if filter_personas:
        personas = [p for p in personas if p["slug"] in filter_personas]

    return personas


# ============================================================
# Query engine (non-streaming)
# ============================================================


def query_persona(persona_slug: str, question: str) -> dict:
    """Send a non-streaming consulting query, return raw result."""
    url = f"{ENGINE_URL}/engine/consulting/query"
    payload = {
        "persona_slug": persona_slug,
        "question": question,
        "top_k": TOP_K,
        "response_language": "zh",
    }

    start = time.perf_counter()
    try:
        resp = httpx.post(url, json=payload, timeout=QUERY_TIMEOUT)
        latency = time.perf_counter() - start

        if resp.status_code != 200:
            return {
                "status": "error",
                "error": f"HTTP {resp.status_code}: {resp.text[:200]}",
                "latency_s": latency,
                "answer": "",
                "sources": [],
            }

        data = resp.json()
        return {
            "status": "ok",
            "error": None,
            "latency_s": latency,
            "answer": data.get("answer", ""),
            "sources": data.get("sources", []),
        }
    except Exception as e:
        latency = time.perf_counter() - start
        return {
            "status": "error",
            "error": str(e),
            "latency_s": latency,
            "answer": "",
            "sources": [],
        }


# ============================================================
# Scorers
# ============================================================

_DISCLAIMER_MARKERS = ("免责声明", "Disclaimer", "disclaimer", "⚠️")

# Redirect keywords indicating cross-domain refusal
_REDIRECT_KEYWORDS = (
    "建议您咨询", "推荐", "不在我的", "不属于", "超出", "请咨询",
    "refer you", "recommend", "not within", "outside my", "suggest",
    "其他顾问", "专业顾问", "其他专家",
)


def score_regular_question(
    answer: str, sources: list[dict], question: str,
) -> dict:
    """Score a high-freq or boundary question (0-100)."""
    # 1. Retrieval: has sources?
    retrieval = W_RETRIEVAL if len(sources) >= 1 else 0

    # 2. Relevance: heuristic keyword match
    #    Extract key nouns from question, check if answer mentions them
    q_chars = set(question)
    # Simple: check if at least 30% of question chars (CJK) appear in answer
    cjk_q = [ch for ch in question if '\u4e00' <= ch <= '\u9fff']
    if cjk_q:
        matched = sum(1 for ch in cjk_q if ch in answer)
        relevance_ratio = matched / max(len(cjk_q), 1)
    else:
        # English: check word overlap
        q_words = set(question.lower().split())
        a_words = set(answer.lower().split())
        common = q_words & a_words - {"the", "a", "an", "is", "are", "in", "to", "of", "and", "for", "what", "how", "can", "do", "i", "my"}
        relevance_ratio = len(common) / max(len(q_words), 1)

    relevance = int(min(relevance_ratio * 2, 1.0) * W_RELEVANCE)

    # 3. Completeness: answer length
    alen = len(answer)
    if 100 <= alen <= 3000:
        completeness = W_COMPLETENESS
    elif 50 <= alen < 100:
        completeness = int(W_COMPLETENESS * 0.6)
    elif alen > 3000:
        completeness = int(W_COMPLETENESS * 0.8)  # too verbose
    else:
        completeness = int(W_COMPLETENESS * 0.3)

    # 4. Compliance: disclaimer + language consistency
    has_disclaimer = any(m in answer for m in _DISCLAIMER_MARKERS)
    # Language match: Chinese question → answer should contain CJK
    q_is_zh = sum(1 for ch in question if '\u4e00' <= ch <= '\u9fff') > len(question) * 0.2
    if q_is_zh:
        a_cjk = sum(1 for ch in answer if '\u4e00' <= ch <= '\u9fff')
        lang_match = a_cjk > 20  # at least some Chinese in response
    else:
        lang_match = True  # English question, any language ok

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


def score_cross_domain_question(
    answer: str, sources: list[dict], question: str, expect_redirect: str | None,
) -> dict:
    """Score a cross-domain question. Key: did it redirect/refuse?"""
    # 1. Redirect detection (50%): did it mention redirect keywords?
    has_redirect = any(kw in answer for kw in _REDIRECT_KEYWORDS)
    redirect_score = 50 if has_redirect else 10

    # 2. Target mention (25%): did it mention the expected target persona?
    target_score = 0
    if expect_redirect:
        # Map slug to likely Chinese/English name fragments
        slug_hints = {
            "legal-labor": ["劳动", "labor", "Labour", "employment", "就业"],
            "fin-banking": ["银行", "banking", "bank", "金融", "财务"],
            "imm-pathways": ["移民", "immigration", "PR", "Express Entry", "EE"],
            "life-rental": ["租房", "rental", "lease", "房屋"],
            "edu-school-planning": ["学校", "教育", "school", "education", "择校"],
            "life-driving": ["驾照", "driving", "driver", "驾驶"],
            "health-insurance": ["医保", "health", "OHIP", "医疗"],
            "career-resume": ["简历", "resume", "career", "求职"],
        }
        hints = slug_hints.get(expect_redirect, [expect_redirect])
        if any(h.lower() in answer.lower() for h in hints):
            target_score = 25

    # 3. Compliance (25%): disclaimer present
    has_disclaimer = any(m in answer for m in _DISCLAIMER_MARKERS)
    compliance_score = 25 if has_disclaimer else 5

    total = redirect_score + target_score + compliance_score
    return {
        "redirect": redirect_score,
        "target_mention": target_score,
        "compliance": compliance_score,
        "total": total,
    }


# ============================================================
# Main benchmark
# ============================================================


def run_benchmark(
    filter_personas: list[str] | None = None,
    dry_run: bool = False,
) -> int:
    """Run the G4 benchmark. Returns 0 if all pass, 1 otherwise."""
    personas = load_dataset(filter_personas)
    logger.info(
        "G4 Benchmark — {} personas, {} questions total",
        len(personas),
        sum(len(p["questions"]) for p in personas),
    )

    all_results: list[dict] = []
    persona_summaries: list[dict] = []

    for pi, persona in enumerate(personas, 1):
        slug = persona["slug"]
        name = persona["name"]
        questions = persona["questions"]
        sep = "=" * 60
        logger.info(
            "\n{}\n[{}/{}] Persona: {} ({})\n{}",
            sep, pi, len(personas), name, slug, sep,
        )

        persona_scores: list[int] = []
        persona_results: list[dict] = []

        for qi, q in enumerate(questions, 1):
            qid = q["id"]
            question = q["question"]
            qtype = q["type"]

            logger.info(
                "  [{}/{}] [{}] {} — {}",
                qi, len(questions), qtype, qid, question[:50],
            )

            if dry_run:
                result = {
                    "status": "dry-run", "answer": "[DRY RUN]",
                    "sources": [], "latency_s": 0, "error": None,
                }
            else:
                result = query_persona(slug, question)

            if result["status"] == "error":
                logger.warning("    ❌ Error: {}", result.get("error"))
                scores = {"total": 0, "error": result.get("error")}
                persona_scores.append(0)
            elif qtype == "cross-domain":
                scores = score_cross_domain_question(
                    result["answer"], result["sources"],
                    question, q.get("expect_redirect"),
                )
                persona_scores.append(scores["total"])
            else:
                scores = score_regular_question(
                    result["answer"], result["sources"], question,
                )
                persona_scores.append(scores["total"])

            logger.info(
                "    → score={}/100 latency={:.1f}s sources={}",
                scores["total"], result["latency_s"], len(result["sources"]),
            )

            entry = {
                "persona_slug": slug,
                "question_id": qid,
                "question": question,
                "type": qtype,
                "latency_s": result["latency_s"],
                "source_count": len(result["sources"]),
                "answer_len": len(result["answer"]),
                "answer_preview": result["answer"][:200],
                "scores": scores,
                "error": result.get("error"),
            }
            persona_results.append(entry)
            all_results.append(entry)

            # Throttle between questions
            if not dry_run:
                time.sleep(1.0)

        # Persona summary
        avg_score = sum(persona_scores) / max(len(persona_scores), 1)
        pass_flag = avg_score >= 75
        persona_summaries.append({
            "slug": slug,
            "name": name,
            "question_count": len(questions),
            "avg_score": round(avg_score, 1),
            "pass": pass_flag,
            "min_score": min(persona_scores) if persona_scores else 0,
            "max_score": max(persona_scores) if persona_scores else 0,
        })

        status = "✅ PASS" if pass_flag else "❌ FAIL"
        logger.info(
            "\n  {} — {} avg={}/100\n",
            status, name, round(avg_score, 1),
        )

    # ── Overall Report ──
    overall_avg = sum(s["avg_score"] for s in persona_summaries) / max(len(persona_summaries), 1)
    all_pass = all(s["pass"] for s in persona_summaries)

    print("\n" + "=" * 70)
    print("  Sprint G4 — Quality Assessment Report")
    print(f"  Date: {time.strftime('%Y-%m-%d %H:%M')}")
    print(f"  Personas: {len(persona_summaries)}")
    print(f"  Questions: {len(all_results)}")
    print(f"  Overall Avg: {overall_avg:.1f}/100")
    print(f"  Target: ≥ 75")
    print(f"  Verdict: {'✅ ALL PASS' if all_pass else '❌ SOME FAIL'}")
    print("=" * 70)

    print("\n  Per-Persona Breakdown:")
    print(f"  {'Persona':<30} {'Avg':>6} {'Min':>6} {'Max':>6} {'Status':>8}")
    print(f"  {'-'*30} {'-'*6} {'-'*6} {'-'*6} {'-'*8}")
    for s in persona_summaries:
        status = "✅" if s["pass"] else "❌"
        print(
            f"  {s['name']:<30} {s['avg_score']:>6.1f} "
            f"{s['min_score']:>6} {s['max_score']:>6} {status:>8}"
        )

    print(f"\n  {'✅' if all_pass else '❌'} G4-01: All personas ≥ 75 → {all_pass}")
    print(f"  {'✅' if overall_avg >= 75 else '❌'} Overall avg ≥ 75 → {overall_avg:.1f}")

    # Save report
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    ts = int(time.time())
    report_path = RESULTS_DIR / f"g4_benchmark_{ts}.json"
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump({
            "version": "g4-v1",
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
            "personas_tested": len(persona_summaries),
            "total_questions": len(all_results),
            "overall_avg": round(overall_avg, 1),
            "all_pass": all_pass,
            "target_threshold": 75,
            "persona_summaries": persona_summaries,
            "results": all_results,
        }, f, ensure_ascii=False, indent=2)

    logger.info("Report saved to {}", report_path)
    return 0 if all_pass else 1


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Sprint G4 Quality Benchmark")
    parser.add_argument(
        "--personas", nargs="+",
        help="Filter to specific persona slugs (default: all 10)",
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Skip actual queries, just validate dataset loading",
    )
    args = parser.parse_args()
    sys.exit(run_benchmark(filter_personas=args.personas, dry_run=args.dry_run))
