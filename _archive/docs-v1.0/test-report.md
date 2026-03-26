# Test Report — Testing Phase

**Date**: 2026-03-07
**Author**: Frank (QA Engineer)
**Phase**: testing (phase 08)

## Summary

| Metric | Value |
|---|---|
| Total tests | 26 |
| Passed | 26 |
| Failed | 0 |
| Skipped | 0 |
| Overall coverage | 83% |
| Duration | ~20 s |

## Coverage Breakdown

| Module | Stmts | Miss | Cover |
|---|---|---|---|
| config.py | 13 | 0 | 100% |
| database.py | 18 | 9 | 50% |
| main.py | 17 | 0 | 100% |
| repositories/book_repo.py | 26 | 10 | 62% |
| repositories/chunk_repo.py | 47 | 11 | 77% |
| repositories/vector_repo.py | 28 | 13 | 54% |
| routers/books.py | 24 | 4 | 83% |
| routers/query.py | 16 | 4 | 75% |
| schemas/books.py | 16 | 0 | 100% |
| schemas/query.py | 27 | 0 | 100% |
| services/generation_service.py | 19 | 0 | 100% |
| services/query_service.py | 20 | 0 | 100% |
| services/retrieval_service.py | 56 | 3 | 95% |

## Test Inventory

### Repository Layer (7 tests)
- **test_book_repo.py** (3): list_books, get_book_found, get_book_not_found
- **test_chunk_repo.py** (4): search_fts_returns_results, search_fts_empty_query, get_source_locators, get_source_locators_empty

### Service Layer (9 tests)
- **test_retrieval_service.py** (6): retrieve_returns_results, retrieve_empty_query, retrieve_with_book_filter, retrieve_source_locators_attached, rrf_fuse_deduplicates, rrf_fuse_empty_lists
- **test_generation_service.py** (3): build_context, generate_success, generate_ollama_error
- **test_query_service.py** (3): query_happy_path, query_sources_have_bbox, query_no_results

### Router / Integration Layer (7 tests)
- **test_books_router.py** (4): list_books, get_book_detail, get_book_not_found, health
- **test_query_router.py** (3): query_endpoint (real Ollama), validation_empty, validation_top_k_too_large

## Coverage Notes

- **vector_repo.py (54%)**: ChromaDB vectors not yet built; `search()` body is tested indirectly via mock in retrieval_service tests. The lazy-singleton init path is uncovered.
- **database.py (50%)**: `get_db` generator and `lifespan` paths exercised implicitly through TestClient but not fully traced by coverage.
- **book_repo.py (62%)**: `get_pdf_path()` and chapter-detail branch not tested (low-risk read-only queries).

## Approach

- Real SQLite database used for repo and router tests (read-only).
- Real Ollama (`llama3.2:3b`) used for the integration query test.
- `vector_repo.search` mocked in retrieval tests (ChromaDB vectors not built yet).
- `generation_service.generate` mocked in query_service unit tests.
- `ollama.Client` mocked in generation_service unit tests.

## Gate Check

```
uv run pytest --tb=short -q → 26 passed ✓
```
