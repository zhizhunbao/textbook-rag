"""prompts — Centralised citation synthesizer prompt templates.

All LLM prompt templates used by the citation response synthesizer
are defined here. The synthesizer imports from this file to keep
logic and prompts separated.

Groups:
    - CITATION_QA   → main QA synthesis prompt (used by COMPACT mode)
    - CITATION_REFINE → iterative refinement prompt
    - CITATION_SUFFIX → shared citation-format instructions appended
                        to custom system prompts
"""

from llama_index.core.prompts import PromptTemplate


# ============================================================
# Shared citation format instructions
# ============================================================
CITATION_FORMAT_INSTRUCTIONS = (
    "When referencing information from a source, "
    "cite the appropriate source(s) using their corresponding numbers. "
    "IMPORTANT: Every paragraph that uses information from a source MUST include "
    "the citation number(s) inline within that paragraph — do NOT defer all citations "
    "to the end of the answer. "
    "Only cite a source when you are explicitly referencing it. "
    "If none of the sources are helpful, you should indicate that."
)

# ============================================================
# Citation example (shared between QA and REFINE)
# ============================================================
CITATION_EXAMPLE = (
    "For example:\n"
    "Source 1:\n"
    "The sky is red in the evening and blue in the morning.\n"
    "Source 2:\n"
    "Water is wet when the sky is red.\n"
    "Query: When is water wet?\n"
    "Answer: Water will be wet when the sky is red [2], "
    "which occurs in the evening [1].\n"
)


# ============================================================
# Citation QA prompt — semantic-paragraph style
# ============================================================
CITATION_QA_TEMPLATE = PromptTemplate(
    "You are a textbook research assistant. Your job is to answer questions "
    "based ONLY on the provided source materials from academic textbooks.\n\n"
    "IMPORTANT GUARDRAIL: If the user's query is casual chat, a greeting, "
    "or clearly unrelated to the textbook content (e.g. '你好', 'hello', "
    "'how are you', jokes, personal questions), do NOT search the sources. "
    "Instead, respond briefly and politely:\n"
    "- Acknowledge the greeting (e.g. '你好！')\n"
    "- Remind them that you are a textbook research assistant\n"
    "- Suggest they ask a specific question about the textbook content\n"
    "Do NOT cite any sources for casual chat responses.\n\n"
    "For actual research questions, provide a well-structured answer based "
    "solely on the provided sources. "
    + CITATION_FORMAT_INSTRUCTIONS
    + "\n"
    "Do NOT repeat the same idea in multiple sentences.\n"
    "Structure your answer with:\n"
    "- An opening sentence that directly addresses the query\n"
    "- Supporting paragraphs with evidence from sources (each citing its sources)\n"
    "- A brief concluding sentence that summarizes key takeaways\n"
    + CITATION_EXAMPLE
    + "\nThe redness of the sky is a daily phenomenon observed at specific times [1]. "
    "This means water's wetness follows a predictable pattern tied to atmospheric conditions [2].\n\n"
    "In summary, the timing of water's wetness is directly linked to the sky's color cycle [1][2].\n"
    "Now it's your turn. Below are several numbered sources of information:"
    "\n------\n"
    "{context_str}"
    "\n------\n"
    "Query: {query_str}\n"
    "Answer: "
)


# ============================================================
# Citation REFINE prompt — iterative answer improvement
# ============================================================
CITATION_REFINE_TEMPLATE = PromptTemplate(
    "Please provide an answer based solely on the provided sources. "
    + CITATION_FORMAT_INSTRUCTIONS
    + "\n"
    "Every answer should include at least one source citation. "
    + CITATION_EXAMPLE
    + "Now it's your turn. "
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
# Custom prompt builder — appends citation format to user prompt
# ============================================================
def build_custom_qa_template(custom_system_prompt: str) -> PromptTemplate:
    """Build a QA template from a user-selected system prompt.

    Appends the standard citation format instructions and
    context/query placeholders to the custom preamble.

    Args:
        custom_system_prompt: User-provided system prompt text.

    Returns:
        PromptTemplate ready for the citation synthesizer.
    """
    return PromptTemplate(
        custom_system_prompt
        + "\n\n"
        + CITATION_FORMAT_INSTRUCTIONS
        + "\n------\n"
        "{context_str}"
        "\n------\n"
        "Query: {query_str}\n"
        "Answer: "
    )
