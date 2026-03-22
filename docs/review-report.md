# 代码审查报告 — Textbook RAG v2.0

- **审查日期**: 2026-03-22
- **审查范围**: `engine/` + `payload/src/`（排除 `backend/` 遗留代码）
- **审查人**: Grace (Reviewer)
- **Ruff lint**: ✅ 2 个 unused import 已自动修复，`All checks passed`

---

## 评分

| 维度       | 得分    | 说明                           |
|------------|---------|--------------------------------|
| 功能正确性 | 9/10    | 核心流程完整，存在1个边界问题  |
| 代码质量   | 9/10    | 结构清晰，模块职责单一         |
| 安全性     | 8/10    | 无硬编码密钥，1个小问题        |
| 性能       | 8/10    | 有1处 N+1 风险                 |
| **总分**   | **87/100** | **通过**                    |

---

## 问题清单

### 🟠 Major (2)

#### [ENG-001] `RAGCore.list_strategies()` 打开 DB 连接但未使用

- **文件**: `engine/rag/core.py:185-190`
- **问题**: `_get_db()` 被调用并在 `finally` 中关闭，但 `registry.list_all()` 完全不需要数据库连接。多余的 I/O 开销，且容易误导维护者。
- **建议**:
  ```python
  def list_strategies(self) -> list[dict]:
      return self._get_retriever().registry.list_all()
  ```

#### [ENG-002] `IngestPipeline` 异常路径未更新 Task/Book 状态

- **文件**: `engine/api/routes/ingest.py:41-44` + `engine/ingest/pipeline.py:77-79`
- **问题**: `ingest.py` 的 `_run_pipeline()` 对顶层异常调用了 `update_task` / `update_book_status`，但 `pipeline.py` 内部 `except` 仅 `raise` 而不更新状态，导致两层都 raise 时 `ingest.py` 的 `update_task(status="error")` 才是实际触发点——若 `update_task` 本身也抛出，Book 状态将永久卡在 `processing`。
- **建议**: 在 `IngestPipeline.run()` 的 `except` 块里也调用 `update_book_status(book_id, "error")`，避免状态悬挂。

---

### 🟡 Minor (4)

#### [ENG-003] `payload_client.batch_create_chunks` 逐条 HTTP（潜在 N+1）

- **文件**: `engine/adapters/payload_client.py:53-66`
- **问题**: 每个 chunk 单独发一次 HTTP POST，一本书若有 500 个 chunks 即为 500 次请求。
- **建议**: Payload 支持 bulk-create（`/api/chunks?bulk=true`），或改为并发 `httpx.AsyncClient`。当前体量可接受，建议下版本优化。

#### [ENG-004] `health_check` 未实际检测 Chroma / Ollama 连通性

- **文件**: `engine/api/routes/health.py:14-16`
- **问题**: `/engine/health` 仅返回硬编码 `"ok"`，无法反映真实服务状态。
- **建议**: 增加 Chroma ping 和 Ollama `/api/tags` 探测，失败返回 503。

#### [PAY-001] `afterChange` hook 使用 `console.error` 而非 Payload logger

- **文件**: `payload/src/hooks/books/afterChange.ts:56`
- **问题**: Payload 有内置 `req.payload.logger`，`console.error` 在生产环境无结构化输出。
- **建议**: 改为 `req.payload.logger.error(...)`。

#### [ENG-005] `config.py` 中 `ENGINE_PORT` 默认值与 `step-09` 文档不一致

- **文件**: `engine/config.py:68`（默认 `8000`）vs `docs/v2.0` 部署文档（`8001`）
- **问题**: 可能导致本地启动时端口冲突（`backend/` 遗留服务也用 `8000`）。
- **建议**: 将 `ENGINE_PORT` 默认值改为 `8001`，与部署文档对齐。

---

### 🔵 Info (2)

#### [ENG-006] `retrieval.py` 文件头注释有旧 Story 编号

- **文件**: `engine/rag/retrieval.py:3`
- 注释 `"STORY-007 full implementation. This file is a stub for STORY-001."` 已过时，可清理。

#### [ENG-007] `query.py` `QueryRequest.filters` 类型为裸 `dict`

- **文件**: `engine/api/routes/query.py:24`
- 建议改为 `dict[str, Any] | None`，或直接用 `QueryFilters` Pydantic 模型，提升 API 文档可读性。

---

## 必须修复（阻断部署）

- [ ] **[ENG-001]** `list_strategies()` 移除无用 DB 连接
- [ ] **[ENG-002]** `IngestPipeline` 异常路径确保 Book 状态更新

## 建议修复（下版本）

- [ ] [ENG-003] Chunk 批量写入改为并发或 bulk API
- [ ] [ENG-004] `/engine/health` 增加真实健康探测
- [ ] [PAY-001] Hook 使用 Payload 结构化 logger
- [ ] [ENG-005] `ENGINE_PORT` 默认值改为 `8001`

---

## 结论

代码整体质量良好，架构分层清晰（Engine ↔ Payload 解耦）。  
**需修复 2 个 Major 问题后可进入部署阶段。**
