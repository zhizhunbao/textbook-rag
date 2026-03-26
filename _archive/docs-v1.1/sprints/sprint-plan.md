# Textbook RAG v1.1 — Sprint Plan

> **版本**: 1.1
> **作者**: Charlie (Tech Lead)
> **日期**: 2026-03-11
> **输入**: requirements.md, prd.md, system-architecture.md
> **总工期**: 3 周 (2026-03-12 ~ 2026-04-03)

---

## Sprint 概览

| Sprint | 时间 | 目标 | Story Points |
|--------|------|------|-------------|
| Sprint 1 | 3/12 ~ 3/19 | RAG Core + 检索 + Citation | 21 |
| Sprint 2 | 3/19 ~ 3/26 | Trace + Generation + 前端面板 | 18 |
| Sprint 3 | 3/26 ~ 4/03 | EcDev + ROS2 + 评估 + 报告 | 16 |

---

## Sprint 1: Foundation (3/12 ~ 3/19)

**目标**: RAG Core OOP 重构 + 5 种检索策略 + Citation 引擎

### STORY-001: RAG Core OOP 骨架

**Epic**: EPIC-07 (M6) | **Points**: 3 | **优先级**: P0
**依赖**: 无

**任务**:
- [ ] T-001.1: 创建 `backend/app/core/` 目录结构
- [ ] T-001.2: 实现 `RAGConfig` 和 `QueryConfig` 数据类
- [ ] T-001.3: 实现 `RAGCore` 类骨架（query 方法签名）
- [ ] T-001.4: 实现 `RetrievalStrategy` 抽象基类 + `StrategyRegistry`
- [ ] T-001.5: 现有 `query_service.py` 改为委托给 `RAGCore`

**DoD**: RAGCore 可实例化，query() 走通旧逻辑，v1.0 测试全部通过

### STORY-002: FTS5 BM25 策略模块化

**Epic**: EPIC-03 (M2) | **Points**: 2 | **优先级**: P0
**依赖**: STORY-001

**任务**:
- [ ] T-002.1: 从 `retrieval_service.py` 提取 FTS5 逻辑到 `FTS5BM25Strategy`
- [ ] T-002.2: 实现 `search()` 方法，返回 `list[ChunkHit]`
- [ ] T-002.3: 注册到 `StrategyRegistry`
- [ ] T-002.4: 新增 3 个 FTS5 策略单元测试

**DoD**: FTS5 作为独立策略可开关，结果与 v1.0 一致

### STORY-003: Vector 策略模块化

**Epic**: EPIC-03 (M2) | **Points**: 2 | **优先级**: P0
**依赖**: STORY-001

**任务**:
- [ ] T-003.1: 从 `retrieval_service.py` 提取 Vector 逻辑到 `VectorStrategy`
- [ ] T-003.2: 实现 `search()` 方法
- [ ] T-003.3: 注册到 `StrategyRegistry`
- [ ] T-003.4: 新增 3 个 Vector 策略单元测试

**DoD**: Vector 作为独立策略可开关，结果与 v1.0 一致

### STORY-004: TOC Heading Search 策略

**Epic**: EPIC-03 (M2) | **Points**: 3 | **优先级**: P0
**依赖**: STORY-001

**任务**:
- [ ] T-004.1: 从 `retrieval_lab/retrievers/toc_retriever.py` 移植算法
- [ ] T-004.2: 实现 `TOCHeadingStrategy.search()` — 词项重叠 + 子串 bonus
- [ ] T-004.3: 匹配 toc_entries → 找到对应 chunks
- [ ] T-004.4: 注册到 `StrategyRegistry`（默认开）
- [ ] T-004.5: 新增 3 个 TOC 策略单元测试

**DoD**: TOC 策略用 toc_entries 表做标题匹配，返回对应页码和 chunks

### STORY-005: PageIndex Structure 策略

**Epic**: EPIC-03 (M2) | **Points**: 3 | **优先级**: P0
**依赖**: STORY-001

**任务**:
- [ ] T-005.1: 从 `retrieval_lab/retrievers/pageindex_retriever.py` 移植算法
- [ ] T-005.2: 实现 `PageIndexStrategy.search()`
- [ ] T-005.3: MinerU `_middle.json` 解析节点树
- [ ] T-005.4: 注册到 `StrategyRegistry`（默认关）
- [ ] T-005.5: 新增 3 个 PageIndex 策略单元测试

**DoD**: PageIndex 策略使用文档结构树节点匹配，返回 node_id + 对应 chunks

### STORY-006: Metadata Filter 策略

**Epic**: EPIC-03 (M2) | **Points**: 2 | **优先级**: P0
**依赖**: STORY-001

**任务**:
- [ ] T-006.1: 实现 `MetadataFilterStrategy.search()`
- [ ] T-006.2: 支持 book/chapter/page/content_type/category 精确匹配
- [ ] T-006.3: 注册到 `StrategyRegistry`（默认关）
- [ ] T-006.4: 新增 3 个 Metadata 策略单元测试

**DoD**: Metadata 策略按结构化条件精确过滤 chunks

### STORY-007: RRF 融合增强 + 策略开关

**Epic**: EPIC-03 (M2) | **Points**: 2 | **优先级**: P0
**依赖**: STORY-002 ~ STORY-006

**任务**:
- [ ] T-007.1: `RetrievalOrchestrator` 根据 `enabled_strategies` 执行策略子集
- [ ] T-007.2: `RRFusion.fuse()` 接受 2~5 个结果列表
- [ ] T-007.3: `rrf_k` 可配置
- [ ] T-007.4: 1 种策略时跳过 RRF
- [ ] T-007.5: API `QueryRequest` 新增 `enabled_strategies`, `rrf_k`, `fetch_k` 字段

**DoD**: 任意策略组合均可正确执行和融合

### STORY-008: Citation 引擎

**Epic**: EPIC-04 (M3) | **Points**: 4 | **优先级**: P0
**依赖**: STORY-007

**任务**:
- [ ] T-008.1: 提取 `_sanitize_citations` 到 `CitationEngine.sanitize()`
- [ ] T-008.2: 实现 `CitationEngine.validate()` — 返回 valid/invalid 列表
- [ ] T-008.3: 实现 `CitationEngine.map_to_sources()` — `[N]` → source locators
- [ ] T-008.4: 实现 `CitationCleaningTrace` 记录
- [ ] T-008.5: 新增 3 个 Citation 单元测试

**DoD**: Citation 校验/清洗/映射完整，trace 中记录 raw vs cleaned

---

## Sprint 2: Transparency & Control (3/19 ~ 3/26)

**目标**: Trace 面板 + Quality 告警 + Generation 配置 + 前端面板

### STORY-009: TraceCollector + QualityChecker

**Epic**: EPIC-02 (M1) | **Points**: 3 | **优先级**: P0
**依赖**: STORY-007, STORY-008

**任务**:
- [ ] T-009.1: 实现 `TraceCollector` — 记录 retrieval/generation/citation 全链路
- [ ] T-009.2: 实现 `QualityChecker.check()` — 生成 warnings 列表
- [ ] T-009.3: 7 种 warning 规则（NO_FTS_HITS, NO_VECTOR_HITS, NO_TOC_HITS, NO_PAGEINDEX_HITS, NO_METADATA_HITS, NO_CONTEXT, NO_VALID_CITATIONS, CITATIONS_REMOVED）
- [ ] T-009.4: 每种 warning 带修复建议文本
- [ ] T-009.5: 新增 3 个 Quality 单元测试

**DoD**: 全链路 trace 完整记录，质量告警自动触发

### STORY-010: 多类别文档入库

**Epic**: EPIC-01 (M0) | **Points**: 2 | **优先级**: P0
**依赖**: 无

**任务**:
- [ ] T-010.1: `rebuild_db.py` 支持 `--category` 参数
- [ ] T-010.2: `books` 表新增 `category` 列
- [ ] T-010.3: `batch_mineru.py` 按类别目录处理
- [ ] T-010.4: 验证 EcDev 季报（12 个）入库成功

**DoD**: 教科书 + EcDev + 房地产三类别文档可入库，chunk 有 category 字段

### STORY-011: Generation 引擎 — Prompt 模板系统

**Epic**: EPIC-05 (M4) | **Points**: 3 | **优先级**: P1
**依赖**: STORY-001

**任务**:
- [ ] T-011.1: 定义 `PromptTemplate` 数据类（id, name, system_prompt, description）
- [ ] T-011.2: 内置 4 个模板: default / concise / detailed / academic
- [ ] T-011.3: `GenerationEngine` 根据 `prompt_template` 参数选择模板
- [ ] T-011.4: 高级模式：接受自定义 system_prompt 字符串覆盖模板
- [ ] T-011.5: API `GET /api/prompt-templates` 返回可用模板
- [ ] T-011.6: API `QueryRequest` 新增 `prompt_template`, `custom_system_prompt` 字段

**DoD**: 4 个预设模板可切换，高级模式支持自定义 prompt

### STORY-012: 前端 — Trace 面板

**Epic**: EPIC-02 (M1) | **Points**: 3 | **优先级**: P0
**依赖**: STORY-009

**任务**:
- [ ] T-012.1: 创建 `frontend/src/features/trace/` 目录
- [ ] T-012.2: `TracePanel` 组件 — tab/折叠式布局
- [ ] T-012.3: `RequestParams` 子组件 — 展示 question, top_k, fetch_k, filters
- [ ] T-012.4: `StrategyResults` 子组件 — 5 策略 + fused，每条 hit 有 rank/score/snippet
- [ ] T-012.5: `GenerationTrace` 子组件 — system_prompt/user_prompt 可折叠
- [ ] T-012.6: `CitationTrace` 子组件 — raw vs cleaned, valid/invalid list
- [ ] T-012.7: `QualityWarnings` 子组件 — warn/error 色块

**DoD**: Trace 面板完整展示全链路信息，告警以色块突显

### STORY-013: 前端 — Retrieval Config 面板

**Epic**: EPIC-03 (M2) | **Points**: 3 | **优先级**: P0
**依赖**: STORY-007

**任务**:
- [ ] T-013.1: 创建 `frontend/src/features/retrieval-config/`
- [ ] T-013.2: `TopKSlider` + `FetchKSlider` 组件
- [ ] T-013.3: `StrategyToggles` 组件 — 5 个 checkbox
- [ ] T-013.4: `RRFKInput` 组件
- [ ] T-013.5: `ContentTypeFilter` + `CategoryFilter` 组件
- [ ] T-013.6: 状态集成到 QueryContext，下次查询使用新参数

**DoD**: 所有检索参数通过面板可调，下次查询即时生效

### STORY-014: 前端 — Generation Config 面板

**Epic**: EPIC-05 (M4) | **Points**: 2 | **优先级**: P1
**依赖**: STORY-011

**任务**:
- [ ] T-014.1: 创建 `frontend/src/features/generation-config/`
- [ ] T-014.2: `PromptTemplateSelector` 组件 — 4 个预设 + 高级编辑
- [ ] T-014.3: `ModelSelector` 增强 — 显示模型信息
- [ ] T-014.4: 集成到 QueryContext

**DoD**: 前端可切换 prompt 模板、编辑 system prompt、选择模型

### STORY-015: 前端 — Citation 交互增强

**Epic**: EPIC-04 (M3) | **Points**: 2 | **优先级**: P0
**依赖**: STORY-008

**任务**:
- [ ] T-015.1: Citation `[N]` 点击 → PDF 跳页 + bbox 高亮（增强已有逻辑）
- [ ] T-015.2: 无效 citation 灰色删除线 + hover 提示
- [ ] T-015.3: 跨页 chunk "还有 N 个位置" 提示

**DoD**: 有效 citation 可点击跳页高亮，无效 citation 灰色不可点击

---

## Sprint 3: EcDev + ROS2 + Delivery (3/26 ~ 4/03)

**目标**: 报告/图表功能 + ROS2 集成 + 评估 + Final Report

### STORY-016: 表格数据提取 + 图表渲染

**Epic**: EPIC-06 (M5) | **Points**: 3 | **优先级**: P1
**依赖**: STORY-007

**任务**:
- [ ] T-016.1: 后端 — 解析 MinerU table content → 结构化 JSON（行列数据）
- [ ] T-016.2: 后端 — `POST /api/reports/generate` 端点
- [ ] T-016.3: 前端 — 安装 Recharts
- [ ] T-016.4: 前端 — `ChartRenderer` 组件（折线图/柱状图/饼图）
- [ ] T-016.5: 图表标题/轴标签/图例自动从 table header 生成

**DoD**: EcDev 季报表格数据可提取并渲染为前端图表

### STORY-017: 叙述性报告生成

**Epic**: EPIC-06 (M5) | **Points**: 3 | **优先级**: P1
**依赖**: STORY-011, STORY-016

**任务**:
- [ ] T-017.1: 报告专用 prompt 模板（Task 1 数据描述 + Task 2 分析叙述）
- [ ] T-017.2: 后端 — 报告生成逻辑，保留 citation
- [ ] T-017.3: 前端 — `ReportViewer` 组件（Markdown 渲染 + 内嵌图表）
- [ ] T-017.4: 前端 — `ReportsPanel` 集成到 RightPanel

**DoD**: 可生成 Task 1/2 风格报告，报告中有 citation + 嵌入图表

### STORY-018: ROS2 Node 集成

**Epic**: EPIC-07 (M6) | **Points**: 3 | **优先级**: P0
**依赖**: STORY-001

**任务**:
- [ ] T-018.1: 创建 `ros2/` 目录
- [ ] T-018.2: 实现 `ollama_publisher.py` — 继承 rclpy.node.Node
- [ ] T-018.3: import RAGCore，配置 qwen2.5:0.5b
- [ ] T-018.4: subscribe `words`, publish `ollama_reply`
- [ ] T-018.5: ROS2 parameters: model, db_path, knowledge_path
- [ ] T-018.6: 在 loaner laptop 上测试完整语音管道

**DoD**: 完整语音管道可演示: Whisper → RAG → gTTS

### STORY-019: 20 题混合评估

**Epic**: EPIC-08 (M7) | **Points**: 2 | **优先级**: P0
**依赖**: STORY-007, STORY-008

**任务**:
- [ ] T-019.1: 准备 20 题（12 教科书 + 8 EcDev）+ ground truth
- [ ] T-019.2: 实现评估脚本 `scripts/evaluate.py` — 批量运行 + 记录
- [ ] T-019.3: 人工评分 + top-3 文档相关性标注
- [ ] T-019.4: 计算 average accuracy，生成评估结果表格

**DoD**: 20 题评估完成，有 accuracy score 和结果表格

### STORY-020: Final Report + PPT

**Epic**: N/A | **Points**: 3 | **优先级**: P0
**依赖**: ALL

**任务**:
- [ ] T-020.1: 6-10 页 Final Report（Abstract, Introduction, Dataset, Method, Results, Challenges, Future Work, References）
- [ ] T-020.2: 10 分钟 PPT（Title, Intro, Method, Evaluation, Outcomes, Discussions）
- [ ] T-020.3: 打包代码 + 数据集 + 报告为 ZIP

**DoD**: 所有交付物打包就绪，可提交

### STORY-021: 集成测试 + 质量保证

**Epic**: N/A | **Points**: 2 | **优先级**: P0
**依赖**: STORY-001 ~ STORY-019

**任务**:
- [ ] T-021.1: v1.0 现有测试全部通过
- [ ] T-021.2: 每个模块 ≥ 3 个新增测试
- [ ] T-021.3: `uv run ruff check backend/` 通过
- [ ] T-021.4: `npx tsc --noEmit` 通过
- [ ] T-021.5: 端到端测试：问答 → citation → PDF 跳页

**DoD**: 所有自动化检查通过，端到端流程可演示

---

## 依赖关系图

```
STORY-001 (RAG Core 骨架)
    ├── STORY-002 (FTS5)
    ├── STORY-003 (Vector)
    ├── STORY-004 (TOC)    ├─→ STORY-007 (RRF + 开关) ─→ STORY-008 (Citation)
    ├── STORY-005 (PageIdx) │                               │
    ├── STORY-006 (Metadata)┘                               │
    │                                                        │
    ├── STORY-011 (Prompt 模板) ─→ STORY-014 (前端 Gen Config)
    │                           │
    │                           └→ STORY-017 (叙述报告)
    │
    └── STORY-018 (ROS2 Node)

STORY-007 ─→ STORY-009 (Trace + Quality) ─→ STORY-012 (前端 Trace)
         └─→ STORY-013 (前端 Retrieval Config)
         └─→ STORY-016 (表格→图表)

STORY-008 ─→ STORY-015 (前端 Citation 增强)

STORY-010 (多类别入库) — 独立，可并行

STORY-019 (评估) — 依赖 STORY-007 + STORY-008
STORY-020 (Report) — 依赖所有
STORY-021 (测试) — 依赖所有代码 story
```

---

## 风险应对

| 风险 | 应对 |
|------|------|
| Sprint 1 延期 | STORY-005 (PageIndex) 可降为 P1，Sprint 2 完成 |
| Sprint 3 时间不够 | STORY-017 (叙述报告) 可简化为仅 Task 1 风格 |
| ROS2 设备不可用 | STORY-018 先在本地模拟测试，设备到手后快速集成 |
| MinerU 表格解析差 | STORY-016 备选方案：手动提供 JSON 数据 |
