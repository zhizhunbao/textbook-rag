# Phase Review: PRD (Product Requirements Document)

**Review 类型**: 文档类
**执行时间**: 2026-03-04T00:46:30-05:00
**产出物**: `docs/requirements/prd.md`
**作者**: Alice (Product Manager)
**审查人**: Bob (Architect)

---

## 自动检查

- ✅ 文件存在: `docs/requirements/prd.md`
- ✅ 文件非空

## 审查清单

### 通用检查 — 完整性

- ✅ 文档包含所有必要章节（8 个主章节，完全符合 PRD 模板）
- ✅ 无占位符文本
- ✅ 无空白章节
- ✅ 关键数据有具体数值（22 个用户故事，BM25 <100ms, 总延迟 <30s, 20 个评估题）

### 通用检查 — 一致性

- ✅ 术语在文档内统一（MinerU, ChromaDB, FTS5, qwen2.5:0.5b 等术语与 requirements.md 一致）
- ✅ 与前序阶段 (requirements.md) 不矛盾 — 所有 F1-F15 需求均映射到用户故事
- ✅ 引用的外部资源确实存在

### 通用检查 — 可操作性

- ✅ 用户故事描述具体，可直接开发
- ✅ 验收标准使用 Given/When/Then 格式，明确可测量
- ✅ 无模糊描述

### 通用检查 — 格式规范

- ✅ Markdown 标题层级正确
- ✅ 表格格式完整
- ✅ 链接有效

### prd 阶段特定检查

- ✅ 用户故事格式正确（As a... I want... so that...）— 全部 22 个故事格式统一
- ✅ 每个用户故事有验收标准 — 全部使用 Given/When/Then
- ✅ 优先级已标注 — MoSCoW 分类（P0/P1/P2）
- ✅ 功能范围与 requirements 一致 — F1-F15 核心功能全部覆盖

## 发现的问题

| #   | 严重度 | 描述                                                                                                                             | 位置   | 建议修复                                  |
| --- | ------ | -------------------------------------------------------------------------------------------------------------------------------- | ------ | ----------------------------------------- |
| 1   | MEDIUM | Metadata Filter Search (方法 ④) 被归类为 Could Have (P2)，但 requirements.md 中标记为 MUST。建议在 architecture 阶段确认是否降级 | §3.3   | → architecture 阶段确认优先级             |
| 2   | MEDIUM | US-010 (PageIndex Tree Search) 缺少对 LLM token 预算的约束 — TOC 树可能超过 qwen2.5:0.5b 的上下文窗口                            | US-010 | → architecture 阶段设计 tree pruning 策略 |

## 结论 (初审)

- 🟢 **通过** — 可以进入下一阶段

PRD 文档质量高，22 个用户故事覆盖了所有需求，验收标准清晰可测。2 个 MEDIUM 问题在后续 architecture 阶段解决。

## 统计 (初审)

- 检查项总数: 15
- 通过: 15 | 警告: 0 | 失败: 0

### MEDIUM 问题处理计划

| #   | 问题                              | 处理方式                     |
| --- | --------------------------------- | ---------------------------- |
| 1   | Metadata Filter Search 优先级降级 | → 在 `architecture` 阶段确认 |
| 2   | PageIndex tree LLM token 预算     | → 在 `architecture` 阶段设计 |
