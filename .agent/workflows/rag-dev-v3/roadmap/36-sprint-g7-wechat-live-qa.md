# Sprint G7 — 微信直播 Q&A：程序员聊留学移民

> 目标：在现有 `/chat` 模块基础上增加"直播模式"（`?mode=live`），让主播直接用 chat 界面直播，无需维护独立 `/live` 页面。Sidebar 管理模块默认折叠，直播时不干扰画面。
>
> 前置条件：G2 ✅（P0 角色已 Seed）、imm-pathways MinerU 已完成
> **状态**: 🔨 重构中 — 从独立 `/live` 页面迁移到 chat 模块直播模式

## 架构变更：从独立页面到模式切换

### 旧方案（已废弃）
- 独立 `/live` 路由 + `LiveQAPage.tsx` + `live.css`
- 代码重复：Streaming、来源引用、PDF 跳转全部重写

### 新方案
- **复用 `/chat?mode=live`** — ChatPanel 检测 `mode=live` 切换直播样式
- **AppSidebar Admin 区默认折叠** — `<details>` 包裹，直播时不碍眼
- **直播样式覆盖** — 通过 CSS class `.live-mode` 控制大字体、深色强调、隐藏次要元素

```
/chat                → 普通聊天模式（现有行为不变）
/chat?mode=live      → 直播模式（大字体 + 深色强调 + sidebar 折叠）
/chat?mode=consulting → 顾问模式（现有行为不变）
```

---

## 概览

| Task | Story 数 | 预估总工时 | 说明 |
|------|----------|-----------|------|
| T1 知识库 + 混合角色 | 3 | 5.5h | 验证知识库 + 教育补充 + `live-study-immigration` 混合角色 |
| T2 直播模式 UI | 3 | 4h | ChatPanel 直播样式 + Sidebar 折叠 + 品牌水印 |
| T3 Engine 调优 | 2 | 3h | 低延迟 Streaming + 混合角色 Prompt 微调 |
| T4 彩排验收 | 1 | 2h | 20 题压测 + 端到端直播模拟 |
| T5 i18n 双语改造 | 1 | 1.5h | 法语 → 中文，英文 + 中文双语 |
| **合计** | **10** | **16h** |

## 质量门禁

| # | 检查项 | 判定依据 |
|---|--------|----------|
| G1 | 知识库覆盖率 | 20 道高频留学移民问题命中率 ≥ 90% |
| G2 | 回答延迟 | 首 token ≤ 2s，完整回答 ≤ 15s（本地 Ollama） |
| G3 | 直播画面可读性 | 1080p 全屏下问题 + 回答文字清晰可读 |
| G4 | 不破坏现有功能 | 普通聊天、顾问模式、角色选择不受影响 |
| G5 | PDF 来源可跳转 | 点击来源引用可打开原始 PDF 并定位到对应页码 |

---

## [G7-T1] 知识库补全

### [G7-01] imm-pathways 知识库验证 & 补缺 ✅ 已完成 2026-05-05

**类型**: Data
**优先级**: P0 · **预估**: 2h

验证已通过 MinerU 提取的 imm-pathways 文档是否已完整入库 ChromaDB。

#### 验收标准

- [x] Payload `live-questions` collection 已 seed 20 道中英双语高频问题 ✅
- [x] 验证脚本输出覆盖率 >= 90% ✅ (实际 100%: 20/20)
- [x] G1 知识库覆盖率 ✅

---

### [G7-02] edu 教育知识库快速补充

**类型**: Data
**优先级**: P1 · **预估**: 2h

快速爬取 IRCC 学习许可页面 + 主要省份 DLI 列表页面，入库 edu-school-planning collection。

#### 验收标准

- [ ] edu-school-planning collection 中有 ≥ 10 篇学签/DLI 相关文档
- [ ] 5 道教育类预设问题命中率 ≥ 80%

---

### [G7-10] 新建 `live-study-immigration` 混合角色 ✅ 已完成 2026-05-03

**类型**: Backend + Data
**优先级**: P0 · **预估**: 1.5h → **实际**: ~1h

新建直播专用混合角色，合并 `imm-pathways` 和 `edu-school-planning` 两个角色的能力。

#### 验收标准

- [x] Payload personas 中存在 `live-study-immigration` 角色 ✅
- [x] Engine 同时检索两个 collection ✅
- [x] 混合检索结果包含移民和教育两个领域的 chunks ✅

---

## [G7-T2] 直播模式 UI（重构）

### [G7-03] ChatPanel 直播模式样式 🔨 重构

**类型**: Frontend
**优先级**: P0
**预估**: 2h

#### 描述

在现有 ChatPanel 中检测 `mode=live`，应用直播专用样式。**不再新建独立页面**。

#### 实现方案

```typescript
// ChatPanel.tsx — 检测直播模式
const searchParams = useSearchParams()
const isLiveMode = searchParams.get('mode') === 'live'

// 外层容器加 .live-mode class
<div className={cn('chat-container', isLiveMode && 'live-mode')}>
```

```css
/* globals.css — 直播模式样式覆盖 */
.live-mode {
  --chat-font-size: 22px;        /* 回答大字体 */
  --chat-question-size: 28px;    /* 问题更大 */
  --chat-max-width: 900px;       /* 更宽的内容区 */
}
.live-mode .message-bubble {
  font-size: var(--chat-font-size);
  line-height: 1.6;
}
.live-mode .message-question {
  font-size: var(--chat-question-size);
  font-weight: 600;
}
```

#### 验收标准

- [ ] `/chat?mode=live` 显示大字体直播样式
- [ ] `/chat` 普通模式不受影响
- [ ] 1080p 全屏下文字清晰可读
- [ ] 默认使用 `live-study-immigration` 角色
- [ ] Streaming 打字机效果正常（复用已有 SSE）
- [ ] 来源引用可点击跳转 PDF（复用已有逻辑）

#### 文件

- `payload-v2/src/features/chat/panel/ChatPanel.tsx` (改造 — 增加 isLiveMode 分支)
- `payload-v2/src/app/(frontend)/globals.css` (改造 — 增加 .live-mode 样式)

---

### [G7-12] AppSidebar 管理模块默认折叠 🆕

**类型**: Frontend
**优先级**: P0
**预估**: 1h

#### 描述

AppSidebar 中 Admin 管理区（10 个导航链接）默认折叠，点击展开。直播时管理入口不占屏幕空间。所有用户角色通用改动，非直播模式也受益。

#### 实现方案

```typescript
// AppSidebar.tsx — Admin 区用 state 控制折叠
const [adminExpanded, setAdminExpanded] = useState(false)

// Admin section
{isAdmin && (
  <div className={cn('shrink-0 border-t border-sidebar-border py-2', collapsed ? 'px-1' : 'px-2')}>
    <button
      onClick={() => setAdminExpanded(v => !v)}
      className="w-full flex items-center justify-between px-3 py-1"
    >
      <span className="text-[10px] font-semibold uppercase tracking-wider text-muted-foreground">
        {t.navGroupAdmin}
      </span>
      <ChevronDown size={12} className={cn(
        'text-muted-foreground transition-transform',
        adminExpanded && 'rotate-180'
      )} />
    </button>
    {adminExpanded && (
      <nav className="flex flex-col gap-0.5 mt-1">
        {adminLinks.map((item) => navLink(item.href, item.icon, String(t[item.titleKey])))}
      </nav>
    )}
  </div>
)}
```

#### 验收标准

- [ ] Admin 管理区默认折叠，点击标题展开
- [ ] 折叠状态不影响 sidebar collapsed（图标模式）的行为
- [ ] 现有管理页面导航功能不受影响
- [ ] 直播模式下 sidebar 更清爽

#### 文件

- `payload-v2/src/features/layout/AppSidebar.tsx` (改造)

---

### [G7-05] 品牌水印 & 二维码叠加 ✅ 部分完成

**类型**: Frontend
**优先级**: P1 · **预估**: 1h

在直播模式下右下角显示品牌水印。复用现有实现，仅在 `isLiveMode` 时渲染。

#### 验收标准

- [x] 右下角显示品牌水印（半透明 "Powered by ConsultRAG"）✅
- [ ] 二维码图片可通过配置替换
- [x] 水印不遮挡问答区域 ✅

---

## [G7-T3] Engine 调优

### [G7-06] Streaming 低延迟优化

**类型**: Backend
**优先级**: P0 · **预估**: 1.5h

优化 Engine Streaming 路径：检索并行化 + top-k 截断 + SSE 逐 token 推送。

#### 验收标准

- [ ] 首 token 延迟 ≤ 2s — **当前 3.8s，需裁剪 multiCollections 或降 top_k**
- [x] 完整回答 ≤ 15s ✅ (实际 10.3s)

---

### [G7-07] 混合角色 Prompt 模板 ✅ 已完成 2026-05-03

**类型**: Backend
**优先级**: P0

System Prompt 已内嵌在 `live-study-immigration.ts` persona seed 中。

#### 验收标准

- [x] 系统提示词融合移民+留学双视角 ✅
- [x] 20 道测试问题回答风格符合口语化要求 ✅ (benchmark 5.0/5)

---

## [G7-T4] 彩排验收

### [G7-08] 端到端直播模拟 & 20 题压测 ✅ 已完成 2026-05-05

**类型**: QA
**优先级**: P0 · **预估**: 2h

#### 验收标准

- [x] 20 题全部有回答，无超时或报错 ✅
- [x] 平均回答质量 ≥ 3.5/5 ✅ (实际 5.0/5)
- [ ] 快速连续提问 5 题无崩溃 (--rapid 模式待执行)
- [x] G1 知识库覆盖率 ✅ (100%)
- [x] G2 总延迟 ✅ (10.3s < 15s)

---

## [G7-T5] i18n 双语改造

### [G7-11] i18n 法语替换为中文 ✅ 已完成 2026-05-03

**类型**: Frontend
**优先级**: P0 · **预估**: 1.5h → **实际**: ~2h

#### 验收标准

- [x] `Locale` 类型为 `'en' | 'zh'` ✅
- [x] `messages.ts` 中 `zh` 字典包含所有 key 的中文翻译 ✅
- [x] `fr` 字典已移除 ✅
- [x] `next-intl` 已集成 ✅

---

## 废弃文件清理

以下文件在重构后可删除：

```
payload-v2/src/app/(frontend)/live/
├── page.tsx              ← 删除（不再需要独立路由）
├── LiveQAPage.tsx        ← 删除（逻辑合并到 ChatPanel）
└── live.css              ← 删除（样式合并到 globals.css .live-mode）
```

保留的直播相关代码：
- `payload-v2/src/seed/consulting-personas/immigration/live-study-immigration.ts` — 混合角色 seed
- `scripts/live_qa/benchmark.py` — 压测脚本
- `messages/*/live.json` — 直播预设问题字典

## 模块文件变更

```
textbook-rag/
+-- scripts/live_qa/
|   +-- verify_knowledge.py                     ← ✅ 已完成
|   +-- benchmark.py                            ← ✅ 已完成
+-- engine_v2/
|   +-- retrievers/consulting.py                ← ✅ 已完成 (multi_collection_retrieve)
|   +-- api/routes/consulting.py                ← ✅ 已完成 (multiCollections 支持)
+-- payload-v2/
    +-- src/features/chat/panel/ChatPanel.tsx    ← 🔨 改造 (增加 isLiveMode 样式分支)
    +-- src/features/layout/AppSidebar.tsx       ← 🔨 改造 (Admin 区默认折叠)
    +-- src/app/(frontend)/globals.css           ← 🔨 改造 (增加 .live-mode CSS)
    +-- src/app/(frontend)/live/                 ← ❌ 删除 (独立页面废弃)
```

## 执行顺序

| Phase | Tasks | Est. | 备注 |
|-------|-------|------|------|
| **Phase 0** ✅ | G7-11 | 2h | i18n 中文化 ✅ |
| **Phase 1** ✅ | G7-01, G7-10, G7-07 | 4.5h | 知识库 + 混合角色 + Prompt ✅ |
| **Phase 2** 🔨 | **G7-03 重构**, **G7-12 新增**, G7-05 | 4h | 直播模式 UI：ChatPanel 样式 + Sidebar 折叠 |
| **Phase 3** | G7-06, G7-02 | 3.5h | Engine 延迟优化 + 教育知识库 |
| **Phase 4** | G7-08 复测 | 1h | 重构后端到端验证 |
