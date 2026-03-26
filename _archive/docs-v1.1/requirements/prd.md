# Textbook RAG v1.1 — 产品需求文档 (PRD)

## 文档信息

- 版本: 1.1
- 作者: Alice (PM)
- 日期: 2026-03-11
- 状态: Approved
- 输入: `docs/v1.1/requirements/requirements.md`

---

## 1. 产品概述

### 1.1 产品愿景

统一的文档 RAG 平台——在同一个系统内完成**教科书问答**和**经济报告分析**，做到检索精准、定位准确、操作透明、结果可控。

### 1.2 目标用户

| 角色 | 核心场景 |
|------|----------|
| 学生 | 教材问答 + 验证来源 |
| TA / 教师 | 排查回答质量、调参优化 |
| NLP 教授 | 评估 RAG 实现 + ROS2 集成 |
| EcDev 分析师 | 从季报中提取数据、生成报告图表 |

### 1.3 核心价值

1. **查的准** — 5 种检索策略协同，覆盖关键词/语义/结构/元数据
2. **定位准** — Citation → PDF 跳页 + bbox 像素级高亮
3. **全透明** — 每次查询的全链路可追踪、可开关、可配置
4. **双场景** — 同一 RAG Core 驱动 Web UI 和 ROS2 语音管道

---

## 2. Epic 与用户故事

### EPIC-01: 数据入库与多类别支持 (M0)

#### US-001: 多类别文档入库

作为**系统管理员**，
我想要将教科书、EcDev 季报和房地产报告统一入库，
以便用户可以跨类别检索和问答。

**优先级**: Must (P0)

**验收标准**:
- Given 存在 `data/raw_pdfs/textbooks/`, `ecdev/`, `real_estate/` 目录
- When 运行 `batch_mineru.py` + `rebuild_db.py`
- Then 所有三个类别的文档均入库，chunk 表有 `category` 字段

#### US-002: 文档目录结构标准化

作为**开发者**，
我想要按统一命名约定组织原始 PDF 和 MinerU 输出，
以便数据管理清晰可维护。

**优先级**: Must (P0)

**验收标准**:
- Given 按命名约定放置 PDF
- When 运行入库脚本
- Then MinerU 输出目录自动镜像分类结构

---

### EPIC-02: 全链路可观测性 (M1)

#### US-003: 查看检索全链路

作为**TA**，
我想要看到每次查询用了哪些检索策略、各自返回了什么结果、最终融合排序如何，
以便快速定位回答质量问题。

**优先级**: Must (P0)

**验收标准**:
- Given 用户提交一次查询
- When 切换到 Trace 面板
- Then 看到 5 种策略分别的 hits（strategy, rank, chunk_id, score, snippet）
- And 看到 RRF fused results

#### US-004: 查看生成链路

作为**TA**，
我想要看到 system_prompt、user_prompt 和 model 信息，
以便理解回答是怎么生成的。

**优先级**: Must (P0)

**验收标准**:
- Given 查询完成后
- When 展开 Trace 面板的生成链路区域
- Then 看到 system_prompt（可折叠）、user_prompt、model 名称

#### US-005: 质量告警自动提示

作为**用户**，
我想要当检索出问题时自动看到警告提示和修复建议，
以便知道下一步该怎么做。

**优先级**: Must (P0)

**验收标准**:
- Given FTS5 返回 0 条结果
- When 前端渲染 Trace 面板
- Then 显示 `NO_FTS_HITS` 告警 + 建议"尝试调整关键词或启用 Vector 检索"
- And 相同逻辑适用于所有 5 种策略

---

### EPIC-03: 检索可控性 (M2)

#### US-006: 调节检索参数

作为**开发者**，
我想要通过滑块调节 top_k 和 fetch_k，
以便实验不同的检索深度对回答质量的影响。

**优先级**: Must (P0)

**验收标准**:
- Given Retrieval 面板可见
- When 拖动 top_k 滑块到 10，fetch_k 到 30
- Then 下次查询使用新参数
- And Trace 面板显示实际使用的参数值

#### US-007: 开关检索策略

作为**开发者**，
我想要独立开关 5 种检索策略的任意组合，
以便对比哪种策略组合效果最好。

**优先级**: Must (P0)

**验收标准**:
- Given 5 个 checkbox 均显示在 Retrieval 面板
- When 取消勾选 FTS5，只保留 Vector
- Then 下次查询只执行 Vector 检索，Trace 中无 FTS5 结果
- And 全部取消时显示提示"至少启用一种策略"

#### US-008: 配置 RRF 融合参数

作为**开发者**，
我想要调节 RRF k 值，
以便优化不同策略结果的融合效果。

**优先级**: Should (P1)

**验收标准**:
- Given RRF k 值输入框可见
- When 修改为 30
- Then 下次查询使用 k=30 进行 RRF 融合
- And 只有 1 种策略启用时自动跳过 RRF

#### US-009: 按类别和内容类型过滤

作为**用户**，
我想要按文档类别（教科书/EcDev/房地产）和内容类型（文本/表格/图片）过滤结果，
以便缩小检索范围。

**优先级**: Must (P0)

**验收标准**:
- Given 过滤控件显示在 Retrieval 面板
- When 选择 category=ecdev, content_type=table
- Then 所有检索策略仅返回 ecdev 类别的 table 类型 chunk

---

### EPIC-04: Citation 可验证性 (M3)

#### US-010: 点击 Citation 跳转 PDF

作为**学生**，
我想要点击回答中的 `[N]` 引用后左侧 PDF 跳到对应页并高亮原文区域，
以便验证答案确实来自教科书。

**优先级**: Must (P0)

**验收标准**:
- Given 回答包含 `[2]` 引用
- When 点击 `[2]`
- Then PDF viewer 跳到对应 page_number
- And 蓝色透明 bbox 覆盖对应 chunk 区域
- And 跨页 chunk 高亮第一个位置并提示"还有 N 个位置"

#### US-011: 无效 Citation 标识

作为**学生**，
我想要无效的 citation 显示为灰色不可点击样式，
以便知道哪些引用不可用。

**优先级**: Must (P0)

**验收标准**:
- Given 后端检测到 `[3]` 无对应 source
- When 前端渲染回答
- Then `[3]` 显示为灰色删除线
- And hover 提示"Citation 3 is not available"
- And 不可点击

#### US-012: Citation 清洗追踪

作为**TA**，
我想要在 Trace 面板看到 citation 清洗前后的对比，
以便了解哪些 citation 被移除了。

**优先级**: Should (P1)

**验收标准**:
- Given 查询完成后
- When 查看 Trace 面板 Citation 区域
- Then 显示 raw_answer vs cleaned_answer
- And 列出 valid_citations 和 invalid_citations

---

### EPIC-05: 生成可优化性 (M4)

#### US-013: 切换 Prompt 模板

作为**开发者**，
我想要在 default/concise/detailed/academic 之间切换 prompt 模板，
以便对比不同 prompt 对回答风格的影响。

**优先级**: Should (P1)

**验收标准**:
- Given Generation 面板显示模板选择器
- When 切换到 "academic"
- Then 下次查询使用 academic prompt 模板
- And Trace 面板显示实际使用的 system_prompt

#### US-014: 模型选择增强

作为**开发者**，
我想要看到每个模型的参数量和上下文窗口大小，
以便选择合适的模型。

**优先级**: Could (P2)

**验收标准**:
- Given Model 下拉列表可见
- When 展开列表
- Then 每个模型旁显示参数量和上下文窗口（如 Ollama API 提供）

#### US-015: 配置 Citation 输出风格

作为**开发者**，
我想要切换 citation 输出为 inline numbered / footnote / none，
以便适应不同场景。

**优先级**: Could (P2)

**验收标准**:
- Given Citation style 选择器可见
- When 切换到 "footnote"
- Then 下次回答以脚注形式输出 citation

---

### EPIC-06: 报告与图表 — EcDev 专属 (M5)

#### US-016: 从表格数据生成图表

作为**EcDev 分析师**，
我想要系统从 PDF 表格中提取数据并用前端 Chart 组件渲染可视化图表，
以便快速理解经济数据趋势。

**优先级**: Should (P1)

**验收标准**:
- Given 查询返回包含 `content_type: table` 的 chunk
- When 系统解析表格 markdown 为结构化 JSON
- Then 前端用 Chart 组件渲染折线图/柱状图
- And 图表有标题、轴标签、图例（从 table header 生成）

#### US-017: 生成叙述性报告

作为**EcDev 分析师**，
我想要基于检索到的数据生成 IELTS Task 1/2 风格的叙述报告，
以便直接用于工作汇报。

**优先级**: Should (P1)

**验收标准**:
- Given 完成检索后有足够的 context
- When 选择"生成报告"模式
- Then 系统生成 Task 1 风格（数据描述：趋势、比较、极值）
- And 系统生成 Task 2 风格（分析性叙述）
- And 报告中保留可追溯的 citation

#### US-018: 报告中嵌入图表

作为**EcDev 分析师**，
我想要生成的报告中内嵌图表，
以便在前端一屏看到完整报告。

**优先级**: Should (P1)

**验收标准**:
- Given 报告生成完成且有关联图表
- When 前端渲染报告
- Then 报告以 Markdown 渲染，图表嵌入对应位置

---

### EPIC-07: ROS2 语音集成 (M6)

#### US-019: RAG Core 共享封装

作为**开发者**，
我想要 RAG Core 以 Python OOP class 形式封装，Web 和 ROS2 共享同一份代码，
以便避免维护两套实现。

**优先级**: Must (P0)

**验收标准**:
- Given RAGCore class 定义在独立模块中
- When FastAPI 和 ROS2 node 分别导入
- Then 两者使用完全相同的检索和生成逻辑

#### US-020: ROS2 语音问答 Node

作为**NLP 课程评审**，
我想要 ROS2 node 接收 Whisper 转写文本并返回 RAG 回答，
以便通过语音管道演示 RAG 系统。

**优先级**: Must (P0)

**验收标准**:
- Given ROS2 node 已启动，model=qwen2.5:0.5b
- When Whisper 发布文本到 `words` topic
- Then node 调用 RAG Core 生成回答
- And 发布回答到 `ollama_reply` topic
- And 模型内存 < 1.5GB

---

### EPIC-08: 评估 (M7)

#### US-021: 20 题混合评估

作为**NLP 课程学生**，
我想要准备 20 个混合领域问题（教科书 + EcDev），运行评估并记录结果，
以便写入 Final Report。

**优先级**: Must (P0)

**验收标准**:
- Given 20 题已准备（建议 12 教科书 + 8 EcDev）
- When 批量运行系统
- Then 每题记录：系统回答、top-3 retrieved documents、人工评分（1/0.5/0）、文档相关性
- And 计算 average accuracy score

#### US-022: 评估结果报告

作为**NLP 课程学生**，
我想要评估结果自动生成可引用的表格和统计数据，
以便直接放入 Final Report。

**优先级**: Should (P1)

**验收标准**:
- Given 20 题评估完成
- When 生成评估报告
- Then 输出包含：每题得分表、overall accuracy、策略分布统计
- And 格式可直接复制到 Final Report

---

## 3. 功能需求 — MoSCoW 分类

### 3.1 Must Have (P0)

| ID | 功能 | 模块 | User Story |
|----|------|------|-----------|
| FR-001 | 多类别文档入库（教科书+EcDev+房地产） | M0 | US-001 |
| FR-002 | 5 种检索策略分层展示 | M1 | US-003 |
| FR-003 | Quality warnings 自动告警 | M1 | US-005 |
| FR-004 | top_k / fetch_k 参数可调 | M2 | US-006 |
| FR-005 | 5 种检索策略独立开关 | M2 | US-007 |
| FR-006 | 类别 + 内容类型过滤 | M2 | US-009 |
| FR-007 | Citation 点击 → PDF 跳页 + bbox 高亮 | M3 | US-010 |
| FR-008 | 无效 Citation 灰色标识 | M3 | US-011 |
| FR-009 | RAG Core OOP 封装 | M6 | US-019 |
| FR-010 | ROS2 语音 Node | M6 | US-020 |
| FR-011 | 20 题混合评估 | M7 | US-021 |

### 3.2 Should Have (P1)

| ID | 功能 | 模块 | User Story |
|----|------|------|-----------|
| FR-012 | 生成链路展示 | M1 | US-004 |
| FR-013 | RRF k 值可配置 | M2 | US-008 |
| FR-014 | Citation 清洗追踪 | M3 | US-012 |
| FR-015 | Prompt 模板切换 | M4 | US-013 |
| FR-016 | 表格数据 → 前端图表 | M5 | US-016 |
| FR-017 | 叙述性报告生成 | M5 | US-017 |
| FR-018 | 报告内嵌图表 | M5 | US-018 |
| FR-019 | 评估结果报告 | M7 | US-022 |

### 3.3 Could Have (P2)

| ID | 功能 | 模块 | User Story |
|----|------|------|-----------|
| FR-020 | 模型信息显示 | M4 | US-014 |
| FR-021 | Citation 输出风格切换 | M4 | US-015 |
| FR-022 | Sirchmunk grep 检索 | M2 | — |
| FR-023 | temperature / max_tokens 配置 | M4 | — |

### 3.4 Won't Have (v1.1)

- 多用户 / 鉴权
- 流式输出 (streaming)
- 多模态检索
- Statistics Canada API 集成
- 报告导出 PDF/Word

---

## 4. 非功能需求

| ID | 类型 | 要求 |
|----|------|------|
| NFR-01 | 性能 | 新增参数不应使单次请求延迟增加超过 10% |
| NFR-02 | 性能 | 前端面板切换 < 100ms |
| NFR-03 | 性能 | ROS2 Node 响应 < 5s |
| NFR-04 | 兼容 | v1.0 API 向后兼容，新字段有默认值 |
| NFR-05 | 兼容 | 现有测试用例全部通过 |
| NFR-06 | 安全 | Prompt injection 防护 |
| NFR-07 | 安全 | content_type filter 白名单校验 |
| NFR-08 | 可用 | 面板以 tab/折叠区域展示，不额外占空间 |
| NFR-09 | 质量 | RAG Core OOP 封装 |
| NFR-10 | 质量 | `ruff check` + `tsc --noEmit` 通过 |

---

## 5. 里程碑与时间线

### 5.1 MVP — Week 1-2 (3/12 ~ 3/25)

**目标**: 核心 RAG 管道可用 + 全透明

| 模块 | 交付物 | 估时 |
|------|--------|------|
| M0 | 多类别入库脚本 + 数据 | 1 天 |
| M2 | 5 种检索策略 + RRF + 开关 | 3 天 |
| M3 | Citation 校验/清洗/跳页/bbox | 2 天 |
| M1 | Trace 面板 + Quality warnings | 2 天 |

### 5.2 Feature Complete — Week 2-3 (3/25 ~ 4/1)

**目标**: 全功能 + 评估 + ROS2

| 模块 | 交付物 | 估时 |
|------|--------|------|
| M4 | Prompt 模板 + Model 选择 | 1 天 |
| M5 | 表格→图表 + 报告生成 | 2 天 |
| M6 | ROS2 Node + RAG Core OOP | 1 天 |
| M7 | 20 题评估 + 评估报告 | 1 天 |

### 5.3 Delivery — 4/1 ~ 4/3

| 交付物 | 估时 |
|--------|------|
| Final Report (6-10 页) | 1 天 |
| PPT (10 分钟演示) | 0.5 天 |
| 打包提交 | 0.5 天 |

---

## 6. 风险与依赖

### 6.1 风险

| 风险 | 概率 | 影响 | 缓解 |
|------|------|------|------|
| 3 周时间不够 | 高 | 高 | 先保 P0，P1/P2 可砍 |
| MinerU 表格解析不准 | 中 | 中 | M5 降级为手动指定数据 |
| ROS2 loaner laptop 不可用 | 低 | 高 | 提前确认设备可用 |
| Ollama <1.5GB 模型质量差 | 中 | 中 | Web 用大模型，ROS2 独立配置 |

### 6.2 外部依赖

- Ollama 本地推理服务
- MinerU v2.7.6 + HuggingFace 模型
- ROS2 + Whisper + gTTS（loaner laptop）
- Ottawa.ca EcDev 报告 PDF（已下载 12 个）

---

## 7. 附录

### 7.1 术语表

| 术语 | 定义 |
|------|------|
| RAG | Retrieval-Augmented Generation |
| bbox | PDF 页面中的矩形定位区域 |
| RRF | Reciprocal Rank Fusion — 多策略结果融合算法 |
| FTS5 | SQLite 全文搜索引擎 v5 |
| Citation | 回答中的 `[N]` 引用标记 |
| Trace | 单次查询的全链路追踪记录 |
| MinerU | PDF 解析引擎，输出结构化 JSON + Markdown |

### 7.2 参考文档

- [requirements.md](../requirements/requirements.md) — v1.1 需求文档
- [v1.0 PRD](../../v1.0/requirements/prd.md) — v1.0 产品需求文档
- [CST8507 Assignment 2](../../nlp/assignment2/CST8507_Assignment2_W26.md) — NLP 作业要求
- Krug, *Don't Make Me Think* — 可用性原则
- Norman, *The Design of Everyday Things* — Discoverability + Feedback
- Manning et al., *Introduction to Information Retrieval* — IR 评估
