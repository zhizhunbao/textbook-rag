# 需求发现笔记 — Unified Document RAG Platform

> 自动生成，随对话实时更新
> 最后更新: 2026-03-12T00:34:00-04:00
> 当前阶段: Phase 3 - Delivery ✅
> 已覆盖维度: 7/7
> 所有 🔴 冲突已解决

## 当前理解摘要

一个**统一的文档 RAG 平台**，合并两个项目：

1. **Textbook RAG**（NLP 课程作业 CST8507 Assignment 2）— 教科书问答 + 深度溯源 + ROS2 语音集成
2. **EcDev Research Assistant**（Ottawa 经济发展部）— 经济报告问答 + 报告/图表生成

两者共享 **RAG Core**（Python OOP），通过不同入口调用：
- Web UI（FastAPI + React）→ 双栏 PDF + Chat + Trace + Reports
- ROS2 Node → 语音问答管道（Whisper → RAG → gTTS）

**核心诉求**：查的准、定位准、全透明可控。

## 七维度状态

| 维度 | 状态 | 置信度 | 关键发现 |
|------|------|--------|----------|
| 🎯 愿景与目标 | ✅ 已完成 | 🟢 | 统一平台，核心是检索精度 + 源文定位 + 全透明可控 |
| 👥 用户与角色 | ✅ 已完成 | 🟢 | 学生/TA/评审 + EcDev 分析师 + NLP 教授(评分) |
| 🔄 核心流程 | ✅ 已完成 | 🟢 | 问答+溯源(共享)、报告+图表(EcDev)、语音(ROS2) |
| 📊 数据与信息 | ✅ 已完成 | 🟢 | 教科书+EcDev季报+房地产报告→MinerU→SQLite+ChromaDB |
| 🚫 边界与约束 | ✅ 已完成 | 🟢 | Deadline 4/3、Ollama<1.5GB(ROS2)、不做多用户/流式 |
| 🔗 集成与依赖 | ✅ 已完成 | 🟢 | FastAPI+React+Ollama+MinerU+ROS2+Whisper+gTTS |
| 📋 优先级与阶段 | ✅ 已完成 | 🟢 | M0→M2→M3→M1→M4→M5→M6→M7 |

## 已确认的需求项

- [x] REQ-001: RAG Core 共享代码，OOP 结构，Web + ROS2 双入口 🟢
- [x] REQ-002: 5 种检索策略可独立开关 + RRF 融合 🟢
- [x] REQ-003: Citation 校验/清洗/映射 + PDF 跳页 bbox 高亮 🟢
- [x] REQ-004: 全链路 Trace + 质量告警 🟢
- [x] REQ-005: 多类别文档支持（教科书+EcDev+房地产） 🟢
- [x] REQ-006: 表格数据提取 → 前端 Chart 组件渲染 🟢
- [x] REQ-007: 叙述性报告生成（IELTS Task 1/2 风格） 🟢
- [x] REQ-008: ROS2 Node（subscribe words, publish ollama_reply） 🟢
- [x] REQ-009: 20 题混合评估（教科书+EcDev） 🟢
- [x] REQ-010: 6-10 页 Final Report + 10 分钟 PPT 🟢
- [x] REQ-011: 报告先前端渲染，不需导出 🟢
- [ ] REQ-012: 管理与监控面板 — 查看每个 PDF 的 pipeline 状态 🟡 **（下一迭代）**

## 待解决的问题

无 — 所有关键问题已解决。

## 下一迭代待探索 Backlog

### REQ-012: 管理与监控面板

**背景**：随着文档类别增加（textbook / ecdev / real_estate），需要一个可视化界面让管理员了解每个 PDF 的处理状态，避免手动查脚本日志。

**期望功能（待需求探索细化）：**
- 列出所有已知 PDF（按类别分组）
- 对每个文档显示 pipeline 各阶段完成状态：
  - MinerU 处理（content_list.json 存在？）
  - 入库 / Chunking（SQLite books + chunks 表）
  - TOC 索引（toc_entries 表有数据？）
  - Embedding（chroma_document_id 已填充？）
- 触发重建操作（rebuild_db / build_vectors / rebuild_toc）
- 显示全局汇总（总书数、各阶段完成率）

**待讨论问题：**
- 是独立管理页面，还是嵌入现有前端？
- 是否需要权限/认证保护？
- 触发操作是异步后台任务，还是同步阻塞？
- 是否需要实时进度（WebSocket / SSE）？

## 发现的矛盾/风险

- ⚠️ RISK-001: 3 周要交 Web UI + ROS2 + 评估 + 报告，时间紧张
- ⚠️ RISK-002: ROS2 部分需要 loaner laptop，硬件依赖
- ⚠️ RISK-003: Ollama 模型 <1.5GB 限制下 RAG 质量可能受限（ROS2 场景）
- ⚠️ RISK-004: MinerU 表格解析精度直接影响图表生成质量
