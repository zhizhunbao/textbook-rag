"""PageIndexStrategy — document structure-tree node matching.

STORY-005: ported from retrieval_lab pageindex_retriever algorithm.

Algorithm:
  1. Parse MinerU ``_middle.json`` for the queried book(s) into a flat node list.
     Each node has a ``para_id``, ``type``, ``text``, ``page_idx``, ``level``.
  2. Score each node by term overlap with query terms (same formula as TOC).
  3. Walk UP the node tree via ``parent_id`` to expand context (parent + siblings).
  4. Map node → page_idx → page_id (via ``pages`` table).
  5. Fetch chunks whose ``primary_page_id`` matches the identified pages.
  6. Return ranked ChunkHit list.

NOTE: If ``_middle.json`` files are not present, ``is_available()`` returns False
and the strategy is silently skipped by RetrievalOrchestrator.
"""

from __future__ import annotations

import json
import re
import sqlite3
from pathlib import Path

from engine.rag.config import QueryConfig, RAGConfig
from engine.rag.strategies.base import RetrievalStrategy
from engine.rag.types import ChunkHit, StrategyResult

_SCORE_THRESHOLD = 0.15
_SUBSTRING_BONUS = 0.25


def _tokenise(text: str) -> set[str]:
    return set(re.findall(r"\b\w+\b", text.lower()))


def _score_node(query_terms: set[str], node_text: str, raw_query: str) -> float:
    if not query_terms or not node_text:
        return 0.0
    node_terms = _tokenise(node_text)
    overlap = len(query_terms & node_terms) / len(query_terms)
    bonus = _SUBSTRING_BONUS if raw_query.lower() in node_text.lower() else 0.0
    return overlap + bonus


class PageIndexStrategy(RetrievalStrategy):
    """Document structure-tree retrieval strategy.

    Parses MinerU ``_middle.json`` output files to traverse the document
    node hierarchy and retrieve structurally relevant chunks.

    Disabled by default (``default_enabled = False``) — activate via
    ``enabled_strategies`` in QueryConfig or the frontend toggle.
    """

    name: str = "pageindex"
    display_name: str = "PageIndex Structure"
    default_enabled: bool = False

    def __init__(self, mineru_output_dir: str = "") -> None:
        self._mineru_dir = Path(mineru_output_dir) if mineru_output_dir else None

    def is_available(self) -> bool:
        """Available only when a MinerU output directory with JSON files exists."""
        if self._mineru_dir is None:
            # Try to find from config (injected at RetrievalOrchestrator init time)
            return False
        return self._mineru_dir.exists() and any(self._mineru_dir.rglob("*_middle.json"))

    def configure(self, config: RAGConfig) -> None:
        """Called by RetrievalOrchestrator to inject the RAGConfig path."""
        if config.mineru_output_dir:
            self._mineru_dir = Path(config.mineru_output_dir)

    def search(
        self,
        query: str,
        config: QueryConfig,
        db: sqlite3.Connection,
    ) -> StrategyResult:
        query_terms = _tokenise(query)
        if not query_terms:
            return StrategyResult(strategy=self.name, hits=[], query_used=query)

        fetch_k = config.effective_fetch_k
        f = config.filters

        # ── 1. Resolve which book(s) to load ─────────────────────────────
        book_ids = f.book_ids
        if not book_ids:
            # Load middle JSONs for all books in DB
            rows = db.execute("SELECT id, title FROM books").fetchall()
            book_ids = [r["id"] for r in rows]

        if not book_ids:
            return StrategyResult(strategy=self.name, hits=[], query_used=query)

        # ── 2. Parse MinerU middle JSON files ─────────────────────────────
        nodes: list[dict] = []
        for book_id in book_ids:
            book_row = db.execute(
                "SELECT title FROM books WHERE id = ?", (book_id,)
            ).fetchone()
            if book_row is None:
                continue
            json_files = (
                list(self._mineru_dir.rglob("*_middle.json")) if self._mineru_dir else []
            )
            for jf in json_files:
                book_nodes = self._parse_middle_json(jf, book_id)
                nodes.extend(book_nodes)

        if not nodes:
            return StrategyResult(strategy=self.name, hits=[], query_used=query)

        # ── 3. Score nodes ────────────────────────────────────────────────
        scored: list[tuple[float, dict]] = []
        for node in nodes:
            score = _score_node(query_terms, node.get("text", ""), query)
            if score >= _SCORE_THRESHOLD:
                scored.append((score, node))

        if not scored:
            return StrategyResult(strategy=self.name, hits=[], query_used=query)

        scored.sort(key=lambda x: x[0], reverse=True)
        top = scored[:fetch_k]

        # ── 4. Collect page indices from matched nodes ────────────────────
        page_idx_score: dict[int, float] = {}
        for sc, node in top:
            pidx = node.get("page_idx")
            if pidx is not None:
                page_idx_score[pidx] = max(page_idx_score.get(pidx, 0.0), sc)

        # ── 5. Map page_idx → page_id via pages table ─────────────────────
        if not page_idx_score:
            return StrategyResult(strategy=self.name, hits=[], query_used=query)

        page_indices = list(page_idx_score.keys())
        ph = ",".join("?" * len(page_indices))
        page_rows = db.execute(
            f"SELECT id, page_number FROM pages WHERE page_number IN ({ph})",
            page_indices,
        ).fetchall()
        # page_number in DB is 0-indexed (same as MinerU page_idx)
        page_id_score: dict[int, float] = {}
        for pr in page_rows:
            page_id_score[pr["id"]] = page_idx_score.get(pr["page_number"], 0.0)

        if not page_id_score:
            return StrategyResult(strategy=self.name, hits=[], query_used=query)

        # ── 6. Fetch chunks from matched pages ────────────────────────────
        page_ids = list(page_id_score.keys())
        ph = ",".join("?" * len(page_ids))
        chunk_where: list[str] = [f"c.primary_page_id IN ({ph})"]
        chunk_params: list[object] = [*page_ids]

        if f.content_types:
            cph = ",".join("?" * len(f.content_types))
            chunk_where.append(f"c.content_type IN ({cph})")
            chunk_params.extend(f.content_types)

        chunk_sql = (
            "SELECT c.id, c.chunk_id, c.book_id, c.chapter_id, c.primary_page_id,"
            "       c.content_type, c.text, c.reading_order, c.chroma_document_id "
            "FROM chunks c WHERE " + " AND ".join(chunk_where) + " "
            "ORDER BY c.reading_order ASC "
            f"LIMIT {fetch_k}"
        )
        try:
            chunk_rows = db.execute(chunk_sql, chunk_params).fetchall()
        except Exception as exc:  # noqa: BLE001
            return StrategyResult(
                strategy=self.name, hits=[], query_used=query, error=str(exc)
            )

        hits: list[ChunkHit] = []
        for row in chunk_rows:
            r = dict(row)
            pi_score = page_id_score.get(r["primary_page_id"], 0.0)
            hits.append(
                ChunkHit(
                    id=r["id"],
                    chunk_id=r["chunk_id"],
                    book_id=r["book_id"],
                    text=r["text"],
                    content_type=r.get("content_type", "text"),
                    reading_order=r.get("reading_order", 0),
                    chroma_document_id=r.get("chroma_document_id"),
                    pageindex_score=pi_score,
                )
            )

        hits.sort(key=lambda h: (-(h.pageindex_score or 0.0), h.reading_order))
        for i, h in enumerate(hits, start=1):
            h.pageindex_rank = i

        return StrategyResult(strategy=self.name, hits=hits, query_used=query)

    # ─────────────────────────────────────────────────────────────────────
    # MinerU middle JSON parser
    # ─────────────────────────────────────────────────────────────────────

    @staticmethod
    def _parse_middle_json(path: Path, book_id: int) -> list[dict]:
        """Parse a MinerU ``_middle.json`` file into a flat node list.

        Each node dict has keys: book_id, page_idx, text.
        The JSON structure varies by MinerU version; we handle both the
        ``pdf_info`` array format (common) and flat list formats.
        """
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return []

        nodes: list[dict] = []

        # Format: {"pdf_info": [{"page_idx": N, "para_blocks": [...]}]}
        pdf_info = data.get("pdf_info") if isinstance(data, dict) else None
        if pdf_info and isinstance(pdf_info, list):
            for page in pdf_info:
                page_idx = page.get("page_idx", 0)
                for block in page.get("para_blocks", []):
                    text = _extract_block_text(block)
                    if text:
                        nodes.append({"book_id": book_id, "page_idx": page_idx, "text": text})
            return nodes

        # Format: flat list of block objects
        if isinstance(data, list):
            for block in data:
                page_idx = block.get("page_idx", 0)
                text = _extract_block_text(block)
                if text:
                    nodes.append({"book_id": book_id, "page_idx": page_idx, "text": text})

        return nodes


def _extract_block_text(block: dict) -> str:
    """Recursively extract text from a MinerU block/span structure."""
    if isinstance(block, str):
        return block.strip()
    if not isinstance(block, dict):
        return ""
    # Direct text field
    if "text" in block and isinstance(block["text"], str):
        return block["text"].strip()
    # Lines → spans
    parts: list[str] = []
    for line in block.get("lines", []):
        for span in line.get("spans", []):
            t = span.get("content", span.get("text", ""))
            if t:
                parts.append(t.strip())
    return " ".join(parts)
