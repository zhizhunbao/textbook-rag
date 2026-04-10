"""citation — Citation-aware response synthesizer.

Responsibilities:
    - Build a COMPACT synthesizer with citation-aware prompt templates
    - Instruct LLM to organise answers by semantic paragraphs
    - Each paragraph's citations are grouped at the end (not scattered inline)

Ref: llama_index — get_response_synthesizer, ResponseMode
"""

from __future__ import annotations

from loguru import logger

from llama_index.core.prompts import PromptTemplate
from llama_index.core.response_synthesizers import (
    BaseSynthesizer,
    get_response_synthesizer,
    ResponseMode,
)

from engine_v2.llms.resolver import resolve_llm

# ============================================================
# Citation QA prompt — semantic-paragraph style
# ============================================================
CITATION_QA_TEMPLATE = PromptTemplate(
    "Please provide a well-structured answer based solely on the provided sources. "
    "When referencing information from a source, "
    "cite the appropriate source(s) using their corresponding numbers. "
    "IMPORTANT: Every paragraph that uses information from a source MUST include "
    "the citation number(s) inline within that paragraph — do NOT defer all citations "
    "to the end of the answer. "
    "Only cite a source when you are explicitly referencing it. "
    "Do NOT repeat the same idea in multiple sentences.\n"
    "Structure your answer with:\n"
    "- An opening sentence that directly addresses the query\n"
    "- Supporting paragraphs with evidence from sources (each citing its sources)\n"
    "- A brief concluding sentence that summarizes key takeaways\n"
    "If none of the sources are helpful, you should indicate that.\n"
    "For example:\n"
    "Source 1:\n"
    "The sky is red in the evening and blue in the morning.\n"
    "Source 2:\n"
    "Water is wet when the sky is red.\n"
    "Query: When is water wet?\n"
    "Answer: Water will be wet when the sky is red [2], "
    "which occurs in the evening [1].\n\n"
    "The redness of the sky is a daily phenomenon observed at specific times [1]. "
    "This means water's wetness follows a predictable pattern tied to atmospheric conditions [2].\n\n"
    "In summary, the timing of water's wetness is directly linked to the sky's color cycle [1][2].\n"
    "Now it's your turn. Below are several numbered sources of information:"
    "\n------\n"
    "{context_str}"
    "\n------\n"
    "Query: {query_str}\n"
    "Answer: "
)

CITATION_REFINE_TEMPLATE = PromptTemplate(
    "Please provide an answer based solely on the provided sources. "
    "When referencing information from a source, "
    "cite the appropriate source(s) using their corresponding numbers. "
    "Every answer should include at least one source citation. "
    "Only cite a source when you are explicitly referencing it. "
    "If none of the sources are helpful, you should indicate that.\n"
    "For example:\n"
    "Source 1:\n"
    "The sky is red in the evening and blue in the morning.\n"
    "Source 2:\n"
    "Water is wet when the sky is red.\n"
    "Query: When is water wet?\n"
    "Answer: Water will be wet when the sky is red [2], "
    "which occurs in the evening [1].\n"
    "Now it's your turn. "
    "We have provided an existing answer: {existing_answer}"
    "Below are several numbered sources of information. "
    "Use them to refine the existing answer. "
    "If the provided sources are not helpful, you will repeat the existing answer."
    "\nBegin refining!"
    "\n------\n"
    "{context_msg}"
    "\n------\n"
    "Query: {query_str}\n"
    "Answer: "
)


# ============================================================
# Factory
# ============================================================
def get_citation_synthesizer(
    mode: ResponseMode = ResponseMode.COMPACT,
    streaming: bool = False,
    model: str | None = None,
    provider: str | None = None,
) -> BaseSynthesizer:
    """Build a citation-aware response synthesizer.

    Uses LlamaIndex's get_response_synthesizer() factory with custom
    prompts that instruct the LLM to produce semantic-paragraph answers
    with [N] citation markers grouped at paragraph end.

    Args:
        mode: LlamaIndex response mode (COMPACT, REFINE, TREE_SUMMARIZE, etc.)
        streaming: Whether to enable streaming generation.
        model: Optional model name override for LLM selection.

    Returns:
        BaseSynthesizer configured for citation-aware generation.
    """
    llm = resolve_llm(model=model, streaming=streaming, provider=provider)

    synthesizer = get_response_synthesizer(
        response_mode=mode,
        streaming=streaming,
        llm=llm,
        text_qa_template=CITATION_QA_TEMPLATE,
        refine_template=CITATION_REFINE_TEMPLATE,
    )

    logger.info("CitationSynthesizer ready (mode={}, streaming={}, model={})",
                mode, streaming, model or 'default')
    return synthesizer
