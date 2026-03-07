# Unit tests for retrieval wrappers.
# Refs:
# - Okken, Python Testing with pytest, Ch2 and parametrize/mocking sections:
#   test thin adapters at the behavior boundary and keep collaborators fakeable.
# - Manning et al., Introduction to Information Retrieval, vector-space ranking
#   chapters: retrieval tests check that ranking scores and top-k selection are
#   preserved through the wrapper layer.
# - Jurafsky and Martin, Speech and Language Processing, IR sections: retrieval
#   quality depends on mapping candidate passages back to stable source spans.

from __future__ import annotations

from backend.app.models import Chunk
from backend.app.retrieval import pageindex_retriever as pageindex_module
from backend.app.retrieval.bm25_retriever import BM25Retriever
from backend.app.retrieval.pageindex_retriever import PageIndexRetriever
from backend.app.retrieval.semantic_retriever import SemanticRetriever


def _make_chunk(chunk_id: str, text: str = "Chunk text", page_number: int = 0) -> Chunk:
    return Chunk(
        chunk_id=chunk_id,
        book_key="book",
        book_title="Book",
        chapter="Chapter 1",
        section="",
        page_number=page_number,
        content_type="text",
        text=text,
        bbox=[0, 0, 1, 1],
    )


class TestRetrieverWrappers:
    """Tests for lightweight retriever wrapper classes."""

    def test_bm25_retriever_wraps_chunks_with_rank_scores(self) -> None:
        """BM25 wrapper delegates to indexer and adds descending reciprocal scores."""

        class FakeIndexer:
            def __init__(self) -> None:
                self.calls = []

            def search(self, **kwargs):
                self.calls.append(kwargs)
                return [_make_chunk("a"), _make_chunk("b")]

        indexer = FakeIndexer()
        retriever = BM25Retriever(indexer)

        results = retriever.search(
            "query", top_k=4, book_filter=["book"], content_type_filter=["text"]
        )

        assert indexer.calls == [
            {
                "query": "query",
                "top_k": 4,
                "book_filter": ["book"],
                "content_type_filter": ["text"],
            }
        ]
        assert [r.chunk.chunk_id for r in results] == ["a", "b"]
        assert [r.score for r in results] == [1.0, 0.5]
        assert all(r.method == "bm25" for r in results)

    def test_semantic_retriever_preserves_similarity_scores(self) -> None:
        """Semantic wrapper maps returned tuples into RetrievedChunk objects."""

        class FakeIndexer:
            def search(self, **kwargs):
                return [(_make_chunk("a"), 0.91), (_make_chunk("b"), 0.83)]

        retriever = SemanticRetriever(FakeIndexer())
        results = retriever.search("query")

        assert [r.chunk.chunk_id for r in results] == ["a", "b"]
        assert [r.score for r in results] == [0.91, 0.83]
        assert all(r.method == "semantic" for r in results)


class TestPageIndexRetriever:
    """Tests for PageIndexRetriever."""

    def test_empty_trees_returns_empty(self, monkeypatch) -> None:
        """No trees means the LLM step is skipped."""

        class FakeClient:
            def __init__(self, host: str) -> None:
                self.host = host

        monkeypatch.setattr(pageindex_module, "Client", FakeClient)

        retriever = PageIndexRetriever(
            "http://ollama", "demo-model", sqlite_indexer=object()
        )
        assert retriever.search("query", trees={}) == []

    def test_llm_failure_returns_empty(self, monkeypatch) -> None:
        """Ollama failures are swallowed and surfaced as no results."""

        class FakeResponseError(Exception):
            pass

        class FakeClient:
            def __init__(self, host: str) -> None:
                self.host = host

            def chat(self, *, model: str, messages: list[dict]) -> dict:
                raise FakeResponseError("down")

        monkeypatch.setattr(pageindex_module, "Client", FakeClient)
        monkeypatch.setattr(pageindex_module, "ResponseError", FakeResponseError)

        retriever = PageIndexRetriever(
            "http://ollama", "demo-model", sqlite_indexer=object()
        )
        trees = {
            "book": {
                "book_title": "Book",
                "tree": [{"title": "Intro", "page_start": 0, "page_end": 5}],
            }
        }
        assert retriever.search("query", trees) == []

    def test_search_matches_selected_chapter_and_fetches_chunks(
        self, monkeypatch
    ) -> None:
        """Selected chapter titles are mapped back to page ranges and converted to results."""

        class FakeClient:
            def __init__(self, host: str) -> None:
                self.host = host

            def chat(self, *, model: str, messages: list[dict]) -> dict:
                return {"message": {"content": "Book - Neural Networks Foundations"}}

        class FakeIndexer:
            def __init__(self) -> None:
                self.calls = []

            def get_chunks_by_pages(
                self, book_key: str, page_start: int, page_end: int
            ):
                self.calls.append((book_key, page_start, page_end))
                return [
                    _make_chunk("a", page_number=page_start),
                    _make_chunk("b", page_number=page_end),
                ]

        monkeypatch.setattr(pageindex_module, "Client", FakeClient)

        indexer = FakeIndexer()
        retriever = PageIndexRetriever(
            "http://ollama", "demo-model", sqlite_indexer=indexer
        )
        trees = {
            "book": {
                "book_title": "Book",
                "tree": [
                    {
                        "title": "Neural Networks Foundations",
                        "page_start": 10,
                        "page_end": 25,
                    }
                ],
            }
        }

        results = retriever.search("What are neural networks?", trees, top_k=1)

        assert indexer.calls == [("book", 10, 15)]
        assert len(results) == 1
        assert results[0].chunk.chunk_id == "a"
        assert results[0].method == "pageindex"
