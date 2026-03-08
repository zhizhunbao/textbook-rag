"""Tests for book_repo — list, detail, PDF path."""

from __future__ import annotations

import sqlite3

from backend.app.repositories import book_repo


def test_list_books(db: sqlite3.Connection) -> None:
    books = book_repo.list_books(db)
    assert len(books) > 0
    first = books[0]
    assert "id" in first
    assert "title" in first
    assert "book_id" in first


def test_get_book_found(db: sqlite3.Connection) -> None:
    books = book_repo.list_books(db)
    book = book_repo.get_book(db, books[0]["id"])
    assert book is not None
    assert "chapters" in book


def test_get_book_not_found(db: sqlite3.Connection) -> None:
    assert book_repo.get_book(db, 999999) is None
