# Textbook RAG v2.0 — 产品需求文档 (PRD)

## 文档信息

- 版本: 2.0
- 作者: Alice (PM)
- 日期: 2026-03-21
- 状态: Draft
- 输入: `docs/v2.0/requirements/requirements.md`, `docs/v1.1/requirements/prd.md`
- 迁移目标: RAG-Project (Ottawa GenAI Research Assistant)

---

## 1. 产品概述

### 1.1 产品愿景

将课程级 RAG 系统升级为**产品级内容管理 + AI 检索平台**，为内容管理引入可视化后台，为入库流程引入自动化管道，同时**完整保留 v1.1 的全部 RAG 能力**。

### 1.2 目标用户

| 角色 | 核心场景 | v2.0 新增能力 | Payload 角色 |
|------|----------|-------------|-------------|
| 学生 | 教材问答 + 验证来源 | 登录查询，查看历史 | reader |
| TA / 教师 | 排查回答质量 | **上传新教材** + 管理内容 | editor |
| NLP 教授 | 评估 RAG | Admin 全权限 | admin |
| EcDev 分析师 | 报告/图表 | **上传新季报** + 分析历史 | editor |
| 系统管理员 | (v1.1 无) | **用户管理 + 部署 + 监控** | admin |

### 1.3 核心价值

1. **v1.1 能力全保** — 5 策略检索 + RRF + Citation + Trace + Quality（不退化）
2. **内容管理可视化** — Payload Admin Panel 替代 CLI 脚本
3. **上传即入库** — PDF 上传 → 自动 MinerU 解析 → 自动向量化 → 可查询
4. **用户系统** — 认证 + 角色权限 + 查询历史
5. **API 自动化** — REST + GraphQL 自动生成，零手写
6. **一键部署** — Docker Compose 全栈启动
7. **Azure 双模式** — Azure AI Search (第 6 策略) + GPT-4o，本地/云端可切换
8. **迁移就绪** — Azure 模块测试后直接移植到 RAG-Project

---

## 2. Epic 与用户故事

### EPIC-P1: Payload CMS 基础设施（P0）

#### US-P01: 内容管理后台

作为**教师**，
我想要通过 Web Admin 面板管理书籍、章节和数据块，
以便不再需要跑 CLI 脚本来添加新教材。

**优先级**: P0

**验收标准**:
- Given 登录 Payload Admin Panel
- When 进入 Books 列表
- Then 可以创建/编辑/删除 Book，看到 title, category, status, chunkCount
- And 可以关联查看该 Book 的所有 Chapters 和 Chunks

#### US-P02: 自动生成 API

作为**前端开发者**，
我想要所有 Collection 自动拥有 REST 和 GraphQL API，
以便不需要手写 FastAPI routers + Pydantic schemas。

**优先级**: P0

**验收标准**:
- Given Books Collection 已定义
- When 访问 `/api/books`
- Then 返回分页的 Book 列表，支持 filter/sort/pagination
- And `/api/books/{id}` 返回单个 Book 详情
- And GraphQL 端点同样可用

---

### EPIC-P2: 用户认证与权限（P0）

#### US-P03: 用户注册与登录

作为**学生**，
我想要注册账号并登录系统，
以便系统记住我的查询历史。

**优先级**: P0

**验收标准**:
- Given 访问注册页面
- When 填写邮箱和密码注册
- Then 账号创建成功，自动登录
- And 获得 JWT token，后续请求携带 token

#### US-P04: 角色权限控制

作为**系统管理员**，
我想要不同角色有不同权限级别，
以便 reader 不能误改内容数据。

**优先级**: P0

**验收标准**:
- Given 用户角色为 reader
- When 尝试创建/修改/删除 Book
- Then 返回 403 Forbidden
- And reader 只能执行查询和查看自己的 QueryLogs

---

### EPIC-P3: 自动化入库管道（P0）

#### US-P05: 上传即入库

作为**教师**，
我想要上传 PDF 后系统自动完成解析、分块、向量化整个流程，
以便不需要手动运行 3 个脚本。

**优先级**: P0

**验收标准**:
- Given 在 Admin Panel 创建 Book 并上传 PDF
- When 保存 Book
- Then 系统自动创建 PipelineTask (status=queued)
- And Engine 自动执行: MinerU 解析 → 分块 → 向量化
- And Book status 从 pending → processing → indexed
- And Book chunkCount 更新为实际 chunk 数量

#### US-P06: 入库进度追踪

作为**教师**，
我想要看到入库任务的实时进度，
以便知道还需要等多久。

**优先级**: P0

**验收标准**:
- Given 入库任务正在执行
- When 查看 Admin → PipelineTasks
- Then 看到 progress 0-100%，status (queued/running/done/error)
- And 失败时看到 error 信息和日志

#### US-P07: 入库失败处理

作为**系统管理员**，
我想要入库失败时看到详细错误并能重试，
以便快速定位和修复问题。

**优先级**: P0

**验收标准**:
- Given 入库任务失败 (status=error)
- When 查看任务详情
- Then 看到 error 文本和 log 内容
- And Book status 显示 error
- And 可以手动触发重试（重新创建 PipelineTask）

---

### EPIC-P4: Engine 模块化重构（P0）

#### US-P08: 脚本 → 模块拆分

作为**开发者**，
我想要 scripts/ 中的 28KB rebuild_db.py 拆分为可复用模块，
以便管道的每个步骤可以独立测试和调用。

**优先级**: P0

**验收标准**:
- Given engine/ingest/ 包含 pdf_parser, chunk_builder, toc_extractor
- When 调用 `chunk_builder.build_chunks(mineru_output)`
- Then 返回与 v1.1 rebuild_db.py 完全一致的 chunk 数据
- And 每个模块有独立的单元测试

#### US-P09: RAG Core 零修改平移

作为**开发者**，
我想要 v1.1 的 RAG Core 在 engine/rag/ 中原封不动运行，
以便所有 RAG 能力不退化。

**优先级**: P0

**验收标准**:
- Given engine/rag/ 包含 v1.1 全部 core 文件
- When 运行 v1.1 的全部测试用例
- Then 100% 通过，查询结果完全一致
- And 唯一改动是 import 路径

---

### EPIC-P5: 数据迁移（P0）

#### US-P10: SQLite → PostgreSQL

作为**开发者**，
我想要把 v1.1 的 164MB SQLite 数据迁移到 PostgreSQL，
以便 Payload 可以管理所有数据。

**优先级**: P0

**验收标准**:
- Given 迁移脚本运行完成
- When 在 Payload Admin 查看 Books
- Then 看到与 v1.1 完全一致的书籍列表和分类
- And Chunks 数量匹配
- And 迁移脚本支持重复运行（幂等）

---

### EPIC-P6: 前端迁移（P1）

#### US-P11: React SPA → Next.js

作为**用户**，
我想要在新的 Next.js 前端获得与 v1.1 完全一致的体验，
以便升级对用户透明。

**优先级**: P1

**验收标准**:
- Given 开 Next.js 主页
- When 看到 UI
- Then 左栏 PDF Viewer + 右栏 Chat Panel 布局与 v1.1 一致
- And Trace 面板、配置面板正常工作
- And Citation 点击跳页 + bbox 高亮正常

#### US-P12: Admin Panel 集成

作为**管理员**，
我想要在 /admin 路径访问 Payload 管理后台，
以便管理内容和用户。

**优先级**: P1

**验收标准**:
- Given 以 admin 角色登录
- When 访问 /admin
- Then 看到 Payload Admin Panel，可管理所有 Collections

---

### EPIC-P7: Docker 部署（P1）

#### US-P13: 一键启动全栈

作为**开发者**，
我想要 `docker compose up` 一键启动 Payload + Engine + PostgreSQL + Ollama，
以便新部署零配置。

**优先级**: P1

**验收标准**:
- Given 仅有 Docker 和 .env 文件
- When 运行 `docker compose up`
- Then 5 分钟内全栈可用: 前端 + Admin + Engine + DB + LLM
- And 可以上传 PDF 并执行查询

---

### EPIC-A1: Azure AI Search 策略（P0）

#### US-A01: Azure AI Search 作为第 6 检索策略

作为**开发者**，
我想要新增 Azure AI Search 作为第 6 个可插拔检索策略，
以便利用 Azure 云端语义检索能力增强查询质量。

**优先级**: P0

**验收标准**:
- Given 配置了 AZURE_SEARCH_ENDPOINT, KEY, INDEX
- When 前端开启 "Azure AI Search" 策略开关
- Then 查询结果包含 Azure Search 的 hits
- And 参与 RRF 融合，Trace 面板正常展示
- And 不配置 Azure 时，该策略不出现在开关列表中

---

### EPIC-A2: Azure OpenAI GPT-4o（P0）

#### US-A02: 双模式 LLM 生成

作为**开发者**，
我想要在 Ollama 本地模型和 Azure OpenAI GPT-4o 之间切换，
以便在本地开发和云端生产环境灵活切换。

**优先级**: P0

**验收标准**:
- Given 配置了 AZURE_OAI_ENDPOINT, KEY, DEPLOYMENT
- When 前端选择 provider = "azure_openai"
- Then 使用 GPT-4o 生成回答
- And Trace 面板显示实际使用的 provider 和 model
- And Azure 不可用时自动回退到 Ollama，显示 warning

---

### EPIC-A3: RAG-Project 迁移（P1）

#### US-A03: Azure 模块移植到 RAG-Project

作为**开发者**，
我想要将验证过的 Azure 模块移植到 RAG-Project，
以便在生产环境中部署 Ottawa GenAI Research Assistant。

**优先级**: P1

**验收标准**:
- Given textbook-rag 中 Azure 模块全部测试通过
- When 将 AzureSearchStrategy + AzureOpenAI Provider 移入 RAG-Project
- Then RAG-Project 的 chat 和 search 功能正常工作
- And RAG-Project 的现有测试全部通过

---

### EPIC-R: v1.1 功能保留（全部）

> 以下 v1.1 Epic 的所有 User Story 和验收标准**原封不动保留**，不在此重复列出。

| v1.1 Epic | 说明 | v2.0 状态 |
|-----------|------|----------|
| EPIC-01 (M0) | 数据入库 + 多类别 | 逻辑保留，运行在 engine/ingest |
| EPIC-02 (M1) | 全链路可观测性 | 保留，engine/rag + 前端 |
| EPIC-03 (M2) | 检索可控性 (5 策略) | 保留，engine/rag/strategies |
| EPIC-04 (M3) | Citation 可验证性 | 保留，engine/rag + 前端 |
| EPIC-05 (M4) | 生成可优化性 | 保留，engine/rag |
| EPIC-06 (M5) | 报告与图表 (EcDev) | 保留，engine/rag + 前端 |
| EPIC-07 (M6) | ROS2 语音集成 | 保留，ros2/ import engine.rag |
| EPIC-08 (M7) | 评估 | 保留 |

---

## 3. 功能需求 — MoSCoW 分类

### 3.1 Must Have (P0)

| ID | 功能 | Epic | User Story |
|----|------|------|-----------|
| FR-P01 | Payload Collections (Books, Chapters, Chunks, PipelineTasks) | EPIC-P1 | US-P01 |
| FR-P02 | 自动生成 REST + GraphQL API | EPIC-P1 | US-P02 |
| FR-P03 | 用户注册/登录 (JWT) | EPIC-P2 | US-P03 |
| FR-P04 | 角色权限 (admin/editor/reader) | EPIC-P2 | US-P04 |
| FR-P05 | 上传即入库管道 | EPIC-P3 | US-P05 |
| FR-P06 | 入库进度追踪 | EPIC-P3 | US-P06 |
| FR-P07 | 入库失败处理 | EPIC-P3 | US-P07 |
| FR-P08 | scripts → engine 模块化 | EPIC-P4 | US-P08 |
| FR-P09 | RAG Core 零修改平移 | EPIC-P4 | US-P09 |
| FR-P10 | SQLite → PostgreSQL 迁移 | EPIC-P5 | US-P10 |
| FR-A01 | Azure AI Search 第 6 策略 | EPIC-A1 | US-A01 |
| FR-A02 | Azure OpenAI GPT-4o 双模式 | EPIC-A2 | US-A02 |

### 3.2 Should Have (P1)

| ID | 功能 | Epic | User Story |
|----|------|------|----------|
| FR-P11 | React → Next.js 前端迁移 | EPIC-P6 | US-P11 |
| FR-P12 | Payload Admin Panel | EPIC-P6 | US-P12 |
| FR-P13 | Docker Compose 部署 | EPIC-P7 | US-P13 |
| FR-A03 | Azure Blob Storage | EPIC-A1 | — |
| FR-A04 | RAG-Project 迁移 | EPIC-A3 | US-A03 |
| FR-P14 | QueryLogs Collection | EPIC-P1 | US-P01 |

### 3.3 Could Have (P2)

| ID | 功能 | 说明 |
|----|------|------|
| FR-P15 | 批量入库（目录扫描） | 类似 v1.1 batch_mineru 但自动化 |
| FR-P16 | 入库调度（定时任务） | 定期检查新 PDF |
| FR-P17 | 多语言 Admin | Payload i18n |

### 3.4 Won't Have (v2.0)

- 付费系统
- 流式输出 (streaming)
- 多模态检索
- Cosmos DB 集成 (迁移到 RAG-Project 后再做)
- Entra ID 认证 (迁移到 RAG-Project 后启用)
- 移动端
- RAG Core 逻辑任何修改

---

## 4. 非功能需求

| ID | 类型 | 要求 | v1.1 对比 |
|----|------|------|-----------|
| NFR-01 | 性能 | Payload → Engine 延迟 < 50ms | 新增 |
| NFR-02 | 性能 | 入库管道 100 页 PDF < 5 分钟 | 新增 |
| NFR-03 | 性能 | v1.1 查询延迟不退化 | 保留 |
| NFR-04 | 兼容 | v1.1 RAG Core 逻辑零修改 | 新增 |
| NFR-05 | 兼容 | v1.1 全部测试通过 | 保留 |
| NFR-06 | 安全 | Payload Auth JWT/Session | 新增 |
| NFR-07 | 安全 | 角色权限控制 | 新增 |
| NFR-08 | 安全 | Engine API 仅内部访问 | 新增 |
| NFR-09 | 安全 | v1.1 安全措施保留 | 保留 |
| NFR-10 | 可用 | Admin Panel 开箱即用 | 新增 |
| NFR-11 | 可用 | v1.1 UI 体验不退化 | 保留 |
| NFR-12 | 质量 | engine/ + payload/ 独立包 | 新增 |
| NFR-13 | 部署 | Docker Compose 一键启动 | 新增 |

---

## 5. 里程碑与时间线

### Phase 1: Payload 基础 + 数据迁移（1-2 周）

| 工作 | 估时 |
|------|------|
| 初始化 Payload + 定义 Collections | 1 天 |
| 数据迁移 SQLite → PostgreSQL | 1 天 |
| 用户认证 + 角色权限 | 1 天 |
| 验证自动 API 工作 | 0.5 天 |

### Phase 2: Engine 重构 + 管道自动化（2-3 周）

| 工作 | 估时 |
|------|------|
| core/ → engine/rag/ 平移 + 修改 import | 1 天 |
| scripts/ → engine/ingest/ + engine/index/ 拆分 | 3 天 |
| Engine API (query + ingest endpoints) | 1 天 |
| Payload afterChange hook + 进度追踪 | 1 天 |
| payload_client adapter | 1 天 |
| 测试全部通过 | 1 天 |

### Phase 3: 前端 + 部署（1-2 周）

| 工作 | 估时 |
|------|------|
| 前端组件迁移到 Next.js | 3 天 |
| Docker Compose 编排 | 1 天 |
| 删除旧代码, 清理 | 1 天 |
| 端到端测试 | 1 天 |

### Phase 4: Azure 集成 + RAG-Project 迁移（1-2 周）

| 工作 | 估时 |
|------|------|
| AzureSearchStrategy 实现 + 测试 | 2 天 |
| AzureOpenAI Provider 实现 + 测试 | 1 天 |
| 双模式切换 + 回退机制 | 1 天 |
| Azure Blob 适配器 | 0.5 天 |
| 迁移到 RAG-Project + 集成测试 | 2 天 |
| RAG-Project 端到端验证 | 1 天 |

---

## 6. 风险与依赖

### 6.1 风险

| 风险 | 概率 | 影响 | 缓解 |
|------|------|------|------|
| Payload 3.x 学习曲线 | 中 | 中 | 先用 blank 模板最小化配置 |
| SQLite FTS5 → PG 全文搜索性能差异 | 低 | 高 | Phase 1 先 PG+SQLite 双轨，保留 FTS5 |
| 28KB rebuild_db.py 拆分引入 bug | 中 | 中 | 拆分后对比输出与 v1.1 一致 |
| 前端迁移丢失交互细节 | 中 | 中 | 逐组件迁移，每步 E2E 测试 |
| ROS2 import 路径变更 | 低 | 低 | 简单改 import，快速验证 |
| Azure API 配额/延迟 | 中 | 中 | 本地 Ollama 回退机制 |
| RAG-Project 接口不兼容 | 低 | 高 | 提前对齐 Settings/ChatService 接口 |

### 6.2 外部依赖

- Payload CMS 3.x (npm)
- PostgreSQL 15+
- Docker + Docker Compose
- Ollama (不变)
- **Azure OpenAI** (GPT-4o deployment)
- **Azure AI Search** (Semantic configuration)
- **Azure Blob Storage** (可选，文件存储)
- RAG-Project 代码库 (github.com/Teegee0/RAG-Project)
- ChromaDB (不变)
- MinerU (不变)
