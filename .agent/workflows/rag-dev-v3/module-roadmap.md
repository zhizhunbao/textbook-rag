# Textbook-RAG v2 — 功能路线图（索引）

> 本文件为 `roadmap/` 目录下各 Sprint 文件的统一索引。
> 
> **总进度**: 91/227 stories 完成 (40%), ~516h 总工时 (含 Sprint Demo 14 stories, Sprint MH 10 stories, Sprint EV2 16 stories ✅, Sprint RB 5 stories ✅, Sprint UEP 14 stories ✅, Sprint AQ-Epic1 10 stories ✅, Sprint EI 11/14 stories 🚧)

## 文件索引

| 文件 | 类别 | 扫描 | 内容 |
|------|------|------|------|
| [00-overview.md](./roadmap/00-overview.md) | **总览** | 🟢 | 核心洞察 · LlamaIndex 对齐原则 · 依赖关系图 · 总进度 · 待重构 |
| [10-sprint-hotfix.md](./roadmap/10-sprint-hotfix.md) | 🔴 **Hotfix** | ⛔ SKIP | **上传→摄取管线修通** — 7 stories, 20h ✅ 7/7 完成 |
| [01-sprint1.md](./roadmap/01-sprint1.md) | **Sprint 执行计划** | ⛔ SKIP | S1 端到端旅程闭环 — 17 stories, 52h ✅ 100% |
| [02-sprint2.md](./roadmap/02-sprint2.md) | **Sprint 执行计划** | 🟢 | S2 评估中枢+引用UX+持久化 — 30 stories, 78h 🚧 22/30 ✅qgen ✅citation ✅eval ✅chat 🚧retrievers ❌home ❌seed |
| [12-sprint-demo.md](./roadmap/12-sprint-demo.md) | ✅ **Demo Sprint** | ⛔ SKIP | **展示日冲刺** — 14 stories, 10.5h ✅ 14/14 全书搜索+暖色主题+建议问题+Citation Score+Report MVP+Admin分离 |
| [13-sprint-question-dataset.md](./roadmap/13-sprint-question-dataset.md) | 🆕 **Sprint QD** | 🟢 | **Question Dataset Pipeline** — 11 stories, 25h ❌ 分层采样+chunk追踪+QuestionPicker+检索评估 |
| [14-sprint-eval-curation.md](./roadmap/14-sprint-eval-curation.md) | 🆕 **Sprint EC** | 🟢 | **回答筛选+自动评估+高分报告** — 9 stories, 11h ❌ Query删除+自动评估触发+达标判定+高分报告生成 |
| [16-sprint-eval-v2.md](./roadmap/16-sprint-eval-v2.md) | ✅ **Sprint EV2** | ⛔ SKIP | **四分类评分+检索策略溯源+自动评估+Agentic RAG基座** — 16 stories, 27h ✅ 13/16 核心完成 ✅T1检索策略溯源 ✅T2四分类评分 ✅T3自动评估 ✅T4路由基座 ✅T5-01评分卡 ⏸️T4-02路由评估(P3延后) ⏸️T5-02诊断面板(P3延后) ⏸️T5-03趋势对比(P3延后) |
| [17-sprint-robustness.md](./roadmap/17-sprint-robustness.md) | ✅ **Sprint RB** | ⛔ SKIP | **LLM输出防御 — structured_predict替换裸json.loads** — 5 stories, 3h ✅ 5/5 完成 |
| [18-sprint-ux-eval-polish.md](./roadmap/18-sprint-ux-eval-polish.md) | ✅ **Sprint UEP** | ⛔ SKIP | **评分交互打磨+BM25修复+双视角模式** — 14 stories, 14.5h ✅ 14/14 完成 ✅T1 BM25全书搜索+缓存 ✅T2评分完整性+回填 ✅T3双视角评分卡 ✅T4 CitationChip+配色 |
| [19-sprint-eval-industrial.md](./roadmap/19-sprint-eval-industrial.md) | 🚧 **Sprint EI** | 🟢 | **工业级评估升级** — 14 stories, 22.5h 🚧 11/14 ✅T1 Golden Dataset ✅T2 IR硬指标 ✅T3-01/02 Guideline+Correctness ✅T5 前端卡片+Tooltip ❌T3-03 Cross-Model(P2) ❌T4 A/B对比(P2) |
| [15-sprint-model-hub.md](./roadmap/15-sprint-model-hub.md) | 🆕 **Sprint MH** | 🟢 | **Ollama模型库+一键拉取** — 10 stories, 10.5h ❌ 精选目录+SSE Pull+进度条+自动注册 (Admin only) |
| [03-sprint3.md](./roadmap/03-sprint3.md) | **Sprint 执行计划** | 🟢 | S3 评估图表+反馈 + 多题型 + toc — 8 stories, 24h ❌ |
| [04-sprint4.md](./roadmap/04-sprint4.md) | **Sprint 执行计划** | 🟢 | S4 基建补全 — 11 stories, 29h ❌ |
| [05-module-status.md](./roadmap/05-module-status.md) | **模块现状** | 🟢 | 17 个模块的 Layout/UI/UX/Func 状态卡 |
| [06-sprint5.md](./roadmap/06-sprint5.md) | **Sprint 执行计划** | 🟢 | S5 智能检索+多步推理 (DeepTutor T1) — 10 stories, 30h ❌ |
| [07-sprint6.md](./roadmap/07-sprint6.md) | **Sprint 执行计划** | 🟢 | S6 问题升级+Web Search (DeepTutor T2) — 9 stories, 28h ❌ |
| [08-sprint7.md](./roadmap/08-sprint7.md) | **Sprint 执行计划** | 🟢 | S7 架构升级+用户记忆 (DeepTutor T3) — 11 stories, 40h ❌ |
| [09-sprint8.md](./roadmap/09-sprint8.md) | **Sprint 执行计划** | 🟢 | S8 多角色报告生成引擎 — 17 stories, 56h ❌ |
| [11-sprint-acquisition.md](./roadmap/11-sprint-acquisition.md) | **Sprint 执行计划** | 🟢 | 数据导入全流程一页化 — 13 stories, 34h 🚧 10/13 ✅ Epic 1 (5-Tab) 全部完成, Epic 2 (readers Tab 补全) 0/3 待做 |

---

## 执行优先级队列

> 按 **依赖关系 + 业务价值 + 风险** 排序，从上到下逐个推进。

| 优先级 | Sprint | 剩余 | 预估 | 理由 |
|--------|--------|------|------|------|
| 🟠 P1 | **EI** (19) 工业级评估 | 3/14 待做 | ~5h | **质量门槛**。T3-03 Cross-Model(P2) + T4-01/T4-02 Pairwise A/B对比(P2)，需数据积累后再做更有意义 |
| 🟠 P1 | **S2** (02) 剩余收尾 | 8/30 待做 | ~20h | retrievers/home/seed 未完成，与 UEP-T1 BM25 有重叠，可合并推进 |
| 🟠 P1 | **AQ-Epic2** (11) readers Tab 补全 | 3/3 待做 | 8h | RT-01 目录 Tab + RT-02 内容 Tab + RT-03 LibraryPage Tab 容器 |
| 🟡 P2 | **QD** (13) Question Dataset | 11/11 待做 | 25h | 分层采样 + chunk 追踪，为 EI Golden Dataset 提供数据源 |
| 🟡 P2 | **EC** (14) 回答筛选 | 9/9 待做 | 11h | 自动评估触发已在 EV2 完成，剩余为 UI 筛选 + 高分报告 |
| 🟢 P3 | **MH** (15) 模型库 | 10/10 待做 | 10.5h | 独立功能模块，无依赖，可随时插入 |
| 🟢 P3 | **S3** (03) 评估图表 | 8/8 待做 | 24h | 需要 EI 的评估数据积累后才有意义 |
| 🔵 P4 | **S4** (04) 基建补全 | 11/11 待做 | 29h | 技术债清理，非功能性需求 |
| 🔵 P4 | **S5–S8** DeepTutor 系列 | 47/47 待做 | 154h | 长期愿景：智能检索 → Web Search → 用户记忆 → 报告引擎 |
| ⏸️ Deferred | EV2 延后项 (T4-02, T5-02, T5-03) | 3 items | ~5h | 路由评估 + 诊断面板 + 趋势图，需数据积累，归入 S3/EI |

### 当前推荐动作

1. **启动 EI**: Golden Dataset + 硬指标 → 质量可量化
2. **S2 收尾**: retrievers/home/seed → 基础功能补全
3. **AQ-Epic2**: readers Tab 补全 → 目录/内容浏览
4. **QD**: 分层采样 + chunk 追踪 → 为 EI 提供数据源

