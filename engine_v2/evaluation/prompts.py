"""prompts — Centralised evaluation prompt templates.

All LLM prompt templates used by the evaluation module are defined here.
Evaluator classes import from this file to keep logic and prompts separated.

Groups:
    - Question Depth    → DEPTH_*  (used by QuestionDepthEvaluator)
    - Completeness      → COMPLETENESS_*  (used by CompletenessEvaluator)
    - Clarity           → CLARITY_*  (used by ClarityEvaluator)
"""

from llama_index.core.prompts import (
    ChatMessage,
    ChatPromptTemplate,
    MessageRole,
)


# ============================================================
# Question Depth — cognitive depth scoring (1–5)
# ============================================================
DEPTH_SYSTEM_TEMPLATE = """
You are an expert evaluator of question quality for a knowledge retrieval system.

You are given a user's question about a topic.

Your job is to assess the **cognitive depth** of the question on a 1–5 scale.

Follow these guidelines for scoring:
- 1: Surface-level recall — asks for a definition or fact verbatim from the text.
- 2: Basic comprehension — asks to explain or paraphrase a concept.
- 3: Application — asks to apply a concept to a new scenario or example.
- 4: Analysis / Synthesis — asks to compare, contrast, or combine multiple concepts.
- 5: Evaluation / Creation — asks to critique, evaluate trade-offs, or propose new ideas.

You must return your response in a line with only the score.
Do not return answers in any other format.
On a separate line provide your reasoning for the score as well.

Example Response:
4.0
This question requires the user to synthesize concepts from multiple sources \
    and analyze their interactions, demonstrating deep understanding.

"""

DEPTH_USER_TEMPLATE = """
## Question
{query}

## Reference Rubric
{reference_answer}

## Assessment Criteria
{generated_answer}
"""

DEPTH_EVAL_TEMPLATE = ChatPromptTemplate(
    message_templates=[
        ChatMessage(role=MessageRole.SYSTEM, content=DEPTH_SYSTEM_TEMPLATE),
        ChatMessage(role=MessageRole.USER, content=DEPTH_USER_TEMPLATE),
    ]
)


# ============================================================
# Completeness — does the answer cover all question aspects? (1–5)
# ============================================================
COMPLETENESS_SYSTEM_TEMPLATE = """\
You are an expert evaluator assessing **answer completeness** for a \
knowledge retrieval system.

Given a user's question, the retrieved source context, and the generated \
answer, determine whether the answer fully addresses ALL aspects of the \
question.

Scoring guidelines (1–5):
- 1: The answer misses the core point of the question entirely.
- 2: The answer addresses part of the question but omits major aspects.
- 3: The answer covers the main point but misses secondary aspects.
- 4: The answer is mostly complete, with only minor gaps.
- 5: The answer comprehensively covers every aspect of the question.

Return your response as a single line with the score, followed by a \
separate line with your reasoning.

Example Response:
4.0
The answer covers the main concept and two of three sub-topics, \
but omits the historical context mentioned in the question.\
"""

COMPLETENESS_USER_TEMPLATE = """\
## User Question
{query}

## Reference Context
{reference_answer}

## Generated Answer
{generated_answer}
"""

COMPLETENESS_EVAL_TEMPLATE = ChatPromptTemplate(
    message_templates=[
        ChatMessage(role=MessageRole.SYSTEM, content=COMPLETENESS_SYSTEM_TEMPLATE),
        ChatMessage(role=MessageRole.USER, content=COMPLETENESS_USER_TEMPLATE),
    ]
)


# ============================================================
# Clarity — is the answer clear, structured, readable? (1–5)
# ============================================================
CLARITY_SYSTEM_TEMPLATE = """\
You are an expert evaluator assessing **answer clarity** for a knowledge \
retrieval system.

Given a generated answer, evaluate how clear, well-structured, and \
readable the response is.

Scoring guidelines (1–5):
- 1: Incoherent, poorly structured, or incomprehensible.
- 2: Understandable but disorganised, with unclear reasoning flow.
- 3: Reasonably clear but could be better structured or more concise.
- 4: Well-structured and clear, with good logical flow.
- 5: Exceptionally clear, concise, well-organised, and easy to follow.

Return your response as a single line with the score, followed by a \
separate line with your reasoning.

Example Response:
4.0
The answer is well-organised with clear topic sentences and logical \
transitions, though the final paragraph could be more concise.\
"""

CLARITY_USER_TEMPLATE = """\
## User Question
{query}

## Reference (unused — judge clarity only)
{reference_answer}

## Generated Answer
{generated_answer}
"""

CLARITY_EVAL_TEMPLATE = ChatPromptTemplate(
    message_templates=[
        ChatMessage(role=MessageRole.SYSTEM, content=CLARITY_SYSTEM_TEMPLATE),
        ChatMessage(role=MessageRole.USER, content=CLARITY_USER_TEMPLATE),
    ]
)
