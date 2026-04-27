"""prompts — Standard benchmark test questions for Model Hub.

Responsibilities:
    - Provide default test questions for model benchmarking
    - Categorize questions by difficulty and type
    - Separate prompt content from execution logic

Ref: Sprint MH — Model Hub benchmark test questions
"""

from __future__ import annotations

from dataclasses import dataclass


# ============================================================
# Data classes
# ============================================================
@dataclass
class BenchmarkQuestion:
    """A standard test question for model benchmarking."""

    id: str  # e.g. "simple-01"
    question: str
    category: str  # "simple" | "reasoning" | "multilingual" | "rag"
    expected_length: str  # "short" | "medium" | "long"
    description: str  # What this question tests


# ============================================================
# Standard benchmark questions
# ============================================================
BENCHMARK_QUESTIONS: list[BenchmarkQuestion] = [
    # ── Simple factual ───────────────────────────────────────
    BenchmarkQuestion(
        id="simple-01",
        question="What is machine learning? Explain in 2-3 sentences.",
        category="simple",
        expected_length="short",
        description="Basic factual recall — tests if model can give a concise definition.",
    ),
    BenchmarkQuestion(
        id="simple-02",
        question="List 5 common activation functions used in neural networks.",
        category="simple",
        expected_length="short",
        description="List generation — tests structured output ability.",
    ),

    # ── Reasoning ────────────────────────────────────────────
    BenchmarkQuestion(
        id="reasoning-01",
        question="Compare and contrast supervised learning and unsupervised learning. "
                 "Give one real-world example for each.",
        category="reasoning",
        expected_length="medium",
        description="Comparison reasoning — tests analytical ability.",
    ),
    BenchmarkQuestion(
        id="reasoning-02",
        question="A model achieves 95% training accuracy but only 60% test accuracy. "
                 "What is likely happening and how would you fix it?",
        category="reasoning",
        expected_length="medium",
        description="Problem diagnosis — tests practical ML understanding.",
    ),
    BenchmarkQuestion(
        id="reasoning-03",
        question="Explain why gradient descent might get stuck in a local minimum. "
                 "What techniques can help overcome this?",
        category="reasoning",
        expected_length="medium",
        description="Deep reasoning — tests understanding of optimization concepts.",
    ),

    # ── Multilingual ─────────────────────────────────────────
    BenchmarkQuestion(
        id="multilingual-01",
        question="什么是梯度下降？请用简单的语言解释，并给出一个直观的比喻。",
        category="multilingual",
        expected_length="medium",
        description="Chinese comprehension — tests multilingual capability.",
    ),
    BenchmarkQuestion(
        id="multilingual-02",
        question="请比较 CNN 和 RNN 的区别，各自适合什么类型的任务？",
        category="multilingual",
        expected_length="medium",
        description="Chinese reasoning — tests analytical ability in Chinese.",
    ),

    # ── RAG-oriented ─────────────────────────────────────────
    BenchmarkQuestion(
        id="rag-01",
        question="Based on the following context, answer the question.\n\n"
                 "Context: 'The transformer architecture was introduced in the paper "
                 "\"Attention Is All You Need\" by Vaswani et al. in 2017. It replaced "
                 "recurrent layers with self-attention mechanisms, enabling parallelization "
                 "and achieving state-of-the-art results in machine translation.'\n\n"
                 "Question: What did the transformer architecture replace and why was it beneficial?",
        category="rag",
        expected_length="medium",
        description="Context-grounded QA — tests faithfulness to provided context.",
    ),
    BenchmarkQuestion(
        id="rag-02",
        question="Based on the following context, answer the question.\n\n"
                 "Context: 'Batch normalization normalizes the input of each layer to "
                 "reduce internal covariate shift. This allows higher learning rates "
                 "and reduces sensitivity to initialization. It was proposed by Ioffe "
                 "and Szegedy in 2015.'\n\n"
                 "Question: What problem does batch normalization solve and who proposed it?",
        category="rag",
        expected_length="short",
        description="Precise extraction — tests if model sticks to context facts.",
    ),
]


# ============================================================
# Helpers
# ============================================================
def get_benchmark_questions(
    category: str | None = None,
) -> list[BenchmarkQuestion]:
    """Get benchmark questions, optionally filtered by category.

    Args:
        category: Optional filter — "simple", "reasoning", "multilingual", "rag".

    Returns:
        List of BenchmarkQuestion.
    """
    if category:
        return [q for q in BENCHMARK_QUESTIONS if q.category == category]
    return list(BENCHMARK_QUESTIONS)


def question_to_dict(q: BenchmarkQuestion) -> dict:
    """Serialize BenchmarkQuestion to JSON-safe dict."""
    return {
        "id": q.id,
        "question": q.question,
        "category": q.category,
        "expectedLength": q.expected_length,
        "description": q.description,
    }
