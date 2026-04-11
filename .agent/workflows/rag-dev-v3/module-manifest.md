# Textbook-RAG v2 — 模块功能清单索引

> 每个模块的详细描述（Layout / UI / UX / Func / Noun + Files）存放在 `module-manifest/` 目录下，按需加载。
> 目录结构与命名规则见 [project-structure.md](./project-structure.md)。
> 功能实现状态见 [module-roadmap.md](./module-roadmap.md)。

### Noun 使用规则

Noun 是 **种子名词集**（seed nouns），不是穷举名单。规则如下：

| # | 规则 | 示例 |
|---|------|------|
| 1 | **所有标识符必须由种子名词组合而成** | `Book` + `Card` → `BookCard`, `book_card` |
| 2 | **前端用 PascalCase（组件）/ camelCase（变量）** | `ChatSession`, `chatId` |
| 3 | **后端用 snake_case** | `chunk_text`, `embedding_model` |
| 4 | **跨模块名词就近归属，不重复定义** | `Book` 归 `readers`，`question_gen` 引用即可 |
| 5 | **新概念必须先在 Noun 中增加种子词，再使用** | 新增概念需 PR 级变更 |
| 6 | **通用名词不在此管理** | `id`, `name`, `type`, `list`, `item`, `count`, `data` 等通用词无需登记 |

---

## 独立功能模块 (`features/<feature>/`)

> 以下模块有独立的路由页面，不属于 engine 子模块。

| 模块 | 说明 | 清单文件 |
|------|------|----------|
| `layout` | 应用骨架 | [layout.md](./module-manifest/layout.md) |
| `home` | 首页仪表盘 | [home.md](./module-manifest/home.md) |
| `auth` | 登录认证 | [auth.md](./module-manifest/auth.md) |
| `seed` | 数据播种 | [seed.md](./module-manifest/seed.md) |

---

## Engine 子模块 (`features/engine/<module>/`)

> 以下模块属于 Engine 控制面板，对应 Python `engine_v2/<module>/`。

| 模块 | 说明 | 清单文件 |
|------|------|----------|
| `readers` | 文档阅读 / 解析 | [readers.md](./module-manifest/readers.md) |
| `ingestion` | 数据摄取 | [ingestion.md](./module-manifest/ingestion.md) |
| `chat` | RAG 对话 | [chat.md](./module-manifest/chat.md) |
| `retrievers` | 检索引擎 | [retrievers.md](./module-manifest/retrievers.md) |
| `response_synthesizers` | 回答合成 | [response_synthesizers.md](./module-manifest/response_synthesizers.md) |
| `llms` | 模型管理 | [llms.md](./module-manifest/llms.md) |
| `query_engine` | 查询引擎 | [query_engine.md](./module-manifest/query_engine.md) |
| `evaluation` | 质量评估 | [evaluation.md](./module-manifest/evaluation.md) |
| `question_gen` | 问题引擎 | [question_gen.md](./module-manifest/question_gen.md) |

---

## 纯后端模块 (`engine_v2/<module>/`，无前端 UI)

| 模块 | 说明 | 清单文件 |
|------|------|----------|
| `chunking` | 文本分块 | [chunking.md](./module-manifest/chunking.md) |
| `toc` | 目录提取 | [toc.md](./module-manifest/toc.md) |
| `embeddings` | 向量嵌入 | [embeddings.md](./module-manifest/embeddings.md) |
| `access` | 权限控制 | [access.md](./module-manifest/access.md) |

---

## 跨模块公共模块 (`features/shared/`)

| 模块 | 说明 | 清单文件 |
|------|------|----------|
| `pdf` | PDF 阅读器 (共用) | [pdf.md](./module-manifest/pdf.md) |
| `shared` | 公共基础设施 | [shared.md](./module-manifest/shared.md) |
