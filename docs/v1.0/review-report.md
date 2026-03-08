# 代码审查报告

## 概览

- **审查日期**: 2026-03-07
- **审查人**: Grace (Code Reviewer)
- **审查范围**: `backend/app/`, `backend/tests/`, `frontend/src/`

## 自动化检查结果

| 检查 | 结果 |
|---|---|
| `uv run ruff check backend/app/` | All checks passed ✓ |
| `npx tsc --noEmit` (frontend) | 0 errors ✓ |
| `uv run pytest --tb=short -q` | 26 passed ✓ |
| Test coverage | 83% overall ✓ |
| Hardcoded secrets scan | None found ✓ |
| XSS pattern scan (dangerouslySetInnerHTML, eval) | None found ✓ |

## 评分

| 维度 | 得分 | 说明 |
|---|---|---|
| 功能正确性 | 9/10 | 所有 API 端点满足 PRD 需求，RAG 管线完整 |
| 代码质量 | 9/10 | 清晰分层，命名规范，函数简短 |
| 安全性 | 9/10 | 参数化查询，FTS5 输入净化，无硬编码密钥 |
| 性能 | 8/10 | FTS5 + RRF 融合高效，DB 连接 per-request 可接受 |
| 测试覆盖 | 8/10 | 83% 覆盖，服务层 95-100% |
| **总分** | **86/100** | **通过** |

## OWASP Top 10 安全检查

- [x] **注入攻击** — 所有 SQL 使用参数化查询 (`?` 占位符)。FTS5 输入通过 `_sanitise_fts()` 清除特殊字符。
- [x] **认证缺陷** — 本地单用户应用，无认证需求（符合 PRD）。
- [x] **敏感数据泄露** — 无密钥、无 .env 硬编码。配置通过环境变量。
- [x] **访问控制** — PDF 端点通过 DB 查询获取路径，`book_id` 为整数，无用户可控文件路径。
- [x] **安全配置错误** — CORS 限制为 localhost:5173，非 `*`。
- [x] **XSS** — 前端未使用 `dangerouslySetInnerHTML`、`innerHTML`、`eval()`。
- [x] **组件漏洞** — 使用最新版 FastAPI、React 18、Vite 6。
- [x] **日志监控** — 错误处理返回适当 HTTP 状态码（404/422/502）。

## 代码质量检查

### 命名规范 ✓
- 变量名语义清晰（`fts_results`, `vec_chunks`, `chroma_to_chunk`）
- 函数名描述行为（`retrieve`, `generate`, `_rrf_fuse`, `_sanitise_fts`）
- 模块按职责分离（repositories / services / routers / schemas）

### 代码结构 ✓
- 最长函数：`retrieve()` ~40 行，在限制内
- 最长文件：`retrieval_service.py` 117 行，远低于 500 行限制
- 无超过 3 层的嵌套循环
- 清晰的 Arrange-Act-Assert 测试结构

### 架构合规 ✓
- 三层架构：Router → Service → Repository
- 依赖注入通过 FastAPI `Depends`
- 配置集中在 `config.py`，全部通过环境变量

## 发现问题

### 🔴 Critical (0)

无。

### 🟠 Major (0)

无。

### 🟡 Minor (2)

1. **[BE-001] PDF 端点缺少路径验证**
   - 文件: `backend/app/repositories/book_repo.py:45-59`
   - 描述: `get_pdf_path()` 从数据库获取相对路径后拼接 base 目录，虽然 `book_id` 是整数无法注入，但数据库中的 `path` 值如果被篡改理论上可导致路径遍历。
   - 风险: 极低（数据库是本地只读文件）
   - 建议: 可选添加 `full.resolve().is_relative_to(base)` 检查

2. **[BE-002] vector_repo 全局单例无锁保护**
   - 文件: `backend/app/repositories/vector_repo.py:14-27`
   - 描述: `_get_collection()` 使用 `global` 变量做惰性初始化，在多线程环境下理论上可能重复初始化。
   - 风险: 低（FastAPI 默认线程池，ChromaDB client 可重复创建无副作用）
   - 建议: 可选使用 `threading.Lock`

### 🔵 Info (1)

1. **[BE-003] DB 连接 per-request**
   - 描述: 每个请求创建新的 SQLite 连接。对于本地桌面应用完全可接受。
   - 建议: 如果将来部署到多用户环境，考虑连接池。

## 结论

代码库质量良好，安全性合规，测试覆盖充分。无 Critical 或 Major 问题。**审查通过。**
