# Unit tests for answer generation.
# Refs:
# - Okken, Python Testing with pytest, mocking chapters: isolate LLM client
#   behavior with fakes so success and failure paths are explicit.
# - Jurafsky and Martin, Speech and Language Processing, QA/RAG sections:
#   answer generation should stay grounded in retrieved evidence and expose
#   source citations rather than free-form unsupported output.

from __future__ import annotations

from backend.app.generation import generator as generator_module
from backend.app.generation.generator import AnswerGenerator
from backend.app.models import Chunk


def _make_chunk(chunk_id: str, text: str = "Chunk body") -> Chunk:
    return Chunk(
        chunk_id=chunk_id,
        book_key="book",
        book_title="Book",
        chapter="Chapter 1",
        section="",
        page_number=3,
        content_type="text",
        text=text,
        bbox=[0, 0, 10, 10],
    )


class TestAnswerGenerator:
    """Tests for AnswerGenerator."""

    def test_generate_returns_fallback_when_no_chunks(self) -> None:
        """No retrieved chunks yields the documented fallback answer."""
        generator = AnswerGenerator.__new__(AnswerGenerator)
        result = generator.generate("What is this?", [])

        assert "could not find relevant information" in result.answer.lower()
        assert result.sources == []

    def test_generate_builds_sources_from_successful_response(
        self, monkeypatch
    ) -> None:
        """Successful chat response returns answer text and citations."""

        class FakeClient:
            def __init__(self, host: str) -> None:
                self.host = host

            def chat(self, *, model: str, messages: list[dict]) -> dict:
                assert model == "demo-model"
                assert messages[0]["role"] == "system"
                assert "Question: Explain" in messages[1]["content"]
                return {"message": {"content": "Answer text [1]"}}

        monkeypatch.setattr(generator_module, "Client", FakeClient)

        generator = AnswerGenerator(host="http://ollama", model="demo-model")
        result = generator.generate("Explain", [_make_chunk("a"), _make_chunk("b")])

        assert result.answer == "Answer text [1]"
        assert len(result.sources) == 2
        assert result.sources[0].citation_id == 1
        assert result.sources[0].chunk.chunk_id == "a"

    def test_generate_handles_response_error(self, monkeypatch) -> None:
        """Ollama-specific failures return a helpful error message."""

        class FakeResponseError(Exception):
            pass

        class FakeClient:
            def __init__(self, host: str) -> None:
                self.host = host

            def chat(self, *, model: str, messages: list[dict]) -> dict:
                raise FakeResponseError("offline")

        monkeypatch.setattr(generator_module, "Client", FakeClient)
        monkeypatch.setattr(generator_module, "ResponseError", FakeResponseError)

        generator = AnswerGenerator(host="http://ollama", model="demo-model")
        result = generator.generate("Explain", [_make_chunk("a")])

        assert "Could not generate answer" in result.answer
        assert result.sources == []

    def test_check_health_reflects_client_list(self, monkeypatch) -> None:
        """Health check returns True only when the client responds."""

        class HealthyClient:
            def __init__(self, host: str) -> None:
                self.host = host

            def list(self) -> list[str]:
                return ["demo-model"]

        class UnhealthyClient:
            def __init__(self, host: str) -> None:
                self.host = host

            def list(self) -> list[str]:
                raise RuntimeError("down")

        monkeypatch.setattr(generator_module, "Client", HealthyClient)
        healthy = AnswerGenerator(host="http://ollama", model="demo-model")
        assert healthy.check_health() is True

        monkeypatch.setattr(generator_module, "Client", UnhealthyClient)
        unhealthy = AnswerGenerator(host="http://ollama", model="demo-model")
        assert unhealthy.check_health() is False
