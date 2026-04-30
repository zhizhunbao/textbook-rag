# Textbook RAG v2.0 — 需求规格说明

> **版本**: 2.0
> **作者**: Product Manager
> **日期**: 2026-03-21
> **前置**: v1.1 已完成全部 8 个模块，RAG Core OOP + 5 策略 + ROS2 集成已通过验收
> **架构方向**: 分层分模块，Payload CMS 主导，双模式 (Local + Azure)
> **迁移目标**: 测试通过后迁移到 RAG-Project (Ottawa GenAI Research Assistant)

---

## 1. 项目概述

### 1.1 愿景

将 v1.1 的课程项目级 RAG 系统**升级为产品级平台**：

- 用户管理 + 权限控制
- 内容可视化管理（Payload Admin Panel）
- 自动化入库管道（上传即入库）
- API 自动生成（REST + GraphQL）
- 生产级部署（Docker Compose）

核心保留：**v1.1 的 RAG Core（5 策略 + RRF + Citation + Trace + Quality）原封不动**。
新增：**Azure AI Search（第 6 策略）+ GPT-4o 生成**，本地/云端双模式切换。
最终目标：测试通过后迁移到 **RAG-Project**（Ottawa GenAI Research Assistant）。

### 1.2 目标

| 序号 | 目标 | 成功标准 | v1.1 对比 |
|------|------|----------|-----------|
| 1 | **内容管理可视化** | Admin Panel 可 CRUD 所有书籍/章节/Chunk | v1.1: 仅 CLI 脚本 |
| 2 | **自动化入库** | 上传 PDF → 自动触发入库管道 → 进度可追踪 | v1.1: 手动跑 3 个脚本 |
| 3 | **用户系统** | JWT/Session 认证 + 角色权限控制 | v1.1: Won't Have |
| 4 | **API 自动化** | 所有 Collection 自动生成 REST + GraphQL API | v1.1: 手写 FastAPI |
| 5 | **RAG 能力保持** | v1.1 全部检索/生成/Citation/Trace 功能不退化 | 原封不动 |
| 6 | **模块化管道** | scripts/ 拆分为 ingest/ index/ 可复用模块 | v1.1: 28KB 单文件 |
| 7 | **Azure 双模式** | Azure AI Search + GPT-4o 可切换，本地保留 | v1.1: 仅本地 |
| 8 | **迁移就绪** | 核心模块可直接移植到 RAG-Project | 新增 |

### 1.3 与 v1.1 的关系

v2.0 是**架构升级**，不是功能重写：

```
v1.1 功能 = 全部保留（RAG Core, 5 策略, ROS2, Trace, Citation）
v2.0 新增 = 架构层（Payload CMS, PostgreSQL, 自动化管道, Auth）
```

### 1.4 范围

**In Scope (v2.0)**:
- Payload CMS 3.x 集成 + Collections 定义
- Python Engine 模块化重构（scripts/ → engine/ingest + engine/index）
- SQLite → PostgreSQL 数据迁移
- 用户认证 + 角色权限
- 自动化入库管道 + 进度追踪
- Next.js 前端迁移
- Docker Compose 部署

**Out of Scope (v2.0)**:
- 流式输出 (streaming)
- 多模态检索
- 付费系统
- 移动端
- Statistics Canada API 集成（Phase 3）

---

## 2. 用户与角色

### 2.1 用户画像（v1.1 扩展）

| 角色 | v1.1 | v2.0 新增能力 | Payload 权限 |
|------|------|-------------|-------------|
| 学生 | 问答 + 验证来源 | 登录后查询，历史记录 | reader |
| TA / 教师 | 排查质量、调参 | 管理书籍、查看所有查询日志 | editor |
| NLP 教授 | 评估 RAG | 管理员面板全权限 | admin |
| EcDev 分析师 | 报告/图表 | 上传新季报、查看分析历史 | editor |
| 系统管理员 | (无) | **新角色**: 管理用户、部署配置 | admin |

### 2.2 使用场景（v2.0 新增）

**场景 A: 教师上传新教材**
1. 登录 Payload Admin → Books → Create
2. 填写标题、作者、类别 → 上传 PDF
3. 系统自动触发入库管道 → 进度条显示
4. 完成后状态变为 "indexed"，学生可立即查询

**场景 B: 管理员监控入库**
1. 进入 Admin → PipelineTasks
2. 看到所有入库任务的状态、进度、日志
3. 失败任务可查看错误信息、重试

**场景 C: 学生登录查询**
1. 登录 → 选择书籍 → 提问
2. 查询自动记录到 QueryLogs
3. 下次登录可查看历史查询

---

## 3. 功能需求 — 模块化架构

### 3.0 架构总览

```
v2.0 三层架构:

┌─────────────────────────────────────────────────────────────┐
│                   Presentation Layer                         │
│  ┌─────────────────────────────────────────────────────┐    │
│  │ Next.js 15 App Router + Payload Admin Panel         │    │
│  │   PDF Viewer / Chat / Trace / Config / Reports      │    │
│  └──────────────────────┬──────────────────────────────┘    │
├─────────────────────────┼───────────────────────────────────┤
│                   Payload CMS Layer                          │
│  ┌──────────────────────▼──────────────────────────────┐    │
│  │ Payload 3.x + PostgreSQL                            │    │
│  │  Collections: Books, Chapters, Chunks, Users,       │    │
│  │              PipelineTasks, QueryLogs                │    │
│  │  Auth: JWT/Session | Hooks: afterChange → Engine    │    │
│  │  REST + GraphQL API (auto-generated)                │    │
│  └──────────────────────┬──────────────────────────────┘    │
├─────────────────────────┼───────────────────────────────────┤
│                   Python Engine Layer                        │
│  ┌──────────────────────▼──────────────────────────────┐    │
│  │ engine/                                             │    │
│  │  rag/     = v1.1 RAG Core (原封不动)                │    │
│  │  ingest/  = v1.1 scripts/ 拆分                     │    │
│  │  index/   = v1.1 scripts/ 拆分                     │    │
│  │  api/     = Thin FastAPI (内部调用)                  │    │
│  └──────────────────────┬──────────────────────────────┘    │
│                         ▼                                    │
│  ┌──────────────────────────────────────────────────────┐    │
│  │ Data: PostgreSQL + ChromaDB + S3/Local FS            │    │
│  └──────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────┘
```

### 3.1 模块清单

| 模块 | 名称 | 类型 | 优先级 | v1.1 来源 |
|------|------|------|--------|----------|
| **P0** | Payload Collections | 新增 | P0 | 无 |
| **P1** | User Auth + Roles | 新增 | P0 | v1.1 Won't Have |
| **P2** | Engine Ingest | 重构 | P0 | v1.1 scripts/ |
| **P3** | Engine Index | 重构 | P0 | v1.1 scripts/ |
| **P4** | Engine RAG | 移动 | P0 | v1.1 backend/app/core/ (不改) |
| **P5** | Pipeline Automation | 新增 | P0 | 无 |
| **P6** | Data Migration | 新增 | P0 | 无 |
| **P7** | Frontend Migration | 重构 | P1 | v1.1 frontend/ |
| **P8** | Docker Deployment | 新增 | P1 | 无 |
| **A1** | Azure AI Search 策略 | 新增 | P0 | RAG-Project 已有实现 |
| **A2** | Azure OpenAI (GPT-4o) | 新增 | P0 | RAG-Project 已有实现 |
| **A3** | Azure Blob Storage | 新增 | P1 | RAG-Project 已有实现 |
| **A4** | RAG-Project 迁移 | 新增 | P1 | 最终目标 |
| **R1-R8** | v1.1 RAG 功能 | 保留 | — | v1.1 M0-M7 全部保留 |

### 3.2 P0: Payload Collections

**FR-P0.1** Books Collection
- 映射 v1.1 SQLite books 表
- 字段: title, authors, isbn, category (textbook/ecdev/real_estate), file (upload), status, chunkCount, metadata
- afterChange hook: 新建/更新时触发 Engine ingest

**FR-P0.2** Chapters Collection
- 映射 v1.1 SQLite chapters 表
- 字段: book (relationship), title, order, level, pageStart, pageEnd

**FR-P0.3** Chunks Collection
- 映射 v1.1 SQLite chunks + chunk_fts + source_locators
- 字段: chunkId (unique), book, chapter, text, contentType, readingOrder, pageNumber, sourceLocators (json), vectorized

**FR-P0.4** PipelineTasks Collection
- 新增: 异步任务追踪
- 字段: taskType (ingest/vectorize/reindex), book, status, progress (0-100), log, error, startedAt, finishedAt

**FR-P0.5** QueryLogs Collection
- 新增: 查询历史记录
- 字段: user, question, answer, sources (json), trace (json), warnings (json), model, latencyMs, config (json)

### 3.3 P1: User Auth + Roles

**FR-P1.1** Payload 内置认证
- JWT/Session 双模式
- 注册/登录/登出

**FR-P1.2** 角色权限
- admin: 全部权限
- editor: 管理 Books/Chapters, 查看 QueryLogs
- reader: 只能查询, 查看自己的 QueryLogs
- student/ta/professor/analyst 映射到 reader/editor/admin

**FR-P1.3** 访问控制
- Chunks: 只有 editor/admin 可修改
- QueryLogs: reader 只能看自己的
- PipelineTasks: editor/admin 可见

### 3.4 P2: Engine Ingest（v1.1 scripts/ 拆分）

**FR-P2.1** pdf_parser 模块
- 来源: v1.1 `scripts/batch_mineru.py`
- 功能: MinerU 解析 PDF → content_list.json, middle.json, .md
- 接口: `parse(pdf_path) -> MineruOutput`

**FR-P2.2** chunk_builder 模块
- 来源: v1.1 `scripts/rebuild_db.py` (28KB 拆分)
- 功能: MinerU 输出 → Chunk 列表
- 包含: bbox 坐标转换 (1000x1000 → PDF 点坐标)
- 接口: `build_chunks(mineru_output) -> list[ChunkData]`

**FR-P2.3** toc_extractor 模块
- 来源: v1.1 `scripts/rebuild_toc.py`
- 功能: PDF 书签 → toc_entries
- 接口: `extract_toc(pdf_path) -> list[TocEntry]`

**FR-P2.4** metadata_enricher 模块
- 来源: v1.1 `scripts/rebuild_db.py` 中的 category 标记逻辑
- 功能: 为 chunk 附加 category、chapter 关联
- 接口: `enrich(chunks, book_meta) -> list[ChunkData]`

### 3.5 P3: Engine Index（v1.1 scripts/ 拆分）

**FR-P3.1** vector_builder 模块
- 来源: v1.1 `scripts/build_vectors.py`
- 功能: Chunk 文本 → ChromaDB 向量化
- 接口: `build_vectors(chunks) -> VectorizeResult`

**FR-P3.2** fts5_builder 模块
- 来源: v1.1 `scripts/rebuild_db.py` 中的 FTS5 索引构建
- 功能: 构建 SQLite FTS5 全文索引
- 接口: `build_fts5(chunks, db_path) -> IndexResult`

**FR-P3.3** topic_indexer 模块
- 来源: v1.1 `scripts/rebuild_topic_index.py` (24KB 拆分)
- 功能: 构建主题索引
- 接口: `build_topic_index(chunks) -> TopicIndex`

### 3.6 P4: Engine RAG（v1.1 Core 扩展 Azure 策略）

**FR-P4.1** RAGCore 平移
- 源码: v1.1 `backend/app/core/` → `engine/rag/`
- 改动: 仅修改 import 路径 + 新增 AzureSearchStrategy + AzureGenerationEngine
- 保留: RAGCore class, query() → RAGResponse

**FR-P4.2** 5 + 1 策略
- 保留: FTS5BM25Strategy, VectorStrategy, TOCHeadingStrategy, PageIndexStrategy, MetadataFilterStrategy
- **新增: AzureSearchStrategy** — Azure AI Search 语义检索 (第 6 策略)
  - 继承 RetrievalStrategy ABC
  - 使用 Azure AI Search REST API (Semantic ranking)
  - 默认关闭，当配置了 AZURE_SEARCH_* 环境变量时可启用
  - 参考实现: RAG-Project `services/azure_search_store.py`
- StrategyRegistry, RetrievalOrchestrator, RRFusion — 不修改，自动支持第 6 策略

**FR-P4.3** 双模式生成引擎
- **本地模式 (默认)**: Ollama + 本地模型 (v1.1 不变)
- **Azure 模式**: Azure OpenAI GPT-4o
  - 当配置了 AZURE_OAI_* 环境变量时可切换
  - 参考实现: RAG-Project `services/ai_providers/azure_rag_service.py`
- GenerationEngine 通过 provider 参数切换: `provider = "ollama" | "azure_openai"`
- 两模式共享同一 prompt template 系统

**FR-P4.4** Engine API
- Thin FastAPI，仅供 Payload 内部调用
- POST /engine/query → RAGCore.query()
- POST /engine/ingest → ingest pipeline
- GET /engine/health
- GET /engine/strategies
- GET /engine/models
- GET /engine/providers → 列出可用 LLM providers (ollama, azure_openai)

### 3.7 P5: Pipeline Automation

**FR-P5.1** Payload Hook 触发
- Books Collection afterChange hook → POST /engine/ingest
- 传入: bookId, fileUrl, category

**FR-P5.2** 进度追踪
- Engine 执行过程中通过 payload_client 更新 PipelineTasks
- 进度: 0%(开始) → 30%(MinerU) → 60%(Chunks) → 90%(Vectors) → 100%(完成)

**FR-P5.3** 错误处理
- 失败时更新 PipelineTasks status=error, 写入 error 日志
- 更新 Book status=error

**FR-P5.4** 结果回写
- Chunks 通过 Payload REST API 批量创建
- Book status 更新为 indexed, chunkCount 更新

### 3.8 P6: Data Migration

**FR-P6.1** SQLite → PostgreSQL 迁移脚本
- 读取 v1.1 textbook_rag.sqlite3 (164MB)
- 通过 Payload REST API 批量导入 books, chapters, chunks
- 保留所有元数据: category, content_type, source_locators, bbox

**FR-P6.2** ChromaDB 保留
- 向量数据不迁移，ChromaDB 继续使用
- Engine 直连 ChromaDB

### 3.9 P7: Frontend Migration

**FR-P7.1** React SPA → Next.js App Router
- v1.1 全部前端组件迁移到 Payload 内嵌 Next.js
- ChatPanel, PdfViewer, TracePanel, RetrievalConfig, GenerationConfig, Reports

**FR-P7.2** Payload Admin Panel
- 自动生成: Books/Chapters/Chunks/Users/PipelineTasks 管理界面
- 零额外开发

**FR-P7.3** API 调用切换
- v1.1 `/api/v1/query` → Payload endpoint → Engine `/engine/query`
- v1.1 `/api/v1/books` → Payload auto-generated `/api/books`

### 3.10 P8: Docker Deployment

**FR-P8.1** Docker Compose 编排
- payload (Payload CMS + Next.js)
- engine (Python Engine + FastAPI)
- postgres (PostgreSQL)
- redis (可选, BullMQ 队列)
- ollama (LLM 服务)

**FR-P8.2** 环境配置
- 统一 .env 文件
- 开发模式 + 生产模式

### 3.11 A1: Azure AI Search 策略（新增第 6 策略）

**FR-A1.1** AzureSearchStrategy 实现
- 继承 v1.1 `RetrievalStrategy` ABC，无需修改框架
- 通过 Azure AI Search REST API 执行语义检索
  - queryType: semantic
  - semanticConfiguration: default
  - captions: extractive
- 返回 `list[ChunkHit]`，与其他 5 策略统一

**FR-A1.2** 配置
- 环境变量: `AZURE_SEARCH_ENDPOINT`, `AZURE_SEARCH_KEY`, `AZURE_SEARCH_INDEX`
- 默认关闭 (default_enabled=False)
- 当三个环境变量均配置时，前端策略开关中出现 "Azure AI Search" 选项

**FR-A1.3** 与本地策略共存
- AzureSearchStrategy 参与 RRF 融合，和 FTS5/Vector/TOC 等并列
- 可以和任何本地策略组合使用
- Trace 面板正常展示 Azure Search hits

### 3.12 A2: Azure OpenAI GPT-4o（双模式生成）

**FR-A2.1** AzureOpenAI Provider
- 新增 `engine/rag/providers/azure_openai.py`
- 使用 Azure OpenAI REST API (deployment: gpt-4o)
- 共享 v1.1 prompt template 系统

**FR-A2.2** Provider 切换
- 配置: `AZURE_OAI_ENDPOINT`, `AZURE_OAI_KEY`, `AZURE_OAI_DEPLOYMENT`
- 前端 Model 选择器新增 Azure 模型
- QueryConfig 新增 `provider` 字段: `"ollama" | "azure_openai"`
- 默认: 有 Azure 配置时 → azure_openai，否则 → ollama

**FR-A2.3** 回退机制
- Azure 调用失败时自动回退到 Ollama
- Quality Warning: `AZURE_FALLBACK_TO_OLLAMA`

### 3.13 A3: Azure Blob Storage（可选文件存储）

**FR-A3.1** 文件存储适配器
- 新增 `engine/adapters/azure_blob.py`
- 上传 PDF 时可存储到 Azure Blob (替代本地文件系统)
- 配置: `AZURE_BLOB_CONNECTION_STRING`, `AZURE_BLOB_CONTAINER`

### 3.14 A4: RAG-Project 迁移准备

**FR-A4.1** 接口对齐
- Engine 的 Azure 相关模块设计与 RAG-Project 接口兼容
- engine/rag/strategies/azure_search.py → 可直接移入 RAG-Project services/
- engine/rag/providers/azure_openai.py → 可直接替换 RAG-Project ai_providers/

**FR-A4.2** 迁移检查清单
- [ ] AzureSearchStrategy 在 textbook-rag 中测试通过
- [ ] AzureOpenAI Provider 在 textbook-rag 中测试通过
- [ ] 双模式切换 (本地 ↔ Azure) 正常工作
- [ ] Trace 面板正确展示 Azure 结果
- [ ] 将验证过的模块移植到 RAG-Project

**FR-A4.3** RAG-Project 目标架构对齐
- RAG-Project 使用: FastAPI + Azure OpenAI + Azure AI Search + Cosmos DB + Entra ID
- textbook-rag v2.0 的 Azure 模块设计需兼容 RAG-Project 的:
  - Settings 类 (Pydantic BaseSettings)
  - ChatService 调用模式
  - AzureSearchStore 接口

### 3.15 保留的 v1.1 功能（R 系列）

> 以下功能**全部保留**，无需重新开发。v2.0 仅改变它们的运行环境（Engine 包内），不改逻辑。

| ID | v1.1 模块 | v1.1 功能 | v2.0 位置 |
|----|----------|----------|-----------|
| R1 | M0 | 多类别入库（教科书/EcDev/房地产） | engine/ingest/ |
| R2 | M1 | Trace 面板 + Quality Warnings | engine/rag/ + 前端 |
| R3 | M2 | 5 策略可控检索 + RRF 融合 | engine/rag/strategies/ |
| R4 | M3 | Citation 校验 + 跳页 + bbox 高亮 | engine/rag/ + 前端 |
| R5 | M4 | Prompt 模板 + 模型选择 | engine/rag/ |
| R6 | M5 | 报告/图表（EcDev） | engine/rag/ + 前端 |
| R7 | M6 | ROS2 语音集成 | ros2/ import engine.rag |
| R8 | M7 | 20 题评估 | 评估脚本 |

---

## 4. 非功能需求

### 4.1 性能
- **NFR-1**: Payload → Engine 调用延迟 < 50ms（同机网络）
- **NFR-2**: 入库管道 100 页 PDF < 5 分钟（含 MinerU + 向量化）
- **NFR-3**: v1.1 所有性能指标不退化

### 4.2 兼容
- **NFR-4**: v1.1 RAG Core 逻辑零修改
- **NFR-5**: v1.1 所有测试用例在 engine/tests/ 中通过
- **NFR-6**: ROS2 Node 通过 `import engine.rag` 正常工作

### 4.3 安全
- **NFR-7**: Payload Auth JWT/Session 认证
- **NFR-8**: 角色权限控制（admin/editor/reader）
- **NFR-9**: Engine API 仅内部访问（不暴露公网）
- **NFR-10**: v1.1 所有安全措施保留（prompt injection 防护等）
- **NFR-11**: Azure API Key 仅存于后端 .env，不暴露到前端
- **NFR-12**: Azure Entra ID 认证（迁移到 RAG-Project 后启用）

### 4.4 可用性
- **NFR-11**: Payload Admin Panel 开箱即用
- **NFR-12**: 前端 UI 保持 v1.1 用户体验
- **NFR-13**: 入库进度实时可见

### 4.5 代码质量
- **NFR-14**: engine/ 独立 pyproject.toml，可独立安装
- **NFR-15**: payload/ 独立 package.json
- **NFR-16**: `ruff check` + `tsc --noEmit` 通过

### 4.6 部署
- **NFR-17**: Docker Compose 一键启动全栈
- **NFR-18**: 支持开发模式（热重载）和生产模式

---

## 5. 约束条件

### 5.1 技术约束

| 层 | 技术 | 约束 |
|----|------|------|
| CMS | Payload 3.x | 必须 TypeScript, 必须 PostgreSQL |
| Engine | Python 3.10+ | 保留 v1.1 全部依赖 |
| 前端 | Next.js 15 | Payload 内嵌, App Router |
| 数据库 | PostgreSQL | Payload 管理; ChromaDB 保留 |
| LLM | Ollama (local) | 不变 |

### 5.2 开发约束
- RAG Core 原有 5 策略**禁止修改**，只允许改 import 路径
- 新增 AzureSearchStrategy 必须继承 `RetrievalStrategy` ABC（不改框架）
- v1.1 测试用例**全部通过**后才能删除旧代码
- Payload Collections 字段必须**映射 v1.1 SQLite schema**
- Azure 模块必须兼容 RAG-Project 接口设计

### 5.3 迁移约束
- Phase 1 (Payload 搭建) 期间旧系统必须可运行
- 数据迁移脚本必须支持重复运行（幂等）
- Phase 3 (清理) 前必须验证所有功能正常
- Phase 4 (RAG-Project 迁移) 前必须在 textbook-rag 中验证 Azure 模块

---

## 6. 验收标准

### 6.1 Payload 层
- [ ] AC-P0.1: Payload Admin 可 CRUD Books/Chapters/Chunks
- [ ] AC-P0.2: 自动生成 REST API 可访问所有 Collections
- [ ] AC-P1.1: 注册/登录/登出正常工作
- [ ] AC-P1.2: 角色权限控制生效（reader 不能改 Books）

### 6.2 Engine 层
- [ ] AC-P2.1: pdf_parser 模块可独立运行
- [ ] AC-P2.2: chunk_builder 输出与 v1.1 rebuild_db.py 一致
- [ ] AC-P3.1: vector_builder 模块可独立运行
- [ ] AC-P4.1: RAGCore.query() 返回结果与 v1.1 完全一致
- [ ] AC-P4.2: 5 策略全部通过原有测试
- [ ] AC-P4.3: Engine API /engine/query 正常响应

### 6.3 Pipeline
- [ ] AC-P5.1: 上传 PDF → 自动触发 →  Chunks 入库 → 状态变 indexed
- [ ] AC-P5.2: PipelineTasks 进度实时更新
- [ ] AC-P5.3: 失败任务有错误日志

### 6.4 迁移
- [ ] AC-P6.1: v1.1 SQLite 全部数据迁移到 PostgreSQL
- [ ] AC-P6.2: 迁移后查询结果与 v1.1 一致

### 6.5 前端
- [ ] AC-P7.1: 所有 v1.1 UI 功能在 Next.js 中可用
- [ ] AC-P7.2: Payload Admin Panel 可正常访问

### 6.6 部署
- [ ] AC-P8.1: `docker compose up` 一键启动全栈
- [ ] AC-P8.2: 5 分钟内首次运行完成

### 6.7 Azure 集成
- [ ] AC-A1.1: AzureSearchStrategy 注册到 StrategyRegistry 并可开关
- [ ] AC-A1.2: Azure Search 结果参与 RRF 融合，Trace 面板正常展示
- [ ] AC-A2.1: Azure OpenAI GPT-4o 可生成回答
- [ ] AC-A2.2: provider 切换 (ollama ↔ azure_openai) 正常工作
- [ ] AC-A2.3: Azure 不可用时自动回退到 Ollama
- [ ] AC-A3.1: PDF 可上传到 Azure Blob Storage

### 6.8 RAG-Project 迁移
- [ ] AC-A4.1: Azure 模块在 textbook-rag 中全部测试通过
- [ ] AC-A4.2: AzureSearchStrategy 可直接移入 RAG-Project
- [ ] AC-A4.3: AzureOpenAI Provider 可直接移入 RAG-Project
- [ ] AC-A4.4: RAG-Project 集成后端到端测试通过

### 6.9 v1.1 功能保留
- [ ] AC-R.1: v1.1 全部 20 题评估精度不退化
- [ ] AC-R.2: Citation 跳页 + bbox 高亮正常
- [ ] AC-R.3: Trace 面板 5+1 策略分层展示正常
- [ ] AC-R.4: ROS2 Node 可 import engine.rag 正常工作
- [ ] AC-R.5: 不配置 Azure 时系统完全以本地模式运行

---

## 7. 附录

### 7.1 v1.1 → v2.0 文件映射

| v1.1 文件 | v2.0 去向 | 改动 |
|----------|----------|------|
| backend/app/core/*  | engine/rag/* | 仅改 import |
| backend/app/routers/* | 删除, Payload 接管 | — |
| backend/app/services/* | 删除, Payload hooks 直调 Engine | — |
| backend/app/schemas/* | 删除, Payload Collections 替代 | — |
| backend/app/repositories/* | 删除, Payload ORM 替代 | — |
| backend/app/config.py | engine/config.py | 合并 |
| backend/app/database.py | 删除, Payload 管 PostgreSQL | — |
| backend/app/main.py | 删除, Payload + Next.js 启动 | — |
| scripts/rebuild_db.py | engine/ingest/chunk_builder.py | 拆分模块化 |
| scripts/batch_mineru.py | engine/ingest/pdf_parser.py | 拆分模块化 |
| scripts/rebuild_toc.py | engine/ingest/toc_extractor.py | 拆分模块化 |
| scripts/build_vectors.py | engine/index/vector_builder.py | 拆分模块化 |
| scripts/rebuild_topic_index.py | engine/index/topic_indexer.py | 拆分模块化 |
| frontend/ | payload/src/app/ + components/ | Next.js 重写 |
| ros2/ | ros2/ (不变, import 改为 engine.rag) | 仅改 import |

### 7.2 检索策略完整列表（v1.1 保留 + Azure 新增）

| # | 策略 | v2.0 位置 | 改动 | 来源 |
|---|------|----------|------|------|
| 1 | FTS5 BM25 | engine/rag/strategies/fts5_strategy.py | 仅改 import | v1.1 |
| 2 | Vector | engine/rag/strategies/vector_strategy.py | 仅改 import | v1.1 |
| 3 | TOC Heading | engine/rag/strategies/toc_strategy.py | 仅改 import | v1.1 |
| 4 | PageIndex | engine/rag/strategies/pageindex_strategy.py | 仅改 import | v1.1 |
| 5 | Metadata Filter | engine/rag/strategies/metadata_strategy.py | 仅改 import | v1.1 |
| 6 | **Azure AI Search** | engine/rag/strategies/azure_search.py | **新增** | RAG-Project |

### 7.3 LLM Provider 列表

| Provider | 模型 | 用途 | 默认 | 来源 |
|----------|------|------|------|------|
| ollama | qwen2.5, llama3, etc. | 本地推理 (开发/ROS2) | 有 Azure 时非默认 | v1.1 |
| azure_openai | gpt-4o | 云端推理 (生产) | 有 Azure 配置时默认 | RAG-Project |

### 7.4 RAG-Project 技术栈对照

| 组件 | textbook-rag v2.0 | RAG-Project | 兼容策略 |
|------|-------------------|-------------|----------|
| 后端框架 | Payload + Engine (FastAPI) | FastAPI | Engine API 直接移植 |
| LLM | Ollama + Azure OpenAI | Azure OpenAI | Provider 接口一致 |
| 检索 | 5 策略 + Azure Search | Azure AI Search | AzureSearchStrategy 移植 |
| 认证 | Payload Auth (JWT) | Entra ID + JWT | JWT 层兼容 |
| 存储 | PostgreSQL + ChromaDB | Cosmos DB + Azure Blob | 适配器模式切换 |
| 前端 | Next.js (Payload) | React + Vite | 组件可复用 |

### 7.5 迁移路线图

```
Phase 1-3: textbook-rag v2.0 (Payload + Engine + Azure)
    │
    │ Azure 模块测试通过
    ▼
Phase 4: 迁移到 RAG-Project
    ├── engine/rag/strategies/azure_search.py  → RAG-Project/backend/app/services/
    ├── engine/rag/providers/azure_openai.py   → RAG-Project/backend/app/services/ai_providers/
    ├── engine/rag/core.py (RAGCore)           → RAG-Project/backend/app/core/
    ├── engine/rag/strategies/* (5策略)         → RAG-Project/backend/app/services/
    └── engine/ingest/*                        → RAG-Project/backend/app/services/
```
