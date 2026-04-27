"""golden_dataset — Generate and manage Golden Dataset QA pairs.

Responsibilities:
    - Generate question-answer pairs from ingested textbook chunks
    - Use LlamaIndex RagDatasetGenerator for high-quality QA generation
    - Match incoming queries against golden records for IR evaluation
    - Persist generated pairs to Payload GoldenDataset collection

Ref: llama_index.core.llama_dataset.generator — RagDatasetGenerator
"""

from __future__ import annotations

from dataclasses import dataclass, field

import httpx
from loguru import logger

from engine_v2.settings import PAYLOAD_URL


# ============================================================
# Data classes
# ============================================================
@dataclass
class GoldenRecord:
    """A single Golden Dataset QA pair."""

    question: str
    expected_answer: str
    expected_chunk_ids: list[str] = field(default_factory=list)
    book_id: str | None = None
    source_page: str = ""
    verified: bool = False
    tags: list[str] = field(default_factory=list)
    id: int | None = None  # Payload record ID (set after persistence)


@dataclass
class GoldenDatasetResult:
    """Result of golden dataset generation."""

    book_id: str
    records: list[GoldenRecord]
    total_generated: int
    errors: list[str] = field(default_factory=list)


# ============================================================
# Golden dataset generation
# ============================================================
async def generate_golden_dataset(
    book_id: str,
    n_questions: int = 50,
    num_questions_per_chunk: int = 2,
) -> GoldenDatasetResult:
    """Generate Golden Dataset QA pairs from ingested textbook chunks.

    Uses LlamaIndex RagDatasetGenerator to create high-quality
    question-answer pairs from the chunks stored in ChromaDB.

    Args:
        book_id: Book identifier to generate from.
        n_questions: Maximum total questions to generate.
        num_questions_per_chunk: Questions per chunk (default 2).

    Returns:
        GoldenDatasetResult with generated records.
    """
    from llama_index.core.llama_dataset.generator import RagDatasetGenerator
    from llama_index.core.schema import TextNode

    import chromadb

    from engine_v2.settings import CHROMA_DIR, CHROMA_COLLECTION

    errors: list[str] = []

    # ── 1. Load chunks from ChromaDB ──
    logger.info(
        "Generating golden dataset for book_id={}, n_questions={}, per_chunk={}",
        book_id, n_questions, num_questions_per_chunk,
    )

    client = chromadb.PersistentClient(path=str(CHROMA_DIR))
    collection = client.get_collection(CHROMA_COLLECTION)

    # Fetch chunks for this book
    results = collection.get(
        where={"book_id": book_id},
        include=["documents", "metadatas"],
    )

    if not results["documents"]:
        msg = f"No chunks found in ChromaDB for book_id={book_id}"
        logger.warning(msg)
        return GoldenDatasetResult(
            book_id=book_id, records=[], total_generated=0, errors=[msg],
        )

    # Convert to LlamaIndex TextNode objects
    nodes: list[TextNode] = []
    for i, (doc, meta) in enumerate(
        zip(results["documents"], results["metadatas"]),
    ):
        if not doc:
            continue
        chunk_id = results["ids"][i] if results["ids"] else f"chunk_{i}"
        node = TextNode(
            text=doc,
            id_=chunk_id,
            metadata=meta or {},
        )
        nodes.append(node)

    logger.info(
        "Loaded {} chunks from ChromaDB for book_id={}",
        len(nodes), book_id,
    )

    # Limit chunks to avoid generating too many questions
    max_chunks = max(1, n_questions // num_questions_per_chunk)
    if len(nodes) > max_chunks:
        # Sample evenly across the document
        step = len(nodes) / max_chunks
        nodes = [nodes[int(i * step)] for i in range(max_chunks)]
        logger.info("Sampled {} chunks for generation", len(nodes))

    # ── 2. Generate QA pairs ──
    try:
        generator = RagDatasetGenerator(
            nodes=nodes,
            num_questions_per_chunk=num_questions_per_chunk,
            show_progress=True,
        )
        dataset = await generator.agenerate_dataset_from_nodes()
    except Exception as exc:
        msg = f"RagDatasetGenerator failed: {exc}"
        logger.error(msg)
        return GoldenDatasetResult(
            book_id=book_id, records=[], total_generated=0, errors=[msg],
        )

    # ── 3. Map to GoldenRecord objects ──
    records: list[GoldenRecord] = []
    for example in dataset.examples:
        # Each example has: query, reference_answer, reference_contexts
        page_idx = ""
        chunk_ids: list[str] = []

        # Try to extract source chunk IDs from the example's context
        if hasattr(example, "reference_contexts") and example.reference_contexts:
            # Match contexts back to node IDs
            for ctx in example.reference_contexts:
                for node in nodes:
                    if node.text and ctx[:100] in node.text[:200]:
                        chunk_ids.append(node.id_)
                        page_str = node.metadata.get("page_idx", "")
                        if page_str:
                            page_idx = str(page_str)
                        break

        record = GoldenRecord(
            question=example.query,
            expected_answer=example.reference_answer or "",
            expected_chunk_ids=chunk_ids,
            book_id=book_id,
            source_page=page_idx,
            verified=False,
            tags=["auto-generated"],
        )
        records.append(record)

        if len(records) >= n_questions:
            break

    logger.info(
        "Generated {} golden records for book_id={}",
        len(records), book_id,
    )

    return GoldenDatasetResult(
        book_id=book_id,
        records=records,
        total_generated=len(records),
        errors=errors,
    )


# ============================================================
# Payload persistence
# ============================================================
async def persist_golden_records(
    records: list[GoldenRecord],
    token: str,
) -> list[int]:
    """Write golden records to Payload GoldenDataset collection.

    Args:
        records: List of GoldenRecord to persist.
        token: Payload JWT token.

    Returns:
        List of created record IDs.
    """
    url = f"{PAYLOAD_URL}/api/golden-dataset"
    created_ids: list[int] = []

    async with httpx.AsyncClient(timeout=30.0) as client:
        for record in records:
            payload_data = {
                "question": record.question,
                "expectedAnswer": record.expected_answer,
                "expectedChunkIds": record.expected_chunk_ids,
                "bookId": record.book_id,
                "sourcePage": record.source_page,
                "verified": record.verified,
                "tags": record.tags,
            }

            try:
                resp = await client.post(
                    url,
                    json=payload_data,
                    headers={"Authorization": f"JWT {token}"},
                )
                resp.raise_for_status()
                doc = resp.json().get("doc", {})
                record_id = doc.get("id")
                if record_id:
                    created_ids.append(record_id)
                    record.id = record_id
            except Exception as exc:
                logger.warning(
                    "Failed to persist golden record: {} — {}",
                    record.question[:60], exc,
                )

    logger.info("Persisted {}/{} golden records", len(created_ids), len(records))
    return created_ids


# ============================================================
# Golden Dataset matching (for IR evaluation)
# ============================================================
async def match_golden_record(
    question: str,
    book_id: str | None = None,
    similarity_threshold: float = 0.90,
) -> GoldenRecord | None:
    """Find a matching golden record for a given question.

    Uses semantic similarity via LlamaIndex SemanticSimilarityEvaluator
    to find the best matching golden record. Returns None if no match
    exceeds the similarity threshold.

    Args:
        question: The query to match.
        book_id: Optional book_id filter.
        similarity_threshold: Minimum similarity (0-1) to consider a match.

    Returns:
        Matching GoldenRecord or None.
    """
    from llama_index.core.evaluation import SemanticSimilarityEvaluator

    # Fetch golden records from Payload
    records = await _fetch_golden_records(book_id=book_id, verified_only=True)
    if not records:
        return None

    sim_eval = SemanticSimilarityEvaluator(
        similarity_threshold=similarity_threshold,
    )

    best_score = 0.0
    best_record: GoldenRecord | None = None

    for record in records:
        try:
            result = await sim_eval.aevaluate(
                response=question,
                reference=record.question,
            )
            score = result.score or 0.0
            if score > best_score:
                best_score = score
                best_record = record
        except Exception:
            continue

    if best_score >= similarity_threshold and best_record:
        logger.info(
            "Golden match found — score={:.3f}, golden_q={}",
            best_score, best_record.question[:60],
        )
        return best_record

    logger.debug(
        "No golden match for question={} (best_score={:.3f})",
        question[:60], best_score,
    )
    return None


async def _fetch_golden_records(
    book_id: str | None = None,
    verified_only: bool = True,
    limit: int = 200,
) -> list[GoldenRecord]:
    """Fetch golden records from Payload GoldenDataset collection.

    Args:
        book_id: Optional filter by book ID.
        verified_only: If True, only return verified records.
        limit: Max records to fetch.

    Returns:
        List of GoldenRecord.
    """
    from engine_v2.evaluation.history import _get_payload_token

    where_clauses: list[str] = []

    if verified_only:
        where_clauses.append("where[verified][equals]=true")
    if book_id:
        where_clauses.append(f"where[bookId][equals]={book_id}")

    url = f"{PAYLOAD_URL}/api/golden-dataset"
    if where_clauses:
        url += "?" + "&".join(where_clauses)
        # Merge limit into URL
        url += f"&limit={limit}"
    else:
        url += f"?limit={limit}"

    try:
        token = await _get_payload_token()
        headers = {"Authorization": f"JWT {token}"}
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(url, headers=headers)
            resp.raise_for_status()
            data = resp.json()
    except Exception as exc:
        logger.warning("Failed to fetch golden records: {}", exc)
        return []

    docs = data.get("docs", [])
    records: list[GoldenRecord] = []
    for doc in docs:
        records.append(GoldenRecord(
            id=doc.get("id"),
            question=doc.get("question", ""),
            expected_answer=doc.get("expectedAnswer", ""),
            expected_chunk_ids=doc.get("expectedChunkIds") or [],
            book_id=doc.get("bookId"),
            source_page=doc.get("sourcePage", ""),
            verified=doc.get("verified", False),
            tags=doc.get("tags") or [],
        ))

    return records
