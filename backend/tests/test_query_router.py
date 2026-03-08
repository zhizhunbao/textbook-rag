"""Tests for the POST /api/v1/query endpoint.

Requires Ollama running locally with llama3.2:3b.
Tests are skipped when Ollama is unreachable.
"""

from __future__ import annotations

import socket

import pytest
from fastapi.testclient import TestClient


def _ollama_reachable() -> bool:
    try:
        s = socket.create_connection(("127.0.0.1", 11434), timeout=1)
        s.close()
        return True
    except OSError:
        return False


@pytest.mark.skipif(not _ollama_reachable(), reason="Ollama not running")
def test_query_endpoint(client: TestClient) -> None:
    resp = client.post(
        "/api/v1/query",
        json={"question": "What is backpropagation?", "top_k": 3},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "answer" in data
    assert "sources" in data
    assert "retrieval_stats" in data


def test_query_validation_empty(client: TestClient) -> None:
    resp = client.post("/api/v1/query", json={"question": ""})
    assert resp.status_code == 422


def test_query_validation_top_k_too_large(client: TestClient) -> None:
    resp = client.post(
        "/api/v1/query",
        json={"question": "hello", "top_k": 100},
    )
    assert resp.status_code == 422
