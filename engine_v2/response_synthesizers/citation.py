"""Citation-aware response synthesizer.

Aligns with llama_index.core.response_synthesizers.
Uses get_response_synthesizer() factory with a custom citation prompt
that instructs the LLM to embed [N] markers for traceability.

LlamaIndex synthesizer modes:
    - COMPACT      → stuff as many chunks as fit, then refine
    - TREE_SUMMARIZE → recursive merge-summarise
    - REFINE       → iterate chunk-by-chunk
    - SIMPLE_SUMMARIZE → one-shot with all chunks
    - NO_TEXT      → return sources only

For textbook RAG we use COMPACT (default) with citation instructions.
"""

from __future__ import annotations

import logging

from llama_index.core.prompts import PromptTemplate
from llama_index.core.response_synthesizers import (
    BaseSynthesizer,
    get_response_synthesizer,
    ResponseMode,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Custom citation prompt
# ---------------------------------------------------------------------------
CITATION_QA_TEMPLATE = PromptTemplate(
    "You are a textbook assistant. Answer the question using ONLY the "
    "provided sources. For every claim, add a citation marker [N] "
    "referencing the source number.\n\n"
    "Sources:\n"
    "-----\n"
    "{context_str}\n"
    "-----\n\n"
    "Question: {query_str}\n\n"
    "Answer (with [N] citations):"
)

CITATION_REFINE_TEMPLATE = PromptTemplate(
    "You are refining an existing answer with additional context.\n"
    "Original question: {query_str}\n"
    "Existing answer: {existing_answer}\n"
    "Additional sources:\n"
    "-----\n"
    "{context_msg}\n"
    "-----\n\n"
    "Refine the answer using the new sources. Keep and update [N] citation "
    "markers. If the new context is not useful, return the original answer."
)


def get_citation_synthesizer(
    mode: ResponseMode = ResponseMode.COMPACT,
    streaming: bool = False,
) -> BaseSynthesizer:
    """Build a citation-aware response synthesizer.

    Uses LlamaIndex's get_response_synthesizer() factory with custom
    prompts that instruct the LLM to add [N] citation markers.

    Args:
        mode: LlamaIndex response mode (COMPACT, REFINE, TREE_SUMMARIZE, etc.)
        streaming: Whether to enable streaming generation.

    Returns:
        BaseSynthesizer configured for citation-aware generation.
    """
    synthesizer = get_response_synthesizer(
        response_mode=mode,
        streaming=streaming,
        text_qa_template=CITATION_QA_TEMPLATE,
        refine_template=CITATION_REFINE_TEMPLATE,
    )

    logger.info("CitationSynthesizer ready (mode=%s, streaming=%s)", mode, streaming)
    return synthesizer
