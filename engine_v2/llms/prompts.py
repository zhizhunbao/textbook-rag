"""prompts — Static registry data and benchmark questions for Model Hub.

Responsibilities:
    - OLLAMA_TO_HF: Ollama name → HuggingFace repo mapping (name lookup only)
    - CATEGORY_RULES: model category classification rules
    - KNOWN_DESCRIPTIONS: human-readable model descriptions (hand-written)
    - BENCHMARK_QUESTIONS: standard test questions for model benchmarking

All content in this file is intentionally static / hand-maintained.
catalog.py contains zero hardcoded metadata — it imports everything from here.

Ref: Sprint MH — Model Hub benchmark test questions
"""

from __future__ import annotations

from dataclasses import dataclass


# ============================================================
# Ollama name → HuggingFace repo mapping
# ============================================================
# 只维护名称映射关系，不含任何模型元数据
# Only maintains name mapping — zero model metadata here
OLLAMA_TO_HF: dict[str, str] = {
    # Qwen family — latest gen (Alibaba)
    "qwen3.6": "Qwen/Qwen3.6-{size}B",
    "qwen3.5": "Qwen/Qwen3.5-{size}B",
    "qwen3": "Qwen/Qwen3-{size}B",
    "qwq": "Qwen/QwQ-32B",           # latest Qwen reasoning model
    # Llama family — latest gen (Meta)
    "llama4-scout": "meta-llama/Llama-4-Scout-17B-16E-Instruct",
    # Gemma family — latest gen (Google)
    "gemma4": "google/gemma-4-{size}-it",
    # Phi family — latest gen (Microsoft)
    "phi4-mini": "microsoft/Phi-4-mini-instruct",
    "phi4": "microsoft/phi-4",
    # DeepSeek — latest reasoning
    "deepseek-r1": "deepseek-ai/DeepSeek-R1-Distill-Qwen-{size}B",
    # Mistral — latest gen
    "mistral-small": "mistralai/Mistral-Small-3.1-24B-Instruct-2503",
    "devstral": "mistralai/Devstral-Small-2505",
    # ── Vision / VLM models ───────────────────────────────────────────────────
    "llama3.2-vision": "meta-llama/Llama-3.2-11B-Vision-Instruct",
    "llava": "liuhaotian/llava-v1.6-mistral-7b",
    "minicpm-v": "openbmb/MiniCPM-V-2_6",
    "moondream": "vikhyatk/moondream2",
    # ── Embedding models ──────────────────────────────────────────────────────
    "nomic-embed-text": "nomic-ai/nomic-embed-text-v1.5",
    "mxbai-embed-large": "mixedbread-ai/mxbai-embed-large-v1",
    "all-minilm": "sentence-transformers/all-MiniLM-L6-v2",
    "bge-m3": "BAAI/bge-m3",
}


# ============================================================
# Category classification rules
# ============================================================
# 模型分类规则 — 根据模型名称和参数量自动分类
CATEGORY_RULES: dict[str, list[str]] = {
    "reasoning": ["deepseek-r1", "qwq"],
    "lightweight": [],  # auto: parameter_size < 2B
    "specialized": [
        "devstral",  # coding-focused
    ],
    # Everything else → "recommended"
}


# ============================================================
# Category display labels (used by /library/categories endpoint)
# ============================================================
CATEGORIES: dict[str, str] = {
    "recommended": "Recommended",
    "reasoning": "Reasoning",
    "lightweight": "Lightweight",
    "specialized": "Specialized",
}


# ============================================================
# Best-for tag lookup tables (size-tiered by model family)
# ============================================================
# Each entry: list of (max_param_b, tags) — first match wins; last entry = ∞
BEST_FOR_BY_FAMILY: dict[str, list[tuple[float, list[str]]]] = {
    "qwen":    [(2, ["Study", "Learning", "Q&A", "Homework", "Quick testing"]),
                (4, ["Study", "Chat", "Q&A", "Tutoring", "RAG", "Analysis"]),
                (8, ["Analysis", "Summarization", "RAG", "Report", "Study", "Writing", "Translation"]),
                (999, ["Analysis", "Report", "Insight", "Long-form", "Writing", "Research", "Compliance"])],
    "llama":   [(3, ["Study", "Learning", "Chat", "Q&A", "Homework"]),
                (8, ["Chat", "RAG", "Analysis", "Study", "Tutoring", "Summarization"]),
                (999, ["Analysis", "Report", "Content", "Research", "Compliance", "Governance"])],
    "gemma":   [(1, ["Study", "Learning", "Q&A", "Homework", "Quick testing"]),
                (4, ["Study", "Chat", "Summarization", "RAG", "Analysis"]),
                (999, ["Analysis", "Research", "Multilingual", "Writing", "Report", "Compliance"])],
    "phi":     [(999, ["Reasoning", "STEM", "Math", "Code", "Analysis", "Study", "Calculation"])],
    "mistral": [(8, ["Chat", "Study", "Multilingual", "Translation", "Writing"]),
                (999, ["Analysis", "RAG", "Compliance", "Multilingual", "Writing", "Content"])],
    "devstral":[(999, ["Chat", "Study", "Multilingual", "Translation", "Writing"])],
    "smollm":  [(999, ["Study", "Learning", "Quick testing", "Homework"])],
}

# Generic fallback tiers (no family match)
BEST_FOR_GENERIC: list[tuple[float, list[str]]] = [
    (2, ["Study", "Learning", "Q&A", "Quick testing"]),
    (7, ["Analysis", "Chat", "RAG", "Summarization", "Study"]),
    (999, ["Analysis", "Report", "Research", "Content", "Writing", "Compliance"]),
]


# ============================================================
# Human-readable model descriptions
# ============================================================
# Keyed by Ollama model name prefix (longest match wins).
# 按 Ollama 模型名前缀匹配，最长前缀优先。
# HuggingFace API descriptions are blank for most major models —
# these are hand-written to give users real, actionable information.
KNOWN_DESCRIPTIONS: dict[str, str] = {
    # ── Qwen3.6 (MoE) ────────────────────────────────────────────────────────
    "qwen3.6:35b": "MoE architecture: 35B total params but only 3B active per token — fast like a small model, capable like a large one. Best for Chinese/English bilingual chat, long-context RAG, and tool calling.",
    "qwen3.6:27b": "MoE architecture: 27B total params with a small active subset — efficient inference at near-27B quality. Strong at Chinese/English bilingual tasks and structured output.",
    # ── QwQ (Qwen reasoning) ──────────────────────────────────────────────────
    "qwq": "Qwen team's 32B reasoning model trained with RL for chain-of-thought. Comparable to OpenAI o1 on math and coding benchmarks. Ideal for complex multi-step reasoning, problem-solving, and research analysis.",
    # ── Qwen3 (dense) ────────────────────────────────────────────────────────
    "qwen3:0.6b": "Ultra-lightweight 0.6B dense model. Runs on any CPU. Good for simple Q&A, classification, and on-device use where memory is extremely limited.",
    "qwen3:1.7b": "1.7B dense model — fits in <4 GB RAM. Suitable for lightweight chat, summarization, and edge deployment.",
    "qwen3:4b": "4B dense model with strong Chinese/English bilingual capability. Good balance of speed and quality for general RAG and chat use cases.",
    "qwen3:8b": "8B dense model. Recommended general-purpose size: fast enough on consumer GPUs, strong at reasoning, tool calling, and multilingual tasks.",
    "qwen3:14b": "14B dense model. Near-frontier quality for Chinese/English tasks; supports 128K context. Ideal for complex RAG, document analysis, and structured output.",
    "qwen3:32b": "32B dense model. Top-tier open-weight performance for Chinese + English. Excellent at long-form reasoning, code generation, and multi-step analysis.",
    # ── LLaMA 3.x ────────────────────────────────────────────────────────────
    "llama3.2:1b": "Meta's 1B instruction-tuned model. Extremely fast, fits on CPU. Best for quick summarization, keyword extraction, and simple classification.",
    "llama3.2:3b": "Meta's 3B instruction-tuned model. Good balance of speed and quality for on-device use, light RAG, and basic chat.",
    "llama3.1:8b": "Meta's 8B flagship open model. Strong general reasoning, tool use, and multilingual support. Widely used as a base for fine-tuning.",
    "llama3.1:70b": "Meta's 70B model — near-GPT-4 quality on many benchmarks. Requires significant VRAM (>=40 GB). Best for complex reasoning and research.",
    "llama3.2-vision:11b": "11B multimodal model supporting image + text input. Can describe images, answer visual questions, and extract structured data from charts or documents.",
    "llama3.2-vision:90b": "90B multimodal model — highest quality vision-language understanding in the LLaMA family. Requires high-end GPU.",
    # ── Gemma 3 / 4 ──────────────────────────────────────────────────────────
    "gemma3:1b": "Google's 1B lightweight model. Optimized for on-device and edge use. Fast, low memory, good for simple instruction following.",
    "gemma3:4b": "Google's 4B model. Capable instruction follower with multilingual support. Good for general chat, summarization, and lightweight RAG.",
    "gemma3:12b": "Google's 12B model. Strong at multilingual tasks, document understanding, and coding. Supports long context.",
    "gemma3:27b": "Google's largest open Gemma model. Near-frontier quality for text generation, reasoning, and structured output.",
    "gemma4:4b": "Google's multimodal 4B model (Gemma 4). Supports image + text input with strong vision understanding at a small footprint.",
    "gemma4:12b": "Google's multimodal 12B model (Gemma 4). Excellent at visual reasoning, document understanding, and multilingual tasks.",
    # ── Phi ──────────────────────────────────────────────────────────────────
    "phi4:14b": "Microsoft's 14B model achieving near-frontier reasoning. Outperforms many larger models on STEM, math, and code benchmarks. Efficient for its size.",
    "phi4-mini:3.8b": "Microsoft's 3.8B compact reasoning model. Punches well above its weight on math and coding tasks. Great for resource-constrained environments.",
    "phi3:3.8b": "Microsoft's 3.8B instruction model. Strong on reasoning and code for its size. Good for developer workloads on limited hardware.",
    # ── DeepSeek ─────────────────────────────────────────────────────────────
    "deepseek-r1:7b": "DeepSeek's 7B reasoning model distilled from R1. Trained with reinforcement learning for step-by-step chain-of-thought. Strong on math, logic, and coding.",
    "deepseek-r1:14b": "14B distilled R1 reasoning model. Near-GPT-o1 performance on AIME and MATH benchmarks. Ideal for complex problem-solving and scientific Q&A.",
    "deepseek-r1:32b": "32B distilled R1 model. Top open-weight reasoning performance. Excels at multi-step math, competitive programming, and research-grade analysis.",
    "deepseek-r1:70b": "70B distilled R1 model — the most capable open reasoning model available. Requires 40+ GB VRAM. Best for frontier-level reasoning tasks.",
    # ── Mistral ──────────────────────────────────────────────────────────────
    "mistral:7b": "Mistral AI's 7B instruction model. Fast, efficient, and strong at instruction following and multilingual text. Popular base for fine-tuning.",
    "mixtral:8x7b": "MoE model: 8 experts x 7B, ~13B active per token. Much faster than a 47B dense model at near-equivalent quality. Great for diverse workloads.",
    "mistral-nemo:12b": "Mistral x NVIDIA 12B model with 128K context. Excellent at long-document RAG, agentic tasks, and multilingual use.",
    "devstral:24b": "Mistral's coding-specialized 24B MoE model. Tops SWE-bench Verified for open models. Purpose-built for code generation, review, and debugging.",
    # ── Embedding models ──────────────────────────────────────────────────────
    "nomic-embed-text": "High-performance text embedding optimized for RAG. Supports 8K token context — far longer than most embedding models. Great for dense retrieval over long documents.",
    "mxbai-embed-large": "Mixedbread AI's SOTA embedding model. Outperforms OpenAI text-embedding-3-large on MTEB at zero cost. Best for semantic search and similarity tasks.",
    "bge-m3": "BAAI's multilingual embedding model supporting 100+ languages and three retrieval modes: dense, sparse (BM25-style), and multi-vector. Excellent for cross-lingual RAG.",
    "all-minilm": "Ultra-fast 23M parameter embedding model. Excellent for real-time semantic search where speed matters more than peak accuracy.",
    # ── Vision / Multimodal ───────────────────────────────────────────────────
    "llava:7b": "7B vision-language model. Understands images, answers visual questions, and can describe charts, screenshots, and photos.",
    "llava:13b": "13B vision-language model with improved image understanding vs the 7B variant. Good for OCR, document image analysis, and visual Q&A.",
    "minicpm-v": "MiniCPM-V multimodal model. Strong OCR and document understanding capability. Efficiently handles high-resolution images and multi-image inputs.",
    "moondream": "Tiny 1.9B vision model designed for edge deployment. Runs on CPU. Good for basic image captioning and simple visual Q&A on constrained hardware.",
}


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


def lookup_known_description(ollama_name: str) -> str:
    """Look up a hand-written description from KNOWN_DESCRIPTIONS by longest prefix.
    按最长前缀匹配查找手写描述。
    """
    if ollama_name in KNOWN_DESCRIPTIONS:
        return KNOWN_DESCRIPTIONS[ollama_name]
    best = ""
    for key in KNOWN_DESCRIPTIONS:
        if ollama_name.startswith(key) and len(key) > len(best):
            best = key
    return KNOWN_DESCRIPTIONS.get(best, "")
