"""Books router — GET /books, /books/{book_id}, /books/{book_id}/pdf."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import FileResponse

from backend.app.database import DB
from backend.app.repositories import book_repo
from backend.app.schemas.books import BookDetail, BookSummary, ChapterInfo, TocEntry

router = APIRouter(prefix="/api/v1/books", tags=["books"])


@router.get("", response_model=list[BookSummary])
def list_books(db: DB) -> list[BookSummary]:
    rows = book_repo.list_books(db)
    return [BookSummary(**r) for r in rows]


@router.get("/{book_id}", response_model=BookDetail)
def get_book(book_id: int, db: DB) -> BookDetail:
    book = book_repo.get_book(db, book_id)
    if book is None:
        raise HTTPException(status_code=404, detail="Book not found")
    chapters = [ChapterInfo(**c) for c in book.pop("chapters", [])]
    return BookDetail(**book, chapters=chapters)


@router.get("/{book_id}/toc", response_model=list[TocEntry])
def get_toc(book_id: int, db: DB) -> list[TocEntry]:
    entries = book_repo.get_toc(db, book_id)
    if entries is None:
        raise HTTPException(status_code=404, detail="Book not found")
    return [TocEntry(**e) for e in entries]


@router.get("/{book_id}/suggestions", response_model=list[str])
def get_suggestions(book_id: int, db: DB) -> list[str]:
    suggestions = book_repo.get_suggestions(db, book_id)
    if suggestions is None:
        raise HTTPException(status_code=404, detail="Book not found")
    return suggestions


@router.get("/{book_id}/pdf")
def get_pdf(
    book_id: int,
    db: DB,
    variant: str = Query("origin", pattern="^(origin|layout)$"),
) -> FileResponse:
    path = book_repo.get_pdf_path(db, book_id, variant=variant)
    if path is None:
        raise HTTPException(status_code=404, detail="PDF not found for this book")
    return FileResponse(
        path=str(path),
        media_type="application/pdf",
        filename=path.name,
    )
