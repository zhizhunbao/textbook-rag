# Textbook-RAG v2 — 功能路线图（索引）

> 本文件为 `roadmap/` 目录下各 Sprint 文件的统一索引。
>
> **总进度**: 180/310 stories 完成 (58%), ~633h 总工时
> **上线进度**: GO 系列 25/30 stories (83%), 剩余功能优先，部署验收最后执行

## 文件索引

### 🎯 GO 系列 — 上线收费关键路径（最高优先级）

| 文件 | 类别 | 扫描 | 内容 |
|------|------|------|------|
| [23-sprint-consulting-c4.md](./roadmap/23-sprint-consulting-c4.md) | ✅ **Sprint C4** | ⛔ SKIP | **双库联合检索+会话绑定** — 7 stories, 12h ✅ 7/7 |
| [24-sprint-consulting-c5.md](./roadmap/24-sprint-consulting-c5.md) | ✅ **Sprint C5** | ⛔ SKIP | **交互打磨+咨询历史+角色创建** — 6 stories, 6h ✅ 6/6 |
| [26-sprint-go-multiuser.md](./roadmap/26-sprint-go-multiuser.md) | ✅ **Sprint GO-MU** | ⛔ SKIP | **多用户加固** — 10 stories, 12h ✅ 10/10 注册+Engine Auth+ACL收紧+限流 |
| [27-sprint-go-monetization.md](./roadmap/27-sprint-go-monetization.md) | ✅ **Sprint GO-MON** | ⛔ SKIP | **计费与付费墙** — 8 stories, 15h ✅ 8/8 QuotaMiddleware+Stripe插件+付费墙UI |
| [29-sprint-go-landing.md](./roadmap/29-sprint-go-landing.md) | 🟢 **Sprint GO-LAND** | 🟢 | **获客入口** — 5 stories, 8h 🚧 4/5 Demo 视频待补，Landing+Pricing+法律合规+SEO 已完成 |
| [28-sprint-go-deployment.md](./roadmap/28-sprint-go-deployment.md) | ⏭️ **Sprint GO-DEPLOY** | 🟢 | **ngrok 本地公网发布** — 7 stories, 7h 🚧 4/7 部署验收放到最后 |

### ✅ 已完成 Sprints

| 文件 | 类别 | 扫描 | 内容 |
|------|------|------|------|
| [10-sprint-hotfix.md](./roadmap/10-sprint-hotfix.md) | ✅ Hotfix | ⛔ SKIP | **上传→摄取管线修通** — 7/7 ✅ |
| [01-sprint1.md](./roadmap/01-sprint1.md) | ✅ S1 | ⛔ SKIP | 端到端旅程闭环 — 17/17 ✅ |
| [12-sprint-demo.md](./roadmap/12-sprint-demo.md) | ✅ Demo | ⛔ SKIP | 展示日冲刺 — 14/14 ✅ |
| [13-sprint-question-dataset.md](./roadmap/13-sprint-question-dataset.md) | ✅ QD | ⛔ SKIP | Question Dataset — 11/11 ✅ |
| [14-sprint-eval-curation.md](./roadmap/14-sprint-eval-curation.md) | ✅ EC | ⛔ SKIP | 回答筛选+自动评估 — 9/9 ✅ |
| [15-sprint-model-hub.md](./roadmap/15-sprint-model-hub.md) | ✅ MH | ⛔ SKIP | 模型库 — 16/16 ✅ `useModels` 已统一 catalog / pullAndRegister |
| [16-sprint-eval-v2.md](./roadmap/16-sprint-eval-v2.md) | ✅ EV2 | ⛔ SKIP | 四分类评分+检索溯源 — 16/16 ✅ 路由评估+检索诊断+趋势图 完成 |
| [17-sprint-robustness.md](./roadmap/17-sprint-robustness.md) | ✅ RB | ⛔ SKIP | LLM输出防御 — 5/5 ✅ |
| [18-sprint-ux-eval-polish.md](./roadmap/18-sprint-ux-eval-polish.md) | ✅ UEP | ⛔ SKIP | 评分交互打磨 — 14/14 ✅ |
| [19-sprint-eval-industrial.md](./roadmap/19-sprint-eval-industrial.md) | ✅ EI | ⛔ SKIP | 工业级评估 — 14/14 ✅ |
| [20-sprint-consulting-c1.md](./roadmap/20-sprint-consulting-c1.md) | ✅ C1 | ⛔ SKIP | 用户身份+引导 — 8/8 ✅ |
| [21-sprint-consulting-c2.md](./roadmap/21-sprint-consulting-c2.md) | ✅ C2 | ⛔ SKIP | 角色管理+知识库 — ✅ |
| [22-sprint-consulting-c3.md](./roadmap/22-sprint-consulting-c3.md) | ✅ C3 | ⛔ SKIP | 用户私有文档 — ✅ |
| [11-sprint-acquisition.md](./roadmap/11-sprint-acquisition.md) | ✅ AQ | ⛔ SKIP | 数据导入 — 13/13 ✅ |

### ⏸️ POST-LAUNCH — 上线后迭代

| 文件 | 类别 | 扫描 | 内容 |
|------|------|------|------|
| [02-sprint2.md](./roadmap/02-sprint2.md) | ⏸️ S2 | 🟢 | S2 剩余 — 🚧 22/30 ⏸️retrievers/home/seed 延后 |
| [25-sprint-eval-ux.md](./roadmap/25-sprint-eval-ux.md) | ⏸️ EUX | 🟢 | 评估体验增强 — ❌ 0/9 |
| [03-sprint3.md](./roadmap/03-sprint3.md) | ⏸️ S3 | 🟢 | 评估图表 — 8 stories ❌ |
| [04-sprint4.md](./roadmap/04-sprint4.md) | ⏸️ S4 | 🟢 | 基建补全 — 11 stories ❌ |
| [06-sprint5.md](./roadmap/06-sprint5.md) | ⏸️ S5 | 🟢 | DeepTutor T1 — 10 stories ❌ |
| [07-sprint6.md](./roadmap/07-sprint6.md) | ⏸️ S6 | 🟢 | DeepTutor T2 — 9 stories ❌ |
| [08-sprint7.md](./roadmap/08-sprint7.md) | ⏸️ S7 | 🟢 | DeepTutor T3 — 11 stories ❌ |
| [09-sprint8.md](./roadmap/09-sprint8.md) | ⏸️ S8 | 🟢 | 报告生成引擎 — 17 stories ❌ |

### 📊 参考文档

| 文件 | 内容 |
|------|------|
| [00-overview.md](./roadmap/00-overview.md) | 核心洞察 · LlamaIndex 对齐原则 · 依赖关系图 |
| [05-module-status.md](./roadmap/05-module-status.md) | 17 个模块的 Layout/UI/UX/Func 状态卡 |

---

## 🚀 功能优先执行队列（部署最后）

> 当前策略：先补产品功能和质量闭环，再做公网部署验收。部署相关只保留文档/模板维护，真实 ngrok、Stripe webhook、持久化验证放到最后。

### 第一梯队：可卖闭环

| 顺序 | 模块 / Sprint | 状态 | 下一步 |
|------|---------------|------|--------|
| ① | **Retrievers UI + Reranker** | ⏸️ S2 剩余 | 配置 top_k / fetch_k、FTS/Vector/Hybrid、Reranker，增加检索测试和策略对比 |

### 第二梯队：回答可信度

| 顺序 | 模块 / Sprint | 状态 | 下一步 |
|------|---------------|------|--------|
| ② | ~~**Eval v2 剩余**~~ | ✅ 16/16 | 路由评估+检索诊断+趋势图 已完成 |
| ③ | **Evaluation 图表 / 反馈循环** | ⏸️ S3 | 雷达图、趋势图、瓶颈建议、CSV/JSON 导出 |

### 第三梯队：教材与题目能力

| 顺序 | 模块 / Sprint | 状态 | 下一步 |
|------|---------------|------|--------|
| ⑤ | **Question Gen 多题型** | ⏸️ S3 | 支持 open / multiple_choice / fill_blank，增加难度筛选和章节覆盖率 |
| ⑥ | **TOC API + 前端** | ⏸️ S3 | 目录树预览、页码跳转、`features/engine/toc/` 模块 |
| ⑦ | **Chunking UI** | ⏸️ S4 | 分块结果预览、chunk_size / overlap / strategy 调参 |
| ⑧ | **Embeddings UI** | ⏸️ S4 | 模型切换、维度配置、缓存状态和清理入口 |

### 第四梯队：后台管理与长期增强

| 顺序 | 模块 / Sprint | 状态 | 下一步 |
|------|---------------|------|--------|
| ⑨ | **Home 真实仪表盘** | ⏸️ S2 剩余 | 书籍数、对话数、索引状态、推荐问题和自动刷新 |
| ⑩ | **Seed 日志与同步** | ⏸️ S2 剩余 | 实时日志流，seed 完成后同步 Engine |
| ⑪ | **Access 权限 UI** | ⏸️ S4 | 角色列表、权限矩阵、角色 CRUD、用户角色分配 |
| ⑫ | **DeepTutor 系列** | ⏸️ S5-S7 | StreamEvent、Smart Retrieve、Deep Solve、Web Search fallback、Reasoning UI、Memory、Tools |
| ⑬ | **Report Engine** | ⏸️ S8 | 报告模板、数据收集、图表、报告合成、PDF/Markdown 导出、报告中心 |
| ⑭ | **GO-LAND Demo 视频** | 🚧 4/5 | 录制 30s 产品演示视频：选角色 → 提问 → 流式回答 → 引用来源 |
| ⑮ | **GO-DEPLOY** 部署验收 | ⏭️ last | ngrok 真实访问、Stripe webhook 实测、本地持久化验证、健康检查 |

### 推荐执行顺序

`Retrievers UI → Evaluation 图表 → Question Gen 多题型 → TOC → Chunking → Embeddings → Home/Seed/Access → DeepTutor → Report Engine → Demo 视频 → 部署`
