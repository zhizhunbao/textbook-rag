"""Tests for generation_service — Ollama prompt building and error handling."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from backend.app.services import generation_service


def _sample_chunks() -> list[dict]:
    return [
        {"book_title": "Deep Learning", "chapter_title": "Ch 6", "text": "Gradient descent is..."},
        {"book_title": "PRML", "chapter_title": "Ch 1", "text": "Bayesian inference..."},
    ]


def test_build_context() -> None:
    """_build_context should number and format chunks."""
    ctx = generation_service._build_context(_sample_chunks())
    assert "[1] Deep Learning" in ctx
    assert "[2] PRML" in ctx
    assert "---" in ctx


def test_generate_success() -> None:
    """generate() should return model response text."""
    mock_client = MagicMock()
    mock_client.chat.return_value = {"message": {"content": "The answer is 42."}}

    with patch("backend.app.services.generation_service._ollama.Client", return_value=mock_client):
        result = generation_service.generate("What is the answer?", _sample_chunks())

    assert result == "The answer is 42."
    mock_client.chat.assert_called_once()
    call_args = mock_client.chat.call_args
    messages = call_args.kwargs.get("messages") or call_args[1].get("messages")
    assert len(messages) == 2
    assert messages[0]["role"] == "system"
    assert "Context" in messages[1]["content"]


def test_generate_ollama_error() -> None:
    """generate() should raise RuntimeError when Ollama fails."""
    mock_client = MagicMock()
    mock_client.chat.side_effect = ConnectionError("refused")

    with (
        patch("backend.app.services.generation_service._ollama.Client", return_value=mock_client),
        pytest.raises(RuntimeError, match="Ollama generation failed"),
    ):
        generation_service.generate("test", [])
