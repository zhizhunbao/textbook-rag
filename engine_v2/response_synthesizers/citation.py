"""citation — Citation-aware response synthesizer.

Responsibilities:
    - Build a COMPACT synthesizer with citation-aware prompt templates
    - Instruct LLM to organise answers by semantic paragraphs
    - Each paragraph's citations are grouped at the end (not scattered inline)

Ref: llama_index — get_response_synthesizer, ResponseMode
"""

from __future__ import annotations

from loguru import logger

from llama_index.core.response_synthesizers import (
    BaseSynthesizer,
    get_response_synthesizer,
    ResponseMode,
)

from engine_v2.llms.resolver import resolve_llm
from engine_v2.response_synthesizers.prompts import (
    CITATION_QA_TEMPLATE,
    CITATION_REFINE_TEMPLATE,
    build_custom_qa_template,
)


# ============================================================
# Factory
# ============================================================
def get_citation_synthesizer(
    mode: ResponseMode = ResponseMode.COMPACT,
    streaming: bool = False,
    model: str | None = None,
    provider: str | None = None,
    custom_system_prompt: str | None = None,
) -> BaseSynthesizer:
    """Build a citation-aware response synthesizer.

    Uses LlamaIndex's get_response_synthesizer() factory with custom
    prompts that instruct the LLM to produce semantic-paragraph answers
    with [N] citation markers grouped at paragraph end.

    Args:
        mode: LlamaIndex response mode (COMPACT, REFINE, TREE_SUMMARIZE, etc.)
        streaming: Whether to enable streaming generation.
        model: Optional model name override for LLM selection.
        provider: Optional provider override (e.g. 'ollama', 'azure').
        custom_system_prompt: Optional user-selected system prompt override.
            When provided, replaces the default CITATION_QA_TEMPLATE preamble
            while keeping the citation-format instructions and context/query
            placeholders intact.

    Returns:
        BaseSynthesizer configured for citation-aware generation.
    """
    llm = resolve_llm(model=model, streaming=streaming, provider=provider)

    # Use custom system prompt if provided, otherwise use the default
    qa_template = (
        build_custom_qa_template(custom_system_prompt)
        if custom_system_prompt
        else CITATION_QA_TEMPLATE
    )

    synthesizer = get_response_synthesizer(
        response_mode=mode,
        streaming=streaming,
        llm=llm,
        text_qa_template=qa_template,
        refine_template=CITATION_REFINE_TEMPLATE,
    )

    logger.info("CitationSynthesizer ready (mode={}, streaming={}, model={}, custom_prompt={})",
                mode, streaming, model or 'default', bool(custom_system_prompt))
    return synthesizer


