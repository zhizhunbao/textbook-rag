# Sprint C1 — 用户身份 + 首次引导

> 目标：完成注册/登录流程增强，首次登录自动弹出角色选择页，选择后进入咨询主界面。
>
> 前置条件：无（全新业务线起点）
> **状态**: ✅ 8/8 完成

## 概览

| Task | Story 数 | 预估总工时 | 说明 |
|------|----------|-----------|------|
| T1 数据层准备 | 3 | 2.5h | Users 扩展 + ConsultingPersonas 集合 + Seed |
| T2 登录增强 + 引导页 | 3 | 4h | LoginForm 增强 + OnboardingPage + 路由薄壳 |
| T3 布局集成 | 2 | 1.5h | Sidebar 角色指示器 + 路由守卫 |
| **合计** | **8** | **8h** |

## 质量门禁

| # | 检查项 | 判定依据 |
|---|--------|----------|
| G1 | 模块归属 | OnboardingPage 在 `features/onboarding/`；PersonaSelectorPanel 在 `features/shared/components/` |
| G2 | 数据流方向 | 前端通过 `/api/consulting-personas` 读角色列表；不直接调 Engine |
| G3 | 不破坏现有 | 现有 Users / ChatSessions / LoginForm 行为不变 |
| G4 | 命名对齐 | Collection slug = `consulting-personas`；前端目录 = `onboarding/` |

---

## [C1-T1] 数据层准备

### [C1-01] Users Collection 增加 selectedPersona + isOnboarded 字段

**类型**: Backend (Payload) · **优先级**: P0 · **预估**: 0.5h

**描述**: Users 集合新增两个字段，记录用户当前选中角色和是否完成首次引导。

**Schema 变更**:
```
Users {
  ...existing fields...
  selectedPersona: relationship → consulting-personas (optional)
  isOnboarded: checkbox (default: false)
}
```

**验收标准**:
- [ ] `selectedPersona` 字段类型 `relationship`，`relationTo: 'consulting-personas'`
- [ ] `isOnboarded` 字段类型 `checkbox`，`defaultValue: false`
- [ ] 现有 Users 数据不受影响 (新字段均 optional)
- [ ] G3 ✅ 向后兼容

**文件**: `payload-v2/src/collections/Users.ts` (改造)

### [C1-02] 新建 ConsultingPersonas Collection

**类型**: Backend (Payload) · **优先级**: P0 · **预估**: 1h

**描述**: 预设咨询角色定义表。每个角色包含名称、图标、描述、人设 Prompt、绑定的 ChromaDB collection 名。

**Schema**:
```
ConsultingPersonas {
  name: text (required) — "律师" / "合规顾问" / "审计检查员"
  slug: text (required, unique, index) — "lawyer" / "compliance" / "auditor"
  icon: text — Lucide icon name (e.g. "scale", "shield-check", "clipboard-check")
  description: textarea — 角色能力简介
  systemPrompt: textarea (rows: 10) — 人设 Prompt 全文
  chromaCollection: text (required) — ChromaDB collection 名 (e.g. "persona_lawyer")
  isEnabled: checkbox (default: true)
  sortOrder: number (default: 0)
}
```

**访问控制**:
- read: 所有已认证用户
- create / update / delete: admin only

**验收标准**:
- [ ] 新文件 `payload-v2/src/collections/ConsultingPersonas.ts`
- [ ] Admin UI group: `Consulting`
- [ ] `useAsTitle: 'name'`
- [ ] slug 字段 unique + index
- [ ] payload.config.ts 注册此 Collection
- [ ] G4 ✅ slug = `consulting-personas`

**文件**: `payload-v2/src/collections/ConsultingPersonas.ts` (新增), `payload-v2/src/payload.config.ts` (改造)

### [C1-03] 角色 Seed 数据 — 预置 律师 / 合规 / 审计

**类型**: Backend (Payload) · **优先级**: P0 · **预估**: 1h

**描述**: 系统启动时预置三个咨询角色，含完整 systemPrompt。

**预置角色**:

| slug | name | icon | chromaCollection |
|------|------|------|------------------|
| `lawyer` | 法律顾问 | `scale` | `persona_lawyer` |
| `compliance` | 合规顾问 | `shield-check` | `persona_compliance` |
| `auditor` | 审计检查员 | `clipboard-check` | `persona_auditor` |

**systemPrompt 格式**:
```
你是一位专业的{角色名}。基于以下参考材料回答用户的咨询问题。

你的专业领域: {角色描述}
你的回答风格:
- 使用专业术语并给出通俗解释
- 引用具体法条/条款/标准编号 (如适用)
- 给出明确的行动建议
- 标注风险等级和注意事项

参考材料:
{context_str}

用户问题: {query_str}
```

**验收标准**:
- [ ] 新文件 `payload-v2/src/seed/consulting-personas.ts`
- [ ] 三个角色各有完整 systemPrompt
- [ ] seed/index.ts 中注册调用
- [ ] 幂等 (重复执行不创建重复数据，用 slug upsert)

**文件**: `payload-v2/src/seed/consulting-personas.ts` (新增), `payload-v2/src/seed/index.ts` (改造)

---

## [C1-T2] 登录增强 + 引导页

### [C1-04] LoginForm 增强 — 登录后检查 isOnboarded

**类型**: Frontend · **优先级**: P0 · **预估**: 1h

**描述**: 登录成功后检查 `user.isOnboarded`，未完成则 redirect 到 `/onboarding`，已完成则进入 `/consulting`。

**实现方案**:
- 登录成功回调中读取 `user.isOnboarded`
- `isOnboarded === false` → `router.push('/onboarding')`
- `isOnboarded === true` → `router.push('/consulting')`

**验收标准**:
- [ ] 登录后根据 isOnboarded 自动跳转
- [ ] 不影响 Admin 用户 (admin 始终进 admin panel)
- [ ] G3 ✅ 现有 LoginForm 样式/功能不变

**文件**: `payload-v2/src/features/auth/LoginForm.tsx` (改造)

### [C1-05] OnboardingPage — 角色选择卡片网格

**类型**: Frontend · **优先级**: P0 · **预估**: 2h

**描述**: 全屏引导页，展示所有启用角色的卡片网格，用户选择后写回 `selectedPersona` + `isOnboarded=true`。

**Layout**:
```
┌──────────────────────────────────────────────┐
│           欢迎！请选择您的咨询服务              │
│                                              │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐   │
│  │  ⚖ 法律  │  │ 🛡 合规  │  │ 📋 审计  │   │
│  │  顾问    │  │  顾问    │  │ 检查员   │   │
│  │          │  │          │  │          │   │
│  │ 提供法律 │  │ 合规风控 │  │ 审计检查 │   │
│  │ 咨询建议 │  │ 咨询分析 │  │ 专业解读 │   │
│  └──────────┘  └──────────┘  └──────────┘   │
│                                              │
│              [确认选择 →]                     │
└──────────────────────────────────────────────┘
```

> 图标用 lucide-react SVG，不用 emoji

**数据获取**:
- `usePersonas()` hook 从 `/api/consulting-personas?where[isEnabled][equals]=true` 拉取列表
- 确认后 `PATCH /api/users/{id}` 写入 `selectedPersona` + `isOnboarded: true`

**验收标准**:
- [ ] 新文件 `features/onboarding/OnboardingPage.tsx`
- [ ] 新文件 `features/onboarding/usePersonas.ts`
- [ ] 卡片显示 icon (SVG) + name + description
- [ ] 选中态高亮 + 确认按钮
- [ ] 确认后写回 Users 并跳转 `/consulting`
- [ ] 响应式 (desktop 3列，tablet 2列，mobile 1列)
- [ ] G1 ✅ 在 `features/onboarding/`

**文件**: `features/onboarding/OnboardingPage.tsx` (新增), `features/onboarding/usePersonas.ts` (新增)

### [C1-06] `/onboarding` 路由 page.tsx 薄壳

**类型**: Frontend · **优先级**: P0 · **预估**: 0.5h

**描述**: Next.js App Router 路由文件，只 import OnboardingPage 并渲染。

**验收标准**:
- [ ] 新文件 `app/(frontend)/onboarding/page.tsx`
- [ ] 薄壳：`import { OnboardingPage } from '@/features/onboarding/OnboardingPage'`
- [ ] G4 ✅ 命名对齐

**文件**: `payload-v2/src/app/(frontend)/onboarding/page.tsx` (新增)

---

## [C1-T3] 布局集成

### [C1-07] AppSidebar 增加角色指示器

**类型**: Frontend · **优先级**: P1 · **预估**: 1h

**描述**: Sidebar 底部 (或顶部) 显示当前选中角色的 icon + name，点击可进入角色切换。

**验收标准**:
- [ ] Sidebar 显示当前角色名称 + icon (SVG)
- [ ] 无角色时显示 "未选择角色"
- [ ] 点击角色区域跳转 `/onboarding` (重新选择)
- [ ] G1 ✅ 在 `features/layout/`

**文件**: `payload-v2/src/features/layout/AppSidebar.tsx` (改造)

### [C1-08] 路由守卫 — 未登录/未引导 重定向

**类型**: Frontend · **优先级**: P1 · **预估**: 0.5h

**描述**: 前端 Layout 层检查用户状态，自动重定向。

**逻辑**:
```
未登录 → /login
已登录 + 未 onboard → /onboarding
已登录 + 已 onboard → 正常渲染
```

**验收标准**:
- [ ] `(frontend)/layout.tsx` 中增加守卫逻辑
- [ ] 不影响 `/login` 页面本身 (避免死循环)
- [ ] Admin 用户跳过守卫

**文件**: `payload-v2/src/app/(frontend)/layout.tsx` (改造)

---

## 模块文件变更

```
payload-v2/src/
├── collections/
│   ├── Users.ts                        ← 改造 (新增 selectedPersona + isOnboarded)
│   └── ConsultingPersonas.ts           ← 新增
├── seed/
│   ├── consulting-personas.ts          ← 新增
│   └── index.ts                        ← 改造 (注册 consulting-personas seed)
├── payload.config.ts                   ← 改造 (注册 ConsultingPersonas)
├── app/(frontend)/
│   ├── layout.tsx                      ← 改造 (路由守卫)
│   └── onboarding/
│       └── page.tsx                    ← 新增
└── features/
    ├── auth/
    │   └── LoginForm.tsx               ← 改造 (登录后跳转逻辑)
    ├── onboarding/
    │   ├── OnboardingPage.tsx          ← 新增
    │   └── usePersonas.ts             ← 新增
    └── layout/
        └── AppSidebar.tsx             ← 改造 (角色指示器)
```

---

## 执行顺序

| Phase | Tasks | Est. Time | 前置 | 备注 |
|-------|-------|-----------|------|------|
| **Phase 1** | C1-01, C1-02 (数据层) | 1.5h | 无 | 可并行 |
| **Phase 2** | C1-03 (Seed 数据) | 1h | Phase 1 | 依赖 Collection 存在 |
| **Phase 3** | C1-05, C1-06 (引导页 + 路由) | 2.5h | Phase 1 | 需读取角色列表 |
| **Phase 4** | C1-04 (登录增强) | 1h | Phase 3 | 需引导页存在 |
| **Phase 5** | C1-07, C1-08 (布局 + 守卫) | 1.5h | Phase 4 | 收尾集成 |
