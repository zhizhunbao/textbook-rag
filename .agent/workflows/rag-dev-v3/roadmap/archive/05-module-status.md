# 模块现状 — Layout / UI / UX / Func 状态卡

> 各模块按 [module-manifest.md](../module-manifest.md) 的维度标注实现状态。

---

## 独立功能模块 (`features/<feature>/`)

> 以下模块有独立的路由页面，不属于 engine 子模块。

## `layout` — 应用骨架 ✅

```
Layout
✅  三栏布局              AppLayout.tsx (三栏: Sidebar + Header + Body)
✅  侧栏＋顶栏＋主体      AppSidebar + AppHeader + 主内容区

UI
✅  侧栏导航              AppSidebar (15 KB) — 多级路由菜单
✅  顶栏标题              AppHeader — 当前页标题
✅  用户菜单              UserMenu.tsx (6 KB) — 头像 + 下拉菜单

UX
✅  折叠展开              侧栏折叠/展开
✅  路径高亮              当前路由高亮
✅  一键登出              UserMenu 内登出按钮

Func
✅  路由框架              Next.js App Router (frontend) 路由组
✅  权限守卫              AuthProvider + ChatPage 守卫
✅  布局容器              SidebarLayout 共享组件
```

---

## `home` — 首页仪表盘 🚧 → Sprint 2

```
Layout
✅  卡片网格              Hero + Features (3卡) + How It Works (3步) + CTA
❌  数据概览              没有实时数据统计，只有静态展示

UI
❌  统计卡片              只有静态功能描述卡，无真实数据统计
✅  快捷入口              "开始提问" + "登录" CTA 按钮
❌  书籍列表              首页无书籍列表预览

UX
❌  一目了然              缺少数据聚合（书籍数量 / 对话次数 / 索引状态 等）
✅  快速跳转              跳转到 /chat 和 /login
❌  数据刷新              无数据，无刷新

Func
❌  数据汇总              无后端汇总 API
❌  书籍预览              首页不展示书籍
❌  状态总览              无系统状态组件
```

---

## `auth` — 登录认证 ✅

```
Layout
✅  居中表单              LoginForm 居中卡片
✅  全屏背景              渐变背景 + 装饰元素

UI
✅  邮箱密码              email + password 输入框
✅  登录按钮              登录提交按钮
✅  错误提示              错误消息展示

UX
✅  即时校验              前端表单校验
✅  回车提交              Enter 键提交
✅  加载反馈              登录按钮 loading 状态

Func
✅  凭证验证              Payload 内置 JWT 认证
✅  令牌存储              Cookie / Session 存储
✅  会话管理              AuthProvider + useAuth hook
```

---

## `seed` — 数据播种 🚧 → Sprint 2

```
Layout
✅  分类侧栏              模块分类侧栏 (user / llm / prompt)
✅  操作面板              每个 seed 模块的控制面板

UI
✅  模块卡片              各 seed 模块卡片
✅  执行按钮              一键 seed 按钮
❌  日志输出              无实时日志流

UX
✅  分类导航              按 seed 类型分类
✅  一键执行              单击执行 seed
❌  进度反馈              无 WebSocket 进度

Func
✅  用户预置              seed/users.ts 预置用户数据
✅  模型预置              seed/llms.ts 预置 LLM 配置
✅  提示预置              seed/prompt-modes.ts + prompt-templates.ts
❌  引擎同步              seed 后无自动同步到 Engine
```

---

## Engine 子模块 (`features/engine/<module>/`)

## `readers` — 文档阅读 / 解析 🚧 → Sprint 1 (P0)

```
Layout
✅  书架网格              LibraryPage — 卡片网格 + 表格视图
✅  详情抽屉              BookCard — 封面 + 元数据 + pipeline 状态

UI
✅  书籍卡片              BookCard.tsx — 封面 + 标题 + 作者 + 状态
✅  封面缩略              coverImage.sizes.thumbnail 缩略图
✅  状态标签              StatusBadge — pending / processing / indexed / error
✅  上传入口              UploadZone.tsx (drag-drop + file picker)           → Sprint 1
✅  删除按钮              deleteBook API + 批量删除 UI (LibraryPage toolbar) → Sprint 1
✅  编辑表单              BookEditDialog.tsx — 标题/作者/分类编辑          → Sprint 1

UX
✅  网格浏览              卡片(grid) / 表格(table) 双视图切换
✅  点击详情              点击进入 PDF 预览 / 选中开始对话
✅  PDF 预览              PdfViewer (33 KB) — 完整 PDF 阅读器
✅  上传反馈              UploadZone 进度条 + 状态反馈 (idle/uploading/success/error) → Sprint 1

Func
✅  PDF 读取              mineru_reader.py — MinerU PDF 解析
✅  MinerU 解析           MinerU Markdown + 图片输出
✅  元数据提取            cover_extractor.py — 封面 + 元数据
✅  目录提取              toc/extractor.py — TOC 提取
✅  上传→解析             useUpload hook → Payload afterChange → Engine ingest  → Sprint 1
✅  上传→摄取             afterChange hook → ingest_book() → ChromaDB      → Sprint 1
```

---

## `acquisition` — 数据导入全流程 ✅ (Sprint AQ)

> **一页 5 Tab 展示完整导入流程** — Sources → Import → Files → Pipeline → Vectors
> 替代原 `ingestion/` 前端模块，后者已完全删除。

```
Layout
✅  5-Tab 页面             ImportPage — SidebarLayout + 5 Tab (Sources/Import/Files/Pipeline/Vectors)
✅  共享书本侧栏           useBookSidebar (同 readers/LibraryPage 模式)

UI
✅  Sources Tab           SourcesTab — Web 数据源发现 + PDF 自动爬取 + 一键导入
✅  Import Tab            FileUploadCard + UrlImportCard — 2 栏并排
✅  Files Tab             MediaTab — Payload Media 文件详情
✅  Pipeline Tab          PipelineTab (92 KB) — 三栏: Stepper + Execute + Data Inspector
✅  Vectors Tab           VectorCheckTab — ChromaDB 向量统计 + 采样
✅  Parse Sub-tabs        ParsePreviewTab — Text/Image/Table/Equation/Discarded 5 个内容类型 sub-tab
✅  Classify Dialog       ClassifyDialog — LLM 分类建议 + 用户确认

UX
✅  实时 SSE 日志          Pipeline 运行时 SSE 实时日志流 + 步骤自动跟踪
✅  Data Inspector        点击步骤 IN/OUT 查看实时数据 (PDF 元数据、content_list、Chunks、ChromaDB)
✅  Batch Pipeline        未选书时显示批量 Pipeline 视图 + 并行执行
✅  一键删除              书本删除 + Engine 侧清理 (向量 + MinerU 输出)
✅  URL 参数持久           Tab 切换通过 ?tab= 持久化

Func
✅  PDF 爬取              sources.py — Playwright 深度爬取 + URL Pattern 生成
✅  文件上传              useFileUpload — Payload Media + afterChange hook
✅  URL 导入              useUrlImport — Engine /ingest 直连
✅  管线编排              pipeline.py — LlamaIndex IngestionPipeline (Parse → Ingest)
✅  向量统计              vectors.py — ChromaDB stats API
✅  解析预览              books.py /parse-stats — content_list.json 分页 + 过滤
```

---

## `ingestion` — 数据摄取 ⛔ 已迁移至 acquisition

> **前端目录已完全删除。** Pipeline Tab 和向量检查功能已迁移至 `acquisition/` 模块。
> 后端 `pipeline.py` / `ingest.py` 等引擎代码不变，由 acquisition 前端调用。

```
Layout
⛔  三栏布局              已迁移 → acquisition/PipelineTab.tsx
⛔  任务列表              已迁移 → acquisition/PipelineTab.tsx (BatchPipelineView)

UI
⛔  管线步骤              已迁移 → acquisition/PipelineTab.tsx (2-stage: Parse + Ingest)
⛔  进度条形              已迁移 → acquisition/PipelineTab.tsx (SSE + 进度条)
⛔  状态徽章              已迁移 → acquisition/PipelineTab.tsx (done/pending/error)

Func
✅  管线编排              pipeline.py — LlamaIndex IngestionPipeline (后端不变)
✅  分块切片              transformations.py — 分块转换器 (后端不变)
✅  向量入库              ChromaDB 向量存储 (后端不变)
✅  增量更新              reindex 模式支持 (后端不变)
```

---

## `chat` — RAG 对话 🚧 → Sprint 1 (P0) + Sprint 2 (Citation UX + 持久化)

```
Layout
✅  双栏布局              ChatPage — PDF 左 + 对话右 (可拖拽分隔)
✅  历史侧栏              chat/history/ — 会话历史列表
✅  问题侧栏              QuestionsSidebar — 右侧可折叠面板，按书分类推荐问题    ✅ Sprint 1

UI
✅  消息气泡              ChatPanel — AI / 用户气泡
✅  输入面板              底部输入框 + 发送按钮
✅  历史列表              ChatHistoryContext — 会话切换
✅  答案分块              AnswerBlock — 按语义段落分块渲染                        → Sprint 2 [S2-CX-FE-02] ✅
✅  行内引用 chip          CitationChip — 默认显示书名+页码                       → Sprint 2 [S2-CX-FE-02] ✅

UX
✅  流式输出              SSE streaming + useSmoothText 打字机效果              ✅ Sprint 1
✅  上下文切换            多文档切换 tab + 会话恢复 (?session=id)
✅  溯源引用              PdfViewer 文本高亮 + BboxOverlay 可视化
✅  推荐问题              WelcomeScreen HQ 问题卡片 + QuestionsSidebar 侧栏      ✅ Sprint 1
✅  Prompt 切换           PromptSelector — 下拉切换 Prompt 模式                  ✅ Sprint 1
✅  引用 hover 预览       CitationPopover — Markdown+KaTeX 完整原文预览           → Sprint 2 [S2-CX-FE-03] ✅
✅  段落级高亮            PdfViewer — click citation 高亮整段支撑原文             → Sprint 2 [S2-CX-FE-04] ✅

Func
✅  检索增强              query_engine/citation.py — 混合检索 + 来源注入
✅  对话管理              ChatHistoryContext — Payload API 为主 + localStorage 缓存（useChatHistory 已重构）→ Sprint 2 [S2-CH-FE-01] ✅
✅  来源追溯              citation_label + page_number + snippet 高亮
✅  聊天持久化            ChatSessions + ChatMessages Payload 集合 → Sprint 2 [S2-CH-BE-01] ✅
❌  全链编排              缺端到端管线配置 UI（参数暴露在 chat 界面）
🆕  全书搜索              新对话默认扫描全部 PDF，跳过选书步骤                  → Sprint Demo [DM-T1-01/02]
🆕  建议问题卡片          WelcomeScreen Ottawa 7 类 120+ 问题                    → Sprint Demo [DM-T3-01/02]
🆕  Citation Score         CitationChip 显示相关性分数徽章 (trustability)         → Sprint Demo [DM-T4-01]
🆕  暖色主题              DeepTutor #FAF9F6 米色 light 主题                      → Sprint Demo [DM-T2-01]
🗑️  answer/trace 删除    trace 可视化移至 evaluation 模块统一管理
```

> **✅ 持久化已完成**: 聊天历史持久化到 Payload `ChatSessions` + `ChatMessages` 集合，`useChatHistory` 已重构为 Payload API 为主 + localStorage 离线缓存。评估模块去重检测自动从 Payload 拉取历史提问。Sprint 2 [S2-CH-*] Epic 全部完成（4/4）。

---

## `retrievers` — 检索引擎 🚧 → Sprint 2

> **LlamaIndex 对齐**: 后端已完全对齐（`QueryFusionRetriever` + `BM25Retriever` + `VectorStoreIndex`）。Sprint 2 新增 Reranker 应使用 LlamaIndex `NodePostprocessor` 标准接口。

```
Layout
❌  配置表单              无独立配置页面（参数硬编码在后端）
❌  结果预览              无独立检索测试页面

UI
❌  参数滑块              无 top_k / fetch_k 等参数 UI
❌  策略选择              无 FTS/Vector/Hybrid 策略选择器
❌  重排选择              无 Reranker 策略选择器 (LLMRerank/SBERTRerank/None)  → Sprint 2 [S2-BE-05]
❌  片段列表              无独立检索结果列表（仅在 TracePanel 中展示）

UX
❌  即调即试              无独立检索调试入口
❌  对比查看              无策略对比功能
✅  相关高亮              PdfViewer + BboxOverlay 命中高亮

Func
✅  向量搜索              hybrid.py — ChromaDB 向量检索 ← LlamaIndex VectorStoreIndex.as_retriever()
✅  BM25 检索             hybrid.py — FTS 全文检索 ← llama_index.retrievers.bm25.BM25Retriever
✅  混合融合              hybrid.py — RRF 融合策略 ← llama_index.core.retrievers.QueryFusionRetriever
❌  重排精选              无 Reranker → Sprint 2 使用 LLMRerank / SentenceTransformerRerank  → [S2-BE-05]
```

---

## `response_synthesizers` — 回答合成 🚧 → Sprint 1 (P1)

```
Layout
✅  配置表单              SidebarLayout — Prompt 模式列表 + 详情面板
✅  输出预览              PromptEditorPage Preview tab — SSE 实时生成预览         ✅ Sprint 1

UI
✅  模板编辑              PromptEditorPage — name/description/icon/systemPrompt 可编辑  ✅ Sprint 1
✅  参数调节              无（只展示现有 Prompt 模式）
✅  结果展示              展示 prompt name / slug / description / systemPrompt

UX
✅  实时预览              Preview tab + SSE /engine/query/stream + custom_system_prompt  ✅ Sprint 1
✅  模板切换              侧栏切换不同 Prompt 模式
❌  质量对比              无 A/B 对比功能

Func
✅  提示拼装              citation.py — 来源注入 + 提示模板
✅  流式生成              后端 SSE + 前端 PromptEditor Preview tab 已接入          ✅ Sprint 1
✅  来源注入              citation.py — 带引用的回答生成
❌  格式标准              无统一输出格式规范 UI
```

---

## `llms` — 模型管理 ✅

```
Layout
✅  模型列表              /engine/llms (29 KB) — 模型列表 + 配置面板
✅  配置详情              每个模型的参数详情

UI
✅  模型卡片              模型卡片 + 状态指示
✅  参数表单              参数配置表单
✅  状态指示              在线/离线状态

UX
✅  一键切换              侧栏切换当前模型
✅  参数微调              useModels.ts (14 KB) 参数管理
✅  连通测试              模型连通性检测

Func
✅  多厂适配              resolver.py — Ollama / Azure OpenAI 适配
✅  参数管理              Llms Collection — 模型参数持久化
❌  令牌统计              无 token 用量统计
❌  故障降级              无自动 fallback 机制
```

---

## `query_engine` — 查询引擎 ✅ → Sprint 1 (P0) 已完成

```
Layout
✅  调试控制台            QueryEnginePage 三栏调试台 (查询配置 + 流式响应 + 来源)

UI
✅  查询输入              textarea + top_k 滑块 + 书籍筛选
✅  管线流程              流式/同步切换 + 实时光标
✅  结果展示              流式文本 + 来源卡片 + 统计栏

UX
✅  端到端试              sync/stream 双模式查询
❌  管线可视              无 (待 Sprint 3 evaluation 模块)
✅  耗时统计              FTS/Vector/TOC/Fused 统计栏

Func
✅  全链调试              后端 api.ts (9 KB) + query.py (SSE + sync)
✅  检索合成              citation.py — 检索 + 合成全链路
✅  上下文管              Queries Collection 记录查询
✅  结果封装              useQueryEngine hook + 来源卡片 UI
```

---

## `evaluation` — 统一评估中枢 🚧 → Sprint 2 (后端 ✅ + 前端 🚧) + Sprint 3 (图表+批量)

> **LlamaIndex 对齐**: evaluator.py 已完成 5 维评估 + 问题深度 + 去重。Sprint 2 后端 Story (EV-BE-01/02/03) 已完成，前端 EvaluationPage 三 Tab 布局已搭建（单条评估 + 问题质量 Tab 可用，批量评测 Tab 待 Sprint 3）。
>
> **数据来源问题**: 评估模块基于三类数据——① RAG 管线实时输出（query + response + source_nodes）、② 问题文本本身（认知深度）、③ 历史提问列表（去重）。其中 ③ 当前只能手动粘贴，需依赖 Sprint 2 [S2-CH-*] chat 持久化完成后自动从 Payload ChatMessages 拉取。

```
Layout
✅  评估面板              EvaluationPage — 三 Tab 布局（单条评估 + 问题质量 + 批量评测）  → Sprint 2 部分完成
❌  指标图表              无独立评估图表页  → Sprint 3

UI
✅  评分卡片              TraceStat — FTS/Vector/TOC/Context 统计卡
✅  5 维评分卡            EvaluationPage Tab 1 — 5 维评分条 + 评估反馈                  → Sprint 2 ✅
✅  深度标签              EvaluationPage Tab 2 — surface/understanding/synthesis badge   → Sprint 2 ✅
✅  重复检测卡            EvaluationPage Tab 2 — 相似度 + 最相似问题 + 建议             → Sprint 2 ✅
❌  雷达图表              无（Sprint 3 前端展示 5 维雷达图）
❌  对比表格              无

UX
❌  批量评测              Tab 3 占位 Coming Soon ← 后端已就绪  → Sprint 3
❌  历史对比              无历史评测对比  → Sprint 3
❌  导出报告              无
✅  去重自动化            EvaluationPage 自动从 Payload ChatMessages 加载用户历史问题 → Sprint 2 [S2-CH-FE-03] ✅

Func
✅  忠实度评              evaluator.py — FaithfulnessEvaluator ← LlamaIndex ✅
✅  相关性评              evaluator.py — RelevancyEvaluator ← LlamaIndex ✅
✅  正确性评              evaluator.py — CorrectnessEvaluator ← LlamaIndex ✅
✅  批量评估              evaluator.py — BatchEvalRunner ← LlamaIndex ✅
✅  上下文相关            evaluator.py — ContextRelevancyEvaluator ← LlamaIndex ✅          → Sprint 2 [S2-EV-BE-01] ✅
✅  答案相关              evaluator.py — AnswerRelevancyEvaluator ← LlamaIndex ✅           → Sprint 2 [S2-EV-BE-01] ✅
✅  问题深度              evaluator.py — QuestionDepthEvaluator ← CorrectnessEvaluator 自定义模板 ✅  → Sprint 2 [S2-EV-BE-01] ✅
✅  问题去重              evaluator.py — question_dedup() ← SemanticSimilarityEvaluator ✅          → Sprint 2 [S2-EV-BE-02] ✅
✅  质量+去重 API         evaluation.py 路由 — POST /evaluation/quality + /evaluation/dedup ✅       → Sprint 2 [S2-EV-BE-03] ✅
❌  反馈循环              feedback.py → Sprint 2 [S2-EV-BE-04] ← 聚合历史评估调参建议
❌  指标计算              前端无指标可视化  → Sprint 3
❌  报告汇总              无报告导出  → Sprint 3
```

---

## `question_gen` — 问题引擎 🚧 → Sprint 2 (P0 生成闭环) + Sprint 2 (P1 质量) + Sprint 3 (P2 多题型)

> 不是出题工具，是 chat 的上游供给系统。
>
> **LlamaIndex 对齐**: ⚠️ 此模块是项目中最大的"造轮子"模块。generator.py 直接用 `chromadb.collection.get()` 绕过 LlamaIndex 的 `VectorStoreIndex`，手写 JSON prompt + parse，评分逻辑重复了 `CorrectnessEvaluator`。Sprint 2 质量模块应复用 LlamaIndex 评估器；Sprint 3 多题型扩展时应将数据访问层迁移到 VectorStoreIndex。LlamaIndex 参考：`RagDatasetGenerator`（`llama_index.core.llama_dataset.generator`）。

```
Layout
✅  书籍选择              GenerationPanel 三级筛选 (Category → Books → Chapters)      → Sprint 2 [S2-FE-09] ✅
✅  生成入口              QuestionsPage 工具栏 Generate 按钮 + 可折叠面板            → Sprint 2 [S2-FE-10] ✅

UI
✅  三级选择器            分类别 → 分书 → 分章节 筛选                                → Sprint 2 [S2-FE-09] ✅
✅  生成按钮              GenerationPanel + count 滑块 + GenerationProgress          → Sprint 2 [S2-FE-09] ✅
✅  题目卡片              QuestionCards.tsx — Markdown 渲染 + 评分
✅  进度动画              GenerationProgress.tsx — 四步动画 + 计时器

UX
✅  选书生成              GenerationPanel 调用 generateQuestions API                   → Sprint 2 [S2-FE-10] ✅
✅  批量浏览              卡片(grid) / 表格(table) 切换 + 全部/筛选
❌  难度筛选              有 scoreDifficulty 展示，但无独立筛选器               → Sprint 3

Func
🚧  自动出题              generator.py 支持 book_ids + category + chapter_key ⚠️ 直接用 ChromaDB API 绕过 LlamaIndex  → Sprint 2 ✅
🚧  生成 API              questions.py 路由支持 book_ids/category/chapter_key            → Sprint 2 ✅
🚧  前端 API              api.ts 默认端口 8001，参数已对齐                               → Sprint 2 ✅
❌  多类题型              当前只有开放题，无选择题/填空题 → Sprint 3 (含 LlamaIndex 数据层迁移)
❌  知识覆盖              无 chapter 级覆盖率统计                  → Sprint 3
❌  去重校验              无重复检测 → Sprint 2 evaluation/ 统一中枢 [S2-EV-BE-02]
✅  问题推荐              suggest.py + useSuggestedQuestions + SuggestedQuestions.tsx → Sprint 1 ✅
❌  质量评估              无问题深度分级 → Sprint 2 evaluation/ 统一中枢 [S2-EV-BE-01] QuestionDepthEvaluator
❌  重复检测              无向量相似度匹配 → Sprint 2 evaluation/ 统一中枢 [S2-EV-BE-02] SemanticSimilarityEvaluator
```

---

## `report` — 报告生成 🆕 → Sprint Demo (MVP) + Sprint 8 (完整版)

> Sprint Demo 实现 MVP：基于聊天历史生成 Markdown 报告。Sprint 8 扩展为完整的多角色报告生成引擎。
> 对应 Project Brief: "produce periodic narrative summaries, tables, and graphs"

```
Layout
🆕  双栏布局              ReportPage — 左侧报告列表 + 右侧 Markdown 预览    → Sprint Demo [DM-T5-03]
❌  生成向导              无（Sprint 8 三步向导 [S8-FE-01]）
❌  图表区域              无（Sprint 8 Recharts 交互图表 [S8-FE-05]）

UI
🆕  报告列表              卡片（标题 + 日期 + 状态）                          → Sprint Demo [DM-T5-03]
🆕  生成按钮              从聊天 session 生成报告                              → Sprint Demo [DM-T5-03]
❌  模板卡片              角色/模板选择卡片                                    → Sprint 8 [S8-FE-01]
❌  导出按钮              PDF / Markdown 导出                                  → Sprint 8 [S8-FE-03]

UX
🆕  一键生成              选择 session → 生成报告                              → Sprint Demo [DM-T5-02]
❌  流式进度              StreamEvent 实时进度                                  → Sprint 8 [S8-BE-11]
❌  引用跳转              报告内引用 → 对话/PDF 跳转                           → Sprint 8 [S8-FE-02]

Func
🆕  Reports 集合          Payload CMS 集合（user/title/content/sessionId）     → Sprint Demo [DM-T5-01]
🆕  报告生成 API          POST /engine/report/generate + GET /list + GET /{id} → Sprint Demo [DM-T5-02]
❌  模板 Registry         多角色模板管理                                        → Sprint 8 [S8-BE-02]
❌  数据收集器            多源数据聚合（chat + eval + sources）                  → Sprint 8 [S8-BE-04]
❌  可视化引擎            code_executor 图表生成                                → Sprint 8 [S8-BE-07]
❌  PDF 导出              Markdown → PDF（含图表）                              → Sprint 8 [S8-BE-12]
```

---

## 纯后端模块 → 需补前端 UI

## `chunking` — 文本分块 ❌ 缺前端 → Sprint 4

```
Func
✅  语义切分              chapter_extractor.py — 按章节切分
❌  标题层级              无层级可视化
❌  重叠窗口              后端有，前端无调参入口
❌  块级元数据            后端有，前端无展示

需要建
❌  API 路由              engine_v2/api/routes/chunking.py
❌  前端模块              features/engine/chunking/
❌  分块预览 UI           可视化分块结果 + 参数调整
```

---

## `toc` — 目录提取 ❌ 缺前端 → Sprint 3

```
Func
✅  层级识别              extractor.py — 多级标题识别 (9.3 KB)
✅  页码映射              pdf_page 映射
✅  标题清洗              标题文本规范化
✅  结构序列              层级树结构输出

需要建
❌  API 路由              engine_v2/api/routes/toc.py
❌  前端模块              features/engine/toc/
❌  目录树预览 UI         层级树展示 + 页码跳转
```

---

## `embeddings` — 向量嵌入 ❌ 缺前端 → Sprint 4

```
Func
✅  模型加载              resolver.py — 模型解析
✅  批量编码              嵌入模型批量调用
❌  维度配置              前端无维度选择
❌  缓存复用              前端无缓存状态展示

需要建
❌  API 路由              engine_v2/api/routes/embeddings.py
❌  前端模块              features/engine/embeddings/
❌  嵌入管理 UI           模型切换 + 维度配置 + 缓存监控
```

---

## `access` — 权限控制 ❌ 缺前端 → Sprint 4

```
Func
✅  角色鉴权              isAdmin.ts
✅  管理独占              isEditorOrAdmin.ts
✅  编辑可写              isEditorOrAdmin.ts
✅  属主可改              isOwnerOrAdmin.ts

需要建
❌  前端模块              features/access/ 或 settings 页面扩展
❌  权限管理 UI           角色列表 + 权限矩阵可视化
```
