# Sprint GO-MON — 计费与付费墙 (Monetization)

> 目标：区分 Free/Pro 用户，设置使用限制，接入支付。没有限制就没有付费。
>
> 前置条件：Sprint GO-MU ✅ (用户注册 + API 认证)
> **状态**: ✅ 8/8 完成

## 概览

| Task | Story 数 | 预估总工时 | 说明 |
|------|----------|-----------|------|
| T1 用量计量 | 2 | 4h | ✅ 查询计数中间件 + UsageRecords Collection (简化: 计数而非 token) |
| T2 用户等级 | 2 | 3h | ✅ Free/Pro tier + 额度限制逻辑 |
| T3 付费墙 UI | 2 | 4h | ✅ 额度展示 + 升级引导弹窗 |
| T4 Stripe 集成 | 2 | 4h | ✅ `@payloadcms/plugin-stripe` 替代手写 |
| **合计** | **8** | **15h** |

## 质量门禁

| # | 检查项 | 判定依据 |
|---|--------|----------|
| G1 | 计量准确 | 每次查询的 input/output tokens 被记录，可在 Admin 中查看 |
| G2 | 限制生效 | Free 用户超额后弹出升级引导，无法继续查询 |
| G3 | 支付闭环 | Stripe 付款成功 → 用户 tier 自动升级为 Pro |

---

## [GO-MON-T1] 用量计量

### [GO-MON-01] Token 计量中间件

**类型**: Backend (Engine) · **优先级**: P0 · **预估**: 2h

**描述**: 在查询端点的 response 流中记录 token 使用量。

**验收标准**:
- [x] 查询完成后，通过 Payload REST API 写入 UsageRecords
- [x] 记录: user_id, endpoint, action(query/ingest), model, timestamp
- [x] **设计变更**: Phase 1 简化为查询计数 (1 record = 1 action)，不追踪 token 数
- [x] 流式查询: 在 `done` 事件后异步写入 UsageRecord (fire-and-forget)

### [GO-MON-02] UsageRecords Collection

**类型**: Backend (Payload) · **优先级**: P0 · **预估**: 2h

**验收标准**:
- [x] 新文件 `collections/UsageRecords.ts`
- [x] Schema: user (rel), endpoint (text), action (select: query/ingest), model (text), personaSlug (text)
- [x] Access: `isOwnerOrAdmin` (read), `isAdmin` (create/update/delete — Engine via API key)
- [x] Admin group: `Billing`
- [x] 索引: user + action

---

## [GO-MON-T2] 用户等级

### [GO-MON-03] Users 表扩展 tier 字段

**类型**: Backend (Payload) · **优先级**: P0 · **预估**: 1h

**验收标准**:
- [x] Users 新增 `tier` select 字段: `free` (默认) / `pro`
- [x] Users 新增 `stripeCustomerId` text 字段 (Stripe 关联)
- [x] **设计变更**: 不加 `tierExpiresAt` — Stripe Subscription 自带过期管理
- [x] 非 admin 不可修改 tier (access control + sanitizeNewUser hook)

### [GO-MON-04] 额度检查逻辑

**类型**: Backend (Engine) · **优先级**: P0 · **预估**: 2h

**描述**: 在查询端点前检查用户剩余额度。

**规则**:
```
Free: 30 queries/day, 3 doc uploads/month
Pro:  200 queries/day, 100 doc uploads/month
```

**验收标准**:
- [x] 新文件 `engine_v2/api/middleware/quota.py` (QuotaMiddleware)
- [x] **设计变更**: 内存滑动窗口计数 (不查 UsageRecords DB), UsageRecords 只做审计日志
- [x] 超额返回 403 + 剩余额度信息 + upgrade_url
- [x] 前端可通过 `GET /engine/billing/me` 查询剩余额度
- [x] 响应 Header: `X-Quota-Limit` + `X-Quota-Remaining`

---

## [GO-MON-T3] 付费墙 UI

### [GO-MON-05] 用量展示面板

**类型**: Frontend · **优先级**: P1 · **预估**: 2h

**验收标准**:
- [x] 新文件 `features/billing/UsagePanel.tsx`
- [x] 展示: 今日查询 X/30, 本月文档 Y/3
- [x] 进度条样式: 绿(0-70%) → 黄(70-90%) → 红(90-100%)
- [x] 在 AppSidebar 中展示 (非 admin, 展开时)
- [x] `useQuota` hook 轮询 `/engine/billing/me` 每 60s

### [GO-MON-06] 升级引导弹窗

**类型**: Frontend · **优先级**: P1 · **预估**: 2h

**验收标准**:
- [x] 新文件 `features/billing/UpgradeModal.tsx`
- [x] 触发: 查询返回 403 额度不足时弹出 (`QuotaExceededError`)
- [x] 展示: Free vs Pro 功能对比表
- [x] CTA: "Upgrade — $19/mo" 按钮 → Stripe Checkout

---

## [GO-MON-T4] Stripe 集成

### [GO-MON-07] Stripe Checkout 创建

**类型**: Backend (Payload) · **优先级**: P1 · **预估**: 2h

**验收标准**:
- [x] **设计变更**: 使用 `@payloadcms/plugin-stripe` 替代手写端点
- [x] 内置 `/api/stripe/rest` REST 代理 (受 Payload ACL 保护)
- [x] 内置 `/api/stripe/webhooks` Webhook 端点
- [x] 前端通过 REST 代理创建 Checkout Session

### [GO-MON-08] Stripe Webhook 处理

**类型**: Backend (Payload) · **优先级**: P1 · **预估**: 2h

**验收标准**:
- [x] `customer.subscription.created` → user.tier = 'pro'
- [x] `customer.subscription.deleted` → user.tier = 'free'
- [x] 签名验证: `STRIPE_WEBHOOKS_ENDPOINT_SECRET`
- [x] `_upgradeUserTier` helper 在 payload.config.ts 中

---

## 执行顺序

| Phase | Tasks | Est. Time | 前置 |
|-------|-------|-----------|------|
| **Phase 1** | GO-MON-02, GO-MON-03 | 3h | GO-MU ✅ |
| **Phase 2** | GO-MON-01, GO-MON-04 | 4h | Phase 1 |
| **Phase 3** | GO-MON-05, GO-MON-06 | 4h | Phase 2 |
| **Phase 4** | GO-MON-07, GO-MON-08 | 4h | Phase 1 |
