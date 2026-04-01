---
description: textbook-rag v2 开发工作流 — LlamaIndex-native 架构、Payload CMS (PostgreSQL)、全栈开发。使用 /rag-dev-v2 启动。
---

# Textbook RAG v2 开发工作流

适用于 textbook-rag v2 的日常开发，覆盖 Engine v2 (LlamaIndex + FastAPI)、Payload v2 (Payload 3 + Next.js + PostgreSQL)。

// turbo-all

---

## 🌍 全局规则（所有操作生效）

### Windows PowerShell 规范

- **Python 命令必须加 `uv run` 前缀**，禁止直接 `python`
- **禁止 `cd` 命令**，使用 `cwd` 参数
- **使用 PowerShell 语法**：`dir`/`Get-ChildItem`（不是 `ls`）、`Remove-Item`（不是 `rm`）
- **命令链接用 `;`**，禁止 `&&` 或 `||`

| 操作        | ✅ 用                     | ❌ 禁止            |
| ----------- | ------------------------- | ------------------ |
| 安装包      | `uv add package`          | `pip install`      |
| 运行 Python | `uv run python script.py` | `python script.py` |
| 列文件      | `dir` / `Get-ChildItem`   | `ls`               |
| 删除        | `Remove-Item`             | `rm`               |
| 切目录      | `cwd` 参数                | `cd`               |
| 链接命令    | `;`                       | `&&`               |

### 四层对齐规则（v2 核心约束）

**所有 LlamaIndex 对齐模块必须在四层中保持命名一致：**

| 层 | 描述 | 命名规则 |
|----|------|----------|
| L1 | `llama_index.core.*` | 原始模块名 |
| L2 | `engine_v2/` 子包 | = L1 模块名 |
| L3 | `features/engine/` 子目录 + 路由路径 | = L2 子包名 |
| L4 | i18n key + AppSidebar `titleKey` | `nav` + PascalCase(L2 子包名) |

**四层对齐表:**

| # | LlamaIndex Module | engine_v2/ | features/engine/ | Route | i18n Key | 显示名 (en/zh) |
|---|-------------------|------------|------------------|-------|----------|----------------|
| 1 | `core.readers` | `readers/` | `readers/` | `/readers` | `navReaders` | Library / 资料库 |
| 2 | `core.ingestion` | `ingestion/` | `ingestion/` | `/engine/ingestion` | `navIngestion` | Ingestion / 数据导入 |
| 3 | `core.retrievers` | `retrievers/` | `retrievers/` | `/engine/retrievers` | `navRetrievers` | Retrievers / 检索器 |
| 4 | `core.response_synthesizers` | `response_synthesizers/` | `response_synthesizers/` | `/engine/response_synthesizers` | `navResponseSynthesizers` | Prompts / Prompt 管理 |
| 5 | `core.query_engine` | `query_engine/` | `query_engine/` | `/engine/query_engine` | `navQueryEngine` | Query Engine / 查询引擎 |
| 6 | `core.llms` | `llms/` | `llms/` | `/engine/llms` | `navLlms` | LLMs / LLMs |
| 7 | `core.evaluation` | `evaluation/` | `evaluation/` | `/engine/evaluation` | `navEvaluation` | Evaluation / 质量评估 |
| 8 | `core.question_gen` | `question_gen/` | `question_gen/` | `/engine/question_gen` | `navQuestionGen` | Questions / 问题库 |

> **新增模块时**: 必须同时创建 L2 子包 + L3 feature 子目录 + L3 路由页面 + L4 i18n key + L4 AppSidebar entry。缺一不可。

### 代码质量底线

- 函数 ≤ 50 行，文件 ≤ 800 行，嵌套 ≤ 4 层
- 不可变模式优先（创建新对象，不修改原对象）
- 无 magic number，无 console.log，无硬编码密钥
- Engine v2: docstring 对齐 LlamaIndex 模块（`"""Aligns with llama_index.core.xxx."""`）
- Payload v2: 使用语义 Tailwind token（`bg-card` 不是 `bg-gray-800`）

### 代码溯源（Textbook + Source Code）

**所有生成的代码必须有来源依据。** 来源分两类：

**A. 教科书溯源** — 算法、设计模式、架构决策
1. 加载映射: `.agent/config/textbook-skill-mapping.yaml`
2. 查阅来源: `textbooks/topic_index.json` → `data/mineru_output/{book_key}/...`
3. 引用标注: `# Ref: Author, Book, ChN — concept`

**B. 源码溯源** — LlamaIndex API 用法、Payload CMS 模式、框架惯例
1. 查阅参考仓库: `.github/references/`
   - `llama_index/` — LlamaIndex 官方源码 (核心 API、基类接口)
   - `payload/` — Payload CMS 官方源码 (Collection 模式、hooks)
   - `react/`, `vite/`, `tailwindcss/` 等 — 前端框架参考
2. 引用标注: `# Ref: llama_index.core.retrievers.fusion_retriever — QueryFusionRetriever`
3. 对 engine_v2 模块，优先查阅 LlamaIndex 源码确认 API 签名再编码

**无来源不生成** — 如果教科书和参考源码中均找不到依据，明确告知用户。

---

## 📂 工作流子文件索引

本工作流由多个子文件组成，按需查阅：

| 文件 | 内容 | 何时查阅 |
|------|------|---------|
| [01-project-structure.md](./rag-dev-v2/01-project-structure.md) | v2 项目结构速查 | 了解代码在哪、模块划分 |
| [02-architecture.md](./rag-dev-v2/02-architecture.md) | LlamaIndex 四层对齐架构 | 理解模块命名规范、数据流、i18n 对齐 |
| [03-core-rules.md](./rag-dev-v2/03-core-rules.md) | 核心开发规则 | 开发任何功能前必读 |
| [04-dev-procedures.md](./rag-dev-v2/04-dev-procedures.md) | 开发流程模板 | 新增 Engine/Payload 功能 |
| [05-run-and-debug.md](./rag-dev-v2/05-run-and-debug.md) | 启动运行与调试 | 启动服务、重建数据、调试问题 |
| [06-llamaindex-reference.md](./rag-dev-v2/06-llamaindex-reference.md) | LlamaIndex 参考速查 | 查找 llama_index.core.* API |
| [07-roadmap.md](./rag-dev-v2/07-roadmap.md) | v2 演进路线 | 规划下一步功能 |
| [08-self-update.md](./rag-dev-v2/08-self-update.md) | 工作流自更新规则 | 项目变更后同步工作流 |

---

## 🔑 快速开始

1. **首次开发**: 先阅读 `01-project-structure.md`、`02-architecture.md`、`03-core-rules.md`
2. **新增功能**: 参考 `04-dev-procedures.md` 的模板
3. **启动调试**: 查看 `05-run-and-debug.md`
4. **查 API**: 参考 `06-llamaindex-reference.md`
5. **规划方向**: 参考 `07-roadmap.md`

---

## 🚀 端口速查

| 服务 | 端口 | 命令 |
|------|------|------|
| Engine v2 | **8001** | `uv run python -m uvicorn engine_v2.api.app:app --reload --host 127.0.0.1 --port 8001` |
| Payload v2 | **3001** | `npm run dev -- --port 3001` (cwd: `payload-v2`) |
| PostgreSQL | 5432 | `postgresql://payload:payload@127.0.0.1:5432/payload` |
| Ollama | 11434 | `http://127.0.0.1:11434` |

## 📦 Git 提交规范

```
feat: add pipeline dashboard with book selector
fix: move Ready badge to bottom-right of BookCard
refactor: extract PipelineDashboard to features/pipeline
chore: update rag-dev-v2 workflow (auto-sync)
```

### 提交前检查清单

1. `npx tsc --noEmit` (在 payload-v2/ 目录)
2. `uv run ruff check engine_v2/`
3. 确认 i18n messages 完整 (四层对齐)
4. page.tsx 只是薄壳
5. 新组件已加入 barrel export (features/engine/index.ts)
