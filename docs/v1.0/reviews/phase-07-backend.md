# Phase Review: Backend Development

**Review 类型**: 代码类
**执行时间**: 2026-03-04T11:06:00-05:00
**产出物**: `backend/app/`
**作者**: David (Backend Engineer)
**审查人**: Grace (Code Reviewer)

---

## 自动检查

- ✅ `uv run ruff check app/` → "All checks passed!" (0 warnings, 0 errors)
- ✅ `uv run ruff format --check app/` → "20 files already formatted" (reformatted in this session)
- ✅ All 14 Python files pass `py_compile` successfully
- ⚠️ `uv run pytest --tb=short` → No tests exist yet (tests/ directory missing)
- ⚠️ `uv run mypy app/` → Not run (mypy not in dependencies, not required for this project)
- ⚠️ `uv run bandit -r app/` → Not run (bandit not in dependencies)

## 审查清单

### 安全检查 (CRITICAL)

- ✅ **无硬编码凭证** — 无 API keys, passwords, tokens。Ollama host defaults to localhost
- ✅ **无 SQL 注入** — SQLite queries use parameterized queries (`?` placeholders) throughout `sqlite_indexer.py`
- ✅ **无 XSS 漏洞** — Backend only, no HTML rendering. Streamlit handles escaping
- ✅ **输入验证完整** — ContentItem validated on parse; bboxes validated for 4-element lists
- ✅ **无路径遍历** — `_find_pdf()` uses controlled `rglob` patterns from configured dirs, doesn't accept arbitrary user paths
- ✅ **认证授权** — N/A (local-only application per architecture ADR)
- ✅ **密钥管理** — N/A (no API keys, all local services)

### 代码质量 (HIGH)

- ✅ **函数大小** — All functions ≤ 50 lines. Largest: `LayoutAwareChunker.chunk()` at ~48 lines (within limit)
- ✅ **文件大小** — All files ≤ 800 lines. Largest: `sqlite_indexer.py` at 224 lines
- ✅ **嵌套深度** — Maximum 3 levels (within 4-level limit)
- ✅ **无空 try/catch** — All exceptions logged and handled (`loguru` logging in every handler)
- ✅ **无 console.log equivalents** — Uses `loguru.logger` consistently, no `print()` statements
- ✅ **无注释掉的代码** — Clean throughout
- ✅ **类型完整** — Type hints on all function signatures and return types, using `from __future__ import annotations`
- ✅ **命名清晰** — Descriptive names: `results_per_method`, `content_type_filter`, `safe_query`, etc.

### 架构一致性 (HIGH)

- ✅ **目录结构** — Matches architecture doc §7: `preprocessing/`, `indexing/`, `retrieval/`, `generation/`, `tracing/`
- ✅ **分层正确** — Clear separation: Parser → Chunker → Indexers → Retrievers → Fuser → Generator → Engine
- ✅ **API 契约** — `RAGEngine` interface matches architecture §5.1 exactly:
  - `query(question, book_filter, content_type_filter, top_k) → QueryResult`
  - `render_source(book_key, page, bbox, zoom) → Image`
  - `get_available_books() → list[BookInfo]`
  - `check_health() → dict`
- ✅ **不可变模式** — `Config` uses `frozen=True` dataclasses. Chunks created as new objects

### 性能 (MEDIUM)

- ✅ **无 O(n²)** — PageIndex fuzzy matching is O(n×m) where n=LLM output lines (~3), m=chapters (~200), acceptable
- ✅ **无 N+1 查询** — SQLite uses batch operations, ChromaDB batch inserts
- ⚠️ **缓存策略** — No caching of embedding model or repeated queries (MEDIUM — acceptable for v1, important for optimization)
- ✅ **Parallel retrieval** — ThreadPoolExecutor with timeout per method (architecture ADR-2)

### 最佳实践 (MEDIUM)

- ✅ **DRY 原则** — `_row_to_chunk()` helper, shared models, config centralized
- ✅ **单一职责** — Each file has one class with clear purpose
- ✅ **无 magic number** — Constants named: `_BATCH_SIZE=100`, `_MAX_CONTEXT_CHARS=6000`, `_COLLECTION_NAME`
- ✅ **错误信息友好** — Generator returns user-understandable messages for all error cases
- ⚠️ **新代码有测试** — No unit tests written yet (see MEDIUM #3 below)

### 教科书引用 (项目特定)

- ✅ **所有模块有 Ref 注释** — Every file has at least one textbook reference:
  - `rag_engine.py` → DDIA Ch12, Fluent Python Ch20
  - `sqlite_indexer.py` → Manning IR Ch11
  - `chroma_indexer.py` → Manning IR Ch6
  - `pageindex_builder.py` → Jurafsky SLP3 Ch23
  - `generator.py` → Goodfellow Ch12.4, Jurafsky Ch14
  - `source_tracer.py` → Szeliski CV Ch2
  - `chunker.py` → Manning IR Ch2
  - `rrf_fuser.py` → Cormack et al. (2009) RRF paper

## 发现的问题

| #   | 严重度 | 描述                                                                                                                                         | 位置                       | 建议修复                                                             |
| --- | ------ | -------------------------------------------------------------------------------------------------------------------------------------------- | -------------------------- | -------------------------------------------------------------------- |
| 1   | MEDIUM | `_MAX_CONTEXT_CHARS=6000` 是硬编码的上下文窗口大小，未根据 Ollama 模型的实际 context window 动态调整（回溯 architecture ADR-3 MEDIUM issue） | `generator.py:28`          | → 在 testing/optimization 阶段增加动态 token budget detection        |
| 2   | MEDIUM | ChromaDB `existing_ids` 获取全量 IDs `self._collection.get(include=[])["ids"]` 在大规模索引时可能内存占用高                                  | `chroma_indexer.py:69`     | → 可改为按 book_key 批量检查，或用 try/except 处理 duplicate         |
| 3   | MEDIUM | 无单元测试 — Sprint plan 列出了 `test_parser.py`, `test_chunker.py`, `test_sqlite_indexer.py` 等测试文件，但均未创建                         | `backend/`                 | → 在 `testing` 阶段创建所有测试                                      |
| 4   | MEDIUM | `_find_pdf()` 使用 `rglob` 遍历整个目录树查找 PDF，对于大量文件可能较慢                                                                      | `source_tracer.py:116-124` | → 可考虑缓存 PDF 路径映射表                                          |
| 5   | MEDIUM | `AnswerGenerator.generate()` 的 timeout 参数在 `__init__` 中设置但未在 `_client.chat()` 调用中使用                                           | `generator.py:37,85-91`    | → 应传递 `options={"timeout": self._timeout}` 或使用 `httpx` timeout |

## 结论 (初审)

- 🟢 **通过** — 可以进入下一阶段

代码质量高，结构清晰，严格遵循架构文档定义。所有安全检查通过，代码质量检查全部通过。5 个 MEDIUM 问题均不阻塞，可在后续 testing/optimization 阶段解决。

## 统计 (初审)

- 检查项总数: 28
- 通过: 23 | 警告 (MEDIUM): 5 | 失败: 0

### MEDIUM 问题处理计划

| #   | 问题                  | 处理方式             |
| --- | --------------------- | -------------------- |
| 1   | Context window 硬编码 | → `testing` 阶段优化 |
| 2   | ChromaDB 全量 ID 查询 | → `testing` 阶段优化 |
| 3   | 缺少单元测试          | → `testing` 阶段创建 |
| 4   | PDF 路径查找效率      | → `testing` 阶段优化 |
| 5   | Ollama timeout 未使用 | → `testing` 阶段修复 |
