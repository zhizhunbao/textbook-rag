# Sprint G3 — Landing 页重构 🔴 Tier 1

> 目标：Landing 页改为 PRD v2 的 7 大类卡片 + 国家选择布局，Onboarding 按类分组，咨询页优化。
>
> 前置条件：Sprint G1 ✅ 国家/语种选择器已完成
> **状态**: ✅ 18/22 — 核心完成，4 项低优先级延后 (G3-01 API化→G5, G3-02 lucide→Won't Do, G3-04/05→P2)
> **优先级**: 🔴 Tier 1 关键路径 — G3-01/02/03 最高优先，G3-04/05 降为 Tier 3

## 概览

| Task | Story 数 | 预估总工时 | 说明 |
|------|----------|-----------|------|
| T1 Landing 重构 | 2 | 6h | 7 类目卡片布局 + 顾问小卡片组件 |
| T2 Onboarding 适配 | 1 | 2.5h | 按 7 大类分组展示角色 |
| T3 咨询页优化 | 2 | 3.5h | 角色/国家标识 + 多语言适配 |
| **合计** | **5** | **12h** |

## 质量门禁

| # | 检查项 | 判定依据 |
|---|--------|----------|
| G1 | 数据流方向 | 前端从 `/api/consulting-personas` 按 category 分组；不直接调 Engine |
| G2 | 响应式布局 | Desktop 3列 / Tablet 2列 / Mobile 1列 |
| G3 | 7 类目完整 | 7 个大类卡片全部展示，空类目显示"即将推出" |
| G4 | 不破坏认证流 | 登录 → Onboarding → 选角色 → 咨询 全流程不变 |

---

## [G3-T1] Landing 重构

### [G3-01] Landing 页 7 大类目卡片布局

**类型**: Frontend
**优先级**: P0
**预估**: 4h

#### 描述

重构 `HomePage` 为"咨询入口"模式：简化 Hero → 7 大类卡片网格 → 每类下平铺顾问小卡片。
数据源从 Payload API 获取已启用角色，按 `category` 分组渲染。

#### 类目定义

```typescript
const CATEGORIES = [
  { value: 'education',    label: 'Education',     icon: 'graduation-cap', emoji: '🎓' },
  { value: 'immigration',  label: 'Immigration',   icon: 'plane',          emoji: '🛂' },
  { value: 'settlement',   label: 'Settlement',    icon: 'home',           emoji: '🏠' },
  { value: 'healthcare',   label: 'Healthcare',    icon: 'heart-pulse',    emoji: '🏥' },
  { value: 'finance',      label: 'Finance',       icon: 'dollar-sign',    emoji: '💰' },
  { value: 'career',       label: 'Career',        icon: 'briefcase',      emoji: '💼' },
  { value: 'legal',        label: 'Legal',         icon: 'scale',          emoji: '⚖️' },
]
```

#### 验收标准

- [x] `HomePage.tsx` 重构为 7 类目卡片布局
- [ ] 数据从 Payload API 按 `category` 分组获取（带 `country` 过滤） — ⚠️ 当前用硬编码 `ALL_ROLES`
- [x] 空类目（无启用角色）显示"Coming soon"
- [x] 响应式：Desktop 3列 / Tablet 2列 / Mobile 1列

#### 文件

- `payload-v2/src/features/home/HomePage.tsx` (改造)
- `payload-v2/src/features/home/CategoryCard.tsx` (新增)

---

### [G3-02] 顾问小卡片组件

**类型**: Frontend
**优先级**: P0
**预估**: 2h

#### 描述

新建 `AdvisorCard` 组件，作为 Landing 页类目展开后的子卡片。
展示角色图标、名称、一句话服务范围、【Start Consulting】按钮。

#### 验收标准

- [x] 新文件 `features/home/AdvisorCard.tsx`
- [ ] 显示角色图标（lucide-react 动态渲染） — ⚠️ 设计决策：保留 Avatar 图片/首字母，比 lucide 图标更专业
- [x] 显示角色名称
- [x] 显示一句话服务范围
- [x] 按钮 → 跳转 `/consulting?persona={slug}`
- [x] 卡片 hover 效果：微上移 + 阴影增强
- [x] 知识库为空时按钮显示"Knowledge base preparing" 并 disabled — ⚠️ AdvisorCard 组件已支持 `hasKnowledgeBase` prop，但 Landing 页未接入实际状态数据（P2 后续接入）

#### 文件

- `payload-v2/src/features/home/AdvisorCard.tsx` (新增)

---

## [G3-T2] Onboarding 适配

### [G3-03] Onboarding 页按 7 大类分组展示

**类型**: Frontend
**优先级**: P1
**预估**: 2.5h

#### 描述

当前 `OnboardingPage` 平铺展示所有角色卡片，改为按 7 大类分组展示。
复用 `AdvisorCard` 组件。

#### 验收标准

- [x] `OnboardingPage.tsx` 改为按 category 分组渲染
- [x] 7 个类目均有标题（icon + 英文名）
- [x] 每组内使用 `AdvisorCard` 渲染角色卡片
- [x] 空类目不显示
- [x] 选择后正常写回 `Users.selectedPersona` + `isOnboarded: true`

#### 文件

- `payload-v2/src/features/onboarding/OnboardingPage.tsx` (改造)

---

## [G3-T3] 咨询页优化

### [G3-04] 咨询页顶部角色 + 国家标识

**类型**: Frontend
**优先级**: P1
**预估**: 1.5h

#### 描述

在 ChatPanel 顶部导航增加角色和国家标识。
点击标识可返回 Landing 页类目选择。

#### 验收标准

- [x] ChatPanel 标题显示当前角色名 + 描述
- [ ] 点击标识区域跳转到 Landing 页
- [x] Consulting 模式以外显示 ConsultRAG 默认名

#### 文件

- `payload-v2/src/features/chat/panel/ChatPanel.tsx` (改造)

---

### [G3-05] 咨询页 UI 优化

**类型**: Frontend
**优先级**: P1
**预估**: 2h

#### 描述

审查咨询相关页面，确保 UI 一致性和专业感。
所有文案通过 i18n 字典管理。

#### 验收标准

- [ ] WelcomeScreen 显示角色名
- [x] Error toast 文案清晰
- [x] Citation label 显示 "Sources"
- [x] 全面审查后 UI 一致
- [x] 全局 "EcDev Research" → "ConsultRAG" 改名（i18n `messages.ts` + `ChatHeader.tsx` 硬编码）

#### 文件

- `payload-v2/src/features/chat/panel/ChatPanel.tsx` (改造)
- `payload-v2/src/features/chat/panel/WelcomeScreen.tsx` (改造)

---

## 执行顺序

| Phase | Tasks | Est. Time | 前置 | 备注 |
|-------|-------|-----------|------|------|
| **Phase 1** | G3-02 | 2h | 无 | 先做可复用组件 |
| **Phase 2** | G3-01, G3-03 | 6.5h | Phase 1 | 可并行 |
| **Phase 3** | G3-04, G3-05 | 3.5h | G1 完成 | 可并行 |
