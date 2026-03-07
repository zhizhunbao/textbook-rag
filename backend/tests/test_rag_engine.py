# Unit tests for RAG engine orchestration.
# Refs:
# - Okken, Python Testing with pytest: orchestrators should be tested with fakes
#   and stable observable contracts.
# - Software Engineering at Google: focus tests on behavior and failure paths.
# - Ramalho, Fluent Python: concurrent.futures timeout/error handling is part of
#   the public orchestration contract here.
# - Jurafsky and Martin, Speech and Language Processing: preserve the
#   evidence-grounded retrieval -> answer flow.

from __future__ import annotations

import shutil
from contextlib import contextmanager
from pathlib import Path
from uuid import uuid4

from backend.app import rag_engine as rag_module
from backend.app.config import (
    ChunkingConfig,
    Config,
    EmbeddingConfig,
    OllamaConfig,
    PathsConfig,
    RetrievalConfig,
)
from backend.app.models import (
    BookInfo,
    Chunk,
    QueryResult,
    RetrievedChunk,
    SourceReference,
)
from backend.app.rag_engine import RAGEngine


REPO_ROOT = Path(__file__).resolve().parents[2]


@contextmanager
def _repo_temp_dir() -> Path:
    """Create a temporary directory under the repository for deterministic cleanup."""
    temp_dir = REPO_ROOT / "backend" / ".tmp-tests" / f"rag-engine-{uuid4().hex}"
    temp_dir.mkdir(parents=True, exist_ok=True)
    try:
        yield temp_dir
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


def _make_chunk(chunk_id: str, page_number: int = 1) -> Chunk:
    return Chunk(
        chunk_id=chunk_id,
        book_key="book",
        book_title="Book",
        chapter="Chapter 1",
        section="",
        page_number=page_number,
        content_type="text",
        text=f"chunk {chunk_id}",
        bbox=[0, 0, 1, 1],
    )


def _make_config(tmp_path: Path, methods: dict[str, bool] | None = None) -> Config:
    return Config(
        ollama=OllamaConfig(),
        embedding=EmbeddingConfig(),
        retrieval=RetrievalConfig(
            methods=methods or {"bm25": True, "semantic": True, "pageindex": True},
            parallel_timeout=3,
            top_k=2,
            rrf_k=60,
        ),
        chunking=ChunkingConfig(),
        paths=PathsConfig(
            mineru_output=tmp_path / "mineru",
            textbooks_dir=tmp_path / "books",
            sqlite_db=tmp_path / "db.sqlite3",
            chroma_db=tmp_path / "chroma",
            pageindex_trees=tmp_path / "trees",
        ),
        project_root=tmp_path,
    )


class _FakeSQLiteIndexer:
    def __init__(self, db_path: Path) -> None:
        self.db_path = db_path
        self.closed = False

    def total_chunks(self) -> int:
        return 3

    def get_books(self) -> list[BookInfo]:
        return [BookInfo(book_key="book", book_title="Book", total_chunks=3)]

    def close(self) -> None:
        self.closed = True


class _FakeChromaIndexer:
    def __init__(self, db_path: Path, model_name: str) -> None:
        self.db_path = db_path
        self.model_name = model_name

    def count(self) -> int:
        return 2


class _FakePageIndexBuilder:
    def load_all_trees(self, trees_dir: Path) -> dict[str, dict]:
        return {"book": {"tree": [{"title": "Intro", "page_start": 0, "page_end": 3}]}}


class _FakeBM25Retriever:
    def __init__(self, indexer) -> None:
        self.indexer = indexer

    def search(self, question: str, top_k: int, book_filter, content_type_filter):
        return [RetrievedChunk(chunk=_make_chunk("bm25"), score=1.0, method="bm25")]


class _FakeSemanticRetriever:
    def __init__(self, indexer) -> None:
        self.indexer = indexer

    def search(self, question: str, top_k: int, book_filter, content_type_filter):
        return [
            RetrievedChunk(chunk=_make_chunk("semantic"), score=0.8, method="semantic")
        ]


class _FakePageIndexRetriever:
    def __init__(self, ollama_host: str, model: str, sqlite_indexer) -> None:
        self.host = ollama_host
        self.model = model
        self.indexer = sqlite_indexer

    def search(self, question: str, trees: dict[str, dict], top_k: int):
        return [
            RetrievedChunk(
                chunk=_make_chunk("pageindex"), score=0.7, method="pageindex"
            )
        ]


class _FakeFuser:
    def __init__(self, k: int) -> None:
        self.k = k

    def fuse(self, results_per_method: dict[str, list[RetrievedChunk]], top_k: int):
        chunks = []
        for items in results_per_method.values():
            chunks.extend(items)
        return chunks[:top_k]


class _FakeGenerator:
    def __init__(self, host: str, model: str, timeout: int) -> None:
        self.host = host
        self.model = model
        self.timeout = timeout

    def generate(self, question: str, chunks: list[Chunk]) -> QueryResult:
        return QueryResult(
            answer="generated answer",
            sources=[
                SourceReference(citation_id=i + 1, chunk=chunk, relevance_score=1.0)
                for i, chunk in enumerate(chunks)
            ],
        )

    def check_health(self) -> bool:
        return True


class _FakeTracer:
    def __init__(self, textbooks_dir: Path, mineru_output_dir: Path) -> None:
        self.textbooks_dir = textbooks_dir
        self.mineru_output_dir = mineru_output_dir

    def render_page_with_highlight(
        self, book_key: str, page_number: int, bbox: list[float], zoom: float
    ):
        return {
            "book_key": book_key,
            "page_number": page_number,
            "bbox": bbox,
            "zoom": zoom,
        }


class TestRAGEngine:
    def test_query_collects_results_and_exposes_helpers(self, monkeypatch) -> None:
        monkeypatch.setattr(rag_module, "SQLiteIndexer", _FakeSQLiteIndexer)
        monkeypatch.setattr(rag_module, "ChromaIndexer", _FakeChromaIndexer)
        monkeypatch.setattr(rag_module, "PageIndexBuilder", _FakePageIndexBuilder)
        monkeypatch.setattr(rag_module, "BM25Retriever", _FakeBM25Retriever)
        monkeypatch.setattr(rag_module, "SemanticRetriever", _FakeSemanticRetriever)
        monkeypatch.setattr(rag_module, "PageIndexRetriever", _FakePageIndexRetriever)
        monkeypatch.setattr(rag_module, "RRFFuser", _FakeFuser)
        monkeypatch.setattr(rag_module, "AnswerGenerator", _FakeGenerator)
        monkeypatch.setattr(rag_module, "SourceTracer", _FakeTracer)

        with _repo_temp_dir() as temp_dir:
            engine = RAGEngine(_make_config(temp_dir))
            result = engine.query("What is this?")

            assert result.answer == "generated answer"
            assert len(result.sources) == 2
            assert "1 results" in result.retrieval_stats["bm25"]
            assert "1 results" in result.retrieval_stats["semantic"]
            assert "1 results" in result.retrieval_stats["pageindex"]
            assert result.retrieval_stats["rrf_fused"] == "2 chunks"
            assert engine.get_available_books()[0].book_key == "book"
            assert engine.render_source("book", 1, [0, 0, 1, 1])["page_number"] == 1
            assert engine.check_health() == {
                "sqlite": True,
                "chroma": True,
                "pageindex": True,
                "ollama": True,
            }

            engine.close()
            assert engine._sqlite.closed is True

    def test_query_handles_timeout_and_retrieval_errors(self, monkeypatch) -> None:
        class FakeFuture:
            def __init__(self, behavior: str) -> None:
                self.behavior = behavior

            def result(self, timeout: int):
                if self.behavior == "timeout":
                    raise rag_module.FutureTimeout()
                if self.behavior == "error":
                    raise RuntimeError("broken")
                return [
                    RetrievedChunk(
                        chunk=_make_chunk("ok"), score=1.0, method="semantic"
                    )
                ]

        class FakeExecutor:
            def __init__(self, max_workers: int) -> None:
                self.max_workers = max_workers

            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc, tb) -> None:
                return None

            def submit(self, fn, *args):
                name = fn.__self__.__class__.__name__
                if name == "_FakeBM25Retriever":
                    return FakeFuture("timeout")
                if name == "_FakeSemanticRetriever":
                    return FakeFuture("error")
                return FakeFuture("ok")

        monkeypatch.setattr(rag_module, "SQLiteIndexer", _FakeSQLiteIndexer)
        monkeypatch.setattr(rag_module, "ChromaIndexer", _FakeChromaIndexer)
        monkeypatch.setattr(rag_module, "PageIndexBuilder", _FakePageIndexBuilder)
        monkeypatch.setattr(rag_module, "BM25Retriever", _FakeBM25Retriever)
        monkeypatch.setattr(rag_module, "SemanticRetriever", _FakeSemanticRetriever)
        monkeypatch.setattr(rag_module, "PageIndexRetriever", _FakePageIndexRetriever)
        monkeypatch.setattr(rag_module, "RRFFuser", _FakeFuser)
        monkeypatch.setattr(rag_module, "AnswerGenerator", _FakeGenerator)
        monkeypatch.setattr(rag_module, "SourceTracer", _FakeTracer)
        monkeypatch.setattr(rag_module, "ThreadPoolExecutor", FakeExecutor)

        with _repo_temp_dir() as temp_dir:
            engine = RAGEngine(_make_config(temp_dir))
            result = engine.query("What is this?")

            assert "timeout" in result.retrieval_stats["bm25"]
            assert "error: broken" in result.retrieval_stats["semantic"]
            assert "1 results" in result.retrieval_stats["pageindex"]

    def test_query_reports_progress_stages(self, monkeypatch) -> None:
        monkeypatch.setattr(rag_module, "SQLiteIndexer", _FakeSQLiteIndexer)
        monkeypatch.setattr(rag_module, "ChromaIndexer", _FakeChromaIndexer)
        monkeypatch.setattr(rag_module, "PageIndexBuilder", _FakePageIndexBuilder)
        monkeypatch.setattr(rag_module, "BM25Retriever", _FakeBM25Retriever)
        monkeypatch.setattr(rag_module, "SemanticRetriever", _FakeSemanticRetriever)
        monkeypatch.setattr(rag_module, "PageIndexRetriever", _FakePageIndexRetriever)
        monkeypatch.setattr(rag_module, "RRFFuser", _FakeFuser)
        monkeypatch.setattr(rag_module, "AnswerGenerator", _FakeGenerator)
        monkeypatch.setattr(rag_module, "SourceTracer", _FakeTracer)

        with _repo_temp_dir() as temp_dir:
            engine = RAGEngine(_make_config(temp_dir))
            progress_messages: list[str] = []

            engine.query("What is this?", progress_callback=progress_messages.append)

            assert progress_messages[0].startswith("Starting retrieval with:")
            assert "BM25 retrieval is scanning keyword matches." in progress_messages
            assert "Semantic retrieval is comparing vector similarity." in progress_messages
            assert "Fusing retrieval results into a ranked shortlist." in progress_messages
            assert progress_messages[-1] == "Answer generation finished."
