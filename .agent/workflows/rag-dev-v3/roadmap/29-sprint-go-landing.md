# Sprint GO-LAND — 获客入口 (Landing & Launch)

> 目标：用户能发现产品、了解价值、完成注册。
>
> 前置条件：Sprint GO-DEPLOY ✅ (产品已上线)
> **状态**: ❌ 0/5 未开始

## 概览

| Task | Story 数 | 预估总工时 | 说明 |
|------|----------|-----------|------|
| T1 Landing Page | 2 | 3.5h | 产品介绍 + 价值主张 + CTA |
| T2 定价页 | 1 | 1.5h | Free vs Pro 功能对比 |
| T3 信任建设 | 2 | 3h | Demo 演示 + 法律合规 |
| **合计** | **5** | **8h** |

---

## [GO-LAND-T1] Landing Page

### [GO-LAND-01] 一页式产品介绍

**类型**: Frontend · **优先级**: P0 · **预估**: 2.5h

**描述**: 面向潜在用户的产品首页 (非登录后首页)。

**验收标准**:
- [ ] 新文件 `app/(frontend)/landing/page.tsx` 或改造根 `/` 页面
- [ ] Hero: 标语 + 副标题 + "开始免费使用" CTA
- [ ] Features: 3-4 个核心卖点 (多角色咨询/私有文档/AI 回答/引用溯源)
- [ ] How it works: 3 步使用流程
- [ ] CTA: 注册按钮 → /register
- [ ] 响应式布局 (手机/平板/桌面)
- [ ] SEO: title / meta description / OpenGraph tags

### [GO-LAND-02] 产品演示展示

**类型**: Frontend · **优先级**: P1 · **预估**: 1h

**验收标准**:
- [ ] 录制一段 30s 产品使用 GIF/视频
- [ ] 嵌入 Landing Page 的 Features 区域
- [ ] 展示: 选角色 → 提问 → 流式回答 → 引用来源

---

## [GO-LAND-T2] 定价页

### [GO-LAND-03] Free vs Pro 对比

**类型**: Frontend · **优先级**: P0 · **预估**: 1.5h

**验收标准**:
- [ ] 新文件 `app/(frontend)/pricing/page.tsx`
- [ ] 双列卡片: Free / Pro
- [ ] Free: 10 次/天, 3 文档/月, 基础角色
- [ ] Pro: 200 次/天, 100 文档/月, 全部角色, 优先回答
- [ ] Pro 卡片 CTA → Stripe Checkout
- [ ] Landing Page 导航链接到定价页

---

## [GO-LAND-T3] 信任建设

### [GO-LAND-04] 法律合规页面

**类型**: Frontend · **优先级**: P1 · **预估**: 1.5h

**验收标准**:
- [ ] `/terms` — Terms of Service (服务条款)
- [ ] `/privacy` — Privacy Policy (隐私政策)
- [ ] 注册页面勾选 "同意服务条款和隐私政策"
- [ ] 底部导航包含 Terms / Privacy 链接

### [GO-LAND-05] SEO 基础

**类型**: Frontend · **优先级**: P2 · **预估**: 1.5h

**验收标准**:
- [ ] 所有页面有合适的 `<title>` 和 `<meta description>`
- [ ] OpenGraph / Twitter Card meta tags
- [ ] robots.txt + sitemap.xml
- [ ] JSON-LD structured data (Product schema)

---

## 执行顺序

| Phase | Tasks | Est. Time | 前置 |
|-------|-------|-----------|------|
| **Phase 1** | GO-LAND-01, GO-LAND-03 | 4h | GO-DEPLOY ✅ |
| **Phase 2** | GO-LAND-02, GO-LAND-04, GO-LAND-05 | 4h | Phase 1 |
