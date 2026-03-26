# Textbook RAG v1.1 — 系统架构文档

> **版本**: 1.1
> **作者**: Bob (Architect)
> **日期**: 2026-03-11
> **输入**: requirements.md, prd.md, v1.0 代码库

---

## 1. 架构概述

### 1.1 设计原则

| 原则 | 说明 |
|------|------|
| **增量扩展** | v1.0 代码只做扩展，不做破坏性重构 |
| **模块可插拔** | 每种检索策略是独立模块，通过注册机制组合 |
| **双入口共享** | Web (FastAPI) 和 ROS2 共享同一个 RAG Core |
| **透明可控** | 每个操作步骤都有 trace 记录，参数可外部配置 |
| **向后兼容** | 新增 API 字段全部有默认值，v1.0 客户端不受影响 |

### 1.2 架构总图

```
┌──────────────────────────────────────────────────────────────────┐
│                        Client Layer                              │
│                                                                  │
│   ┌────────────────────────┐    ┌────────────────────────────┐   │
│   │     Web Frontend       │    │     ROS2 Voice Pipeline    │   │
│   │  React / TypeScript    │    │  Whisper → RAG → gTTS      │   │
│   │                        │    │                            │   │
│   │  ┌──────┐ ┌──────────┐ │    │  subscribe: words          │   │
│   │  │ PDF  │ │  Chat    │ │    │  publish: ollama_reply      │   │
│   │  │Viewer│ │  Panel   │ │    └─────────────┬──────────────┘   │
│   │  └──────┘ └──────────┘ │                  │                  │
│   │  ┌──────────────────┐  │                  │                  │
│   │  │ Trace/Retrieval  │  │                  │                  │
│   │  │ Config Panel     │  │                  │                  │
│   │  └──────────────────┘  │                  │                  │
│   │  ┌──────────────────┐  │                  │                  │
│   │  │ Reports & Charts │  │                  │                  │
│   │  │ (EcDev)          │  │                  │                  │
│   │  └──────────────────┘  │                  │                  │
│   └───────────┬────────────┘                  │                  │
│               │ HTTP                          │ Python import    │
├───────────────┼───────────────────────────────┼──────────────────┤
│               ▼                               ▼                  │
│   ┌────────────────────┐          ┌──────────────────────┐       │
│   │   FastAPI Backend  │          │   ROS2 Node Wrapper  │       │
│   │   (HTTP API)       │          │ (ollama_publisher.py)│       │
│   └─────────┬──────────┘          └──────────┬───────────┘       │
│             │                                │                   │
│             └──────────────┬─────────────────┘                   │
│                            ▼                                     │
│   ┌─────────────────────────────────────────────────────────┐    │
│   │                   RAG Core Layer                         │    │
│   │                                                          │    │
│   │  ┌──────────────────────────────────────────────────┐    │    │
│   │  │             RAGCore (OOP Class)                   │    │    │
│   │  │                                                   │    │    │
│   │  │  query(question, config) → RAGResponse            │    │    │
│   │  │                                                   │    │    │
│   │  │  ┌─────────────────────────────────────────────┐  │    │    │
│   │  │  │ RetrievalOrchestrator                       │  │    │    │
│   │  │  │                                             │  │    │    │
│   │  │  │  ┌────────────┐  ┌────────────────────────┐ │  │    │    │
│   │  │  │  │ Strategy   │  │     Strategies         │ │  │    │    │
│   │  │  │  │ Registry   │──│  ① FTS5BM25Strategy    │ │  │    │    │
│   │  │  │  │            │  │  ② VectorStrategy      │ │  │    │    │
│   │  │  │  │  enable/   │  │  ③ TOCHeadingStrategy  │ │  │    │    │
│   │  │  │  │  disable   │  │  ④ PageIndexStrategy   │ │  │    │    │
│   │  │  │  │  per query │  │  ⑤ MetadataStrategy    │ │  │    │    │
│   │  │  │  └────────────┘  └────────────────────────┘ │  │    │    │
│   │  │  │                                             │  │    │    │
│   │  │  │  RRFusion.fuse(results[], k) → ranked[]     │  │    │    │
│   │  │  └─────────────────────────────────────────────┘  │    │    │
│   │  │                                                   │    │    │
│   │  │  ┌──────────────────┐  ┌────────────────────┐    │    │    │
│   │  │  │ CitationEngine   │  │ GenerationEngine   │    │    │    │
│   │  │  │ validate()       │  │ generate()         │    │    │    │
│   │  │  │ sanitize()       │  │ prompt_templates   │    │    │    │
│   │  │  │ map_to_source()  │  │ model_selection    │    │    │    │
│   │  │  └──────────────────┘  └────────────────────┘    │    │    │
│   │  │                                                   │    │    │
│   │  │  ┌──────────────────┐  ┌────────────────────┐    │    │    │
│   │  │  │ TraceCollector   │  │ QualityChecker     │    │    │    │
│   │  │  │ record()         │  │ check(trace)       │    │    │    │
│   │  │  │ get_trace()      │  │ → warnings[]       │    │    │    │
│   │  │  └──────────────────┘  └────────────────────┘    │    │    │
│   │  └───────────────────────────────────────────────────┘    │    │
│   └─────────────────────────┬───────────────────────────────┘    │
│                             ▼                                    │
│   ┌─────────────────────────────────────────────────────────┐    │
│   │                    Data Layer                             │    │
│   │  ┌────────────┐  ┌────────────┐  ┌───────────────────┐  │    │
│   │  │  SQLite DB  │  │  ChromaDB  │  │  MinerU Files     │  │    │
│   │  │  books      │  │  vectors   │  │  content_list.json│  │    │
│   │  │  chapters   │  │  embeddings│  │  middle.json      │  │    │
│   │  │  pages      │  │            │  │  *.md             │  │    │
│   │  │  chunks     │  │            │  │                   │  │    │
│   │  │  chunk_fts  │  │            │  │                   │  │    │
│   │  │  toc_entries│  │            │  │                   │  │    │
│   │  └────────────┘  └────────────┘  └───────────────────┘  │    │
│   └─────────────────────────────────────────────────────────┘    │
└──────────────────────────────────────────────────────────────────┘
```

---

## 2. 技术选型

### 2.1 后端

| 组件 | 选型 | 理由 |
|------|------|------|
| 语言 | Python 3.10+ | v1.0 已有，ROS2 兼容 |
| Web 框架 | FastAPI | v1.0 已有，async + auto OpenAPI |
| LLM | Ollama (local) | 课程要求本地推理 |
| 向量 DB | ChromaDB | v1.0 已有，轻量够用 |
| 全文搜索 | SQLite FTS5 | v1.0 已有，亚毫秒级 |
| 包管理 | uv | v1.0 已有 |

### 2.2 前端

| 组件 | 选型 | 理由 |
|------|------|------|
| 框架 | React 18 + TypeScript | v1.0 已有 |
| 构建 | Vite | v1.0 已有 |
| 样式 | Tailwind CSS | v1.0 已有 |
| PDF 渲染 | react-pdf | v1.0 已有 |
| 图表 | Recharts | 新增，React 生态最流行 |

### 2.3 ROS2（新增）

| 组件 | 选型 | 理由 |
|------|------|------|
| ROS2 | Humble/Iron | 课程提供 loaner laptop |
| STT | Whisper | 课程指定 |
| TTS | gTTS | 课程指定 |
| Model | qwen2.5:0.5b | < 1.5GB 限制 |

### 2.4 基础设施

| 组件 | 选型 | 理由 |
|------|------|------|
| 部署 | 本地开发 | 课程项目无需云部署 |
| CI | 手动 | ruff + pytest + tsc |
| 版本控制 | Git | 已有 |

---

## 3. 系统组件设计

### 3.1 RAG Core — 核心抽象

v1.1 的核心变化是将 retrieval/generation/citation 逻辑从松散的 service 函数**重构为 OOP 结构**，使 Web 和 ROS2 共享同一份代码。

#### 3.1.1 RAGCore 类

```python
# backend/app/core/rag_core.py

class RAGCore:
    """Unified RAG pipeline — shared by FastAPI and ROS2."""

    def __init__(self, db_path: str, config: RAGConfig | None = None):
        self.db = sqlite3.connect(db_path)
        self.config = config or RAGConfig()
        self.retriever = RetrievalOrchestrator(self.db, self.config)
        self.generator = GenerationEngine(self.config)
        self.citation_engine = CitationEngine()
        self.trace = TraceCollector()
        self.quality = QualityChecker()

    def query(self, question: str, config: QueryConfig | None = None) -> RAGResponse:
        """Full RAG pipeline: retrieve → generate → cite → trace."""
        cfg = config or QueryConfig()

        # 1. Retrieve
        retrieval_result = self.retriever.retrieve(question, cfg)
        self.trace.record_retrieval(retrieval_result)

        # 2. Generate
        answer = self.generator.generate(question, retrieval_result.chunks, cfg)
        self.trace.record_generation(answer)

        # 3. Citation validation & sanitization
        citation_result = self.citation_engine.process(answer, retrieval_result.chunks)
        self.trace.record_citations(citation_result)

        # 4. Quality check
        warnings = self.quality.check(retrieval_result, citation_result)

        return RAGResponse(
            answer=citation_result.cleaned_answer,
            sources=citation_result.sources,
            trace=self.trace.get_trace(),
            warnings=warnings,
            stats=retrieval_result.stats,
        )
```

#### 3.1.2 Strategy Pattern — 可插拔检索策略

```python
# backend/app/core/strategies/base.py

class RetrievalStrategy(ABC):
    """Base class for all retrieval strategies."""

    name: str           # e.g. "fts5_bm25"
    display_name: str   # e.g. "FTS5 BM25"
    default_enabled: bool

    @abstractmethod
    def search(self, query: str, config: QueryConfig) -> list[ChunkHit]:
        ...

# backend/app/core/strategies/fts5_strategy.py
class FTS5BM25Strategy(RetrievalStrategy):
    name = "fts5_bm25"
    display_name = "FTS5 BM25"
    default_enabled = True
    ...

# backend/app/core/strategies/vector_strategy.py
class VectorStrategy(RetrievalStrategy):
    name = "vector"
    display_name = "Vector (Semantic)"
    default_enabled = True
    ...

# backend/app/core/strategies/toc_strategy.py
class TOCHeadingStrategy(RetrievalStrategy):
    name = "toc_heading"
    display_name = "TOC Heading Search"
    default_enabled = True
    ...

# backend/app/core/strategies/pageindex_strategy.py
class PageIndexStrategy(RetrievalStrategy):
    name = "pageindex"
    display_name = "PageIndex Structure"
    default_enabled = False
    ...

# backend/app/core/strategies/metadata_strategy.py
class MetadataFilterStrategy(RetrievalStrategy):
    name = "metadata_filter"
    display_name = "Metadata Filter"
    default_enabled = False
    ...
```

#### 3.1.3 RetrievalOrchestrator

```python
# backend/app/core/retrieval.py

class RetrievalOrchestrator:
    """Runs enabled strategies and fuses results with RRF."""

    def __init__(self, db, config):
        self.strategies = StrategyRegistry()
        self.strategies.register(FTS5BM25Strategy(db))
        self.strategies.register(VectorStrategy())
        self.strategies.register(TOCHeadingStrategy(db))
        self.strategies.register(PageIndexStrategy(db))
        self.strategies.register(MetadataFilterStrategy(db))

    def retrieve(self, question: str, config: QueryConfig) -> RetrievalResult:
        enabled = self.strategies.get_enabled(config.enabled_strategies)
        results_per_strategy = {}

        for strategy in enabled:
            hits = strategy.search(question, config)
            results_per_strategy[strategy.name] = hits

        if len(enabled) == 1:
            fused = results_per_strategy[enabled[0].name]
        else:
            fused = RRFusion.fuse(
                list(results_per_strategy.values()),
                k=config.rrf_k,
            )

        return RetrievalResult(
            chunks=fused[:config.top_k],
            per_strategy=results_per_strategy,
            stats=self._compute_stats(results_per_strategy, fused),
        )
```

### 3.2 v1.0 → v1.1 迁移路径

现有 v1.0 代码不做破坏性重构，而是**渐进迁移**：

```
v1.0 结构                          v1.1 结构
─────────                          ─────────
services/                          core/                    ← NEW
  retrieval_service.py  ───→         rag_core.py
  generation_service.py ───→         retrieval.py
  query_service.py      ───→         generation.py
                                     citation.py
                                     trace.py
                                     quality.py
                                     strategies/
                                       base.py
                                       fts5_strategy.py
                                       vector_strategy.py
                                       toc_strategy.py
                                       pageindex_strategy.py
                                       metadata_strategy.py

services/                          services/                ← KEEP (thin wrappers)
  retrieval_service.py  ───→         retrieval_service.py   (delegates to core)
  generation_service.py ───→         generation_service.py  (delegates to core)
  query_service.py      ───→         query_service.py       (delegates to core)

routers/                           routers/                 ← KEEP
  query.py              ───→         query.py               (enhanced request schema)
  books.py              ───→         books.py               (unchanged)
  demo.py               ───→         demo.py                (unchanged)

schemas/                           schemas/                 ← KEEP (enhanced)
  query.py              ───→         query.py               (already has trace schemas)
```

**策略**：`services/` 保留为 thin wrappers 调用 `core/`，保持 v1.0 API 路由不变。新功能全部在 `core/` 中实现。

---

## 4. 目录结构

```
textbook-rag/
├── backend/
│   ├── app/
│   │   ├── core/                       ← NEW: RAG Core (OOP)
│   │   │   ├── __init__.py
│   │   │   ├── rag_core.py             ← RAGCore class
│   │   │   ├── retrieval.py            ← RetrievalOrchestrator
│   │   │   ├── generation.py           ← GenerationEngine
│   │   │   ├── citation.py             ← CitationEngine
│   │   │   ├── trace.py                ← TraceCollector
│   │   │   ├── quality.py              ← QualityChecker
│   │   │   ├── config.py               ← RAGConfig, QueryConfig
│   │   │   └── strategies/             ← 检索策略模块
│   │   │       ├── __init__.py
│   │   │       ├── base.py             ← RetrievalStrategy ABC
│   │   │       ├── registry.py         ← StrategyRegistry
│   │   │       ├── fts5_strategy.py
│   │   │       ├── vector_strategy.py
│   │   │       ├── toc_strategy.py
│   │   │       ├── pageindex_strategy.py
│   │   │       └── metadata_strategy.py
│   │   ├── services/                   ← v1.0 保留 (thin wrappers)
│   │   │   ├── query_service.py
│   │   │   ├── retrieval_service.py
│   │   │   └── generation_service.py
│   │   ├── routers/                    ← v1.0 保留 (enhanced)
│   │   ├── schemas/                    ← v1.0 保留 (already has trace)
│   │   ├── repositories/              ← v1.0 保留
│   │   ├── config.py
│   │   ├── database.py
│   │   └── main.py
│   └── tests/
│
├── frontend/
│   └── src/
│       ├── features/
│       │   ├── chat/                   ← v1.0 保留
│       │   ├── pdf-viewer/             ← v1.0 保留
│       │   ├── source/                 ← v1.0 保留
│       │   ├── book-selector/          ← v1.0 保留
│       │   ├── trace/                  ← NEW: Trace 面板
│       │   ├── retrieval-config/       ← NEW: 检索配置面板
│       │   ├── generation-config/      ← NEW: 生成配置面板
│       │   └── reports/                ← NEW: 报告/图表 (EcDev)
│       ├── api/
│       ├── components/
│       ├── context/
│       └── types/
│
├── ros2/                               ← NEW: ROS2 集成
│   ├── ollama_publisher.py             ← ROS2 Node
│   └── knowledge/                      ← 知识文件目录
│
├── scripts/                            ← v1.0 保留 + 扩展
│   ├── rebuild_db.py
│   ├── rebuild_toc.py
│   ├── batch_mineru.py
│   └── download_ecdev_pdfs.py
│
├── retrieval_lab/                      ← 实验验证平台
│
├── data/
│   ├── raw_pdfs/{category}/
│   └── mineru_output/{category}/
│
└── docs/
    └── v1.1/
```

---

## 5. API 设计

### 5.1 增强的 Query API

`POST /api/query` — 保持 v1.0 兼容，新增可选字段：

```yaml
# Request (QueryRequest enhanced)
question: str                         # 必填
filters:                              # 可选
  book_ids: list[int]
  chapter_ids: list[int]
  content_types: list[str]            # ["text", "table", "image", "equation"]
  categories: list[str]               # NEW: ["textbook", "ecdev", "real_estate"]
top_k: int = 5                        # 1~20
fetch_k: int | null                   # NEW: null = top_k * 3
model: str | null
enabled_strategies: list[str] | null  # NEW: ["fts5_bm25", "vector", "toc_heading", ...]
rrf_k: int = 60                       # NEW: 1~200
prompt_template: str = "default"      # NEW: "default"|"concise"|"detailed"|"academic"
citation_style: str = "inline"        # NEW: "inline"|"footnote"|"none"
```

```yaml
# Response (QueryResponse — already has trace/warnings)
answer: str
sources: list[SourceInfo]
retrieval_stats: RetrievalStats       # fts_hits, vector_hits, ...
trace: QueryTrace                     # full trace
warnings: list[QualityWarning]        # quality warnings
```

### 5.2 新增 API

```yaml
GET /api/strategies
  # 返回可用检索策略列表及其默认状态
  Response: list[{name, display_name, default_enabled, description}]

GET /api/prompt-templates
  # 返回可用 prompt 模板列表
  Response: list[{id, name, description, content}]

POST /api/reports/generate           # NEW: EcDev 报告生成
  Request: {question, report_type: "task1"|"task2", filters}
  Response: {report_markdown, charts: list[{type, data, title}], citations}

POST /api/evaluate                   # NEW: 批量评估
  Request: {questions: list[{question, ground_truth}]}
  Response: {results: list[{question, answer, top3_docs, score}], avg_accuracy}
```

### 5.3 向后兼容策略

所有新增字段均有默认值。v1.0 客户端发送不含新字段的请求时：
- `enabled_strategies = null` → 使用所有 default_enabled=true 的策略（FTS5 + Vector + TOC = v1.0 行为）
- `fetch_k = null` → 自动计算 top_k * 3（v1.0 行为）
- `rrf_k = 60` → v1.0 硬编码值
- `prompt_template = "default"` → v1.0 system prompt
- `categories = []` → 不过滤类别（所有文档）

---

## 6. 数据架构

### 6.1 SQLite Schema 变更

v1.0 schema 保持不变，仅新增：

```sql
-- books 表新增 category 列
ALTER TABLE books ADD COLUMN category TEXT DEFAULT 'textbook';
-- 值: 'textbook', 'ecdev', 'real_estate'

-- （可选）如果 PageIndex 需要独立表
CREATE TABLE IF NOT EXISTS page_structure (
    id INTEGER PRIMARY KEY,
    book_id INTEGER NOT NULL REFERENCES books(id),
    node_id TEXT NOT NULL,
    title TEXT NOT NULL,
    level INTEGER NOT NULL,
    parent_node_id TEXT,
    page_number INTEGER,
    line_num INTEGER
);
```

### 6.2 数据流

```
PDF 文件
    │
    ▼ batch_mineru.py
MinerU 输出 (content_list.json, middle.json, *.md)
    │
    ▼ rebuild_db.py (增强: category 支持, bbox 坐标转换)
    │
    ├──→ SQLite DB (books, chapters, pages, chunks, chunk_fts, toc_entries)
    │
    └──→ ChromaDB (chunk embeddings)
```

---

## 7. 前端组件架构

```
App.tsx
├── BookSelector (v1.0)
├── ResizableLayout
│   ├── PdfViewer (v1.0, 增强: bbox overlay)
│   └── RightPanel
│       ├── ChatPanel (v1.0, 增强: citation click)
│       ├── TracePanel (NEW)
│       │   ├── RequestParams
│       │   ├── StrategyResults (×5 + fused)
│       │   ├── GenerationTrace
│       │   ├── CitationTrace
│       │   └── QualityWarnings
│       ├── RetrievalConfigPanel (NEW)
│       │   ├── TopKSlider
│       │   ├── FetchKSlider
│       │   ├── StrategyToggles (×5)
│       │   ├── RRFKInput
│       │   ├── ContentTypeFilter
│       │   └── CategoryFilter
│       ├── GenerationConfigPanel (NEW)
│       │   ├── PromptTemplateSelector
│       │   ├── ModelSelector (enhanced)
│       │   └── CitationStyleSelector
│       └── ReportsPanel (NEW, EcDev)
│           ├── ChartRenderer (Recharts)
│           └── ReportViewer (Markdown)
```

---

## 8. ROS2 集成架构

```
ros2/ollama_publisher.py
    │
    │  import
    ▼
backend/app/core/rag_core.py (RAGCore)
    │
    │  uses
    ▼
backend/app/core/strategies/* + repositories/*
    │
    ▼
SQLite DB + ChromaDB
```

ROS2 Node 通过直接 Python import 使用 RAGCore，无需 HTTP 调用。
配置通过 ROS2 parameters 传入（model, knowledge_path, db_path）。

---

## 9. 安全考虑

| 威胁 | 缓解 |
|------|------|
| Prompt injection | system_prompt 不接受用户直接输入；user_prompt 仅拼接 context + question |
| content_type 注入 | 白名单校验: ["text", "table", "image", "equation"] |
| SQL injection | 使用参数化查询（v1.0 已有） |
| 路径遍历 | 文件路径配置化，不接受用户输入的路径 |

---

## 10. 扩展性考虑

### 10.1 新增检索策略

只需：
1. 创建 `backend/app/core/strategies/new_strategy.py`，继承 `RetrievalStrategy`
2. 在 `RetrievalOrchestrator.__init__` 中 `register()`
3. 自动出现在前端策略开关中

### 10.2 新增文档类别

只需：
1. 在 `data/raw_pdfs/` 下创建目录
2. 运行 `batch_mineru.py` + `rebuild_db.py`（传入 category 参数）
3. 前端 CategoryFilter 自动从 DB 读取可用类别

### 10.3 新增 Prompt 模板

只需：
1. 在模板配置文件中添加新模板
2. 自动出现在前端选择器中
