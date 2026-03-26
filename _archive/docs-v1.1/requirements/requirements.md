# Textbook RAG v1.1 — 需求规格说明

> **版本**: 1.1
> **作者**: Product Manager
> **日期**: 2026-03-11
> **前置**: v1.0 已完成并通过全部 10 阶段 Review
> **Deadline**: 2026-04-03

---

## 1. 项目概述

### 1.1 愿景

构建一个**统一的文档 RAG 平台**，将两个共享底层能力的项目合并：

- **Textbook RAG**（NLP 课程作业 CST8507）— 教科书领域的问答 + 深度溯源
- **EcDev Research Assistant**（Ottawa 经济发展部）— 经济报告的问答 + 报告/图表生成

核心价值：**查的准、定位准、全透明可控**。

### 1.2 目标

| 序号 | 目标 | 成功标准 |
|------|------|----------|
| 1 | **检索精度** | 20 题评估中 top-3 retrieved documents 相关性 ≥ 80% |
| 2 | **源文定位** | Citation 点击后 PDF 跳页 + bbox 高亮，位置误差 < 1px |
| 3 | **全透明可控** | 所有检索策略可追踪、可开关、参数可调，质量告警自动触发 |
| 4 | **多场景交付** | Web UI + ROS2 Node 共享同一个 RAG Core |

### 1.3 背景

v1.0 交付了可用的教科书 RAG 系统（双栏 UI、混合检索、Ollama LLM、citation 跳页），
但存在四个核心问题：

1. **不知道哪里坏了** — 检索无命中、citation 无效时无诊断手段
2. **无法调参** — top_k / fetch_k / 策略权重硬编码
3. **citation 不可靠** — LLM 生成的 `[N]` 可能指向错误 source
4. **仅限教科书** — 不支持 EcDev 季报等多类别文档

同时，NLP 课程作业要求 RAG 系统以 OOP 形式实现，并集成到 ROS2 语音管道中。

> **Ref**: Krug, *Don't Make Me Think*, Ch9 — v1.0 缺乏可观测性，等效于没有 usability testing 的系统。

### 1.4 范围

**In Scope (v1.1)**:
- 8 个模块的完整实现（见第 3 节）
- 向后兼容 v1.0 API
- 多类别文档库支持
- ROS2 Node 集成
- 20 题混合评估
- 6-10 页报告 + 10 分钟演示

**Out of Scope (v1.1)**:
- 多用户 / 鉴权
- RAG 管道的流式输出 (streaming)
- 多模态检索（图表 / 公式检索）
- Statistics Canada API 集成（Phase 2）
- 报告导出（PDF/Word）— 先前端渲染

---

## 2. 用户与角色

### 2.1 用户画像

| 角色 | 描述 | 技术水平 | 使用频率 | 核心目标 |
|------|------|----------|----------|----------|
| 学生 | 学习 AI/ML/NLP 的学生 | 中 | 每日 | 问答 + 验证来源 |
| TA / 教师 | 需要核对教材出处 | 中高 | 每周 | 排查回答质量、调参 |
| NLP 教授 | 评分 Assignment 2 | 高 | 一次性 | 评估 RAG 实现质量 |
| EcDev 分析师 | Ottawa 经济发展部门 | 低中 | 每周 | 从季报中提取数据、生成报告 |
| 项目评审员 | 评估系统健康度 | 低 | 一次性 | 直观了解系统质量 |

### 2.2 使用场景

**场景 1: 学生验证答案来源**（Web）
1. 提问 → 看到带 citation 的回答
2. 点击 `[2]` → PDF 跳到对应页 + bbox 高亮
3. 确认答案确实来自教科书

**场景 2: TA 排查回答质量**（Web）
1. 打开 Trace 面板 → 看到 FTS 0 hits
2. 看到 Quality warning: `NO_FTS_HITS`
3. 切到 Retrieval 面板 → 关闭 FTS，只用 vector → 拿到正确结果

**场景 3: EcDev 分析师生成报告**（Web）
1. 选择 "经济发展季报" 文档类别
2. 提问 "2023 年 Q3 建筑许可趋势" → 系统检索到相关表格数据
3. 前端用 Chart 组件渲染趋势图
4. 系统生成叙述性报告（IELTS Task 1/2 风格）

**场景 4: 语音问答**（ROS2）
1. 用户对机器人说话 → Whisper 转文字 → publish to `words` topic
2. ROS2 RAG Node 接收 → RAG Core 检索 + 生成回答
3. 回答 publish to `ollama_reply` → gTTS 转语音播放

**场景 5: NLP 教授评分**
1. 查看 20 题评估结果 → 每题有人工评分 + top-3 文档相关性
2. 运行 Part 1 完整 Web UI 演示
3. 运行 Part 2 ROS2 语音管道演示

---

## 3. 功能需求 — 模块化架构

### 3.0 架构总览

```
┌─────────────────────────────────────────────────────────────┐
│                   Delivery Targets                          │
│  ┌─────────────────────┐  ┌──────────────────────────────┐  │
│  │ Web UI (React/TS)   │  │ ROS2 Node (Python)           │  │
│  │ PDF + Chat + Trace  │  │ Whisper → RAG → gTTS         │  │
│  │ Reports + Charts    │  │ subscribe: words              │  │
│  └─────────┬───────────┘  │ publish: ollama_reply         │  │
│            │              └──────────────┬───────────────┘  │
│            │                             │                  │
│            ▼                             ▼                  │
│  ┌─────────────────┐          ┌──────────────────┐         │
│  │ FastAPI Backend  │          │ Direct Python    │         │
│  │ HTTP API         │          │ Function Call    │         │
│  └────────┬────────┘          └────────┬─────────┘         │
│           │                            │                   │
│           └──────────┬─────────────────┘                   │
│                      ▼                                     │
│  ┌──────────────────────────────────────────────────────┐  │
│  │              RAG Core (Python OOP)                    │  │
│  │                                                       │  │
│  │  M1 Trace ──→ M2 Retrieval ──→ M3 Citations          │  │
│  │                    │                                   │  │
│  │              M4 Generation                            │  │
│  │                    │                                   │  │
│  │              M5 Reports & Charts (EcDev)              │  │
│  └──────────────────────┬───────────────────────────────┘  │
│                         ▼                                  │
│  ┌──────────────────────────────────────────────────────┐  │
│  │              Data Layer                               │  │
│  │  SQLite (FTS5) + ChromaDB (Vectors) + MinerU Files   │  │
│  └──────────────────────────────────────────────────────┘  │
│                         ▲                                  │
│  ┌──────────────────────┴───────────────────────────────┐  │
│  │  M0 Ingestion Pipeline                                │  │
│  │  PDF → MinerU → rebuild_db.py → SQLite + ChromaDB    │  │
│  └──────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

### 3.1 模块清单与依赖

| 模块 | 名称 | 优先级 | 服务场景 | 依赖 |
|------|------|--------|----------|------|
| **M0** | Ingestion Pipeline | P0 | 共享 | 无 |
| **M1** | Trace & Quality | P0 | 共享 | M0 |
| **M2** | Retrieval | P0 | 共享 | M0 |
| **M3** | Citations | P0 | 共享 | M2 |
| **M4** | Generation | P1 | 共享 | M3 |
| **M5** | Reports & Charts | P1 | EcDev | M2+M4 |
| **M6** | ROS2 Integration | P1 | NLP Part 2 | RAG Core |
| **M7** | Evaluation | P1 | NLP 评分 | M2+M3+M4 |

### 3.2 开发顺序（强制依赖链）

```
M0 Ingestion ──→ M2 Retrieval ──→ M3 Citations ──→ M4 Generation
                      │                                    │
                      ├──→ M1 Trace & Quality              ├──→ M5 Reports & Charts
                      │                                    │
                      └──→ M7 Evaluation ←─────────────────┘
                                                           │
                                      M6 ROS2 Integration ←┘
```

逻辑：
- 没 M0，没数据可查
- 没 M2，搜不到东西
- 没 M3，citation 没证据可挂
- 没 M1，不知道哪里坏了（可与 M2 平行开发）
- 没 M4，报告生成没基础
- M5 建立在 M2（检索表格）+ M4（生成叙述）之上
- M6 共享 RAG Core，需要 M2+M3+M4 稳定后集成
- M7 需要完整管道才能跑评估

### 3.3 M0: Ingestion Pipeline（数据入库）

**优先级**: P0 | **状态**: v1.0 已有基础，需扩展

**FR-0.1** 多类别文档入库
- 支持三类文档：教科书、EcDev 季报、房地产报告
- 统一目录结构：`data/raw_pdfs/{category}/` → `data/mineru_output/{category}/`
- 命名约定：教科书 `{author}_{short_title}`，EcDev `ed_update_q{N}_{year}`，房地产 `oreb_{type}_{date}`

**FR-0.2** MinerU 批处理
- `scripts/batch_mineru.py` 支持按类别批量处理
- 输出：`content_list.json`、`middle.json`、`model.json`、`.md` 文件

**FR-0.3** 数据库重建
- `scripts/rebuild_db.py` 支持多类别 chunk 入库
- bbox 坐标转换：content_list 1000×1000 → PDF 点坐标（v1.0 已修复）
- 每个 chunk 标记 `category` 字段（textbook / ecdev / real_estate）

**FR-0.4** TOC 与结构索引
- `scripts/rebuild_toc.py` 提取 PDF 书签 → `toc_entries` 表
- `scripts/rebuild_topic_index.py` 构建主题索引

**FR-0.5** PageIndex 树结构构建
- `scripts/build_pageindex.py` 使用本地 Ollama 模型为每本 PDF 生成层次化树结构索引
- 输出：`data/pageindex/{category}/{book}_structure.json`
- 参考实现：VectifyAI/PageIndex（`.github/references/PageIndex`）
- 通过 monkey-patch openai 库指向 Ollama 的 OpenAI 兼容端点实现零 API 费用

### 3.4 M1: Trace & Quality（可观测性）

**优先级**: P0 | **依赖**: M0

**FR-1.1** 请求参数展示
- 在 Trace 面板展示: question, top_k, fetch_k, filters, active_book_title, 启用的策略列表

**FR-1.2** 检索结果分层展示
- 分别展示 4 种检索策略各自的命中结果：
  - ① FTS5 BM25 hits
  - ② Vector (Semantic) hits
  - ③ TOC Heading Search hits
  - ④ PageIndex Structure hits
- Fused results：RRF 融合后的最终排序
- 每条 hit 显示: strategy, rank, chunk_id, book_title, chapter_title, page_number, score, snippet
- 可视化对比：哪些 chunk 只被一种策略命中、哪些被多种同时命中

**FR-1.3** 生成链路展示
- 展示 system_prompt, user_prompt（可折叠）
- 展示实际使用的 model 名称
- 展示 citation 清洗结果：raw_answer vs cleaned_answer

**FR-1.4** Quality Warnings
- 自动检测并返回 warnings：
  - `NO_FTS_HITS` / `NO_VECTOR_HITS` / `NO_TOC_HITS` / `NO_PAGEINDEX_HITS`
  - `NO_CONTEXT` / `NO_VALID_CITATIONS` / `CITATIONS_REMOVED`
- 前端以 warn/error 色块展示
- 各策略 0 hits 时显示建议

### 3.5 M2: Retrieval（可控性）

**优先级**: P0 | **依赖**: M0

**FR-2.1** top_k 和 fetch_k 控制
- 前端滑块：top_k（1~20）、fetch_k（top_k~60）

**FR-2.2** 检索策略独立开关（5 种）
- ① FTS5 BM25：开/关（默认开）
- ② Vector (Semantic)：开/关（默认开）
- ③ TOC Heading Search：开/关（默认开）
- ④ PageIndex Structure：开/关（默认关，需先运行 `build_pageindex.py` 生成树索引）
- ⑤ Ripgrep Raw Search：开/关（默认关，需安装 ripgrep）
- 至少保留一种策略启用

**FR-2.3** RRF 融合参数
- RRF k 值可配置（默认 60，范围 1~200）
- 只有 1 种策略启用时跳过 RRF

**FR-2.4** Filters 控制
- content_type 多选（text / table / image / equation）
- chapter_ids filter
- document category filter（textbook / ecdev / real_estate）

**FR-2.5** TOC Heading Search 配置
- 数据源：`toc_entries` 表
- 算法：词项重叠 + 子串 bonus（与 retrieval_lab 一致）

**FR-2.6** PageIndex Structure 配置
- 数据源：`data/pageindex/{category}/{book}_structure.json`（由 `build_pageindex.py` 生成的 LLM 层次化树索引）
- 算法：词项重叠 + 节点 summary 匹配
- Fallback：若无 PageIndex 数据，使用 MinerU `_middle.json` 做简单关键词匹配

**FR-2.7** Query Rewriter（查询改写）
- 在检索前使用 LLM 对用户的模糊/不完整/口语化查询进行改写
- 输出标准化的搜索查询，提高检索命中率
- 支持多轮对话上下文理解（参考 Sirchmunk v0.0.6 的 query rewriting 机制）
- 可配置开关：默认关闭，前端可启用
- 改写结果在 Trace 面板展示（原始 query → 改写后 query）

**FR-2.8** Sirchmunk Agentic Search 配置
- 依赖：`pip install sirchmunk`（Python SDK，可直接 import）
- 数据源：`data/mineru_output/**/*.md` 原始文件（零索引，无需预构建）
- 算法：Sirchmunk AgenticSearch — ripgrep 全文搜索 + Monte Carlo 证据采样
- 调用方式：`AgenticSearch(llm=ollama).search(query, paths=[mineru_output_dir])`
- LLM 交互：FAST 模式 2 次 LLM 调用（关键词提取 + 结果综合）
- 命中结果映射回 SQLite chunk_id 参与 RRF 融合
- 参考实现：Sirchmunk SDK（`.github/references/Sirchmunk`，`pip install sirchmunk`）

### 3.6 M3: Citations（可验证性）

**优先级**: P0 | **依赖**: M2

**FR-3.1** Citation 校验
- 检查每个 `[N]` 是否映射到有效 source

**FR-3.2** Citation 清洗
- 移除无效 citation，记录原始 vs 清洗结果

**FR-3.3** Citation → Source 映射
- 点击 `[N]` → 精确映射到 sources[N-1] → 获取 source_locators

**FR-3.4** PDF 跳页 + bbox 高亮
- 点击 citation → PDF 跳到对应页 + bbox 蓝色高亮
- 跨页 chunk 高亮第一个并提示 "还有 N 个位置"

**FR-3.5** 无效 Citation UI
- 灰色删除线样式，hover 提示，不可点击

### 3.7 M4: Generation（可优化性）

**优先级**: P1 | **依赖**: M3

**FR-4.1** 模型选择
- 保持 model 下拉选择，新增模型信息显示

**FR-4.2** Prompt 模板
- 预设：default / concise / detailed / academic
- 高级模式：直接编辑 system prompt

**FR-4.3** Citation 输出规则
- citation_style: inline_numbered（默认）/ footnote / none

**FR-4.4** 回答参数
- max_tokens、temperature 可配置

**FR-4.5** Citation 失败补救
- 0 有效 citation 时自动 warning + 可选重试策略

### 3.8 M5: Reports & Charts（EcDev 专属）

**优先级**: P1 | **依赖**: M2 + M4

**FR-5.1** 表格数据提取
- 从 MinerU 解析结果中提取 `content_type: table` 的结构化数据
- 解析表格 markdown → 结构化 JSON（行列数据）

**FR-5.2** 前端图表渲染
- 使用前端 Chart 组件（如 Recharts）渲染提取的表格数据
- 支持：折线图、柱状图、饼图（根据数据类型自动选择或用户选择）
- 图表标题、坐标轴标签、图例自动从表格 header 生成

**FR-5.3** 叙述性报告生成
- **Task 1 风格**（数据描述）：描述图表中的趋势、比较、极值
- **Task 2 风格**（分析报告）：基于检索到的多个文档段落，生成分析性叙述
- 报告中保留 citation，可追溯到原始 PDF

**FR-5.4** 报告展示
- 前端直接渲染（Markdown → HTML）
- 图表嵌入报告中
- 暂不支持导出 PDF/Word

### 3.9 M6: ROS2 Integration（NLP Part 2）

**优先级**: P1 | **依赖**: RAG Core (M2+M3+M4)

**FR-6.1** RAG Core OOP 封装
- RAG Core 以 Python class 形式封装，Web 和 ROS2 共享同一个 class
- 接口：`rag_core.query(question: str) -> RAGResponse`

**FR-6.2** ROS2 Node 实现
- `ollama_publisher.py`：继承 `rclpy.node.Node`
- Subscribe to `words` topic (String) — Whisper 输出
- Publish to `ollama_reply` topic (String) — RAG 回答
- ROS2 parameter: `model`（默认 qwen2.5:0.5b，< 1.5GB）
- ROS2 parameter: `knowledge_path`（知识文件路径）

**FR-6.3** 模型约束
- ROS2 场景下模型内存 < 1.5GB（与 Whisper + gTTS 共存）
- 推荐 qwen2.5:0.5b（~0.4GB）

### 3.10 M7: Evaluation（NLP 评分）

**优先级**: P1 | **依赖**: M2 + M3 + M4

**FR-7.1** 20 题评估集
- 混合教科书 + EcDev 领域问题
- 每题人工标注 ground truth 答案

**FR-7.2** 自动评估运行
- 批量运行 20 题，记录系统回答
- 记录每题 top-3 retrieved documents

**FR-7.3** 评分记录
- 人工评分：1 = correct / 0.5 = partially correct / 0 = incorrect
- top-3 文档相关性标注：relevant / not relevant
- 计算 average accuracy score

**FR-7.4** 评估报告输出
- 生成评估结果表格，可直接引用到 Final Report 中

---

## 4. 非功能需求

### 4.1 性能
- **NFR-1**: 新增参数不应使单次请求延迟增加超过 10%
- **NFR-2**: 前端面板切换 < 100ms
- **NFR-3**: ROS2 Node 响应时间需适配语音交互节奏（< 5s）

### 4.2 向后兼容
- **NFR-4**: 所有新增 API 字段有默认值，v1.0 客户端不受影响
- **NFR-5**: 现有测试用例全部通过

### 4.3 安全
- **NFR-6**: Prompt injection 防护
- **NFR-7**: content_type filter 白名单校验

### 4.4 可用性
- **NFR-8**: Trace / Retrieval / Generation 面板以 tab 或可折叠区域展示
- **NFR-9**: 所有新增控件默认值与 v1.0 行为一致

### 4.5 代码质量
- **NFR-10**: RAG Core 以 OOP 形式封装（NLP 作业要求）
- **NFR-11**: `ruff check` 通过
- **NFR-12**: `tsc --noEmit` 通过

---

## 5. 约束条件

### 5.1 技术约束
- 后端: Python / FastAPI
- 前端: React / TypeScript / Tailwind
- 数据库: SQLite FTS5 + ChromaDB
- LLM: Ollama（Web 可用大模型，ROS2 限制 < 1.5GB）
- 解析: MinerU v2.7.6
- ROS2: 需要 loaner laptop

### 5.2 开发约束
- 强制开发顺序: M0 → M2 → M3 → M1 → M4 → M5/M6/M7
- v1.0 代码只做扩展，不做破坏性重构
- RAG Core 必须 OOP，支持 Web + ROS2 双入口

### 5.3 时间约束
- **Deadline**: 2026-04-03（Final Report + Code + PPT + ROS2 Demo）
- **可用时间**: ~3 周
- 每个模块独立可测试、可 review

---

## 6. 验收标准

### 6.1 M0: Ingestion Pipeline
- [ ] AC-0.1: 教科书、EcDev 季报、房地产报告均可入库
- [ ] AC-0.2: 每个 chunk 有 category 字段标记

### 6.2 M1: Trace & Quality
- [ ] AC-1.1: Trace 面板展示所有请求参数和启用的策略列表
- [ ] AC-1.2: 分别展示 5 种策略结果 + fused 结果
- [ ] AC-1.3: 展示 system_prompt / user_prompt
- [ ] AC-1.4: 展示 citation 清洗结果
- [ ] AC-1.5: Quality warnings 以色块展示

### 6.3 M2: Retrieval
- [ ] AC-2.1: top_k / fetch_k 滑块正确响应
- [ ] AC-2.2: 4 种策略可独立开关，任意组合正确执行
- [ ] AC-2.3: RRF k 值可配置
- [ ] AC-2.4: content_type + category filter 生效
- [ ] AC-2.5: 1 种策略时跳过 RRF
- [ ] AC-2.6: Query Rewriter 可开关，改写结果在 Trace 面板可见

### 6.4 M3: Citations
- [ ] AC-3.1: citation 校验返回 valid/invalid 列表
- [ ] AC-3.2: 点击有效 citation → PDF 跳页 + bbox 高亮
- [ ] AC-3.3: 无效 citation 灰色样式，不可点击

### 6.5 M4: Generation
- [ ] AC-4.1: prompt 模板可切换
- [ ] AC-4.2: model 选择正常工作
- [ ] AC-4.3: citation 风格可配置

### 6.6 M5: Reports & Charts
- [ ] AC-5.1: 从 MinerU 表格数据生成前端图表
- [ ] AC-5.2: 生成 Task 1 风格数据描述
- [ ] AC-5.3: 生成 Task 2 风格分析报告
- [ ] AC-5.4: 报告中保留可追溯 citation

### 6.7 M6: ROS2 Integration
- [ ] AC-6.1: RAG Core 以 OOP class 封装，Web + ROS2 共享
- [ ] AC-6.2: ROS2 node 正确 subscribe words / publish ollama_reply
- [ ] AC-6.3: 使用 < 1.5GB 模型完成问答
- [ ] AC-6.4: 完整语音管道可演示

### 6.8 M7: Evaluation
- [ ] AC-7.1: 20 题混合评估集准备完成
- [ ] AC-7.2: 每题有人工评分 + top-3 文档相关性标注
- [ ] AC-7.3: 计算并输出 average accuracy score
- [ ] AC-7.4: 评估结果可直接引用到 Final Report

### 6.9 通用
- [ ] AC-9.1: v1.0 现有测试用例全部通过
- [ ] AC-9.2: 每个模块新增至少 3 个测试用例
- [ ] AC-9.3: `tsc --noEmit` 通过
- [ ] AC-9.4: `ruff check` 通过
- [ ] AC-9.5: 6-10 页 Final Report 完成
- [ ] AC-9.6: 10 分钟演示 PPT 完成

---

## 7. 附录

### 7.1 教科书引用

| 引用 | 来源 |
|------|------|
| Usability testing surprises | Krug, *Don't Make Me Think*, Ch9 |
| Discoverability | Norman, *The Design of Everyday Things*, Ch1 |
| Don't make me think | Krug, *Don't Make Me Think*, Ch3 |
| Feedback principle | Norman, *The Design of Everyday Things*, Ch1 |
| Evaluation in IR | Manning et al., *Introduction to Information Retrieval*, Ch8 |
| Provenance & evaluation | Manning et al., *Introduction to Information Retrieval*, Ch8.6 |
| Conceptual models & visibility | Norman, *The Design of Everyday Things*, Ch2 |

### 7.2 与 v1.0 的关系

v1.1 是 v1.0 的增量扩展，不是重写。所有 v1.0 功能保持不变。v1.0 文档保留在 `docs/v1.0/`。

### 7.3 NLP 作业交付物清单

| 交付物 | 对应模块 | 格式 |
|--------|---------|------|
| RAG 实现（Part 1, 65%） | M0-M4 + Web UI | Python + React |
| ROS2 集成（Part 2, 25%） | M6 | Python ROS2 Node |
| Final Report（10%） | M7 + 写作 | 6-10 页文档 |
| 演示 PPT | 所有 | 10 分钟 PPT |
| 评估数据 | M7 | 20 题 + 评分表 |

### 7.4 MinerU 坐标系与 bbox 修复

详见 v1.0 文档。核心结论：`content_list.json` 的 bbox 使用归一化 1000×1000 画布坐标，`rebuild_db.py` 入库时将其转换为 PDF 点坐标（`÷1000×page_size`），误差 < 1px。

### 7.5 数据目录结构

```
data/
├── raw_pdfs/
│   ├── textbooks/          ← 教科书
│   ├── ecdev/              ← 经济发展季报
│   └── real_estate/        ← 房地产报告
├── mineru_output/
│   ├── textbooks/
│   ├── ecdev/
│   └── real_estate/
```

### 7.6 检索策略总览

| # | 策略 | 优势 | 劣势 | 适用场景 | 默认 |
|---|------|------|------|----------|------|
| ① | FTS5 BM25 | 速度极快，精确词匹配 | 不理解同义词 | 已知关键术语 | 开 |
| ② | Vector (ChromaDB) | 语义理解 | 计算开销大 | 自然语言问题 | 开 |
| ③ | TOC Heading Search | 利用文档结构 | 仅标题级匹配 | 章节导航 | 开 |
| ④ | PageIndex Structure | 精准结构定位 | 需离线构建树索引 | "第X章讲了什么" | 关 |
| ⑤ | Sirchmunk Agentic | 零索引，跨chunk搜索，SDK集成 | 需LLM调用，需pip install | Agentic搜索，复杂问题 | 关 |

### 7.7 参考项目

| 项目 | 位置 | 用途 |
|------|------|------|
| VectifyAI/PageIndex | `.github/references/PageIndex` | 层次化树结构索引构建，LLM 推理检索 |
| ModelScope/Sirchmunk | `.github/references/Sirchmunk` | Query Rewriting、Monte Carlo Evidence Sampling、KnowledgeCluster 自进化 |
