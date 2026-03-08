"""Tests for the /api/v1/books endpoints."""

from __future__ import annotations

from fastapi.testclient import TestClient


def test_list_books(client: TestClient) -> None:
    resp = client.get("/api/v1/books")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    assert len(data) > 0
    assert "title" in data[0]


def test_get_book_detail(client: TestClient) -> None:
    # First get a valid id
    books = client.get("/api/v1/books").json()
    book_id = books[0]["id"]
    resp = client.get(f"/api/v1/books/{book_id}")
    assert resp.status_code == 200
    detail = resp.json()
    assert "chapters" in detail


def test_get_book_not_found(client: TestClient) -> None:
    resp = client.get("/api/v1/books/999999")
    assert resp.status_code == 404


def test_health(client: TestClient) -> None:
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}
