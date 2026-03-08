# Testing Codemap

## Scope

Backend-only testing. No frontend tests.

## Existing Tests (14 passing)

| File | Tests | Layer |
|---|---|---|
| test_book_repo.py | list_books, get_book_found, get_book_not_found | Unit (repo) |
| test_chunk_repo.py | search_fts, empty_query, get_source_locators, empty_locators | Unit (repo) |
| test_books_router.py | list, detail, 404, health | Integration (API) |
| test_query_router.py | query_endpoint (skip w/o Ollama), validation ×2 | Integration (API) |

## New Tests Planned

### Service Layer (unit with mocks)

| File | Tests | What's Mocked |
|---|---|---|
| test_retrieval_service.py | retrieve_fts_only, rrf_fusion_logic, empty_results, metadata_enrichment, filters_passed | vector_repo.search (returns []) |
| test_generation_service.py | generate_success, generate_ollama_failure, context_building | ollama.Client |
| test_query_service.py | query_happy_path, sources_built_correctly | retrieval_service + generation_service |

### Additional Integration

| File | Tests | Notes |
|---|---|---|
| test_query_router.py (extend) | filter_params, missing_body | Extend existing |

## Fixtures

- `db`: Real SQLite connection (conftest.py)
- `client`: FastAPI TestClient with DB override (conftest.py)

## Coverage Target

All backend services and repositories covered. Gate: `uv run pytest --tb=short -q`.
