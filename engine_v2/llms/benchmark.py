"""benchmark — Model benchmark test execution.

Responsibilities:
    - Run a test question against a single model
    - Measure latency, token counts, and cost
    - Support serial execution across multiple models (4060 8GB constraint)
    - Stream results via SSE for real-time UI updates

Ref: Sprint MH — Model Hub benchmark testing
"""

from __future__ import annotations

import time
from dataclasses import dataclass

from loguru import logger

from engine_v2.settings import OLLAMA_BASE_URL


# ============================================================
# Data classes
# ============================================================
@dataclass
class BenchmarkResult:
    """Result of running a single benchmark test."""

    model: str
    question: str
    answer: str
    latency_ms: int
    input_tokens: int
    output_tokens: int
    total_tokens: int
    estimated_cost: float  # USD, 0.0 for free/local models
    error: str | None = None

    def to_dict(self) -> dict:
        """Serialize to JSON-safe dict."""
        return {
            "model": self.model,
            "question": self.question,
            "answer": self.answer,
            "latencyMs": self.latency_ms,
            "inputTokens": self.input_tokens,
            "outputTokens": self.output_tokens,
            "totalTokens": self.total_tokens,
            "estimatedCost": round(self.estimated_cost, 6),
            "error": self.error,
        }


# ============================================================
# Core benchmark execution
# ============================================================
async def run_benchmark(
    model: str,
    question: str,
    provider: str | None = None,
) -> BenchmarkResult:
    """Run a single benchmark test against a model.

    Measures latency, collects token counts, estimates cost.
    Uses the LLM resolver to route to the correct provider.

    Args:
        model: Model name (e.g. "qwen2.5:1.5b", "gpt-4o-mini").
        question: The test question to ask.
        provider: Optional provider hint.

    Returns:
        BenchmarkResult with all metrics.
    """
    from engine_v2.llms.resolver import resolve_llm

    logger.info("Benchmark — model={}, question={}", model, question[:60])

    try:
        llm = resolve_llm(model=model, provider=provider)
        start = time.perf_counter()
        response = await llm.acomplete(question)
        elapsed_ms = int((time.perf_counter() - start) * 1000)

        answer = str(response)

        # Extract token usage from response metadata if available
        raw = getattr(response, "raw", None) or {}
        usage = _extract_usage(raw, question, answer)

        # Estimate cost
        cost = _estimate_cost(model, usage["input"], usage["output"])

        result = BenchmarkResult(
            model=model,
            question=question,
            answer=answer,
            latency_ms=elapsed_ms,
            input_tokens=usage["input"],
            output_tokens=usage["output"],
            total_tokens=usage["total"],
            estimated_cost=cost,
        )

        logger.info(
            "Benchmark complete — model={}, latency={}ms, tokens={}, cost=${:.6f}",
            model, elapsed_ms, usage["total"], cost,
        )
        return result

    except Exception as exc:
        logger.error("Benchmark failed — model={}: {}", model, exc)
        return BenchmarkResult(
            model=model,
            question=question,
            answer="",
            latency_ms=0,
            input_tokens=0,
            output_tokens=0,
            total_tokens=0,
            estimated_cost=0.0,
            error=str(exc),
        )


# ============================================================
# Token extraction helpers
# ============================================================
def _extract_usage(
    raw: dict,
    question: str,
    answer: str,
) -> dict[str, int]:
    """Extract token usage from LLM response metadata.

    Tries provider-specific fields, falls back to character-based estimate.
    """
    # Ollama format
    if "prompt_eval_count" in raw:
        inp = raw.get("prompt_eval_count", 0)
        out = raw.get("eval_count", 0)
        return {"input": inp, "output": out, "total": inp + out}

    # OpenAI / Azure format
    usage = raw.get("usage", {})
    if usage:
        inp = usage.get("prompt_tokens", 0)
        out = usage.get("completion_tokens", 0)
        return {"input": inp, "output": out, "total": inp + out}

    # Fallback: rough estimate (~4 chars per token)
    inp = max(1, len(question) // 4)
    out = max(1, len(answer) // 4)
    return {"input": inp, "output": out, "total": inp + out}


# ============================================================
# Cost estimation
# ============================================================
# Known pricing (USD per 1K tokens)
_PRICING: dict[str, tuple[float, float]] = {
    # (input_per_1k, output_per_1k)
    "gpt-4o": (0.0025, 0.01),
    "gpt-4o-mini": (0.00015, 0.0006),
    "gpt-4.1-mini": (0.0004, 0.0016),
}


def _estimate_cost(
    model: str,
    input_tokens: int,
    output_tokens: int,
) -> float:
    """Estimate cost in USD. Returns 0.0 for local Ollama models."""
    # Ollama models (contain ':') are free
    if ":" in model:
        return 0.0

    pricing = _PRICING.get(model.lower())
    if not pricing:
        return 0.0

    input_cost = (input_tokens / 1000) * pricing[0]
    output_cost = (output_tokens / 1000) * pricing[1]
    return input_cost + output_cost
