# Textbook-RAG v2 — 功能路线图（索引）

> 本文件为 `roadmap/` 目录下各 Sprint 文件的统一索引。
>
> **总进度**: 150/308 stories 完成 (49%), ~630h 总工时
> **上线进度**: GO 系列 0/30 stories (0%), 距离上线收费还需 ~57h

## 文件索引

### 🎯 GO 系列 — 上线收费关键路径（最高优先级）

| 文件 | 类别 | 扫描 | 内容 |
|------|------|------|------|
| [23-sprint-consulting-c4.md](./roadmap/23-sprint-consulting-c4.md) | ✅ **Sprint C4** | ⛔ SKIP | **双库联合检索+会话绑定** — 7 stories, 12h ✅ 7/7 |
| [24-sprint-consulting-c5.md](./roadmap/24-sprint-consulting-c5.md) | ✅ **Sprint C5** | ⛔ SKIP | **交互打磨+咨询历史** — 6 stories, 6h ✅ 5/6 |
| [26-sprint-go-multiuser.md](./roadmap/26-sprint-go-multiuser.md) | ✅ **Sprint GO-MU** | ⛔ SKIP | **多用户加固** — 10 stories, 12h ✅ 10/10 注册+Engine Auth+ACL收紧+限流 |
| [27-sprint-go-monetization.md](./roadmap/27-sprint-go-monetization.md) | ✅ **Sprint GO-MON** | ⛔ SKIP | **计费与付费墙** — 8 stories, 15h ✅ 8/8 QuotaMiddleware+Stripe插件+付费墙UI |
| [28-sprint-go-deployment.md](./roadmap/28-sprint-go-deployment.md) | 🔴 **Sprint GO-DEPLOY** | 🟢 | **部署上线** — 7 stories, 12h ❌ 0/7 Docker+云平台+HTTPS+监控 |
| [29-sprint-go-landing.md](./roadmap/29-sprint-go-landing.md) | 🟢 **Sprint GO-LAND** | 🟢 | **获客入口** — 5 stories, 8h ❌ 0/5 Landing Page+定价页+法律合规 |

### ✅ 已完成 Sprints

| 文件 | 类别 | 扫描 | 内容 |
|------|------|------|------|
| [10-sprint-hotfix.md](./roadmap/10-sprint-hotfix.md) | ✅ Hotfix | ⛔ SKIP | **上传→摄取管线修通** — 7/7 ✅ |
| [01-sprint1.md](./roadmap/01-sprint1.md) | ✅ S1 | ⛔ SKIP | 端到端旅程闭环 — 17/17 ✅ |
| [12-sprint-demo.md](./roadmap/12-sprint-demo.md) | ✅ Demo | ⛔ SKIP | 展示日冲刺 — 14/14 ✅ |
| [13-sprint-question-dataset.md](./roadmap/13-sprint-question-dataset.md) | ✅ QD | ⛔ SKIP | Question Dataset — 11/11 ✅ |
| [14-sprint-eval-curation.md](./roadmap/14-sprint-eval-curation.md) | ✅ EC | ⛔ SKIP | 回答筛选+自动评估 — 9/9 ✅ |
| [16-sprint-eval-v2.md](./roadmap/16-sprint-eval-v2.md) | ✅ EV2 | ⛔ SKIP | 四分类评分+检索溯源 — 13/16 核心完成 |
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
| [15-sprint-model-hub.md](./roadmap/15-sprint-model-hub.md) | ⏸️ MH | 🟢 | 模型库 — 🚧 15/16 ⏳useModels hook合并(延后) |
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

## 🚀 上线收费执行路径（以终为始）

> **唯一目标：用户注册 → 使用 → 付费。** 每个 Sprint 必须在这条链路上。

### Phase 1: 核心交付 — 咨询闭环（~18h）
> 用户能"选角色 → 上传文档 → 提问 → 得到答案"

| 顺序 | Sprint | 状态 | 说明 |
|------|--------|------|------|
| ① | **C4** 双库联合检索+流式 | ✅ 7/7 | 已完成 |
| ② | **C5** 交互打磨+历史 | ✅ 5/6 | C5-03 deferred (Payload Admin UI) |

### Phase 2: 安全加固 — 多用户（~12h）🔴 上线前必须
> 没有这步上线 = 数据裸奔

| 顺序 | Sprint | 状态 | 说明 |
|------|--------|------|------|
| ③ | **GO-MU** 多用户加固 | ❌ 0/10 | 注册流 + Engine API JWT + ACL 收紧 + 限流 |

#### 🔴 多用户安全审计（当前状态）

| 维度 | 红灯问题 | 修复 Sprint |
|------|----------|------------|
| 用户注册 | 无 RegisterForm，Users.create 限 admin | GO-MU-01/02/03 |
| Engine Auth | FastAPI 零认证，user_id 前端传入可伪造 | GO-MU-04/05/06/07 |
| Collection ACL | 10+ 个 Collection `read: () => true` 全公开 | GO-MU-08/09 |
| Rate Limit | 无限流，单用户可刷爆 LLM | GO-MU-10 |

### Phase 3: 商业闭环 — 付费墙（~15h）
> Free/Pro 分层 + 使用限制 + Stripe 付款

| 顺序 | Sprint | 状态 | 说明 |
|------|--------|------|------|
| ④ | **GO-MON** 计费与付费墙 | ❌ 0/8 | Token 计量 + Free/Pro tier + Stripe Checkout |

### Phase 4: 公网发布（~20h）
> localhost → https://your-domain.com

| 顺序 | Sprint | 状态 | 说明 |
|------|--------|------|------|
| ⑤ | **GO-DEPLOY** 部署上线 | ❌ 0/7 | Docker Compose + 云 + HTTPS + 监控 |
| ⑥ | **GO-LAND** 获客入口 | ❌ 0/5 | Landing Page + 定价页 + 法律合规 |

---

### 依赖关系

```
C4 (咨询闭环) ─────────────────┐
                                ├──→ GO-MU (多用户) ──→ GO-MON (付费) ──→ GO-DEPLOY ──→ GO-LAND ──→ 🎉 上线
C5 (精选: 历史列表) ────────────┘                                              |
                                                                              ↓
                                                                    用户注册 → 使用 → 付费
```

### 总工时

| 阶段 | 工时 | 累计 |
|------|------|------|
| Phase 1 (C4+C5) | ~18h | 18h |
| Phase 2 (GO-MU) | ~12h | 30h |
| Phase 3 (GO-MON) | ~15h | 45h |
| Phase 4 (GO-DEPLOY+GO-LAND) | ~20h | **65h** |

---

### 当前推荐动作

1. **C5 启动**: 咨询历史列表 + 基本留存。
2. **GO-MU 启动**: 用户注册 + Engine API 认证 + ACL 收紧 — 多用户安全是上线的硬门槛。
3. **GO-MON 实施**: Token 计量 + Free/Pro + Stripe — 没有付费墙就不可能收钱。
4. **GO-DEPLOY + GO-LAND**: 部署到公网 + 落地页 — 产品触达用户。
