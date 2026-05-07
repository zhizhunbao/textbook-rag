"""test_immigration_qa — Unified QA benchmark for consulting personas.

Dynamically fetches questions from the persona's suggestedQuestions via
Payload CMS API — no hardcoded question bank needed.

Supports two modes:
    --mode sync    Non-streaming /query endpoint (default, simpler)
    --mode stream  SSE streaming /query/stream endpoint (first-token latency)

Evaluates:
    1. Retrieval: has sources? collection origins? heading-only chunks?
    2. Relevance: keyword overlap between question and answer
    3. Completeness: answer length band
    4. Compliance: disclaimer + "Source N" citations

Usage:
    cd textbook-rag
    uv run python scripts/eval/test_immigration_qa.py                     # all Qs, sync
    uv run python scripts/eval/test_immigration_qa.py --limit 5           # first 5
    uv run python scripts/eval/test_immigration_qa.py --category core_concepts
    uv run python scripts/eval/test_immigration_qa.py --mode stream
    uv run python scripts/eval/test_immigration_qa.py --persona imm-pgwp
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import datetime
from pathlib import Path

# ── Windows UTF-8 stdout ──
if sys.platform == "win32" and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

import httpx

# ============================================================
# Config
# ============================================================

ENGINE_URL = "http://127.0.0.1:8001"
DEFAULT_PERSONA = "live-study-immigration"
TOP_K = 5
QUERY_TIMEOUT = 120.0
PAYLOAD_URL = "http://localhost:3001"  # Payload CMS (for fetching persona config)

# ============================================================
# Scoring constants
# ============================================================

W_RETRIEVAL = 25
W_RELEVANCE = 25
W_COMPLETENESS = 25
W_COMPLIANCE = 25
_DISCLAIMER_MARKERS = ("Disclaimer", "disclaimer", "⚠️", "仅供参考", "免责声明")


# ============================================================
# Fetch questions from Payload CMS
# ============================================================


def fetch_questions(persona_slug: str) -> list[dict]:
    """Fetch persona's suggestedQuestions from Payload CMS API.

    Queries Payload CMS directly (not the engine proxy) because
    the engine /personas endpoint strips suggestedQuestions.

    Returns list of dicts: [{category, label, question}, ...]
    """
    # Payload CMS runs on a different port than the engine
    payload_url = PAYLOAD_URL

    url = f"{payload_url}/api/consulting-personas"
    params = {
        "where[slug][equals]": persona_slug,
        "where[isEnabled][equals]": "true",
        "limit": "1",
    }

    resp = httpx.get(url, params=params, timeout=15.0)
    resp.raise_for_status()

    docs = resp.json().get("docs", [])
    if not docs:
        print(f"  ❌ Persona '{persona_slug}' not found in Payload CMS.")
        sys.exit(1)

    persona = docs[0]
    suggested = persona.get("suggestedQuestions") or []
    if not suggested:
        print(f"  ❌ Persona '{persona_slug}' has no suggestedQuestions.")
        sys.exit(1)

    questions = []
    for cat in suggested:
        cat_id = cat.get("id", "unknown")
        cat_label = cat.get("label", cat_id)
        for q in cat.get("questions", []):
            questions.append({
                "category": cat_id,
                "label": cat_label,
                "question": q,
            })

    return questions


# ============================================================
# Heuristics & scoring
# ============================================================


def _is_heading_chunk(text: str) -> bool:
    """Heuristic: chunk is likely a heading/title if short + single line."""
    text = text.strip()
    if len(text) < 50:
        return True
    if "\n" not in text and len(text) < 120:
        return True
    return False


def _score_4dim(question: str, answer: str, sources: list[dict]) -> dict:
    """4-dimensional scoring (0-100 scale)."""
    retrieval = W_RETRIEVAL if len(sources) >= 1 else 0

    q_words = set(question.lower().split())
    a_words = set(answer.lower().split())
    stopwords = {
        "the", "a", "an", "is", "are", "in", "to", "of", "and", "for",
        "what", "how", "can", "do", "i", "my", "it", "if", "or", "on",
    }
    q_content = q_words - stopwords
    ratio = min(len(q_content & a_words) / max(len(q_content), 1) * 1.5, 1.0) if q_content else 0.5
    relevance = int(ratio * W_RELEVANCE)

    alen = len(answer)
    if 100 <= alen <= 2000:
        completeness = W_COMPLETENESS
    elif 50 <= alen < 100:
        completeness = int(W_COMPLETENESS * 0.6)
    elif alen > 2000:
        completeness = int(W_COMPLETENESS * 0.8)
    else:
        completeness = int(W_COMPLETENESS * 0.3)

    compliance = 0
    if any(m in answer for m in _DISCLAIMER_MARKERS):
        compliance += int(W_COMPLIANCE * 0.5)
    if "Source" in answer:
        compliance += int(W_COMPLIANCE * 0.5)

    total = retrieval + relevance + completeness + compliance
    return {"retrieval": retrieval, "relevance": relevance,
            "completeness": completeness, "compliance": compliance, "total": total}


# ============================================================
# HTTP callers
# ============================================================


def _query_sync(persona_slug: str, question: str) -> dict:
    """Non-streaming POST /engine/consulting/query."""
    t0 = time.perf_counter()
    try:
        resp = httpx.post(
            f"{ENGINE_URL}/engine/consulting/query",
            json={"persona_slug": persona_slug, "question": question, "top_k": TOP_K},
            timeout=QUERY_TIMEOUT,
        )
        latency = time.perf_counter() - t0
        if resp.status_code != 200:
            return {"status": "error", "error": f"HTTP {resp.status_code}",
                    "latency_s": latency, "first_token_s": None,
                    "answer": "", "sources": []}
        data = resp.json()
        return {"status": "ok", "latency_s": latency, "first_token_s": None,
                "answer": data.get("answer", ""), "sources": data.get("sources", [])}
    except Exception as e:
        return {"status": "error", "error": str(e),
                "latency_s": time.perf_counter() - t0, "first_token_s": None,
                "answer": "", "sources": []}


def _query_stream(persona_slug: str, question: str) -> dict:
    """SSE streaming POST /engine/consulting/query/stream."""
    t0 = time.perf_counter()
    first_token_time = None
    full_answer = ""
    sources: list[dict] = []
    error = None
    event_type = ""

    try:
        with httpx.stream(
            "POST", f"{ENGINE_URL}/engine/consulting/query/stream",
            json={"persona_slug": persona_slug, "question": question, "top_k": TOP_K},
            timeout=QUERY_TIMEOUT,
        ) as resp:
            if resp.status_code != 200:
                return {"status": "error", "error": f"HTTP {resp.status_code}",
                        "latency_s": time.perf_counter() - t0,
                        "first_token_s": None, "answer": "", "sources": []}
            for line in resp.iter_lines():
                if not line:
                    continue
                if line.startswith("event: "):
                    event_type = line[7:].strip()
                    continue
                if line.startswith("data: "):
                    try:
                        data = json.loads(line[6:])
                    except json.JSONDecodeError:
                        continue
                    if event_type == "token":
                        if first_token_time is None:
                            first_token_time = time.perf_counter() - t0
                        full_answer += data.get("t", "")
                    elif event_type == "retrieval_done":
                        sources = data.get("sources", [])
                    elif event_type == "done":
                        full_answer = data.get("answer", full_answer)
                        sources = data.get("sources", sources)
                    elif event_type == "error":
                        error = data.get("message", "Unknown error")
    except Exception as e:
        error = str(e)

    return {"status": "error" if error else "ok", "error": error,
            "latency_s": time.perf_counter() - t0,
            "first_token_s": first_token_time, "answer": full_answer, "sources": sources}


# ============================================================
# Main test runner
# ============================================================


def run_test(
    persona_slug: str,
    questions: list[dict],
    category_filter: str | None,
    limit: int | None,
    mode: str,
) -> list[dict]:
    """Run questions and collect results."""
    query_fn = _query_stream if mode == "stream" else _query_sync

    # Filter by category if specified
    if category_filter:
        questions = [q for q in questions if q["category"] == category_filter]
        if not questions:
            print(f"  ❌ No questions in category '{category_filter}'")
            available = sorted(set(q["category"] for q in questions))
            print(f"     Available: {available}")
            sys.exit(1)

    if limit:
        questions = questions[:limit]

    results: list[dict] = []
    total_q = len(questions)

    for idx, qinfo in enumerate(questions, 1):
        q = qinfo["question"]
        short_q = q[:55] + "..." if len(q) > 55 else q
        print(f"  [{idx:>2}/{total_q}] {short_q}", end="", flush=True)

        resp = query_fn(persona_slug, q)
        answer = resp["answer"]
        sources = resp["sources"]
        has_answer = bool(answer and answer.strip().lower() != "empty response" and len(answer.strip()) > 20)

        # Analyze citations
        heading_count = 0
        origins: dict[str, int] = {}
        citation_details = []

        for i, src in enumerate(sources, 1):
            full_text = src.get("full_content") or src.get("text", "")
            origin = src.get("retrieval_origin", "unknown")
            origins[origin] = origins.get(origin, 0) + 1
            is_heading = _is_heading_chunk(full_text)
            if is_heading:
                heading_count += 1
            citation_details.append({
                "index": i, "text_len": len(full_text), "origin": origin,
                "retrieval_source": src.get("retrieval_source", "?"),
                "vector_score": src.get("vector_score", 0.0),
                "bm25_score": src.get("bm25_score", 0.0),
                "is_heading": is_heading,
                "preview": full_text[:100].replace("\n", " "),
            })

        scores = _score_4dim(q, answer, sources)

        results.append({
            "category": qinfo["category"],
            "category_label": qinfo["label"],
            "question": q,
            "answer_preview": answer[:300],
            "answer_len": len(answer),
            "source_count": len(sources),
            "has_answer": has_answer,
            "heading_chunks": heading_count,
            "origins": origins,
            "latency_s": round(resp["latency_s"], 2),
            "first_token_s": round(resp["first_token_s"], 2) if resp.get("first_token_s") else None,
            "scores": scores,
            "citations": citation_details,
            "error": resp.get("error"),
        })

        status = "✅" if has_answer else "❌"
        ft = f" ft={resp['first_token_s']:.1f}s" if resp.get("first_token_s") else ""
        hdg = f" hdg={heading_count}" if heading_count else ""
        print(f" {status} {scores['total']:>3}/100 {len(sources)}src {resp['latency_s']:.1f}s{ft}{hdg}")

        time.sleep(0.3)

    return results


# ============================================================
# Summary printer
# ============================================================


def print_summary(results: list[dict], mode: str) -> None:
    """Print human-readable summary."""
    total = len(results)
    if total == 0:
        print("No results.")
        return

    answered = sum(1 for r in results if r["has_answer"])
    with_sources = sum(1 for r in results if r["source_count"] > 0)
    heading_issues = sum(1 for r in results if r["heading_chunks"] > 0)
    errors = sum(1 for r in results if r["error"])
    avg_latency = sum(r["latency_s"] for r in results) / total
    avg_score = sum(r["scores"]["total"] for r in results) / total
    min_score = min(r["scores"]["total"] for r in results)
    max_score = max(r["scores"]["total"] for r in results)

    dim_avgs = {}
    for dim in ("retrieval", "relevance", "completeness", "compliance"):
        dim_avgs[dim] = sum(r["scores"][dim] for r in results) / total

    all_origins: dict[str, int] = {}
    for r in results:
        for origin, count in r["origins"].items():
            all_origins[origin] = all_origins.get(origin, 0) + count

    print("\n" + "=" * 70)
    print(f"  QA Benchmark — {total} questions ({mode} mode)")
    print("=" * 70)

    print(f"\n  📊 Score:    {avg_score:.1f}/100 (min={min_score}, max={max_score})")
    print(f"  ✅ Answered: {answered}/{total} ({answered*100//total}%)")
    print(f"  📚 Sources:  {with_sources}/{total} | 🏷️ Heading chunks: {heading_issues}")
    print(f"  ❌ Errors:   {errors} | ⏱️ Avg latency: {avg_latency:.1f}s")

    ft_results = [r for r in results if r.get("first_token_s") is not None]
    if ft_results:
        avg_ft = sum(r["first_token_s"] for r in ft_results) / len(ft_results)
        print(f"  ⚡ Avg first token: {avg_ft:.1f}s")

    print(f"\n  Dimensions:")
    for dim, avg_val in dim_avgs.items():
        bar = "█" * int(avg_val / 25 * 20) + "░" * (20 - int(avg_val / 25 * 20))
        print(f"    {dim:<14} {bar} {avg_val:.1f}/25")

    if all_origins:
        total_cit = sum(all_origins.values())
        print(f"\n  Collection Origins ({total_cit} citations):")
        for origin, count in sorted(all_origins.items(), key=lambda x: -x[1]):
            pct = count * 100 // total_cit
            print(f"    {origin:<30} {count:>3} ({pct}%)")

    # Per-category
    by_cat: dict[str, list[dict]] = {}
    for r in results:
        by_cat.setdefault(r["category"], []).append(r)

    print(f"\n  Per-Category:")
    print(f"  {'Category':<32} {'Score':>5} {'Ans':>5} {'Hdg':>4} {'Lat':>6}")
    print(f"  {'-'*32} {'-'*5} {'-'*5} {'-'*4} {'-'*6}")
    for cat_id, cr in by_cat.items():
        n = len(cr)
        label = cr[0].get("category_label", cat_id)[:32]
        score = sum(r["scores"]["total"] for r in cr) / n
        ans = sum(1 for r in cr if r["has_answer"])
        hdg = sum(r["heading_chunks"] for r in cr)
        lat = sum(r["latency_s"] for r in cr) / n
        print(f"  {label:<32} {score:>5.1f} {ans:>3}/{n} {hdg:>4} {lat:>5.1f}s")

    # Gates
    coverage = with_sources / total if total > 0 else 0
    print(f"\n  Gates:")
    print(f"  {'✅' if coverage >= 0.9 else '❌'} Coverage ≥ 90% ({coverage*100:.0f}%)")
    print(f"  {'✅' if avg_latency <= 15 else '❌'} Latency ≤ 15s ({avg_latency:.1f}s)")
    print(f"  {'✅' if errors == 0 else '❌'} No errors ({errors})")
    print(f"  {'✅' if avg_score >= 75 else '❌'} Score ≥ 75 ({avg_score:.1f})")

    problems = [r for r in results if not r["has_answer"] or r["heading_chunks"] > 1
                or r["error"] or r["scores"]["total"] < 50]
    if problems:
        print(f"\n  ⚠️ Problems ({len(problems)}):")
        for r in problems[:10]:
            issues = []
            if not r["has_answer"]: issues.append("NO_ANS")
            if r["heading_chunks"] > 1: issues.append(f"HDG={r['heading_chunks']}")
            if r["error"]: issues.append("ERR")
            if r["scores"]["total"] < 50: issues.append(f"LOW={r['scores']['total']}")
            print(f"    [{', '.join(issues)}] {r['question'][:60]}")

    print("=" * 70)


# ============================================================
# Entry point
# ============================================================


def main():
    parser = argparse.ArgumentParser(description="QA benchmark for consulting personas")
    parser.add_argument("--limit", type=int, default=None, help="Max questions")
    parser.add_argument("--category", type=str, default=None, help="Filter by category ID")
    parser.add_argument("--mode", choices=["sync", "stream"], default="sync")
    parser.add_argument("--persona", type=str, default=DEFAULT_PERSONA)
    args = parser.parse_args()

    print(f"\n  🚀 QA Benchmark")
    print(f"     Engine:  {ENGINE_URL}")
    print(f"     Persona: {args.persona}")
    print(f"     Mode:    {args.mode}")

    # Fetch questions dynamically from persona config
    print(f"     Fetching questions from Payload CMS...", end="", flush=True)
    questions = fetch_questions(args.persona)
    cats = sorted(set(q["category"] for q in questions))
    print(f" {len(questions)} questions in {len(cats)} categories")
    print(f"     Categories: {', '.join(cats)}")
    print(f"     Limit:   {args.limit or f'all {len(questions)}'}")
    print()

    results = run_test(
        persona_slug=args.persona,
        questions=questions,
        category_filter=args.category,
        limit=args.limit,
        mode=args.mode,
    )
    print_summary(results, args.mode)

    # Save JSON report
    out_dir = Path(__file__).parent / "results"
    out_dir.mkdir(exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_path = out_dir / f"qa_{args.persona}_{ts}.json"

    with open(out_path, "w", encoding="utf-8") as f:
        json.dump({
            "version": "v3",
            "persona": args.persona,
            "mode": args.mode,
            "timestamp": datetime.now().isoformat(),
            "total": len(results),
            "avg_score": round(sum(r["scores"]["total"] for r in results) / max(len(results), 1), 1),
            "results": results,
        }, f, indent=2, ensure_ascii=False)

    print(f"\n  📁 Saved to {out_path}")
    avg = sum(r["scores"]["total"] for r in results) / max(len(results), 1)
    sys.exit(0 if avg >= 75 else 1)


if __name__ == "__main__":
    main()
