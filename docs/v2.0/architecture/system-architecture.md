# Textbook RAG v2.0 — 系统架构文档

> **版本**: 2.0
> **作者**: Bob (Architect)
> **日期**: 2026-03-21
> **输入**: v2.0 requirements.md, v2.0 prd.md, v1.1 system-architecture.md, v1.1 代码库
> **迁移目标**: RAG-Project (github.com/Teegee0/RAG-Project)

---

## 1. 架构概述

### 1.1 设计原则

| 原则 | v1.1 | v2.0 |
|------|------|------|
| **增量扩展** | v1.0 只做扩展 | v1.1 RAG Core 零修改，仅包裹 Payload |
| **模块可插拔** | 检索策略注册机制 | 保留 + Payload Collection 也可插拔 |
| **双入口共享** | Web + ROS2 共享 RAGCore | 保留，ROS2 import engine.rag |
| **透明可控** | Trace 全链路 | 保留 + Payload QueryLogs 永久记录 |
| **向后兼容** | v1.0 客户端不受影响 | v1.1 测试全部通过 |
| **关注点分离** | (新) | Payload 管内容, Engine 管计算 |
| **自动化优先** | (新) | API 自动生成, 入库自动触发 |

### 1.2 架构总图

```
┌──────────────────────────────────────────────────────────────────┐
│                     Presentation Layer                            │
│                                                                   │
│   ┌──────────────────────────────────┐                           │
│   │     Next.js 15 App Router        │                           │
│   │                                  │                           │
│   │  ┌──────┐ ┌──────────┐          │  ┌─────────────────────┐  │
│   │  │ PDF  │ │  Chat    │          │  │ Payload Admin Panel │  │
│   │  │Viewer│ │  Panel   │          │  │ (auto-generated)    │  │
│   │  └──────┘ └──────────┘          │  │                     │  │
│   │  ┌──────────────────┐           │  │ Books / Chapters    │  │
│   │  │ Trace + Config   │           │  │ Chunks / Users      │  │
│   │  │ Panels           │           │  │ PipelineTasks       │  │
│   │  └──────────────────┘           │  │ QueryLogs           │  │
│   │  ┌──────────────────┐           │  └─────────────────────┘  │
│   │  │ Reports (EcDev)  │           │                           │
│   │  └──────────────────┘           │                           │
│   └───────────┬──────────────────────┘                           │
│               │                                                   │
├───────────────┼───────────────────────────────────────────────────┤
│               ▼                                                   │
│   ┌────────────────────────────────────────────────────────────┐  │
│   │                   Payload CMS Layer                         │  │
│   │                   Payload 3.x + PostgreSQL                  │  │
│   │                                                             │  │
│   │  ┌──────────────────────────────────────────────────────┐  │  │
│   │  │  Collections                                         │  │  │
│   │  │  Books | Chapters | Chunks | Users                   │  │  │
│   │  │  PipelineTasks | QueryLogs                           │  │  │
│   │  └──────────────────────────────────────────────────────┘  │  │
│   │                                                             │  │
│   │  ┌──────────────────┐  ┌────────────────┐  ┌───────────┐  │  │
│   │  │ Auth             │  │ Hooks          │  │ Access    │  │  │
│   │  │ JWT / Session    │  │ afterChange    │  │ Roles     │  │  │
│   │  │                  │  │ → call Engine  │  │ ACL       │  │  │
│   │  └──────────────────┘  └───────┬────────┘  └───────────┘  │  │
│   │                                │                            │  │
│   │  ┌─────────────────────────────┴───────────────────────┐   │  │
│   │  │ REST API (auto) + GraphQL API (auto) + Custom EP    │   │  │
│   │  └─────────────────────────────────────────────────────┘   │  │
│   └──────────────────────────┬─────────────────────────────────┘  │
│                              │ HTTP (internal)                    │
├──────────────────────────────┼────────────────────────────────────┤
│                              ▼                                    │
│   ┌────────────────────────────────────────────────────────────┐  │
│   │                   Python Engine Layer                       │  │
│   │                                                             │  │
│   │  ┌──────────────────────────────────────────────────────┐  │  │
│   │  │ Thin FastAPI  (engine/api/)                           │  │  │
│   │  │  POST /engine/query   → RAGCore.query()               │  │  │
│   │  │  POST /engine/ingest  → Ingest Pipeline               │  │  │
│   │  │  GET  /engine/health                                   │  │  │
│   │  └──────────┬──────────────────────┬─────────────────────┘  │  │
│   │             │                      │                        │  │
│   │  ┌──────────▼──────────┐  ┌───────▼──────────────────┐    │  │
│   │  │ rag/ (= v1.1 Core) │  │ ingest/ + index/         │    │  │
│   │  │                     │  │ (= v1.1 scripts/ 模块化)  │    │  │
│   │  │ ┌───────────────┐  │  │                           │    │  │
│   │  │ │ RAGCore       │  │  │ ┌───────────────────────┐ │    │  │
│   │  │ │ .query()      │  │  │ │ pdf_parser            │ │    │  │
│   │  │ └───────────────┘  │  │ │ chunk_builder         │ │    │  │
│   │  │                     │  │ │ toc_extractor         │ │    │  │
│   │  │ ┌───────────────┐  │  │ │ metadata_enricher     │ │    │  │
│   │  │ │ Retrieval     │  │  │ └───────────────────────┘ │    │  │
│   │  │ │ Orchestrator  │  │  │                           │    │  │
│   │  │ │               │  │  │ ┌───────────────────────┐ │    │  │
│   │  │ │ ┌───────────┐ │  │  │ │ vector_builder        │ │    │  │
│   │  │ │ │ Strategy  │ │  │  │ │ fts5_builder          │ │    │  │
│   │  │ │ │ Registry  │ │  │  │ │ topic_indexer         │ │    │  │
│   │  │ │ └───────────┘ │  │  │ └───────────────────────┘ │    │  │
│   │  │ │               │  │  └───────────────────────────┘    │  │
│   │  │ │ 5 Strategies: │  │                                   │  │
│   │  │ │ FTS5, Vector  │  │  ┌───────────────────────────┐    │  │
│   │  │ │ TOC, PageIdx  │  │  │ adapters/                 │    │  │
│   │  │ │ Metadata      │  │  │ payload_client            │    │  │
│   │  │ │               │  │  │ chroma_adapter            │    │  │
│   │  │ │ RRFusion      │  │  └───────────────────────────┘    │  │
│   │  │ └───────────────┘  │                                   │  │
│   │  │                     │                                   │  │
│   │  │ ┌───────────────┐  │                                   │  │
│   │  │ │ Generation    │  │                                   │  │
│   │  │ │ Citation      │  │  ┌──────────────────────────┐     │  │
│   │  │ │ Trace         │  │  │ ROS2 Node (unchanged)    │     │  │
│   │  │ │ Quality       │  │  │ import engine.rag        │     │  │
│   │  │ └───────────────┘  │  └──────────────────────────┘     │  │
│   │  └─────────────────────┘                                   │  │
│   └────────────────────────────────────────────────────────────┘  │
│                              │                                    │
├──────────────────────────────┼────────────────────────────────────┤
│                              ▼                                    │
│   ┌────────────────────────────────────────────────────────────┐  │
│   │                    Data Layer                               │  │
│   │  ┌──────────────┐  ┌──────────────┐  ┌────────────────┐   │  │
│   │  │ PostgreSQL   │  │  ChromaDB    │  │ S3 / Local FS  │   │  │
│   │  │ (Payload DB) │  │  (vectors)   │  │ (PDF files +   │   │  │
│   │  │ books        │  │  embeddings  │  │  MinerU output)│   │  │
│   │  │ chapters     │  │              │  │                │   │  │
│   │  │ chunks       │  │              │  │                │   │  │
│   │  │ users        │  │              │  │                │   │  │
│   │  │ pipeline_    │  │              │  │                │   │  │
│   │  │   tasks      │  │              │  │                │   │  │
│   │  │ query_logs   │  │              │  │                │   │  │
│   │  └──────────────┘  └──────────────┘  └────────────────┘   │  │
│   └────────────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────────────┘
```

---

## 2. 技术选型

### 2.1 Payload CMS 层（新增）

| 组件 | 选型 | 理由 |
|------|------|------|
| CMS | Payload 3.x | TypeScript, 自带 Admin UI, REST+GraphQL 自动生成 |
| 数据库 | PostgreSQL 15+ | Payload 默认, 生产级 |
| 认证 | Payload Auth | 内置 JWT + Session |
| 前端 | Next.js 15 | Payload 3.x 原生内嵌 |

### 2.2 Python Engine 层（v1.1 保留 + 重组织）

| 组件 | 选型 | 理由 |
|------|------|------|
| 语言 | Python 3.10+ | v1.1 已有 |
| Web 框架 | FastAPI (thin) | 仅供 Payload 内部调用 |
| LLM | Ollama (local) | v1.1 已有 |
| 向量 DB | ChromaDB | v1.1 已有 |
| 全文搜索 | SQLite FTS5 | v1.1 已有, Engine 内部使用 |
| 嵌入模型 | all-MiniLM-L6-v2 | v1.1 已有 |
| 包管理 | uv | v1.1 已有 |

### 2.3 前端（v1.1 → 迁移到 Next.js）

| 组件 | v1.1 | v2.0 | 理由 |
|------|------|------|------|
| 框架 | React 18 + Vite | Next.js 15 (Payload 内嵌) | 统一栈 |
| 样式 | Tailwind CSS | Tailwind CSS | 不变 |
| PDF 渲染 | react-pdf | react-pdf | 不变 |
| 图表 | Recharts | Recharts | 不变 |
| 类型 | TypeScript | TypeScript | 不变 |

### 2.4 ROS2（v1.1 不变）

| 组件 | 选型 | 变更 |
|------|------|------|
| ROS2 | Humble/Iron | 不变 |
| STT | Whisper | 不变 |
| TTS | gTTS | 不变 |
| Model | qwen2.5:0.5b | 不变 |
| Import | `from engine.rag import RAGCore` | import 路径改 |

### 2.5 基础设施（新增）

| 组件 | 选型 | 理由 |
|------|------|------|
| 容器化 | Docker Compose | 全栈编排 |
| 反向代理 | (可选) Nginx | 生产环境 |
| 日志 | Payload built-in + loguru | 分层日志 |

---

## 3. 系统组件设计

### 3.1 Payload Collections — 映射 v1.1 Schema

#### 3.1.1 Books

```typescript
// payload/src/collections/Books.ts
const Books: CollectionConfig = {
  slug: 'books',
  admin: { useAsTitle: 'title' },
  access: {
    read: () => true,                    // 所有人可读
    create: isEditorOrAdmin,             // editor/admin 可创建
    update: isEditorOrAdmin,
    delete: isAdmin,                     // 仅 admin 可删
  },
  fields: [
    // --- v1.1 原有字段 ---
    { name: 'title',      type: 'text',     required: true },
    { name: 'authors',    type: 'text' },
    { name: 'isbn',       type: 'text' },
    { name: 'category',   type: 'select',
      options: [
        { label: 'Textbook',    value: 'textbook' },
        { label: 'EcDev',       value: 'ecdev' },
        { label: 'Real Estate', value: 'real_estate' },
      ],
      defaultValue: 'textbook',
    },
    // --- v2.0 新增 ---
    { name: 'file',       type: 'upload',   relationTo: 'media' },
    { name: 'status',     type: 'select',
      options: ['pending', 'processing', 'indexed', 'error'],
      defaultValue: 'pending',
      admin: { readOnly: true },
    },
    { name: 'chunkCount', type: 'number',   admin: { readOnly: true } },
    { name: 'metadata',   type: 'json' },
  ],
  hooks: {
    afterChange: [triggerIngestionPipeline],
  },
}
```

#### 3.1.2 Chunks

```typescript
// payload/src/collections/Chunks.ts
const Chunks: CollectionConfig = {
  slug: 'chunks',
  access: {
    read: () => true,
    create: isEditorOrAdmin,
    update: isEditorOrAdmin,
    delete: isEditorOrAdmin,
  },
  fields: [
    { name: 'chunkId',        type: 'text',     required: true, unique: true },
    { name: 'book',           type: 'relationship', relationTo: 'books' },
    { name: 'chapter',        type: 'relationship', relationTo: 'chapters' },
    { name: 'text',           type: 'textarea', required: true },
    { name: 'contentType',    type: 'select',
      options: ['text', 'table', 'equation', 'code', 'image'],
    },
    { name: 'readingOrder',   type: 'number' },
    { name: 'pageNumber',     type: 'number' },
    { name: 'sourceLocators', type: 'json' },   // v1.1 bbox [{x0,y0,x1,y1,page,w,h}]
    { name: 'vectorized',     type: 'checkbox', defaultValue: false },
  ],
}
```

#### 3.1.3 Users

```typescript
const Users: CollectionConfig = {
  slug: 'users',
  auth: true,   // Payload 内置 JWT/Session
  access: {
    read: isAdminOrSelf,
    update: isAdminOrSelf,
    delete: isAdmin,
  },
  fields: [
    { name: 'role', type: 'select',
      options: [
        { label: 'Admin',      value: 'admin' },
        { label: 'Editor',     value: 'editor' },
        { label: 'Reader',     value: 'reader' },
      ],
      defaultValue: 'reader',
      access: { update: isAdmin },   // 只有 admin 能改角色
    },
    { name: 'displayName', type: 'text' },
  ],
}
```

#### 3.1.4 PipelineTasks

```typescript
const PipelineTasks: CollectionConfig = {
  slug: 'pipeline-tasks',
  access: {
    read: isEditorOrAdmin,
    create: isEditorOrAdmin,
  },
  fields: [
    { name: 'taskType',   type: 'select',
      options: ['ingest', 'vectorize', 'reindex', 'full'] },
    { name: 'book',       type: 'relationship', relationTo: 'books' },
    { name: 'status',     type: 'select',
      options: ['queued', 'running', 'done', 'error'],
      defaultValue: 'queued' },
    { name: 'progress',   type: 'number', min: 0, max: 100, defaultValue: 0 },
    { name: 'log',        type: 'textarea' },
    { name: 'error',      type: 'textarea' },
    { name: 'startedAt',  type: 'date' },
    { name: 'finishedAt', type: 'date' },
  ],
}
```

#### 3.1.5 QueryLogs

```typescript
const QueryLogs: CollectionConfig = {
  slug: 'query-logs',
  access: {
    read: isAdminOrOwner,
  },
  fields: [
    { name: 'user',       type: 'relationship', relationTo: 'users' },
    { name: 'question',   type: 'text',     required: true },
    { name: 'answer',     type: 'textarea' },
    { name: 'sources',    type: 'json' },
    { name: 'trace',      type: 'json' },   // v1.1 QueryTrace 完整快照
    { name: 'warnings',   type: 'json' },   // v1.1 QualityWarning[]
    { name: 'model',      type: 'text' },
    { name: 'latencyMs',  type: 'number' },
    { name: 'config',     type: 'json' },   // QueryConfig 快照
  ],
}
```

### 3.2 RAG Core — v1.1 原封不动

> v1.1 的 `§3.1 RAG Core` 设计**完全保留**，新增 Azure 策略和 Azure 生成引擎。以下列出位置变更和新增：

```
v1.1 位置                              v2.0 位置
─────────                              ─────────
backend/app/core/rag_core.py      →    engine/rag/core.py
backend/app/core/retrieval.py     →    engine/rag/retrieval.py
backend/app/core/generation.py    →    engine/rag/generation.py
backend/app/core/citation.py      →    engine/rag/citation.py
backend/app/core/trace.py         →    engine/rag/trace.py
backend/app/core/quality.py       →    engine/rag/quality.py
backend/app/core/fusion.py        →    engine/rag/fusion.py
backend/app/core/config.py        →    engine/rag/config.py
backend/app/core/types.py         →    engine/rag/types.py
backend/app/core/strategies/*     →    engine/rag/strategies/*
(新增)                              →    engine/rag/strategies/azure_search.py
(新增)                              →    engine/rag/providers/azure_openai.py
(新增)                              →    engine/rag/providers/ollama.py
```

**改动**: 原有 5 策略仅 import 路径从 `backend.app.core` → `engine.rag`。逻辑零修改。

#### 3.2.1 RAGCore 类（不变）

```python
# engine/rag/core.py (原 backend/app/core/rag_core.py)
class RAGCore:
    """Unified RAG pipeline — shared by Payload Engine, Web, and ROS2."""
    
    def query(self, question: str, config: QueryConfig | None = None) -> RAGResponse:
        # 1. Retrieve (5+1 strategies + RRF)
        # 2. Generate (Ollama or Azure OpenAI)
        # 3. Citation (validate + sanitize)
        # 4. Quality (warnings)
        # 5. Trace (full audit trail)
        ...
```

#### 3.2.2 Strategy Pattern（扩展第 6 策略）

5 个原有策略原封不动移入 `engine/rag/strategies/`。

**新增 AzureSearchStrategy**:

```python
# engine/rag/strategies/azure_search.py
class AzureSearchStrategy(RetrievalStrategy):
    """Azure AI Search semantic retrieval."""
    name = "azure_search"
    display_name = "Azure AI Search"
    default_enabled = False  # 需配置 Azure 环境变量才可启用

    def __init__(self, settings: EngineSettings):
        self.endpoint = settings.AZURE_SEARCH_ENDPOINT
        self.key = settings.AZURE_SEARCH_KEY
        self.index = settings.AZURE_SEARCH_INDEX
        self._available = bool(self.endpoint and self.key and self.index)

    @property
    def is_available(self) -> bool:
        return self._available

    def search(self, query: str, config: QueryConfig) -> list[ChunkHit]:
        """Semantic search via Azure AI Search REST API."""
        # queryType: semantic
        # semanticConfiguration: default
        # captions: extractive
        # 返回统一 ChunkHit 格式
        ...
```

参考实现: RAG-Project `backend/app/services/azure_search_store.py`

#### 3.2.3 双模式 GenerationEngine

v1.1 的 GenerationEngine 扩展为 Provider 模式:

```python
# engine/rag/generation.py (扩展)
class GenerationEngine:
    def __init__(self, config: RAGConfig):
        self.providers = {
            "ollama": OllamaProvider(config),      # v1.1 原有
            "azure_openai": AzureOpenAIProvider(config),  # 新增
        }
        self.default_provider = self._detect_default()

    def generate(self, question, chunks, config) -> str:
        provider_name = config.provider or self.default_provider
        provider = self.providers.get(provider_name)
        try:
            return provider.generate(question, chunks, config)
        except Exception:
            # Azure 失败时回退到 Ollama
            if provider_name == "azure_openai":
                return self.providers["ollama"].generate(question, chunks, config)
            raise

# engine/rag/providers/azure_openai.py
class AzureOpenAIProvider:
    """Azure OpenAI GPT-4o provider."""
    def __init__(self, config):
        self.endpoint = settings.AZURE_OAI_ENDPOINT
        self.key = settings.AZURE_OAI_KEY
        self.deployment = settings.AZURE_OAI_DEPLOYMENT  # default: gpt-4o

    def generate(self, question, chunks, config) -> str:
        # 共享 v1.1 prompt template 系统
        prompt = self._build_prompt(question, chunks, config)
        # Azure OpenAI REST API 调用
        ...

# engine/rag/providers/ollama.py
class OllamaProvider:
    """v1.1 原有 Ollama provider，提取自 GenerationEngine."""
    ...
```

参考实现: RAG-Project `backend/app/services/ai_providers/azure_rag_service.py`

#### 3.2.4 RetrievalOrchestrator（不变）

策略注册、RRF 融合、元数据 enrich 逻辑不变。AzureSearchStrategy 自动通过 `register()` 接入。

### 3.3 v1.1 → v2.0 迁移路径

```
v1.1 结构                          v2.0 结构
─────────                          ─────────

backend/app/core/          ====>   engine/rag/                 ← 平移 (仅改 import)
  rag_core.py                        core.py
  retrieval.py                       retrieval.py
  strategies/*                       strategies/*
  ...                                ...

backend/app/services/      ====>   (删除)                      ← Payload hooks 直调 Engine
  query_service.py                   
  generation_service.py              
  retrieval_service.py               

backend/app/routers/       ====>   (删除)                      ← Payload auto-gen API 替代
  query.py
  books.py
  demo.py

backend/app/schemas/       ====>   (删除)                      ← Payload Collections 替代
  query.py
  books.py

backend/app/repositories/  ====>   (删除)                      ← Payload ORM 替代
  book_repo.py
  chunk_repo.py
  vector_repo.py

backend/app/config.py      ====>   engine/config.py            ← 合并
backend/app/database.py    ====>   (删除)                      ← Payload 管 PostgreSQL
backend/app/main.py        ====>   (删除)                      ← Payload + Next.js 启动

scripts/rebuild_db.py      ====>   engine/ingest/              ← 拆分模块化
  (28KB single file)                 chunk_builder.py
                                     metadata_enricher.py

scripts/batch_mineru.py    ====>   engine/ingest/pdf_parser.py
scripts/rebuild_toc.py     ====>   engine/ingest/toc_extractor.py
scripts/build_vectors.py   ====>   engine/index/vector_builder.py
scripts/rebuild_topic_*.py ====>   engine/index/topic_indexer.py

frontend/                  ====>   payload/src/app/            ← Next.js 重写
  src/features/chat/                 (app)/page.tsx
  src/features/pdf-viewer/           components/PdfViewer.tsx
  src/features/trace/                components/TracePanel.tsx
  ...                                ...

ros2/                      ====>   ros2/                       ← 不变
  ollama_publisher.py                ollama_publisher.py
                                     (import 改 engine.rag)
```

---

## 4. 目录结构

```
textbook-rag/
├── payload/                              # Payload CMS + Next.js
│   ├── src/
│   │   ├── app/                          # Next.js App Router (前端)
│   │   │   ├── (app)/
│   │   │   │   ├── page.tsx              # 主页: PDF+Chat 双栏 (v1.1 App.tsx)
│   │   │   │   ├── trace/page.tsx        # Trace 面板页 (v1.1 TracePanel)
│   │   │   │   └── reports/page.tsx      # EcDev 报告页 (v1.1 ReportsPanel)
│   │   │   └── layout.tsx
│   │   ├── collections/                  # Payload Collections
│   │   │   ├── Books.ts
│   │   │   ├── Chapters.ts
│   │   │   ├── Chunks.ts
│   │   │   ├── Users.ts
│   │   │   ├── PipelineTasks.ts
│   │   │   └── QueryLogs.ts
│   │   ├── hooks/
│   │   │   └── triggerIngestion.ts        # Books afterChange → POST /engine/ingest
│   │   ├── access/
│   │   │   └── roles.ts                  # admin/editor/reader ACL
│   │   ├── components/                   # React 组件 (v1.1 迁移)
│   │   │   ├── PdfViewer.tsx
│   │   │   ├── ChatPanel.tsx
│   │   │   ├── BookSelector.tsx
│   │   │   ├── TracePanel.tsx
│   │   │   ├── RetrievalConfig.tsx
│   │   │   ├── GenerationConfig.tsx
│   │   │   └── ResizeHandle.tsx
│   │   └── payload.config.ts
│   ├── package.json
│   └── tsconfig.json
│
├── engine/                               # Python Engine (独立包)
│   ├── engine/
│   │   ├── __init__.py
│   │   ├── config.py                     # 统一配置
│   │   │
│   │   ├── rag/                          # === v1.1 Core + Azure 扩展 ===
│   │   │   ├── __init__.py
│   │   │   ├── core.py                   # RAGCore class
│   │   │   ├── retrieval.py              # RetrievalOrchestrator
│   │   │   ├── generation.py             # GenerationEngine (dual-mode)
│   │   │   ├── citation.py               # CitationEngine
│   │   │   ├── quality.py                # QualityChecker
│   │   │   ├── fusion.py                 # RRFusion
│   │   │   ├── trace.py                  # TraceCollector
│   │   │   ├── config.py                 # RAGConfig, QueryConfig
│   │   │   ├── types.py                  # ChunkHit, RAGResponse
│   │   │   ├── strategies/               # 5+1 策略
│   │   │   │   ├── base.py
│   │   │   │   ├── registry.py
│   │   │   │   ├── fts5_strategy.py
│   │   │   │   ├── vector_strategy.py
│   │   │   │   ├── toc_strategy.py
│   │   │   │   ├── pageindex_strategy.py
│   │   │   │   ├── metadata_strategy.py
│   │   │   │   └── azure_search.py        # NEW: Azure AI Search
│   │   │   └── providers/                 # NEW: LLM providers
│   │   │       ├── __init__.py
│   │   │       ├── ollama.py              # v1.1 原有
│   │   │       └── azure_openai.py        # NEW: GPT-4o
│   │   │
│   │   ├── ingest/                       # === v1.1 scripts/ 拆分 ===
│   │   │   ├── __init__.py
│   │   │   ├── pdf_parser.py             # < batch_mineru.py
│   │   │   ├── chunk_builder.py          # < rebuild_db.py (28KB)
│   │   │   ├── toc_extractor.py          # < rebuild_toc.py
│   │   │   └── metadata_enricher.py      # < rebuild_db.py (category/bbox)
│   │   │
│   │   ├── index/                        # === v1.1 scripts/ 拆分 ===
│   │   │   ├── __init__.py
│   │   │   ├── vector_builder.py         # < build_vectors.py
│   │   │   ├── fts5_builder.py           # < rebuild_db.py (FTS5 部分)
│   │   │   └── topic_indexer.py          # < rebuild_topic_index.py (24KB)
│   │   │
│   │   ├── api/                          # Thin FastAPI (内部)
│   │   │   ├── __init__.py
│   │   │   ├── app.py
│   │   │   └── routes/
│   │   │       ├── query.py              # POST /engine/query
│   │   │       ├── ingest.py             # POST /engine/ingest
│   │   │       └── health.py             # GET /engine/health
│   │   │
│   │   └── adapters/                     # 外部适配器
│   │       ├── __init__.py
│   │       ├── payload_client.py         # 调 Payload REST API
│   │       ├── chroma_adapter.py         # ChromaDB 连接
│   │       └── azure_blob.py             # NEW: Azure Blob Storage
│   │
│   ├── pyproject.toml                    # 独立 Python 包
│   └── tests/
│       ├── test_rag/                     # v1.1 测试平移
│       ├── test_ingest/
│       └── test_index/
│
├── ros2/                                 # v1.1 ROS2 (不变)
│   ├── ollama_publisher.py
│   └── knowledge/
│
├── data/                                 # 共享数据
│   ├── raw_pdfs/
│   │   ├── textbooks/
│   │   ├── ecdev/
│   │   └── real_estate/
│   ├── mineru_output/
│   └── chroma_persist/
│
├── docker-compose.yml
├── .env
└── docs/
    ├── v1.0/
    ├── v1.1/
    └── v2.0/
```

---

## 5. API 设计

### 5.1 Payload 自动 API（替代 v1.1 手写 FastAPI routers）

Payload 自动为每个 Collection 生成：

```yaml
# Books
GET    /api/books                 # 列表 (分页, filter, sort)
GET    /api/books/:id             # 详情
POST   /api/books                 # 创建
PATCH  /api/books/:id             # 更新
DELETE /api/books/:id             # 删除

# 同理: /api/chapters, /api/chunks, /api/users,
#        /api/pipeline-tasks, /api/query-logs

# Auth
POST   /api/users/login           # 登录 → JWT
POST   /api/users/logout          # 登出
GET    /api/users/me              # 当前用户

# GraphQL
POST   /api/graphql               # 所有 Collection 均可 GraphQL 查询
```

### 5.2 Engine Internal API（仅 Payload → Engine 调用）

```yaml
# 查询 (替代 v1.1 POST /api/v1/query)
POST /engine/query
  Request:
    question: str
    filters: { book_ids, chapter_ids, content_types, categories }
    top_k: int = 5
    fetch_k: int | null
    model: str | null
    provider: str | null                     # NEW: "ollama" | "azure_openai"
    enabled_strategies: list[str] | null     # v1.1 5+1 策略
    rrf_k: int = 60
    prompt_template: str = "default"       # v1.1 4 模板
    custom_system_prompt: str | null
  Response:
    answer: str
    sources: list[SourceInfo]              # v1.1 格式
    trace: QueryTrace                      # v1.1 完整 trace
    warnings: list[QualityWarning]         # v1.1 quality warnings
    stats: RetrievalStats

# 入库 (Payload hook 调用)
POST /engine/ingest
  Request:
    book_id: int
    file_url: str
    category: str
    task_id: int                           # PipelineTask ID
  Response:
    status: "started"

# 其他
GET /engine/health
GET /engine/strategies                     # v1.1 5 策略 + Azure Search
GET /engine/models                         # Ollama 模型列表
GET /engine/providers                      # NEW: ['ollama', 'azure_openai']
GET /engine/prompt-templates               # v1.1 模板列表
```

### 5.3 v1.1 API 兼容

| v1.1 API | v2.0 替代 | 说明 |
|----------|----------|------|
| POST /api/v1/query | Payload custom EP → /engine/query | 转发 |
| GET /api/v1/books | GET /api/books (Payload auto) | 直接替代 |
| GET /api/v1/strategies | GET /engine/strategies | Engine 直接 |
| GET /api/v1/models | GET /engine/models | Engine 直接 |
| GET /api/v1/prompt-templates | GET /engine/prompt-templates | Engine 直接 |

---

## 6. 数据架构

### 6.1 PostgreSQL（Payload 管理）

Payload 自动创建和管理表结构，无需手写 SQL。表名由 Collection slug 决定。

v1.1 SQLite schema 映射：

| v1.1 SQLite 表 | v2.0 Payload Collection | 说明 |
|----------------|------------------------|------|
| books | Books | 字段一一对应 + 新增 file/status |
| chapters | Chapters | 字段一一对应 |
| pages | (嵌入 Chunks.pageNumber) | 合并简化 |
| chunks | Chunks | 含 sourceLocators json |
| chunk_fts | (Engine 内部 SQLite) | FTS5 保留在 Engine 端 |
| toc_entries | (Engine 内部 SQLite) | TOC 策略保留在 Engine 端 |
| source_locators | Chunks.sourceLocators | 合并到 Chunks json 字段 |

### 6.2 Engine 内部 SQLite（检索专用）

Engine 保留一个轻量 SQLite 用于 FTS5 和 TOC 检索策略，与 v1.1 行为一致。数据由 Engine ingest 流程写入。

### 6.3 ChromaDB（不变）

向量存储不迁移，Engine 直连 ChromaDB。

### 6.4 数据流

```
入库流程:
  User upload PDF → Payload creates Book (status=pending)
                  → afterChange hook
                  → POST /engine/ingest
                  → Engine: pdf_parser → chunk_builder → toc_extractor
                  → Engine: Payload API batch create Chunks
                  → Engine: vector_builder → ChromaDB
                  → Engine: fts5_builder → internal SQLite
                  → Engine: Payload API update Book (status=indexed)

查询流程:
  User question → Payload custom endpoint
               → POST /engine/query
               → Engine: RAGCore.query()
                   → RetrievalOrchestrator (5 strategies)
                   → RRFusion
                   → GenerationEngine (Ollama)
                   → CitationEngine
                   → QualityChecker
               → Response → Payload creates QueryLog
               → Return to User
```

---

## 7. 前端组件架构

### 7.1 v1.1 → v2.0 组件映射

```
v1.1 React SPA (Vite)                 v2.0 Next.js (Payload 内嵌)
─────────────────────                 ──────────────────────────
App.tsx                          →    layout.tsx + (app)/page.tsx
features/chat/ChatPanel          →    components/ChatPanel.tsx
features/pdf-viewer/PdfViewer    →    components/PdfViewer.tsx
features/book-selector/          →    components/BookSelector.tsx
features/trace/TracePanel        →    components/TracePanel.tsx
features/retrieval-config/       →    components/RetrievalConfig.tsx
features/generation-config/      →    components/GenerationConfig.tsx
features/reports/                →    (app)/reports/page.tsx
components/ResizeHandle          →    components/ResizeHandle.tsx
                                 NEW  /admin (Payload Admin, 自动生成)
```

### 7.2 页面路由

```
/                    主页 (PDF + Chat 双栏布局)
/admin               Payload Admin Panel (自动)
/admin/collections   管理所有 Collections
/login               登录页
/register            注册页
```

---

## 8. ROS2 集成架构（v1.1 不变）

```
ros2/ollama_publisher.py
    │
    │  from engine.rag import RAGCore     ← import 路径改
    ▼
engine/rag/core.py (RAGCore)
    │
    │  uses
    ▼
engine/rag/strategies/* + internal SQLite + ChromaDB
```

ROS2 Node 通过直接 Python import 使用 RAGCore，无需 HTTP 调用。
唯一变更：`from backend.app.core.rag_core import RAGCore` → `from engine.rag.core import RAGCore`

---

## 9. 安全考虑

| 威胁 | v1.1 缓解 | v2.0 增强 |
|------|----------|----------|
| 未授权访问 | (无防护) | Payload Auth JWT + 角色 ACL |
| Prompt injection | system_prompt 不接受用户输入 | 不变 |
| SQL injection | 参数化查询 | 不变 + Payload ORM |
| content_type 注入 | 白名单校验 | 不变 |
| Engine API 暴露 | (无) | 仅内部网络可访问 |
| 数据泄露 | (无) | QueryLogs 只能看自己的 |

---

## 10. 扩展性考虑

### 10.1 新增检索策略（v1.1 不变）

1. 创建 `engine/rag/strategies/new_strategy.py`，继承 `RetrievalStrategy`
2. 在 `RetrievalOrchestrator.__init__` 中 `register()`
3. 自动出现在前端策略开关中

### 10.2 新增文档类别（v1.1 增强）

1. v1.1: 在 `data/raw_pdfs/` 下创建目录 + 跑脚本
2. v2.0: 在 Books.category select 中添加选项 → Admin 上传 → 自动入库

### 10.3 新增 Payload Collection

1. 创建 `payload/src/collections/NewThing.ts`
2. 注册到 `payload.config.ts`
3. 自动获得 REST + GraphQL + Admin UI

### 10.4 新增 Prompt 模板（v1.1 不变）

在 `engine/rag/generation.py` 的 `_TEMPLATES` 中添加，自动出现在前端。

---

## 11. 部署架构

### 11.1 Docker Compose

```yaml
services:
  payload:
    build: ./payload
    ports: ["3000:3000"]
    depends_on: [postgres]
    environment:
      DATABASE_URI: postgres://...
      PAYLOAD_SECRET: ...
      ENGINE_URL: http://engine:8000

  engine:
    build: ./engine
    ports: ["8000:8000"]
    depends_on: [postgres]
    environment:
      OLLAMA_BASE_URL: http://ollama:11434
      CHROMA_PERSIST_DIR: /data/chroma_persist
      DATABASE_PATH: /data/engine.sqlite3
      PAYLOAD_URL: http://payload:3000

  postgres:
    image: postgres:15
    volumes: [pgdata:/var/lib/postgresql/data]

  ollama:
    image: ollama/ollama
    volumes: [ollama_models:/root/.ollama]
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: 1
              capabilities: [gpu]

volumes:
  pgdata:
  ollama_models:
```

### 11.2 网络拓扑

```
外部用户 → payload:3000 (Next.js + Payload Admin + API)
                 │
                 ├── postgres:5432 (内部)
                 ├── engine:8000 (内部, 不暴露)
                 │       │
                 │       ├── ollama:11434 (内部)
                 │       ├── chromadb (嵌入式)
                 │       └── engine.sqlite3 (FTS5)
                 └── S3/LocalFS (文件存储)
```

---

## 12. RAG-Project 迁移架构

### 12.1 目标项目技术栈

RAG-Project (Ottawa GenAI Research Assistant):
- 后端: FastAPI + Python 3.13
- LLM: Azure OpenAI (GPT-4o)
- 检索: Azure AI Search (Semantic)
- 认证: Microsoft Entra ID + JWT
- 存储: Azure Blob Storage + Cosmos DB
- 前端: React + Vite + TypeScript

### 12.2 模块迁移映射

```
textbook-rag v2.0                      RAG-Project
─────────────────────                  ───────────────

engine/rag/strategies/                 backend/app/services/
  azure_search.py            →          azure_search_store.py (替换)

engine/rag/providers/                  backend/app/services/ai_providers/
  azure_openai.py            →          azure_rag_service.py (增强)

engine/rag/core.py           →         backend/app/core/ (新增 RAGCore)
  + retrieval.py
  + strategies/*
  + citation.py
  + trace.py

engine/ingest/               →         backend/app/services/
  pdf_parser.py                          document_service.py (增强)
  chunk_builder.py                       vector_store.py (增强)
```

### 12.3 接口对齐点

| 接口 | textbook-rag v2.0 | RAG-Project | 对齐策略 |
|------|-------------------|-------------|----------|
| Settings | engine/config.py (EngineSettings) | app/core/config.py (Settings) | 字段名一致 |
| Search API | AzureSearchStrategy.search() | AzureSearchStore.search() | 返回格式对齐 |
| LLM API | AzureOpenAIProvider.generate() | AzureRAGService.generate_response() | prompt 共享 |
| Auth | Payload JWT | Entra ID + JWT | JWT 层兼容 |
| Storage | PostgreSQL + ChromaDB | Cosmos DB + Azure Blob | 适配器切换 |

### 12.4 迁移路线

```
Phase 1-3: textbook-rag v2.0 (Payload + Engine)
    │
    │ Azure 模块开发 + 测试
    ▼
Phase 4a: Azure 模块验证
    ├── AzureSearchStrategy 通过测试
    ├── AzureOpenAI Provider 通过测试
    └── 双模式切换正常工作
    │
    │ 验证通过
    ▼
Phase 4b: 迁移到 RAG-Project
    ├── azure_search.py     → RAG-Project/backend/app/services/
    ├── azure_openai.py     → RAG-Project/backend/app/services/ai_providers/
    ├── core.py (RAGCore)   → RAG-Project/backend/app/core/
    ├── strategies/* (5策略) → RAG-Project/backend/app/services/
    └── ingest/*            → RAG-Project/backend/app/services/
```
