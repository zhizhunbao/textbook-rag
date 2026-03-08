# Phase 05 — Database Design Review

## Review Info

| 属性 | 值 |
|------|------|
| Phase | 05 - database |
| Author | Architect (Bob) |
| Reviewer | Backend Engineer (David) |
| Date | 2026-03-07 |
| Deliverable | `docs/codemaps/database.md` |
| Rebuild Script | `scripts/rebuild_db.py` |

---

## Automated Validation

| Check | Result |
|-------|--------|
| `docs/codemaps/database.md` exists | ✅ PASS (23,553 bytes) |
| `data/textbook_rag.sqlite3` exists | ✅ PASS (141 MB) |
| Foreign key violations | ✅ PASS (0 violations) |
| chunks ↔ chunk_fts sync | ✅ PASS (239,878 = 239,878) |
| chunks ↔ source_locators sync | ✅ PASS (239,878 = 239,878) |
| Orphan chunks (bad book_id) | ✅ PASS (0) |
| Orphan chunks (bad chapter_id) | ✅ PASS (0) |
| Orphan chunks (bad page_id) | ✅ PASS (0) |
| FTS5 MATCH query works | ✅ PASS |

---

## Findings

### LOW: chapters.chapter_key 缺少 UNIQUE 约束

`chapters` 表的 `(book_id, chapter_key)` 组合应逻辑唯一，但当前未加 UNIQUE 约束。数据完整性依赖 `rebuild_db.py` 中的去重逻辑。

**建议**: 添加 `CREATE UNIQUE INDEX idx_chapters_book_key ON chapters(book_id, chapter_key)`。

### LOW: 4,162 chunks 无 chapter_id 归属

约 1.7% 的 chunks 的 `chapter_id` 为 NULL，主要是前言、目录、版权页等前导内容。这是预期行为，不影响检索。

### INFO: ChromaDB 向量未构建

当前使用 `--skip-vectors` 跑的重建，ChromaDB 未填充。向量检索功能在后端实现前不阻塞。

---

## Textbook Basis Summary

| 教材 | 引用 | 验证 |
|------|------|------|
| Kreibich, *Using SQLite* | WAL mode, FTS5, 虚拟表 | ✅ 文档中有正确引用 |
| Kleppmann, *DDIA* | Ch2-3 数据模型/存储引擎 | ✅ 文档中有正确引用 |
| Manning et al., *Intro to IR* | 倒排索引/BM25 | ✅ 文档中有正确引用 |
| Fontaine, *Art of PostgreSQL* | 索引策略 | ✅ 文档中有正确引用 |
| Zalewski, *Tangled Web* | SQL 注入防护 | ✅ 文档中有正确引用 |

**Textbook compliance**: 教材查阅在设计前完成，无违规。

---

## Conclusion

**PASS** — 无 CRITICAL 或 HIGH 级别问题。

数据库 schema 完整、数据已灌入、FTS5 工作正常。两个 LOW 级建议可在后端开发阶段处理。Phase 可标记为 completed。
