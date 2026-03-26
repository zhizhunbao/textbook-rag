"""Pydantic schemas for the /books endpoints."""

from __future__ import annotations

from pydantic import BaseModel


class BookSummary(BaseModel):
    id: int
    book_id: str
    title: str
    authors: str
    page_count: int
    chapter_count: int
    chunk_count: int


class ChapterInfo(BaseModel):
    id: int
    chapter_key: str
    title: str
    start_page: int | None = None


class BookDetail(BookSummary):
    chapters: list[ChapterInfo]


class TocEntry(BaseModel):
    id: int
    level: int
    number: str
    title: str
    pdf_page: int
