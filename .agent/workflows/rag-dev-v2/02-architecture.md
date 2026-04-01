---
description: textbook-rag v2 LlamaIndex 对齐架构 — 模块命名、数据流、组合模式
---

# 🧩 LlamaIndex 对齐架构

## 核心设计原则

**engine_v2 的每个子包都 1:1 对齐 `llama_index.core.*` 模块，且这个对齐贯穿四层。**

四层对齐意味着：
1. **L1 LlamaIndex** — 模块命名跟随 `llama_index.core.*`（`readers/`, `retrievers/`, `response_synthesizers/` 等）
2. **L2 Engine v2** — Python 子包名 = LlamaIndex 模块名，内部类继承 LlamaIndex 基类
3. **L3 Payload v2** — `features/engine/` 子目录名 = Engine v2 子包名 = 前端路由路径
4. **L4 i18n** — 侧边栏导航 key 命名规则: `nav` + PascalCase(子包名)

**只有 `api/`、`schema.py`、`chat/`、`shared/` 是纯项目特定代码，不参与四层对齐。**

## 四层对齐表

| # | LlamaIndex Module | engine_v2/ | features/engine/ | Route | Sidebar i18n Key | 显示名 (en/zh) |
|---|-------------------|------------|------------------|-------|------------------|----------------|
| 1 | `core.readers` | `readers/` | `readers/` | `/readers` | `navReaders` | Library / 资料库 |
| 2 | `core.ingestion` | `ingestion/` | `ingestion/` | `/engine/ingestion` | `navIngestion` | Ingestion / 数据导入 |
| 3 | `core.retrievers` | `retrievers/` | `retrievers/` | `/engine/retrievers` | `navRetrievers` | Retrievers / 检索器 |
| 4 | `core.response_synthesizers` | `response_synthesizers/` | `response_synthesizers/` | `/engine/response_synthesizers` | `navResponseSynthesizers` | Prompts / Prompt 管理 |
| 5 | `core.query_engine` | `query_engine/` | `query_engine/` | `/engine/query_engine` | `navQueryEngine` | Query Engine / 查询引擎 |
| 6 | `core.llms` | `llms/` | `llms/` | `/engine/llms` | `navLlms` | LLMs / LLMs |
| 7 | `core.evaluation` | `evaluation/` | `evaluation/` | `/engine/evaluation` | `navEvaluation` | Evaluation / 质量评估 |
| 8 | `core.question_gen` | `question_gen/` | `question_gen/` | `/engine/question_gen` | `navQuestionGen` | Questions / 问题库 |
| — | (project) | `api/` | — | — | — | — |
| — | (project) | `schema.py` | — | — | — | — |
| — | — | — | `../chat/` | `/chat` | `navNewChat` | New Chat / 新对话 |
| — | — | — | `../shared/` | — | — | — |

> **对齐规则**: 新增子模块时，必须在四层中同时创建对应条目:
> 1. engine_v2 子包目录名 = LlamaIndex 模块名
> 2. features/engine/ 子目录名 = engine_v2 子包名
> 3. app/(frontend)/engine/ 路由目录名 = engine_v2 子包名
> 4. i18n key = `nav` + PascalCase(子包名)
> 5. AppSidebar.tsx adminLinks href = `/engine/{子包名}`

### i18n 命名规范

```typescript
// messages.ts — Sidebar Nav 区域
interface Messages {
  navReaders: string             // readers       → navReaders
  navIngestion: string           // ingestion     → navIngestion
  navRetrievers: string          // retrievers    → navRetrievers
  navResponseSynthesizers: string // response_synthesizers → navResponseSynthesizers
  navQueryEngine: string         // query_engine  → navQueryEngine
  navLlms: string                // llms          → navLlms
  navEvaluation: string          // evaluation    → navEvaluation
  navQuestionGen: string         // question_gen  → navQuestionGen
}
// 规则: nav + PascalCase(snake_case 子包名)
// response_synthesizers → navResponseSynthesizers
// query_engine          → navQueryEngine
// question_gen          → navQuestionGen
```

### AppSidebar adminLinks 对齐

```typescript
// AppSidebar.tsx
const adminLinks = [
  { titleKey: 'navAnalytics',            href: '/engine/analytics' },       // analytics (project-specific page)
  { titleKey: 'navLlms',                 href: '/engine/llms' },            // L6: llms
  { titleKey: 'navResponseSynthesizers', href: '/engine/response_synthesizers' }, // L4: response_synthesizers
  { titleKey: 'navEvaluation',           href: '/engine/evaluation' },      // L7: evaluation
  { titleKey: 'navFeedback',             href: '/engine/feedback' },        // feedback (project-specific)
  { titleKey: 'navIngestion',            href: '/engine/ingestion' },       // L2: ingestion
  { titleKey: 'navRetrievers',           href: '/engine/retrievers' },      // L3: retrievers
  { titleKey: 'navQueryEngine',          href: '/engine/query_engine' },    // L5: query_engine
]
// titleKey 跟 i18n key 一致; href 跟 engine_v2 子包名一致
```

## 数据流 (Query)

```
用户输入问题
  ↓
[payload-v2 frontend]  POST /engine/query
  ↓
[engine_v2 API]  routes/query.py
  ↓
[query_engine]   RetrieverQueryEngine.query()
  ├── [retrievers]   QueryFusionRetriever (RRF)
  │   ├── VectorIndexRetriever (ChromaDB cosine)
  │   └── BM25Retriever (rank_bm25)
  └── [response_synthesizers]  CitationSynthesizer (COMPACT mode)
      └── [llms]  Settings.llm (Azure OpenAI or Ollama)
  ↓
RAGResponse { answer, sources[], warnings[], stats{} }
  ↓
[payload-v2 frontend]  渲染答案 + 引用 [N] + PDF 定位
```

## 数据流 (Ingest)

```
用户上传 PDF
  ↓
[payload-v2]  POST /engine/ingest  (background thread)
  ↓
[readers]     MinerUReader.load_data() → Document[]
  ↓
[ingestion]   IngestionPipeline.run()
  ├── transformations: [BBoxNormalizer, Settings.embed_model]
  └── vector_store: ChromaVectorStore (auto-upsert)
  ↓
ChromaDB  ← 持久化到 data/chroma_persist/
  ↓
[ingestion]   _push_chunks_to_payload()  → Payload CMS chunks
[ingestion]   _update_book_status()      → Payload CMS books
```

## 数据流 (Evaluation)

```
POST /engine/evaluation/single
  ↓
[evaluation]  evaluate_response(query)
  ├── engine.query(query) → response
  ├── FaithfulnessEvaluator.aevaluate_response()
  └── RelevancyEvaluator.aevaluate_response()
  ↓
EvalResult { faithfulness, relevancy, feedback }

POST /engine/evaluation/batch
  ↓
[evaluation]  evaluate_dataset(queries)
  ├── BatchEvalRunner(evaluators)
  └── aevaluate_queries(engine, queries)
  ↓
EvalResult[] + optional CorrectnessEvaluator (if reference_answers)
```

## Settings Singleton 模式

```python
# settings.py → init_settings() 在 app lifespan 中调用一次
from llama_index.core.settings import Settings

Settings.embed_model = HuggingFaceEmbedding(model_name="all-MiniLM-L6-v2")
Settings.llm = resolve_llm()  # Azure OpenAI or Ollama
```

所有子模块通过 `Settings.llm` / `Settings.embed_model` 隐式获取模型，无需手动传参。

## LlamaIndex 参考源码位置

```
.github/references/llama_index/
└── llama-index-core/llama_index/core/
    ├── readers/              # BaseReader 接口
    ├── ingestion/            # IngestionPipeline
    ├── retrievers/           # BaseRetriever, QueryFusionRetriever
    ├── response_synthesizers/# get_response_synthesizer(), ResponseMode
    ├── query_engine/         # RetrieverQueryEngine
    ├── llms/                 # LLM 基类
    ├── evaluation/           # FaithfulnessEvaluator, etc.
    ├── question_gen/         # QuestionGen 基类
    ├── schema.py             # Document, TextNode, BaseNode
    └── settings.py           # Settings singleton
```
