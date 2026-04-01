---
description: textbook-rag v2 演进路线图 — 从 LlamaIndex 基础到 Agentic RAG
---

# 🧠 v2 演进路线

> v2 已经完成了从 v1 自研 pipeline 到 LlamaIndex-native 的架构迁移。
> 下一步的重点是利用 LlamaIndex 生态快速实现 Agentic RAG 能力。

---

## 当前架构 (v2.0: LlamaIndex-native RAG)

```
用户提问 → HybridRetriever (BM25+Vector → RRF) → CitationSynthesizer → 答案 + [N] 引用
```

**已完成:**
- ✅ MinerUReader (BaseReader 接口)
- ✅ IngestionPipeline (Reader → Transform → ChromaDB)
- ✅ QueryFusionRetriever (BM25 + Vector → RRF)
- ✅ CitationSynthesizer (COMPACT mode + [N] markers)
- ✅ RetrieverQueryEngine (retriever + synthesizer)
- ✅ LLM Resolver (Azure OpenAI / Ollama dynamic routing)
- ✅ Evaluation (Faithfulness + Relevancy + Correctness)
- ✅ QuestionGenerator (LLM-based study questions)
- ✅ Payload 3 + PostgreSQL + GPT-style frontend

---

## Phase 1: Self-Reflection + Query Rewrite 🔴 高优先

给现有 pipeline 加 self-reflection:

```
问 → 检索 → LLM 自评:"检索结果能回答吗?"
  ├─ Yes → 生成答案
  └─ No  → 改写 query → 再检索 → 生成答案
```

**实现路径 (LlamaIndex-native):**
- 使用 `llama_index.core.query_engine.RetryQueryEngine` 或 `RetryGuidelineQueryEngine`
- 或用 `llama_index.core.agent` 的 `ReActAgent` 做 tool-based 检索

**位置:** `engine_v2/query_engine/` 新增 `agentic.py`

### Phase 2: 多步查询分解 🟡 中优先

```
"比较 Ch3 和 Ch7 对 normalization 的讲解"
  → Step 1: 检索 Ch3
  → Step 2: 检索 Ch7
  → Step 3: 综合比较
```

**实现路径:**
- `llama_index.core.question_gen.SubQuestionQueryEngine`
- 或自定义 `llama_index.core.workflow.Workflow` (LlamaIndex 0.11+ 新范式)

### Phase 3: Workflow-based Pipeline 🟡 中优先

将 query pipeline 重构为 LlamaIndex Workflow:

```python
from llama_index.core.workflow import Workflow, step, Event

class RAGWorkflow(Workflow):
    @step
    async def retrieve(self, ev: QueryEvent) -> RetrieveEvent: ...

    @step
    async def evaluate_retrieval(self, ev: RetrieveEvent) -> ...: ...

    @step
    async def synthesize(self, ev: RetrieveEvent) -> ResponseEvent: ...
```

**优势:** 异步、可观测 (tracing)、可复用 steps

### Phase 4: Agent + Tools 🟢 低优先

```python
from llama_index.core.agent import ReActAgent
from llama_index.core.tools import QueryEngineTool

# 把 QueryEngine 包装成 Tool
rag_tool = QueryEngineTool.from_defaults(
    query_engine=my_engine,
    name="textbook_search",
    description="Search textbook content for answers",
)

agent = ReActAgent.from_tools([rag_tool, ...])
response = agent.chat("Compare normalization in chapters 3 and 7")
```

### Phase 5: Multi-Agent ⚪ 远期

```
Orchestrator Agent
  ├── Query Analyzer (理解意图、分解问题)
  ├── Retrieval Agent (选策略、执行检索、评估结果)
  ├── Synthesis Agent (生成答案、标注引用)
  └── QA Agent (验证答案 → 防幻觉)
```

---

## 技术债 & 改进

| 项目 | 优先级 | 描述 |
|------|--------|------|
| Streaming response | 高 | `CitationSynthesizer(streaming=True)` + SSE |
| Async retriever | 高 | `QueryFusionRetriever(use_async=True)` |
| Node postprocessor | 中 | 添加 `SimilarityPostprocessor` 过滤低分 chunks |
| Metadata filter | 中 | 支持 book_id / chapter 级别的过滤 |
| Observability | 中 | 接入 `llama_index.core.instrumentation` 或 Arize Phoenix |
| Caching | 低 | `IngestionCache` 避免重复嵌入 |
| Multi-modal | 低 | 处理图片 chunks (image retrieval) |

---

## 设计原则

1. **LlamaIndex-native first** — 优先使用 LlamaIndex 内置组件，只在必要时自定义
2. **三层对齐** — engine_v2 子包 ↔ llama_index.core.* ↔ features/engine/*
3. **渐进式改造** — 每个 phase 独立可交付、可回滚
4. **Settings singleton** — 所有模块通过 `Settings.llm` / `Settings.embed_model` 共享配置
5. **API 薄层** — FastAPI routes 只是 thin wrapper，核心逻辑在子模块内
