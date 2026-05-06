"""consulting.keyword_extractor — spaCy-based keyword extraction with source cross-referencing.

Extracts meaningful noun phrases and data values from user questions,
then filters them against source document text to ensure only
verifiable, cross-referenced terms are highlighted in the UI.

Architecture:
    Python (here)  → extracts + cross-references → returns verified keywords
    Frontend (TS)  → receives keywords from API  → renders <mark> tags

Usage:
    from engine_v2.consulting.keyword_extractor import extract_verified_keywords

    keywords = extract_verified_keywords(
        question="How did construction permit values change in Q4 2024?",
        source_texts=["total construction permit value increased by 9.8% ..."],
    )
    # → [
    #     {"text": "construction permit values", "type": "phrase", "color_index": 0},
    #     {"text": "Q4 2024", "type": "phrase", "color_index": 1},
    #     {"text": "9.8%", "type": "data_value", "color_index": -1},
    #   ]
"""

from __future__ import annotations

import re
from typing import Any

from loguru import logger

# ── Lazy-loaded spaCy models (singleton) ─────────────────────
_nlp_en = None
_nlp_zh = None


def _get_nlp_en():
    """Load English spaCy model (lazy singleton)."""
    global _nlp_en
    if _nlp_en is None:
        import spacy
        _nlp_en = spacy.load("en_core_web_sm")
        logger.info("Loaded spaCy model: en_core_web_sm")
    return _nlp_en


def _get_nlp_zh():
    """Load Chinese spaCy model (lazy singleton)."""
    global _nlp_zh
    if _nlp_zh is None:
        import spacy
        _nlp_zh = spacy.load("zh_core_web_sm")
        logger.info("Loaded spaCy model: zh_core_web_sm")
    return _nlp_zh


def _detect_language(text: str) -> str:
    """Simple language detection: Chinese if >30% CJK characters, else English."""
    if not text:
        return "en"
    cjk_count = sum(1 for c in text if '\u4e00' <= c <= '\u9fff')
    return "zh" if cjk_count / max(len(text), 1) > 0.3 else "en"


# ── Core extraction ──────────────────────────────────────────

# Compound patterns to extract before NLP (always extracted regardless of language)
# Only truly non-NLP patterns that spaCy can't handle structurally.
# Quarter/date patterns are handled by dep-tree expansion (see _expand_chunk).
_COMPOUND_PATTERNS = [
    re.compile(r'\b(\w+(?:-\w+){1,})\b'),                   # year-over-year
    re.compile(r'[+-]?\d+(?:,\d{3})*(?:\.\d+)?%'),          # percentages: +9.8%
    re.compile(r'\$\d+(?:,\d{3})*(?:\.\d+)?'),              # dollar amounts: $1,234
]


def _expand_chunk(chunk, doc) -> str:
    """Expand a spaCy noun chunk using dependency tree analysis.

    This is the UNIVERSAL technique for merging split tokens — instead of
    hand-writing regex for every temporal/numeric pattern, we walk the dep
    tree to find structurally attached modifiers that spaCy excluded from
    the noun chunk.

    Rules applied:
        1. nummod attachment:  Q3 ← 2024(nummod) → "Q3 2024"
        2. from/to range merging:
           "from Q2 to Q3 2024" → detects parallel pobj structure
           and merges both halves into "Q2 to Q3 2024"

    Args:
        chunk: A spaCy Span (noun chunk).
        doc: The full spaCy Doc for accessing sibling tokens.

    Returns:
        The expanded phrase string (or original chunk text if no expansion).
    """
    head = chunk.root
    start_i = chunk.start
    end_i = chunk.end  # exclusive

    # ── Rule 1: Attach nummod children outside the chunk span ──
    # e.g., chunk="Q3"(idx=10), child="2024"(idx=11, dep_=nummod) → "Q3 2024"
    for child in head.children:
        if child.dep_ in ("nummod", "appos") and child.i >= end_i:
            end_i = max(end_i, child.i + 1)
        if child.dep_ in ("nummod", "appos") and child.i < start_i:
            start_i = min(start_i, child.i)

    # ── Rule 2: from/to range merging ──
    # Detect "from X to Y [year]" parallel prep structure.
    # If this chunk is pobj of "to"/"from", look for the sibling pobj.
    # Example: "from Q2(pobj) to Q3(pobj) 2024(nummod)"
    #   → merge into "Q2 to Q3 2024"
    if head.dep_ == "pobj" and head.head.dep_ == "prep":
        prep_token = head.head  # "to" or "from"
        prep_text = prep_token.text.lower()
        if prep_text in ("to", "from", "between", "and"):
            # Find the sibling prep in the same verbal/nominal structure
            prep_parent = prep_token.head  # the verb/noun governing the preps
            sibling_preps = [
                child for child in prep_parent.children
                if child.dep_ == "prep"
                and child.i != prep_token.i
                and child.text.lower() in ("from", "to", "between", "and")
            ]
            for sib in sibling_preps:
                # Find sib's pobj
                for sib_child in sib.children:
                    if sib_child.dep_ == "pobj":
                        sib_start = sib_child.i
                        sib_end = sib_child.i + 1
                        # Also grab sib's nummod children
                        for sc in sib_child.children:
                            if sc.dep_ in ("nummod", "appos"):
                                sib_end = max(sib_end, sc.i + 1)
                                sib_start = min(sib_start, sc.i)
                        # Merge: take the full span from min(sib, chunk) to max
                        start_i = min(start_i, sib_start)
                        end_i = max(end_i, sib_end)

    # ── Rule 3: Compound chain expansion ──
    # spaCy sometimes mis-tags tokens (e.g., "permit" as VERB in
    # "construction permit values"), breaking noun chunks.
    # The dep tree still links them via compound/nsubj deps:
    #   values ← permit(compound) ← construction(nsubj)
    # We walk the full compound chain to reconstruct the phrase.
    #
    # 3a: Walk UP the compound chain — if head's head is connected via
    #     compound dep, keep walking until we reach the true head noun.
    #     construction → permit(compound→values) → values(nsubj→change)
    token = head
    # Walk while current token's HEAD is a compound child of something,
    # or current token itself is part of a compound chain.
    while token.head != token:
        parent = token.head
        # If the parent is a compound dep (i.e., parent modifies its own head),
        # include it and keep walking.
        if parent.dep_ == "compound":
            start_i = min(start_i, parent.i)
            end_i = max(end_i, parent.i + 1)
            # Include parent's head (the actual target noun)
            target = parent.head
            start_i = min(start_i, target.i)
            end_i = max(end_i, target.i + 1)
            # Include all compound/amod/nsubj children of the target
            for child in target.children:
                if child.dep_ in ("compound", "amod"):
                    start_i = min(start_i, child.i)
                    end_i = max(end_i, child.i + 1)
                    # Also grab the compound child's own dependents
                    for grandchild in child.children:
                        if grandchild.dep_ in ("nsubj", "amod", "compound", "nummod"):
                            start_i = min(start_i, grandchild.i)
                            end_i = max(end_i, grandchild.i + 1)
            token = target
        # If current token links to parent via nsubj and parent is a compound,
        # follow (construction→nsubj→permit, permit→compound→values)
        elif token.dep_ in ("nsubj", "amod") and parent.dep_ == "compound":
            start_i = min(start_i, parent.i)
            end_i = max(end_i, parent.i + 1)
            token = parent
        else:
            break

    # 3b: Walk DOWN — include compound children and THEIR subtrees
    def _expand_compounds(tok, s, e):
        for child in tok.children:
            if child.dep_ in ("compound", "amod"):
                s = min(s, child.i)
                e = max(e, child.i + 1)
                # Recurse: compound child may have its own nsubj/compound
                for grandchild in child.children:
                    if grandchild.dep_ in ("nsubj", "amod", "compound", "nummod"):
                        s = min(s, grandchild.i)
                        e = max(e, grandchild.i + 1)
                s, e = _expand_compounds(child, s, e)
        return s, e

    start_i, end_i = _expand_compounds(head, start_i, end_i)

    expanded = doc[start_i:end_i].text.strip()
    return expanded


def _extract_candidates(question: str, source_texts: list[str] | None = None) -> list[dict[str, Any]]:
    """Extract keyword candidates from the question using spaCy NP chunking.

    Uses a hybrid approach:
        1. Regex compound patterns (percentages, $, hyphenated words)
        2. spaCy noun phrase chunking + dep-tree expansion
        3. spaCy named entities
        4. Source-driven n-gram matching (catches phrases spaCy misses)

    The dep-tree expansion (step 2) is the UNIVERSAL technique that replaces
    hand-written regex for temporal/numeric patterns. Instead of enumerating
    regex for "Q2 to Q3 2024", "Q4 2024", etc., we let spaCy parse the
    syntax tree and automatically merge structurally-linked tokens.

    Returns a list of candidate dicts:
        {"text": "construction permit values", "type": "phrase"}
        {"text": "9.8%", "type": "data_value"}
        {"text": "Q3 2024", "type": "phrase"}
    """
    if not question or not question.strip():
        return []

    candidates: list[dict[str, Any]] = []
    seen_lower: set[str] = set()

    def _add(text: str, ctype: str) -> None:
        lower = text.lower().strip()
        if lower and lower not in seen_lower and len(lower) >= 2:
            # Sub-phrase suppression: skip if this text is fully contained
            # within an already-seen longer phrase (word-level substring).
            # e.g., "Q3" is suppressed when "Q2 to Q3 2024" already exists.
            if any(lower in existing and lower != existing for existing in seen_lower):
                return
            seen_lower.add(lower)
            candidates.append({"text": text.strip(), "type": ctype})

    # 1. Extract compound patterns (percentages, dollar amounts, hyphenated)
    for pattern in _COMPOUND_PATTERNS:
        for m in pattern.finditer(question):
            matched = (m.group(1) if m.lastindex else m.group(0)).strip()
            # Classify percentages and dollar amounts as data_value
            if re.match(r'^[+-]?\d', matched) and '%' in matched:
                _add(matched, "data_value")
            elif matched.startswith('$'):
                _add(matched, "data_value")
            else:
                _add(matched, "phrase")

    # 2. Use spaCy for noun phrase extraction + dep-tree expansion
    lang = _detect_language(question)
    try:
        nlp = _get_nlp_zh() if lang == "zh" else _get_nlp_en()
        doc = nlp(question)

        # Extract noun chunks (multi-word noun phrases)
        # Note: zh_core_web_sm does NOT support noun_chunks
        if lang == "zh":
            # Chinese: extract consecutive NOUN/PROPN tokens as compound phrases
            current_phrase: list[str] = []
            for token in doc:
                if token.pos_ in ("NOUN", "PROPN"):
                    current_phrase.append(token.text)
                else:
                    if len(current_phrase) >= 2:
                        _add("".join(current_phrase), "phrase")
                    elif len(current_phrase) == 1 and len(current_phrase[0]) >= 2:
                        _add(current_phrase[0], "phrase")
                    current_phrase = []
            # Flush remaining
            if len(current_phrase) >= 2:
                _add("".join(current_phrase), "phrase")
            elif len(current_phrase) == 1 and len(current_phrase[0]) >= 2:
                _add(current_phrase[0], "phrase")
        else:
            # English: noun chunks with dep-tree expansion
            # Sort chunks by length descending so longer expansions register
            # first in seen_lower, auto-suppressing shorter sub-phrases.
            expanded_chunks: list[tuple[str, int]] = []
            for chunk in doc.noun_chunks:
                expanded = _expand_chunk(chunk, doc)
                expanded_chunks.append((expanded, len(expanded)))
            expanded_chunks.sort(key=lambda x: x[1], reverse=True)

            for expanded, _ in expanded_chunks:
                # Skip if too short
                if len(expanded) < 2:
                    continue
                # Clean: remove leading determiners/pronouns/interrogatives
                cleaned = re.sub(
                    r'^(the|an|this|that|these|those|my|your|his|her|its|our|their|what|which|who|whom|whose|how|where|when|why)\s+',
                    '', expanded, flags=re.IGNORECASE,
                ).strip()
                # Also handle standalone "a" separately (avoid matching "average")
                cleaned = re.sub(
                    r'^a\s+(?=[a-z])',
                    '', cleaned, flags=re.IGNORECASE,
                ).strip()
                # Reject if cleaned result is itself a pure stop/interrogative word
                _STOP_WORDS = {
                    'what', 'which', 'who', 'whom', 'whose', 'how',
                    'where', 'when', 'why', 'the', 'a', 'an', 'it',
                    'did', 'does', 'do', 'is', 'are', 'was', 'were',
                }
                if cleaned.lower() in _STOP_WORDS:
                    continue
                if len(cleaned) >= 2:
                    _add(cleaned, "phrase")

        # 3. Extract significant named entities (ORG, GPE, DATE, MONEY, PERCENT)
        for ent in doc.ents:
            if ent.label_ in ("ORG", "GPE", "LOC", "DATE", "MONEY", "PERCENT",
                              "PRODUCT", "EVENT", "FAC", "NORP"):
                _add(ent.text, "phrase")

        # 4. Source-driven n-gram matching (catches phrases spaCy misses)
        #    Generate 2-3 word windows from the question and check if the
        #    lemmatized form exists in the source text.
        if source_texts:
            combined_source = " ".join(source_texts).lower()
            # Pre-compute lemmatized source for fuzzy matching
            source_doc = nlp(combined_source[:10000])  # limit to avoid slow processing
            source_lemma = " ".join(t.lemma_.lower() for t in source_doc)

            # Stop words for n-gram filtering
            _NGRAM_STOP = {
                'how', 'did', 'does', 'do', 'is', 'are', 'was', 'were',
                'the', 'a', 'an', 'in', 'on', 'at', 'to', 'for', 'of',
                'with', 'by', 'from', 'and', 'or', 'but', 'not', 'what',
                'which', 'who', 'when', 'where', 'why', 'change', 'changed',
                'changes', 'increase', 'decrease', 'affect', 'impact',
            }

            # Clean question words
            q_clean = re.sub(r'[?!.,;:()\[\]{}"\'""]', ' ', question)
            q_words = [w for w in q_clean.split() if len(w) >= 2]

            for ngram_len in (3, 2):
                for i in range(len(q_words) - ngram_len + 1):
                    window = q_words[i:i + ngram_len]
                    # Skip if any word is a stop word
                    if any(w.lower() in _NGRAM_STOP for w in window):
                        continue
                    # Skip if any word is purely numeric
                    if any(re.match(r'^\d+$', w) for w in window):
                        continue

                    phrase_text = " ".join(window)
                    phrase_lower = phrase_text.lower()

                    # Check already seen
                    if phrase_lower in seen_lower:
                        continue

                    # Lemmatize the n-gram for fuzzy matching
                    ngram_doc = nlp(phrase_lower)
                    ngram_lemma = " ".join(t.lemma_.lower() for t in ngram_doc)

                    # Check if lemmatized n-gram exists in lemmatized source
                    if ngram_lemma in source_lemma or phrase_lower in combined_source:
                        _add(phrase_text, "phrase")

    except Exception as e:
        logger.warning("spaCy extraction failed, falling back to regex: {}", e)
        # Fallback: simple word extraction (skip very common words)
        _FALLBACK_STOP = {
            'how', 'did', 'does', 'do', 'is', 'are', 'was', 'were', 'the', 'a',
            'an', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by', 'from',
            'and', 'or', 'but', 'not', 'what', 'which', 'who', 'when', 'where',
            'why', 'change', 'changed', 'changes', 'increase', 'decrease',
        }
        for word in question.split():
            clean = re.sub(r'[?!.,;:]', '', word).strip()
            if clean and clean.lower() not in _FALLBACK_STOP and len(clean) >= 2:
                _add(clean, "phrase")

    return candidates


# ── Cross-referencing ────────────────────────────────────────

def _lemmatize_text(text: str, lang: str = "en") -> str:
    """Lemmatize text for fuzzy matching (values→value, permits→permit)."""
    try:
        nlp = _get_nlp_zh() if lang == "zh" else _get_nlp_en()
        doc = nlp(text[:10000])  # limit for performance
        return " ".join(t.lemma_.lower() for t in doc)
    except Exception:
        return text.lower()


def _normalize_quotes(text: str) -> str:
    """Normalize curly/smart quotes to ASCII equivalents.

    PDF sources often use typographic quotes (\u2018\u2019\u201c\u201d) while user input
    uses ASCII quotes ('"). This normalization ensures cross-referencing
    doesn't fail due to quote style differences.
    """
    return (
        text
        .replace('\u2018', "'")   # left single quote → '
        .replace('\u2019', "'")   # right single quote / apostrophe → '
        .replace('\u201c', '"')   # left double quote → "
        .replace('\u201d', '"')   # right double quote → "
        .replace('\u2032', "'")   # prime → '
        .replace('\u2033', '"')   # double prime → "
    )


def _cross_reference(
    candidates: list[dict[str, Any]],
    source_texts: list[str],
) -> list[dict[str, Any]]:
    """Filter candidates to only those found in source document text.

    Uses lemma-based fuzzy matching so 'construction permit values'
    matches 'construction permit value' in sources.
    Longer phrases take priority — if a phrase matches, its sub-words are
    removed to avoid redundant highlighting.

    Quote normalization: curly quotes (\u2018\u2019\u201c\u201d) are normalized to ASCII
    so "Ottawa\u2019s" in PDF sources matches "Ottawa's" from user input.
    """
    if not source_texts or not candidates:
        return candidates

    # Aggregate all source text into one lowercase string for matching
    # Normalize quotes so Ottawa\u2019s matches Ottawa's
    combined = _normalize_quotes(" ".join(source_texts).lower())
    combined_lemma = _lemmatize_text(combined)

    verified: list[dict[str, Any]] = []
    for c in candidates:
        text_lower = _normalize_quotes(c["text"].lower())
        # Exact match
        if text_lower in combined:
            verified.append(c)
            continue
        # Lemma-based fuzzy match (values↔value, permits↔permit)
        text_lemma = _lemmatize_text(text_lower)
        if text_lemma in combined_lemma:
            verified.append(c)

    # Deduplicate: remove sub-phrases covered by longer phrases
    # Sort by length descending
    verified.sort(key=lambda c: len(c["text"]), reverse=True)
    final: list[dict[str, Any]] = []
    covered_words: set[str] = set()

    for c in verified:
        words = set(c["text"].lower().split())
        # If ALL words of this candidate are already covered by a longer phrase, skip
        if words and words.issubset(covered_words) and c["type"] != "data_value":
            continue
        final.append(c)
        covered_words.update(words)

    return final


# ── Public API ───────────────────────────────────────────────

MAX_KEYWORDS = 8


def extract_verified_keywords(
    question: str,
    source_texts: list[str],
) -> list[dict[str, Any]]:
    """Extract keywords from a user question for highlighting.

    User question keywords are always highlighted — they represent the
    user's own search intent and should be visible regardless of whether
    the exact phrase appears in source texts. Cross-referencing is only
    applied for answer/citation highlighting (extract_answer_keywords).

    Args:
        question: The user's question text.
        source_texts: List of source document texts (passed to
                      _extract_candidates for n-gram matching heuristics).

    Returns:
        List of keyword dicts, each containing:
            - text: The keyword/phrase text
            - type: "phrase" or "data_value"
            - color_index: Deterministic color assignment (0-7 for phrases,
                          -1 for data values which use a fixed accent style)
    """
    candidates = _extract_candidates(question, source_texts)

    # Deduplicate: remove sub-phrases covered by longer phrases
    candidates.sort(key=lambda c: len(c["text"]), reverse=True)
    final: list[dict[str, Any]] = []
    covered_words: set[str] = set()
    for c in candidates:
        words = set(c["text"].lower().split())
        if words and words.issubset(covered_words) and c["type"] != "data_value":
            continue
        final.append(c)
        covered_words.update(words)

    # Assign deterministic color indices
    color_idx = 0
    result: list[dict[str, Any]] = []
    for kw in final:
        if len(result) >= MAX_KEYWORDS:
            break
        entry = {
            "text": kw["text"],
            "type": kw["type"],
            "color_index": -1 if kw["type"] == "data_value" else color_idx,
        }
        if kw["type"] != "data_value":
            color_idx += 1
        result.append(entry)

    return result


MAX_ANSWER_KEYWORDS = 12

# Common LLM filler phrases to skip when extracting from answer text
_ANSWER_STOP_PHRASES = {
    "provided data", "available data", "provided information",
    "relevant information", "specific data", "detailed figure",
    "latest detailed figure", "percentage points", "percentage point",
    "largest rise", "greatest increase", "direct answer",
    "provided documents", "source documents", "data available",
}


def extract_answer_keywords(
    answer_text: str,
    source_texts: list[str],
    question_keywords: list[dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    """Extract cross-referenced keywords from LLM answer text for citation highlighting.

    Uses spaCy NLP to extract meaningful noun phrases from the answer,
    then cross-references them against source texts. Only terms that appear
    in the sources are kept. Skips terms already covered by question keywords.

    Args:
        answer_text: The LLM-generated answer text.
        source_texts: List of source document texts to cross-reference against.
        question_keywords: Already-extracted question keywords to avoid duplicates.

    Returns:
        List of keyword dicts (same schema as extract_verified_keywords):
            - text, type ("phrase"), color_index
    """
    if not answer_text or not answer_text.strip():
        return []

    # Build set of already-highlighted keywords from question to avoid duplicates
    already_highlighted = set()
    if question_keywords:
        for kw in question_keywords:
            already_highlighted.add(kw["text"].lower())

    candidates: list[dict[str, Any]] = []
    seen_lower: set[str] = set()

    def _add(text: str) -> None:
        lower = text.lower().strip()
        if (
            lower
            and lower not in seen_lower
            and lower not in already_highlighted
            and lower not in _ANSWER_STOP_PHRASES
            and len(lower) >= 3
        ):
            seen_lower.add(lower)
            candidates.append({"text": text.strip(), "type": "phrase"})

    # Use spaCy for NLP extraction
    lang = _detect_language(answer_text)
    try:
        nlp = _get_nlp_zh() if lang == "zh" else _get_nlp_en()
        doc = nlp(answer_text[:10000])  # limit for performance

        if lang == "zh":
            # Chinese: consecutive NOUN/PROPN tokens
            current_phrase: list[str] = []
            for token in doc:
                if token.pos_ in ("NOUN", "PROPN"):
                    current_phrase.append(token.text)
                else:
                    if len(current_phrase) >= 2:
                        _add("".join(current_phrase))
                    current_phrase = []
            if len(current_phrase) >= 2:
                _add("".join(current_phrase))
        else:
            # English: noun chunks
            for chunk in doc.noun_chunks:
                phrase = chunk.text.strip()
                if len(phrase) < 3:
                    continue
                # Clean leading determiners
                cleaned = re.sub(
                    r'^(the|a|an|this|that|these|those|my|your|his|her|its|our|their)\s+',
                    '', phrase, flags=re.IGNORECASE,
                ).strip()
                if len(cleaned) >= 3:
                    _add(cleaned)

        # Named entities
        for ent in doc.ents:
            if ent.label_ in ("ORG", "GPE", "LOC", "PRODUCT", "EVENT", "FAC", "NORP"):
                _add(ent.text)

    except Exception as e:
        logger.warning("spaCy extraction failed for answer keywords: {}", e)
        return []

    if not candidates:
        return []

    # Cross-reference with sources — only keep terms found in source text
    verified = _cross_reference(candidates, source_texts)

    # Assign color indices (continuing after question keyword palette range)
    # Use a separate color offset so answer keywords are visually distinct
    color_offset = len(question_keywords) if question_keywords else 0
    color_idx = color_offset
    result: list[dict[str, Any]] = []
    for kw in verified:
        if len(result) >= MAX_ANSWER_KEYWORDS:
            break
        result.append({
            "text": kw["text"],
            "type": kw["type"],
            "color_index": color_idx,
        })
        color_idx += 1

    return result


# ── Numeric data value extraction (migrated from frontend) ───

# Regex patterns for numeric data values worth highlighting.
# Ordered by specificity: higher-priority patterns first, catch-all last.
# Overlap check in extract_numeric_highlights() prevents double-matching.
_NUMERIC_PATTERNS = [
    # Quarter-year compounds: Q4 2024, Q1 2022 (must be first — most specific)
    re.compile(r'\bQ[1-4]\s*\d{4}\b', re.IGNORECASE),
    # Percentages: +9.8%, -16.6%, 20.3%
    re.compile(r'[+-]?\d+(?:,\d{3})*(?:\.\d+)?\s?%'),
    # Dollar amounts: $1,234, $17.8 billion
    re.compile(r'\$\d+(?:,\d{3})*(?:\.\d+)?(?:\s?(?:billion|million|thousand|B|M|K))?', re.IGNORECASE),
    # Large comma-separated numbers (at least 4 digits): 10,077  2,405
    re.compile(r'\b\d{1,3}(?:,\d{3})+(?:\.\d+)?\b'),
    # Signed numbers with explicit +/- prefix: +3.8, -1.3, +35
    re.compile(r'[+-]\d+(?:,\d{3})*(?:\.\d+)?'),
    # Decimal numbers (any digit count): 3.8, 1.3, 0.5, 9.8
    re.compile(r'\b\d+\.\d+\b'),
    # Standalone integers ≥2 digits: years (2024), counts (35, 100).
    # Single-digit integers excluded to avoid noise (1, 2, 3…).
    re.compile(r'\b\d{2,}\b'),
]


def _strip_trailing_zeros(s: str) -> str:
    """Normalize trailing decimal zeros for flexible cross-referencing.

    '6.0%' → '6%', '6.10%' → '6.1%', '$1,234.00' → '$1,234'
    Leaves already-clean values unchanged: '4.6%' → '4.6%', '6%' → '6%'
    """
    # Strip trailing zeros after significant decimal digits: 6.10 → 6.1
    s = re.sub(r'(\.\d*[1-9])0+(?=\D|$)', r'\1', s)
    # Strip .0 entirely: 6.0 → 6
    s = re.sub(r'(\d)\.0+(?=\D|$)', r'\1', s)
    return s


def _extract_numeric_values(text: str) -> set[str]:
    """Extract all numeric values from text for cross-referencing.

    Returns a Set of normalized numeric strings.
    Each value is stored in multiple forms (with/without sign,
    with/without trailing zeros) for flexible matching:
        '6.0%' produces: {'6.0%', '6%'}
        '+20.3%' produces: {'+20.3%', '20.3%'}
    """
    values: set[str] = set()
    if not text:
        return values

    for pattern in _NUMERIC_PATTERNS:
        for m in pattern.finditer(text):
            # Normalize: strip whitespace, collapse spaces before %
            normalized = re.sub(r'\s+', '', m.group(0)).lower()
            values.add(normalized)
            # Also add without sign for flexible matching (+20.3% matches 20.3%)
            unsigned = re.sub(r'^[+-]', '', normalized)
            if unsigned != normalized:
                values.add(unsigned)
            # Also add with trailing zeros stripped: 6.0% ↔ 6%
            stripped = _strip_trailing_zeros(normalized)
            if stripped != normalized:
                values.add(stripped)
            stripped_unsigned = _strip_trailing_zeros(unsigned)
            if stripped_unsigned != unsigned:
                values.add(stripped_unsigned)

    return values


def extract_numeric_highlights(
    answer_text: str,
    source_texts: list[str],
) -> list[dict[str, Any]]:
    """Extract numeric data values from LLM answer and cross-reference with sources.

    Uses a hybrid approach:
        1. Primary: spaCy NER (CARDINAL, PERCENT, MONEY, DATE, QUANTITY)
           — universal, no manual patterns needed
        2. Fallback: regex patterns for edge cases spaCy misses
           (signed numbers, Q-year compounds, etc.)

    Cross-referencing:
        - verified=True:  number appears in source texts → backed by evidence
        - verified=False: number NOT in any source → LLM-generated
    """
    if not answer_text:
        return []

    # Build set of numeric values from source texts for cross-referencing
    source_numbers: set[str] = set()
    for src in source_texts:
        source_numbers.update(_extract_numeric_values(src))
    has_sources = len(source_numbers) > 0

    results: list[dict[str, Any]] = []

    def _overlaps(idx: int, end: int) -> bool:
        return any(
            idx < r["offset"] + len(r["text"]) and end > r["offset"]
            for r in results
        )

    def _verify(matched: str) -> bool:
        normalized = re.sub(r'\s+', '', matched).lower()
        unsigned = re.sub(r'^[+-]', '', normalized)
        stripped = _strip_trailing_zeros(normalized)
        stripped_unsigned = _strip_trailing_zeros(unsigned)
        return (not has_sources) or any(
            v in source_numbers
            for v in (normalized, unsigned, stripped, stripped_unsigned)
        )

    # ── Phase 1: spaCy NER (universal numeric entity recognition) ──
    _NER_LABELS = {"CARDINAL", "PERCENT", "MONEY", "DATE", "QUANTITY"}
    lang = _detect_language(answer_text)
    try:
        nlp = _get_nlp_zh() if lang == "zh" else _get_nlp_en()
        doc = nlp(answer_text)
        for ent in doc.ents:
            if ent.label_ not in _NER_LABELS:
                continue
            # Skip non-numeric entities (e.g. "Monday", "several")
            if not re.search(r'\d', ent.text):
                continue
            # Skip very short values (single digits) — they cause massive
            # false positives when matched against citation/source text
            clean = re.sub(r'\s+', '', ent.text)
            if len(clean) < 2:
                continue
            idx, end = ent.start_char, ent.end_char
            if _overlaps(idx, end):
                continue
            results.append({
                "text": ent.text,
                "verified": _verify(ent.text),
                "offset": idx,
            })
    except Exception as e:
        logger.warning("spaCy NER failed for numeric extraction: {}", e)

    # ── Phase 2: regex fallback for patterns spaCy might miss ──
    for pattern in _NUMERIC_PATTERNS:
        for m in pattern.finditer(answer_text):
            idx, end = m.start(), m.end()
            matched = m.group(0)
            if _overlaps(idx, end):
                continue
            results.append({
                "text": matched,
                "verified": _verify(matched),
                "offset": idx,
            })

    results.sort(key=lambda r: r["offset"])
    return results


def extract_source_numeric_highlights(
    source_text: str,
    answer_numbers: set[str] | None = None,
) -> list[dict[str, Any]]:
    """Extract numeric highlights from a single source/citation text.

    Used by the API to enrich each source with per-source numeric data
    so the frontend doesn't need a catch-all regex.

    Cross-referencing:
        - verified=True:  number also appears in the LLM answer → actively used
        - verified=False: number exists in source but not cited → context only

    All numbers ≥2 chars are returned so the frontend can show gray
    highlights for uncited data points, building user trust.
    """
    if not source_text:
        return []

    results: list[dict[str, Any]] = []

    def _overlaps(idx: int, end: int) -> bool:
        return any(
            idx < r["offset"] + len(r["text"]) and end > r["offset"]
            for r in results
        )

    def _verify(matched: str) -> bool:
        if not answer_numbers:
            return False
        normalized = re.sub(r'\s+', '', matched).lower()
        unsigned = re.sub(r'^[+-]', '', normalized)
        stripped = _strip_trailing_zeros(normalized)
        stripped_unsigned = _strip_trailing_zeros(unsigned)
        return any(
            v in answer_numbers
            for v in (normalized, unsigned, stripped, stripped_unsigned)
        )

    # Phase 1: spaCy NER
    _NER_LABELS = {"CARDINAL", "PERCENT", "MONEY", "DATE", "QUANTITY"}
    lang = _detect_language(source_text)
    try:
        nlp = _get_nlp_zh() if lang == "zh" else _get_nlp_en()
        doc = nlp(source_text[:10000])
        for ent in doc.ents:
            if ent.label_ not in _NER_LABELS:
                continue
            if not re.search(r'\d', ent.text):
                continue
            clean = re.sub(r'\s+', '', ent.text)
            if len(clean) < 2:
                continue
            idx, end = ent.start_char, ent.end_char
            if _overlaps(idx, end):
                continue
            results.append({
                "text": ent.text,
                "verified": _verify(ent.text),
                "offset": idx,
            })
    except Exception as e:
        logger.warning("spaCy NER failed for source numeric extraction: {}", e)

    # Phase 2: regex fallback
    for pattern in _NUMERIC_PATTERNS:
        for m in pattern.finditer(source_text):
            idx, end = m.start(), m.end()
            matched = m.group(0)
            if _overlaps(idx, end):
                continue
            clean = re.sub(r'\s+', '', matched)
            if len(clean) < 2:
                continue
            results.append({
                "text": matched,
                "verified": _verify(matched),
                "offset": idx,
            })

    results.sort(key=lambda r: r["offset"])
    return results

