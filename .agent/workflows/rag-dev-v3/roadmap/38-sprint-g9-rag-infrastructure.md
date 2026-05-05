# Sprint G9 — RAG 基础设施升级

> **目标**: 从 ChromaDB 原型栈迁移到生产级 Agentic RAG 架构
> **技术栈**: MinerU + Qdrant + bge-small-en-v1.5 + PostgreSQL + LlamaIndex
> **前置**: G8（统一查询模式）完成后执行

---

## Stories

### G9-S1: Qdrant 向量数据库替换 ChromaDB
- [ ] 部署 Qdrant（Docker / 本地二进制）
- [ ] 创建 Collection schema（384 维，cosine 距离）
- [ ] 编写 `engine_v2/vectordb/qdrant_client.py` 适配层
- [ ] 迁移现有 ChromaDB 数据 → Qdrant
- [ ] 验证检索精度不低于原 ChromaDB

### G9-S2: Embedding 模型切换 bge-small-en-v1.5
- [ ] 替换当前 embedding 模型为 `BAAI/bge-small-en-v1.5`（384 维）
- [ ] 重新向量化所有文档（federal-ircc, provincial, algonquin-programs）
- [ ] 基准测试：Top-5 recall 对比旧模型

### G9-S3: PostgreSQL 结构化数据层
- [ ] 设计 schema：`programs`（学费/学制/入学时间/校区）
- [ ] 设计 schema：`immigration_streams`（配额/条件/处理时间）
- [ ] 设计 schema：`cost_of_living`（城市/房租/交通/餐饮）
- [ ] ETL 脚本：从 MinerU 解析结果提取结构化字段入库
- [ ] SQL 查询接口封装

### G9-S4: LlamaIndex Agentic RAG 路由
- [ ] 接入 LlamaIndex `QueryEngine` 对接 Qdrant
- [ ] 接入 LlamaIndex `SQLTableRetrieverQueryEngine` 对接 PostgreSQL
- [ ] 实现 `RouterQueryEngine` 路由分发：
  - 政策/流程类 → Qdrant 向量检索
  - 对比/排序/计算类 → PostgreSQL SQL
  - 混合类 → 先 SQL 再向量补充
- [ ] Function Calling 工具注册

### G9-S5: 数据管线整合
- [ ] 爬虫 → MinerU → Qdrant 全自动管线
- [ ] 爬虫 → 结构化提取 → PostgreSQL 全自动管线
- [ ] 增量更新机制（只处理新增/变更文档）
- [ ] 数据源溯源（每个 chunk 标注来源 URL + 抓取时间）

### G9-S6: 端到端验证
- [ ] 20 题压力测试（政策类 10 题 + 对比类 10 题）
- [ ] 响应延迟基准 < 3s（P95）
- [ ] 对比类问题（如"哪个省配额最多"）必须走 SQL 返回精确结果
- [ ] 政策类问题必须附带来源引用

---

## 技术决策

| 决策 | 选择 | 理由 |
|------|------|------|
| 向量库 | Qdrant | 海量向量性能优于 Chroma/pgvector，原生 REST + gRPC |
| Embedding | bge-small-en-v1.5 | 纯英文、384 维、轻量快速、MTEB 排名靠前 |
| 结构化存储 | PostgreSQL | 成熟稳定、SQL 对比/时序/聚合能力 |
| Agent 框架 | LlamaIndex | Agentic RAG 路由 + 工具调用生态最成熟 |
| 数据解析 | MinerU | 已验证，PDF/表格/版面解析质量高 |

---

## 架构图

```
用户问题
   │
   ▼
┌──────────────────┐
│  LlamaIndex      │
│  RouterEngine    │
└──────┬───────────┘
       │
  ┌────┴────┐
  │ Router  │
  └────┬────┘
       │
  ┌────┼────────────┐
  ▼    ▼             ▼
Qdrant  PostgreSQL  混合
(向量)  (SQL)       (先SQL后向量)
  │       │            │
  ▼       ▼            ▼
政策文档  结构化数据    综合回答
+ 来源   + 精确对比    + 引用
```

---

## 完成标准

- [ ] ChromaDB 完全移除，Qdrant 接管所有向量检索
- [ ] PostgreSQL 至少 3 张结构化表可查询
- [ ] LlamaIndex Router 正确分发 > 90% 问题
- [ ] 20 题压力测试通过率 > 85%
