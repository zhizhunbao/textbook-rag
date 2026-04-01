---
description: textbook-rag v2 项目结构速查
---

# 🏗️ v2 项目结构速查

```
textbook-rag/
├── engine_v2/                 # 后端引擎 v2 (LlamaIndex-native + FastAPI)
│   ├── __init__.py            # 版本号 + 模块文档
│   ├── settings.py            # LlamaIndex Settings singleton + env config
│   ├── schema.py              # 项目特定类型 (BookMeta, RAGResponse, SourceLocator)
│   ├── readers/               # ← llama_index.core.readers
│   │   └── mineru_reader.py   # MinerUReader(BaseReader) → Document[]
│   ├── ingestion/             # ← llama_index.core.ingestion
│   │   ├── pipeline.py        # IngestionPipeline: Reader → Transform → ChromaDB
│   │   └── transformations.py # BBoxNormalizer(TransformComponent)
│   ├── retrievers/            # ← llama_index.core.retrievers
│   │   └── hybrid.py          # QueryFusionRetriever (BM25 + Vector → RRF)
│   ├── response_synthesizers/ # ← llama_index.core.response_synthesizers
│   │   └── citation.py        # CitationSynthesizer (COMPACT + [N] markers)
│   ├── query_engine/          # ← llama_index.core.query_engine
│   │   └── citation.py        # RetrieverQueryEngine (retriever + synthesizer)
│   ├── llms/                  # ← llama_index.core.llms
│   │   └── resolver.py        # Dynamic routing: Azure OpenAI / Ollama
│   ├── evaluation/            # ← llama_index.core.evaluation
│   │   └── evaluator.py       # Faithfulness + Relevancy + Correctness
│   ├── question_gen/          # ← llama_index.core.question_gen
│   │   └── generator.py       # LLM-based study question generation
│   └── api/                   # FastAPI thin layer (project-specific)
│       ├── app.py             # create_app() + lifespan (init_settings)
│       ├── deps.py            # DI: singleton QueryEngine
│       └── routes/
│           ├── health.py      # GET  /engine/health
│           ├── query.py       # POST /engine/query
│           ├── ingest.py      # POST /engine/ingest
│           ├── retrievers.py  # POST /engine/retrievers/search
│           ├── llms.py        # GET  /engine/llms/providers, /models
│           ├── evaluation.py  # POST /engine/evaluation/single, /batch
│           └── questions.py   # POST /engine/questions/generate
│
├── payload-v2/                # 前端 v2 (Payload 3 + Next.js + PostgreSQL)
│   ├── src/
│   │   ├── payload.config.ts  # Payload 配置 (collections, db, plugins)
│   │   ├── app/
│   │   │   ├── (frontend)/    # 用户界面
│   │   │   │   ├── layout.tsx # Root layout (Providers + AppLayout)
│   │   │   │   ├── globals.css
│   │   │   │   ├── page.tsx   # 首页 → redirect to /chat
│   │   │   │   ├── chat/page.tsx
│   │   │   │   ├── readers/   # 阅读器 (PDF viewer)
│   │   │   │   ├── settings/  # 设置页
│   │   │   │   ├── login/     # 登录页
│   │   │   │   ├── seed/      # 数据初始化
│   │   │   │   └── engine/    # Engine Dashboard
│   │   │   │       ├── page.tsx           # Dashboard 总览
│   │   │   │       ├── analytics/         # 使用统计
│   │   │   │       ├── evaluation/        # 质量评估
│   │   │   │       ├── feedback/          # 反馈管理
│   │   │   │       ├── ingestion/         # 数据摄入
│   │   │   │       ├── llms/              # 模型管理
│   │   │   │       ├── query_engine/      # 查询引擎
│   │   │   │       ├── question_gen/      # 问题生成
│   │   │   │       ├── response_synthesizers/ # Prompt 管理
│   │   │   │       └── retrievers/        # 检索器调试
│   │   │   └── (payload)/     # Payload Admin 自动生成
│   │   ├── collections/       # Payload CMS collections
│   │   │   ├── Books.ts
│   │   │   ├── Chapters.ts
│   │   │   ├── Chunks.ts
│   │   │   ├── Users.ts
│   │   │   ├── IngestTasks.ts
│   │   │   ├── Llms.ts
│   │   │   ├── Prompts.ts
│   │   │   ├── Queries.ts
│   │   │   ├── Questions.ts
│   │   │   ├── Evaluations.ts
│   │   │   └── endpoints/     # Custom Payload endpoints (seed, sync-engine)
│   │   ├── features/          # ⭐ 核心前端代码，按功能模块组织
│   │   │   ├── auth/          # 认证
│   │   │   ├── chat/          # 聊天功能 (ChatPage, history, panel)
│   │   │   ├── home/          # 首页
│   │   │   ├── seed/          # 初始化数据
│   │   │   ├── engine/        # ⭐ Engine Dashboard 前端
│   │   │   │   ├── index.ts   # Barrel export (mirrors engine_v2/ 8 modules)
│   │   │   │   ├── readers/
│   │   │   │   ├── ingestion/
│   │   │   │   ├── retrievers/
│   │   │   │   ├── response_synthesizers/
│   │   │   │   ├── query_engine/
│   │   │   │   ├── llms/
│   │   │   │   ├── evaluation/
│   │   │   │   └── question_gen/
│   │   │   ├── shared/        # 公共 (Providers, AuthProvider, AppContext, i18n, theme)
│   │   │   │   ├── components/ui/  # shadcn/ui 组件
│   │   │   │   ├── hooks/
│   │   │   │   ├── i18n/
│   │   │   │   ├── config/
│   │   │   │   └── theme/
│   │   │   └── layout/        # 布局 (AppSidebar, AppHeader, AppLayout, UserMenu)
│   │   ├── access/            # Payload access control
│   │   ├── hooks/             # Payload hooks
│   │   └── seed/              # Seed data
│   ├── package.json
│   ├── next.config.ts
│   ├── tailwind.config.ts
│   └── tsconfig.json
│
├── data/                      # 数据存储 (v1/v2 共享)
│   ├── raw_pdfs/              # 原始 PDF (textbooks/, ecdev/, real_estate/)
│   ├── mineru_output/         # MinerU 解析输出
│   ├── chroma_persist/        # ChromaDB 向量持久化
│   └── textbook_rag.sqlite3   # Engine v1 SQLite (v2 不用)
│
├── .env                       # 环境变量 (v1 + v2 共用)
├── pyproject.toml             # Python 依赖 (含 llama-index-*)
├── .vscode/tasks.json         # VS Code 启动任务
│
└── .github/references/        # 参考项目 (只读)
    ├── llama_index/            # LlamaIndex 源码参考
    └── payload/               # Payload CMS 源码参考
```

## 与 v1 的关键差异

| 维度 | v1 (`engine/` + `payload/`) | v2 (`engine_v2/` + `payload-v2/`) |
|------|---------------------------|-----------------------------------|
| **Python 框架** | 自研 RAG pipeline | LlamaIndex-native |
| **模块命名** | `rag/strategies/`, `ingest/` | 对齐 `llama_index.core.*` (readers, retrievers, ...) |
| **向量存储** | 手动 ChromaDB client | `ChromaVectorStore` (LlamaIndex integration) |
| **检索** | 自研 FTS5 + 向量 | `QueryFusionRetriever` (BM25 + Vector → RRF) |
| **生成** | 手动 prompt 拼接 | `get_response_synthesizer()` + citation prompts |
| **数据库** | SQLite (Engine) + SQLite (Payload dev) | SQLite (Engine v1, optional) + **PostgreSQL** (Payload v2) |
| **Payload** | Payload 2 + SQLite adapter | **Payload 3** + `@payloadcms/db-postgres` |
| **前端 Engine** | `dashboard/` 子页 | `engine/` 子页，结构 1:1 映射 engine_v2 子包 |
| **端口** | Engine 8000, Payload 3000 | Engine **8001**, Payload **3001** |
