"""Ingest route — POST /engine/ingest.

Triggers the 2-stage ingest pipeline for an uploaded PDF:
  1. Parse with MinerU (do_parse → content_list.json + middle.json)
  2. Read with MinerUReader → LlamaIndex IngestionPipeline → ChromaDB

PDF files are read directly from data/raw_pdfs/ (shared with Payload
pdf-uploads collection) — no HTTP download needed.

Ref: HF-04 — integrate MinerU parsing
"""

from __future__ import annotations

import asyncio
import queue
import threading
from pathlib import Path
from typing import Any

from fastapi import APIRouter
from loguru import logger
from pydantic import BaseModel
from starlette.responses import StreamingResponse

from engine_v2.settings import DATA_DIR, MINERU_OUTPUT_DIR

router = APIRouter()

# ── Cancellation registry — tracks active pipeline runs by book_id ──
_cancel_flags: dict[int, threading.Event] = {}
_cancel_lock = threading.Lock()

# ── Log queue registry — per-book log queues for SSE streaming ──
_log_queues: dict[int, queue.Queue] = {}
_log_queues_lock = threading.Lock()

# ── Shared PDF directory (Payload pdf-uploads stores files here) ──
RAW_PDF_DIR = DATA_DIR / "raw_pdfs"


class IngestRequest(BaseModel):
    book_id: int
    pdf_filename: str | None = None  # Filename in data/raw_pdfs/ (from Payload)
    category: str = "textbook"
    task_id: int | None = None
    title: str | None = None
    force_parse: bool = False  # Delete existing MinerU output and re-parse


def _derive_book_dir_name(req: IngestRequest) -> str:
    """Derive a filesystem-safe book directory name."""
    if req.title:
        # Sanitise title: lowercase, replace spaces/special chars with underscores
        safe = req.title.lower().strip()
        safe = "".join(c if c.isalnum() or c in (" ", "-", "_") else "" for c in safe)
        safe = safe.replace(" ", "_").replace("-", "_")
        # Remove consecutive underscores
        while "__" in safe:
            safe = safe.replace("__", "_")
        return safe.strip("_") or f"book_{req.book_id}"
    return f"book_{req.book_id}"



def _run_mineru_parse(pdf_path, book_dir_name: str, category: str) -> None:
    """Run MinerU parsing on a PDF file.

    Uses MinerU Python API (do_parse) to generate:
      - {book_dir_name}_content_list.json
      - {book_dir_name}_middle.json
      - {book_dir_name}_origin.pdf
      - {book_dir_name}.md
      - images/

    Output is placed in: mineru_output/{category}/{book_dir_name}/{book_dir_name}/auto/
    to match the directory structure expected by MinerUReader.

    Ref: .github/references/MinerU/mineru/cli/common.py — do_parse()
    """
    from pathlib import Path

    from mineru.cli.common import do_parse, read_fn

    # MinerU outputs to: output_dir/{pdf_file_name}/{parse_method}/
    # We need: mineru_output/{category}/{book_dir_name}/{book_dir_name}/auto/
    # So set output_dir = mineru_output/{category}/{book_dir_name}
    # and pdf_file_name = book_dir_name
    # and parse_method = "auto"
    output_dir = str(MINERU_OUTPUT_DIR / category / book_dir_name)

    logger.info("Running MinerU parse: {} → {}", pdf_path, output_dir)

    pdf_bytes = read_fn(Path(pdf_path))

    do_parse(
        output_dir=output_dir,
        pdf_file_names=[book_dir_name],
        pdf_bytes_list=[pdf_bytes],
        p_lang_list=["en"],
        backend="pipeline",
        parse_method="auto",
        f_draw_layout_bbox=True,
        f_draw_span_bbox=False,   # Skip span bbox (not needed)
        f_dump_md=True,
        f_dump_middle_json=True,
        f_dump_model_output=False,  # Skip model output (saves disk)
        f_dump_orig_pdf=True,
        f_dump_content_list=True,
    )

    # Verify output exists
    content_list = Path(output_dir) / book_dir_name / "auto" / f"{book_dir_name}_content_list.json"
    if not content_list.exists():
        raise FileNotFoundError(
            f"MinerU parse completed but content_list.json not found at {content_list}"
        )
    logger.info("MinerU parse complete: {}", content_list)


def _update_parse_stage(
    book_id: int,
    parse_output: dict | None = None,
) -> None:
    """Mark parse stage as done in Payload CMS and seed parseOutput data."""
    import httpx
    from engine_v2.settings import PAYLOAD_URL, PAYLOAD_API_KEY

    headers = {"Content-Type": "application/json"}
    if PAYLOAD_API_KEY:
        headers["Authorization"] = f"Bearer {PAYLOAD_API_KEY}"

    body: dict = {"status": "processing", "pipeline": {"parse": "done"}}
    if parse_output:
        body["pipeline"]["parseOutput"] = parse_output

    try:
        httpx.patch(
            f"{PAYLOAD_URL}/api/books/{book_id}",
            json=body,
            headers=headers,
            timeout=30.0,
        ).raise_for_status()
    except Exception as e:
        logger.warning("Failed to update parse stage for book {}: {}", book_id, e)


def _collect_parse_output(book_dir_name: str, category: str) -> dict:
    """Collect MinerU parse output metadata for Payload seeding."""
    import json as json_mod

    auto_dir = MINERU_OUTPUT_DIR / category / book_dir_name / book_dir_name / "auto"
    content_list_path = auto_dir / f"{book_dir_name}_content_list.json"
    md_path = auto_dir / f"{book_dir_name}.md"
    images_dir = auto_dir / "images"

    result: dict = {
        "outputPath": str(auto_dir),
        "contentListExists": content_list_path.exists(),
        "mdExists": md_path.exists(),
        "imagesCount": len(list(images_dir.iterdir())) if images_dir.exists() else 0,
    }

    # Build file tree (relative to auto_dir, max 50 entries)
    file_tree: list[dict] = []
    if auto_dir.exists():
        try:
            for p in sorted(auto_dir.rglob("*")):
                if len(file_tree) >= 50:
                    break
                rel = str(p.relative_to(auto_dir)).replace("\\", "/")
                entry: dict = {"path": rel, "isDir": p.is_dir()}
                if p.is_file():
                    entry["size"] = p.stat().st_size
                    # Categorize by extension
                    ext = p.suffix.lower()
                    if ext == ".json":
                        entry["kind"] = "json"
                    elif ext == ".md":
                        entry["kind"] = "markdown"
                    elif ext in (".png", ".jpg", ".jpeg", ".gif", ".svg"):
                        entry["kind"] = "image"
                    elif ext == ".pdf":
                        entry["kind"] = "pdf"
                    else:
                        entry["kind"] = "file"
                file_tree.append(entry)
        except Exception:
            pass
    result["fileTree"] = file_tree

    if content_list_path.exists():
        try:
            raw = json_mod.loads(content_list_path.read_text(encoding="utf-8"))
            result["contentListCount"] = len(raw) if isinstance(raw, list) else 0
            # First 3 entries as sample
            if isinstance(raw, list):
                result["sample"] = raw[:3]
        except Exception:
            result["contentListCount"] = -1

    return result


def _resolve_pdf_path(req: IngestRequest) -> Path | None:
    """Locate the PDF file in the shared data/raw_pdfs/ directory.

    Search order:
        1. req.pdf_filename directly under RAW_PDF_DIR
        2. RAW_PDF_DIR / {category} / {pdf_filename}
        3. RAW_PDF_DIR / {category} / {book_dir_name}.pdf
        4. Scan all category subdirs for {book_dir_name}.pdf
    """
    book_dir_name = _derive_book_dir_name(req)

    # 1. Direct path from request
    if req.pdf_filename:
        path = RAW_PDF_DIR / req.pdf_filename
        if path.exists():
            return path
        # 2. Check under category subdir
        path = RAW_PDF_DIR / req.category / req.pdf_filename
        if path.exists():
            return path
        # 2b. Scan ALL subdirs for exact pdf_filename (file may be in a different category)
        for subdir in RAW_PDF_DIR.iterdir():
            if subdir.is_dir():
                candidate = subdir / req.pdf_filename
                if candidate.exists():
                    logger.info("Found PDF at {}", candidate)
                    return candidate
        logger.warning("PDF not found at {} or {}", RAW_PDF_DIR / req.pdf_filename, path)

    # 3. Try {category}/{book_dir_name}.pdf
    path = RAW_PDF_DIR / req.category / f"{book_dir_name}.pdf"
    if path.exists():
        return path

    # 4. Scan all subdirectories for {book_dir_name}.pdf (exact match)
    for subdir in RAW_PDF_DIR.iterdir():
        if subdir.is_dir():
            candidate = subdir / f"{book_dir_name}.pdf"
            if candidate.exists():
                logger.info("Found PDF at {}", candidate)
                return candidate

    # 5. Prefix match — find PDFs whose stem starts with book_dir_name
    #    (handles suffixed filenames like economic_update_q4_2024_en.pdf)
    for subdir in RAW_PDF_DIR.iterdir():
        if subdir.is_dir():
            for candidate in sorted(subdir.glob(f"{book_dir_name}*.pdf")):
                if candidate.is_file():
                    logger.info("Found PDF via prefix match at {}", candidate)
                    return candidate
    # Also check top-level raw_pdfs/ directory for prefix matches
    for candidate in sorted(RAW_PDF_DIR.glob(f"{book_dir_name}*.pdf")):
        if candidate.is_file():
            logger.info("Found PDF via prefix match at {}", candidate)
            return candidate

    logger.warning("No PDF found for book_dir_name={}", book_dir_name)
    return None


class CancelledError(Exception):
    """Raised when a pipeline run is cancelled by the user."""


def _check_cancel(book_id: int) -> None:
    """Check the cancellation flag and raise CancelledError if set."""
    with _cancel_lock:
        flag = _cancel_flags.get(book_id)
    if flag and flag.is_set():
        raise CancelledError(f"Pipeline cancelled for book {book_id}")


def _ingest_pipeline(req: IngestRequest) -> None:
    """Full ingest pipeline: parse → ingest."""
    from engine_v2.api.log_capture import register_thread, unregister_thread
    from engine_v2.ingestion.pipeline import ingest_book, _notify

    book_dir_name = _derive_book_dir_name(req)
    pdf_path = _resolve_pdf_path(req)

    # Register cancellation flag for this run
    cancel_event = threading.Event()
    with _cancel_lock:
        _cancel_flags[req.book_id] = cancel_event

    # Set up log capture for SSE streaming
    log_q: queue.Queue = queue.Queue(maxsize=5000)
    with _log_queues_lock:
        _log_queues[req.book_id] = log_q

    # Capture stdout/stderr from this thread
    register_thread(log_q)

    # Add loguru sink to capture loguru messages from this thread
    pipeline_tid = threading.current_thread().ident
    def _loguru_sink(message: Any) -> None:
        try:
            log_q.put_nowait(str(message).rstrip())
        except queue.Full:
            pass

    sink_id = logger.add(
        _loguru_sink,
        filter=lambda record: record["thread"].id == pipeline_tid,
        level="DEBUG",
        format="{time:HH:mm:ss} | {level:<5} | {message}",
    )

    # Reset pipeline stages at the start of each run
    try:
        import httpx
        from engine_v2.settings import PAYLOAD_URL, PAYLOAD_API_KEY
        headers = {"Content-Type": "application/json"}
        if PAYLOAD_API_KEY:
            headers["Authorization"] = f"Bearer {PAYLOAD_API_KEY}"
        httpx.patch(
            f"{PAYLOAD_URL}/api/books/{req.book_id}",
            json={
                "status": "processing",
                "pipeline": {"parse": "pending", "ingest": "pending"},
            },
            headers=headers,
            timeout=30.0,
        )
    except Exception:
        pass

    try:
        _check_cancel(req.book_id)

        # ── Step 1: MinerU parse ──
        # Check if MinerU output already exists (idempotent)
        auto_dir = MINERU_OUTPUT_DIR / req.category / book_dir_name / book_dir_name / "auto"
        content_list_path = auto_dir / f"{book_dir_name}_content_list.json"

        # Force re-parse: delete existing MinerU output if requested
        if req.force_parse and content_list_path.exists():
            import shutil
            shutil.rmtree(auto_dir.parent, ignore_errors=True)
            logger.info("Force re-parse: deleted existing MinerU output for {}", book_dir_name)
            _notify(req.task_id, status="running", progress=3, log="Deleted cached MinerU output, re-parsing...")

        if not content_list_path.exists():
            if pdf_path and pdf_path.exists():
                _notify(req.task_id, status="running", progress=5, log="Parsing PDF with MinerU...")
                _run_mineru_parse(pdf_path, book_dir_name, req.category)
                _check_cancel(req.book_id)
                _notify(req.task_id, status="running", progress=30, log="MinerU parsing complete")
            else:
                msg = f"No PDF found and no MinerU output for {book_dir_name}"
                logger.error(msg)
                _notify(req.task_id, status="error", error=msg)
                return
        else:
            logger.info("MinerU output already exists for {}, skipping parse", book_dir_name)
            _notify(req.task_id, status="running", progress=30, log="MinerU output found (cached)")

        _check_cancel(req.book_id)

        # Mark parse stage as done + seed parseOutput
        parse_output = _collect_parse_output(book_dir_name, req.category)
        _update_parse_stage(req.book_id, parse_output=parse_output)

        _check_cancel(req.book_id)

        # ── Step 2: Ingest (Reader → Chunking → Embedding → ChromaDB → Payload) ──
        ingest_book(
            book_id=req.book_id,
            book_dir_name=book_dir_name,
            category=req.category,
            task_id=req.task_id,
        )

    except CancelledError:
        logger.warning("Pipeline cancelled for book {}", req.book_id)
        _notify(req.task_id, status="error", error="Pipeline cancelled by user")
        try:
            import httpx
            from engine_v2.settings import PAYLOAD_URL, PAYLOAD_API_KEY
            headers = {"Content-Type": "application/json"}
            if PAYLOAD_API_KEY:
                headers["Authorization"] = f"Bearer {PAYLOAD_API_KEY}"
            httpx.patch(
                f"{PAYLOAD_URL}/api/books/{req.book_id}",
                json={"status": "error", "pipeline": {"parse": "error", "ingest": "error"}},
                headers=headers, timeout=30.0,
            )
        except Exception:
            pass

    except Exception as e:
        logger.exception("Ingest pipeline failed for book {}", req.book_id)
        _notify(req.task_id, status="error", error=str(e))

        # Update book status to error
        try:
            import httpx
            from engine_v2.settings import PAYLOAD_URL, PAYLOAD_API_KEY
            headers = {"Content-Type": "application/json"}
            if PAYLOAD_API_KEY:
                headers["Authorization"] = f"Bearer {PAYLOAD_API_KEY}"
            httpx.patch(
                f"{PAYLOAD_URL}/api/books/{req.book_id}",
                json={
                    "status": "error",
                    "pipeline": {"parse": "error", "ingest": "error"},
                },
                headers=headers,
                timeout=30.0,
            )
        except Exception:
            pass

    finally:
        # Clean up cancellation flag
        with _cancel_lock:
            _cancel_flags.pop(req.book_id, None)

        # Clean up log capture
        logger.remove(sink_id)
        unregister_thread()
        # Signal end-of-stream, then remove queue after a delay
        # (gives SSE clients time to read remaining messages)
        try:
            log_q.put_nowait("__END__")
        except queue.Full:
            pass

        def _cleanup_queue() -> None:
            import time
            time.sleep(5)
            with _log_queues_lock:
                _log_queues.pop(req.book_id, None)

        threading.Thread(target=_cleanup_queue, daemon=True).start()


@router.post("/ingest")
async def ingest(req: IngestRequest):
    """Trigger book ingestion in a background thread.

    Reads PDF directly from data/raw_pdfs/ (shared with Payload),
    runs MinerU parsing, then LlamaIndex ingestion into ChromaDB.
    """
    book_dir_name = _derive_book_dir_name(req)
    pdf_path = _resolve_pdf_path(req)

    logger.info(
        "Ingest request: book_id={}, dir={}, pdf={}, category={}",
        req.book_id, book_dir_name, pdf_path, req.category,
    )

    thread = threading.Thread(
        target=_ingest_pipeline,
        args=(req,),
        daemon=True,
    )
    thread.start()

    return {
        "status": "accepted",
        "cancellable": True,
        "book_id": req.book_id,
        "book_dir_name": book_dir_name,
    }


class CancelRequest(BaseModel):
    book_id: int


@router.post("/ingest/cancel")
async def cancel_ingest(req: CancelRequest):
    """Cancel a running ingest pipeline by setting its cancellation flag.

    The pipeline thread checks this flag between stages and aborts
    gracefully if set. Note: MinerU parsing cannot be interrupted
    mid-process — cancellation takes effect after the current step.
    """
    with _cancel_lock:
        flag = _cancel_flags.get(req.book_id)

    if flag is None:
        return {"status": "not_found", "message": "No active pipeline for this book"}

    flag.set()
    logger.info("Cancel signal sent for book {}", req.book_id)
    return {"status": "cancelled", "book_id": req.book_id}


class ResetTasksRequest(BaseModel):
    book_id: int


@router.post("/ingest/reset-tasks")
async def reset_stale_tasks(req: ResetTasksRequest):
    """Mark all queued/running ingest tasks for a book as error.

    Used to clean up zombie tasks that were never completed
    (e.g. engine crashed during processing).
    """
    import httpx
    from engine_v2.settings import PAYLOAD_URL, PAYLOAD_API_KEY

    headers: dict[str, str] = {"Content-Type": "application/json"}
    if PAYLOAD_API_KEY:
        headers["Authorization"] = f"Bearer {PAYLOAD_API_KEY}"

    # Fetch stale tasks for this book
    reset_count = 0
    try:
        resp = httpx.get(
            f"{PAYLOAD_URL}/api/ingest-tasks",
            params={
                "where[book][equals]": str(req.book_id),
                "where[status][in]": "queued,running",
                "limit": "50",
            },
            headers=headers, timeout=15.0,
        )
        resp.raise_for_status()
        docs = resp.json().get("docs", [])

        for doc in docs:
            try:
                httpx.patch(
                    f"{PAYLOAD_URL}/api/ingest-tasks/{doc['id']}",
                    json={"status": "error", "error": "Reset by user (stale task)"},
                    headers=headers, timeout=10.0,
                ).raise_for_status()
                reset_count += 1
            except Exception:
                pass

    except Exception as e:
        logger.warning("Failed to reset tasks for book {}: {}", req.book_id, e)

    return {"status": "ok", "reset_count": reset_count, "book_id": req.book_id}


# ── SSE log streaming endpoint ───────────────────────────────────
@router.get("/ingest/stream/{book_id}")
async def stream_logs(book_id: int):
    """Stream real-time pipeline logs via Server-Sent Events.

    The pipeline thread pushes log lines (stdout, stderr, loguru)
    to a per-book queue. This endpoint reads from that queue
    and streams to the frontend as SSE events.

    Events:
        data: <log line>       — regular log line
        event: done            — pipeline finished
        event: error           — no active pipeline
    """
    from engine_v2.api.log_capture import is_significant_tqdm

    async def generate():
        with _log_queues_lock:
            log_q = _log_queues.get(book_id)

        if not log_q:
            yield "event: error\ndata: No active pipeline for this book\n\n"
            return

        while True:
            # Drain all available lines from the queue
            lines: list[str] = []
            try:
                while True:
                    line = log_q.get_nowait()
                    if line == "__END__":
                        # Flush remaining lines then signal done
                        for ln in lines:
                            yield f"data: {ln}\n\n"
                        yield "event: done\ndata: Pipeline completed\n\n"
                        return
                    # Filter noisy tqdm updates
                    if is_significant_tqdm(line):
                        lines.append(line)
            except queue.Empty:
                pass

            # Send accumulated lines
            for ln in lines:
                yield f"data: {ln}\n\n"

            # Check if queue was removed (pipeline cleanup)
            with _log_queues_lock:
                if book_id not in _log_queues:
                    yield "event: done\ndata: Pipeline completed\n\n"
                    return

            await asyncio.sleep(0.2)

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
# ── Data Inspector endpoint ──────────────────────────────────────
@router.get("/inspect")
async def inspect(book_id: int, title: str = "", category: str = "textbook"):
    """Return real file/data info for the Data Inspector UI.

    Checks actual filesystem paths, content_list.json, ChromaDB, etc.
    """
    import json as json_mod

    # Derive paths
    fake_req = IngestRequest(book_id=book_id, title=title or None, category=category)
    book_dir_name = _derive_book_dir_name(fake_req)

    # PDF info
    pdf_files = list(RAW_PDF_DIR.glob("*")) if RAW_PDF_DIR.exists() else []
    pdf_info = None
    for f in pdf_files:
        if f.stem.lower().replace(" ", "_").replace("-", "_") == book_dir_name or f.stem == title:
            pdf_info = {
                "filename": f.name,
                "path": str(f),
                "size_bytes": f.stat().st_size,
                "size_mb": round(f.stat().st_size / (1024 * 1024), 2),
            }
            break
    # Fallback: look for the pdf_filename
    if not pdf_info:
        # Try matching by pdf_filename from Payload
        pdf_info = {
            "filename": "(not found locally)",
            "path": str(RAW_PDF_DIR),
            "size_bytes": 0,
            "size_mb": 0,
            "note": f"PDF not found. Available files: {[f.name for f in pdf_files[:5]]}",
        }

    # MinerU output
    auto_dir = MINERU_OUTPUT_DIR / category / book_dir_name / book_dir_name / "auto"
    content_list_path = auto_dir / f"{book_dir_name}_content_list.json"
    md_path = auto_dir / f"{book_dir_name}.md"
    images_dir = auto_dir / "images"

    mineru_info = {
        "exists": auto_dir.exists(),
        "path": str(auto_dir),
        "content_list_exists": content_list_path.exists(),
        "md_exists": md_path.exists(),
        "images_count": len(list(images_dir.iterdir())) if images_dir.exists() else 0,
    }

    # content_list.json sample
    content_list_sample = None
    content_list_count = 0
    if content_list_path.exists():
        try:
            raw = json_mod.loads(content_list_path.read_text(encoding="utf-8"))
            content_list_count = len(raw) if isinstance(raw, list) else 0
            content_list_sample = raw[:3] if isinstance(raw, list) else raw
        except Exception:
            content_list_sample = {"error": "Failed to parse"}

    # ChromaDB info
    chroma_info = {"count": 0}
    try:
        import chromadb
        from engine_v2.settings import CHROMA_PERSIST_DIR, CHROMA_COLLECTION
        client = chromadb.PersistentClient(
            path=str(CHROMA_PERSIST_DIR),
            settings=chromadb.Settings(anonymized_telemetry=False),
        )
        col = client.get_or_create_collection(CHROMA_COLLECTION)
        chroma_info["count"] = col.count()
        chroma_info["collection_name"] = CHROMA_COLLECTION
    except Exception:
        chroma_info["note"] = "ChromaDB not available"

    return {
        "book_id": book_id,
        "book_dir_name": book_dir_name,
        "category": category,
        "pdf": pdf_info,
        "mineru": mineru_info,
        "content_list": {
            "count": content_list_count,
            "sample": content_list_sample,
        },
        "chroma": chroma_info,
    }


@router.get("/ingest/file-tree/{book_id}")
async def file_tree(book_id: int, category: str = "textbook", book_dir_name: str = ""):
    """Return real-time file tree for a book's MinerU output directory.

    Scans filesystem directly — no database seeding required.
    """
    if not book_dir_name:
        return {"error": "book_dir_name required"}

    auto_dir = MINERU_OUTPUT_DIR / category / book_dir_name / book_dir_name / "auto"
    if not auto_dir.exists():
        return {"outputPath": str(auto_dir), "fileTree": [], "exists": False}

    file_tree: list[dict] = []
    try:
        for p in sorted(auto_dir.rglob("*")):
            if len(file_tree) >= 80:
                break
            rel = str(p.relative_to(auto_dir)).replace("\\", "/")
            entry: dict = {"path": rel, "isDir": p.is_dir()}
            if p.is_file():
                entry["size"] = p.stat().st_size
                ext = p.suffix.lower()
                if ext == ".json":
                    entry["kind"] = "json"
                elif ext == ".md":
                    entry["kind"] = "markdown"
                elif ext in (".png", ".jpg", ".jpeg", ".gif", ".svg"):
                    entry["kind"] = "image"
                elif ext == ".pdf":
                    entry["kind"] = "pdf"
                else:
                    entry["kind"] = "file"
            file_tree.append(entry)
    except Exception as e:
        return {"outputPath": str(auto_dir), "fileTree": [], "error": str(e)}

    return {"outputPath": str(auto_dir), "fileTree": file_tree, "exists": True}
