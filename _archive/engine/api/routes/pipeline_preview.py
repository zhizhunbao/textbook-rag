"""GET /engine/pipeline-preview/{book_id} — real input/output for each pipeline stage.

Returns actual data samples for each pipeline stage so the frontend dashboard
can show what each step consumed and produced.

每个 Pipeline 步骤的真实输入/输出数据预览。
"""

from __future__ import annotations

import json
import logging
import sqlite3
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException

from engine.config import DATABASE_PATH, MINERU_OUTPUT_DIR, CHROMA_PERSIST_DIR, DATA_DIR

logger = logging.getLogger(__name__)
router = APIRouter(tags=["pipeline-preview"])


def _get_db() -> sqlite3.Connection:
    conn = sqlite3.connect(str(DATABASE_PATH))
    conn.row_factory = sqlite3.Row
    return conn


def _find_content_list(book_id: str) -> Path | None:
    """Search for content_list.json across all categories."""
    for category in ["textbook", "ecdev", "real_estate"]:
        p = MINERU_OUTPUT_DIR / category / book_id / book_id / "auto" / f"{book_id}_content_list.json"
        if p.exists():
            return p
    return None


def _find_middle_json(book_id: str) -> Path | None:
    """Search for middle.json across all categories."""
    for category in ["textbook", "ecdev", "real_estate"]:
        p = MINERU_OUTPUT_DIR / category / book_id / book_id / "auto" / f"{book_id}_middle.json"
        if p.exists():
            return p
    return None


def _find_pdf(book_id: str) -> Path | None:
    """Find source PDF."""
    for subdir in ["textbooks", "ecdev", "real_estate", "uploads"]:
        p = DATA_DIR / "raw_pdfs" / subdir / f"{book_id}.pdf"
        if p.exists():
            return p
    return None


@router.get("/pipeline-preview/{book_id}")
def pipeline_preview(book_id: str):
    """Return real input/output samples for every pipeline stage.

    Stages:
      1. pdf_parse   — PDF → content_list.json
      2. chunk_build  — content_list.json → structured chunks
      3. store        — chunks → SQLite rows
      4. vector       — chunk texts → ChromaDB vectors
      5. fts          — chunk texts → FTS5 virtual table
      6. toc          — PDF bookmarks → toc_entries
    """
    stages: list[dict[str, Any]] = []

    # ── Shared lookups ─────────────────────────────────────────────────────

    # Check if book exists in SQLite
    conn = _get_db()
    book_row = conn.execute(
        "SELECT id, book_id, title, authors, page_count, chapter_count, chunk_count "
        "FROM books WHERE book_id = ?",
        (book_id,),
    ).fetchone()

    # How many chunks in SQLite
    chunk_count = 0
    sample_chunks: list[dict] = []
    if book_row:
        chunk_count = book_row["chunk_count"] or conn.execute(
            "SELECT COUNT(*) FROM chunks WHERE book_id = ?", (book_row["id"],)
        ).fetchone()[0]

        rows = conn.execute(
            "SELECT chunk_id, content_type, text, reading_order "
            "FROM chunks WHERE book_id = ? ORDER BY reading_order LIMIT 3",
            (book_row["id"],),
        ).fetchall()
        sample_chunks = [
            {
                "chunk_id": r["chunk_id"],
                "content_type": r["content_type"],
                "text": r["text"][:200] + ("..." if len(r["text"]) > 200 else ""),
                "reading_order": r["reading_order"],
            }
            for r in rows
        ]

    # TOC entries
    toc_entries: list[dict] = []
    if book_row:
        try:
            toc_rows = conn.execute(
                "SELECT t.level, t.number, t.title, t.pdf_page "
                "FROM toc_entries t WHERE t.book_id = ? ORDER BY t.sort_order LIMIT 5",
                (book_row["id"],),
            ).fetchall()
            toc_entries = [
                {"level": r["level"], "number": r["number"], "title": r["title"], "pdf_page": r["pdf_page"]}
                for r in toc_rows
            ]
        except Exception:
            pass  # toc_entries table may not exist
        if not toc_entries:
            try:
                ch_rows = conn.execute(
                    "SELECT 1 as level, chapter_key as number, title "
                    "FROM chapters WHERE book_id = ? ORDER BY id LIMIT 5",
                    (book_row["id"],),
                ).fetchall()
                toc_entries = [
                    {"level": r["level"], "number": r["number"], "title": r["title"]}
                    for r in ch_rows
                ]
            except Exception:
                pass  # chapters table may not exist

    # FTS5 count
    fts_count = 0
    if book_row:
        try:
            fts_count = conn.execute(
                "SELECT COUNT(*) FROM chunk_fts cf "
                "JOIN chunks c ON cf.rowid = c.id "
                "WHERE c.book_id = ?",
                (book_row["id"],),
            ).fetchone()[0]
        except Exception:
            fts_count = 0

    conn.close()

    # ── MinerU outputs ─────────────────────────────────────────────────────

    content_list_path = _find_content_list(book_id)
    pdf_path = _find_pdf(book_id)

    content_list_items: list[dict] = []
    content_list_total = 0
    if content_list_path and content_list_path.exists():
        try:
            with open(content_list_path, "r", encoding="utf-8") as f:
                cl = json.load(f)
            content_list_total = len(cl)
            # Sample first 3 items
            for item in cl[:3]:
                content_list_items.append({
                    "type": item.get("type", "unknown"),
                    "page_idx": item.get("page_idx", 0),
                    "text": (item.get("text", "") or "")[:150] + ("..." if len(item.get("text", "") or "") > 150 else ""),
                    "text_level": item.get("text_level"),
                })
        except Exception as e:
            logger.warning("Failed to read content_list.json for %s: %s", book_id, e)

    # ── ChromaDB vector count ──────────────────────────────────────────────

    vector_count = 0
    vector_sample: list[dict] = []
    try:
        from engine.adapters.chroma_adapter import get_collection
        collection = get_collection()
        # Count vectors for this book
        result = collection.get(
            where={"book_id": book_id},
            limit=3,
            include=["metadatas", "documents"],
        )
        if result and result["ids"]:
            vector_count = collection.count()  # total collection count (approximate)
            # Get actual count for this book
            all_ids = collection.get(
                where={"book_id": book_id},
                limit=1,
                include=[],
            )
            # Use a count query
            vector_count_result = collection.get(
                where={"book_id": book_id},
                include=[],
            )
            vector_count = len(vector_count_result["ids"]) if vector_count_result else 0

            for i, doc_id in enumerate(result["ids"][:3]):
                meta = result["metadatas"][i] if result["metadatas"] else {}
                doc_text = result["documents"][i] if result["documents"] else ""
                vector_sample.append({
                    "id": doc_id,
                    "text": (doc_text or "")[:120] + "...",
                    "content_type": meta.get("content_type", ""),
                })
    except Exception as e:
        logger.warning("ChromaDB preview failed for %s: %s", book_id, e)

    # ── Build stages ───────────────────────────────────────────────────────

    # Stage 1: PDF Parse
    pdf_size_mb = round(pdf_path.stat().st_size / 1024 / 1024, 1) if pdf_path else 0
    stages.append({
        "stage": "pdf_parse",
        "label": "PDF 解析 (MinerU)",
        "labelEn": "PDF Parse (MinerU)",
        "status": "done" if content_list_path else "pending",
        "input": {
            "type": "pdf",
            "description": f"原始 PDF 文件 ({pdf_size_mb} MB)",
            "preview": [
                {"字段": "文件", "值": pdf_path.name if pdf_path else "未找到"},
                {"字段": "大小", "值": f"{pdf_size_mb} MB"},
                {"字段": "路径", "值": str(pdf_path.relative_to(DATA_DIR)) if pdf_path else "N/A"},
            ],
        },
        "output": {
            "type": "json",
            "description": f"content_list.json ({content_list_total} 个元素)",
            "preview": content_list_items,
        },
    })

    # Stage 2: Chunk Build
    stages.append({
        "stage": "chunk_build",
        "label": "分块 (Chunking)",
        "labelEn": "Chunk Build",
        "status": "done" if chunk_count > 0 else ("pending" if content_list_path else "missing"),
        "input": {
            "type": "json",
            "description": f"content_list.json ({content_list_total} 个原始元素)",
            "preview": content_list_items[:2] if content_list_items else [],
        },
        "output": {
            "type": "chunks",
            "description": f"{chunk_count} 个结构化文本块",
            "preview": sample_chunks,
        },
    })

    # Stage 3: Store (SQLite)
    page_count = book_row["page_count"] if book_row else 0
    chapter_count = book_row["chapter_count"] if book_row else 0
    stages.append({
        "stage": "store",
        "label": "存储 (SQLite)",
        "labelEn": "Store (SQLite)",
        "status": "done" if book_row else "pending",
        "input": {
            "type": "chunks",
            "description": f"{chunk_count} 个文本块 + 元数据",
            "preview": sample_chunks[:2] if sample_chunks else [],
        },
        "output": {
            "type": "db_rows",
            "description": f"SQLite 数据库: {chunk_count} chunks, {page_count} pages, {chapter_count} chapters",
            "preview": [
                {"表": "books", "记录数": 1, "字段": "book_id, title, authors, category, page_count, chunk_count"},
                {"表": "chunks", "记录数": chunk_count, "字段": "chunk_id, text, content_type, reading_order"},
                {"表": "chapters", "记录数": chapter_count, "字段": "chapter_key, title"},
            ],
        },
    })

    # Stage 4: Vector (ChromaDB)
    stages.append({
        "stage": "vector",
        "label": "向量化 (ChromaDB)",
        "labelEn": "Vector Embed (ChromaDB)",
        "status": "done" if vector_count > 0 else "pending",
        "input": {
            "type": "texts",
            "description": f"{chunk_count} 个文本块的 text 字段",
            "preview": [
                {"chunk_id": c["chunk_id"], "text": c["text"][:100] + "..."}
                for c in sample_chunks[:2]
            ] if sample_chunks else [],
        },
        "output": {
            "type": "vectors",
            "description": f"{vector_count} 个向量 (384维, all-MiniLM-L6-v2)",
            "preview": vector_sample if vector_sample else [
                {"info": "ChromaDB 集合", "模型": "all-MiniLM-L6-v2", "维度": 384},
            ],
        },
    })

    # Stage 5: FTS5
    stages.append({
        "stage": "fts",
        "label": "全文检索 (FTS5)",
        "labelEn": "Full-Text Search (FTS5)",
        "status": "done" if fts_count > 0 else "pending",
        "input": {
            "type": "texts",
            "description": f"{chunk_count} 个文本块的 text 字段",
            "preview": [
                {"chunk_id": c["chunk_id"], "text": c["text"][:100] + "..."}
                for c in sample_chunks[:2]
            ] if sample_chunks else [],
        },
        "output": {
            "type": "fts_index",
            "description": f"FTS5 虚拟表: {fts_count} 条索引 (BM25 排序)",
            "preview": [
                {"虚拟表": "chunk_fts", "索引量": fts_count, "算法": "BM25"},
                {"触发器": "chunks_ai / chunks_ad / chunks_au", "说明": "自动同步 INSERT/DELETE/UPDATE"},
            ],
        },
    })

    # Stage 6: TOC
    stages.append({
        "stage": "toc",
        "label": "目录提取 (TOC)",
        "labelEn": "Table of Contents",
        "status": "done" if toc_entries else "pending",
        "input": {
            "type": "pdf",
            "description": "PDF 书签 / 大纲结构 + 章节标题",
            "preview": [
                {"来源": "PDF 书签 (bookmarks)", "说明": "通过 MinerU 提取"},
                {"来源": "text_level=1 标题", "说明": "正则匹配 Chapter / Appendix 模式"},
            ],
        },
        "output": {
            "type": "toc_entries",
            "description": f"{len(toc_entries)} 个目录条目",
            "preview": toc_entries,
        },
    })

    return {
        "bookId": book_id,
        "title": book_row["title"] if book_row else book_id,
        "status": "indexed" if book_row else "pending",
        "category": "textbook" if book_row else "unknown",
        "stages": stages,
    }
