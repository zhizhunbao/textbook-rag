# 🔧 Features 模块单一职责拆分方案

## 当前模块 vs 职责分析

### 🔴 问题模块

````carousel
### ❌ `chat/` — 上帝模块 (God Module)

**当前状态**: 5 个子目录 + 4 个顶层文件，混合了 4 种不同的关注点

```
chat/
├── ChatPage.tsx          ← 页面路由
├── ResizeHandle.tsx      ← 通用 UI 组件 (不该在这)
├── UserMenu.tsx          ← 布局组件 (不该在这)
├── types.ts              ← 对话类型
├── panel/                ← 聊天面板 (输入/消息/欢迎)
│   ├── ChatHeader.tsx
│   ├── ChatInput.tsx
│   ├── ChatPanel.tsx     ← 12KB 核心逻辑
│   ├── MessageBubble.tsx
│   ├── ModeToggle.tsx
│   ├── SourceCard.tsx
│   └── WelcomeScreen.tsx ← 18KB 太大
├── book/                 ← 书本选择器
├── pdf/                  ← PDF 阅读器 (31KB 巨大组件)
├── history/              ← 聊天历史
└── trace/                ← RAG 溯源面板
```

**SRP 违反**: 聊天、PDF 阅读、溯源调试、书本选择 = 4 个独立关注点

<!-- slide -->

### ❌ `shared/` — 万能垃圾桶

**当前状态**: 混合了 6 种完全不同的关注点

```
shared/
├── AppContext.tsx         ← 应用状态 → 应属于 app/
├── AuthProvider.tsx       ← 认证 → 应合并到 auth/
├── Providers.tsx          ← 组合 Provider → 应属于 app/
├── ResizeHandle.tsx       ← 通用 UI → 应属于 ui/
├── api.ts                 ← Engine API → 应属于独立 api 层
├── types.ts               ← 核心类型 → 应属于独立 types/
├── utils.ts               ← 工具函数
├── components/
│   ├── SidebarLayout.tsx  ← 布局 → 应属于 layout/
│   ├── ComingSoon.tsx     ← 通用 UI
│   ├── DashboardShell.tsx ← 布局 → 应属于 layout/
│   ├── LanguageToggle.tsx ← i18n 组件
│   ├── ThemeToggle.tsx    ← 主题组件
│   ├── charts/            ← 图表组件
│   └── ui/                ← 基础 UI 组件
├── config/                ← 配置
├── i18n/                  ← 国际化
└── theme/                 ← 主题
```

**SRP 违反**: API、类型、UI 组件、状态管理、i18n、主题 = 6 个关注点挤在一起

<!-- slide -->

### ✅ `library/` — 相对规范的模块

```
library/
├── types.ts              ← 类型定义
├── api.ts                ← API 封装
├── useLibraryBooks.ts    ← 数据 hook
├── StatusBadge.tsx       ← UI 组件
├── BookCard.tsx          ← UI 组件
├── LibraryPage.tsx       ← 页面组件
└── index.ts              ← barrel export
```

**评价**: 结构清晰，职责单一。可以作为其他模块的参考模板。

<!-- slide -->

### ✅ `models/` — 结构良好但 api.ts 过大

```
models/
├── types.ts              ← 类型定义 (156 行，合理)
├── api.ts                ← API 封装 (626 行!! 过大)
├── useModels.ts          ← 数据 hook
├── ModelContext.tsx       ← 状态管理
└── index.ts              ← barrel export
```

**评价**: 结构好，但 `api.ts` 626 行包含了:
- Model CRUD
- Provider 健康检测
- Ollama 本地探测
- 自动修补逻辑

应拆为 `api/crud.ts` + `api/health.ts` + `api/discovery.ts`

````

---

## ✅ 目标模块结构

```
features/
├── auth/                    ← 🔐 认证 (不变)
│   ├── LoginForm.tsx
│   ├── AuthProvider.tsx     ← 从 shared 移入
│   └── index.ts
│
├── chat/                    ← 💬 RAG 对话 (精简)
│   ├── types.ts
│   ├── ChatPage.tsx
│   ├── components/
│   │   ├── ChatHeader.tsx
│   │   ├── ChatInput.tsx
│   │   ├── ChatPanel.tsx
│   │   ├── MessageBubble.tsx
│   │   ├── ModeToggle.tsx
│   │   ├── SourceCard.tsx
│   │   └── WelcomeScreen.tsx
│   ├── history/
│   │   ├── ChatHistoryContext.tsx
│   │   ├── ChatHistoryPanel.tsx
│   │   └── useChatHistory.ts
│   └── index.ts
│
├── pdf/                     ← 📄 PDF 阅读器 (从 chat 拆出)
│   ├── PdfViewer.tsx
│   ├── BboxOverlay.tsx
│   └── index.ts
│
├── trace/                   ← 🔍 RAG 溯源 (从 chat 拆出)
│   ├── ThinkingProcessPanel.tsx
│   ├── TraceComponents.tsx
│   ├── TracePanel.tsx
│   └── index.ts
│
├── book-picker/             ← 📚 书本选择 (从 chat 拆出)
│   ├── BookPicker.tsx
│   ├── BookSelector.tsx
│   └── index.ts
│
├── library/                 ← 📖 资料库 (基本不变)
│   ├── types.ts
│   ├── api.ts
│   ├── useLibraryBooks.ts
│   ├── StatusBadge.tsx
│   ├── BookCard.tsx
│   ├── LibraryPage.tsx
│   └── index.ts
│
├── models/                  ← 🤖 模型管理 (拆分 api)
│   ├── types.ts
│   ├── api/
│   │   ├── crud.ts          ← 模型 CRUD
│   │   ├── health.ts        ← 可用性检测
│   │   ├── discovery.ts     ← 本地探测
│   │   └── index.ts         ← re-export all
│   ├── useModels.ts
│   ├── ModelContext.tsx
│   └── index.ts
│
├── home/                    ← 🏠 首页 (不变)
│   └── HomePage.tsx
│
├── layout/                  ← 📐 布局 (扩充)
│   ├── AppHeader.tsx
│   ├── AppLayout.tsx
│   ├── AppSidebar.tsx
│   ├── SidebarLayout.tsx    ← 从 shared 移入
│   ├── DashboardShell.tsx   ← 从 shared 移入
│   ├── ResizeHandle.tsx     ← 从 shared/chat 移入
│   ├── UserMenu.tsx         ← 从 chat 移入
│   └── index.ts
│
├── api/                     ← 🔗 统一 API 层 (从 shared 拆出)
│   ├── engine.ts            ← Engine API (query, books, toc, pdf)
│   ├── payload.ts           ← Payload REST helpers
│   ├── types.ts             ← 请求/响应类型
│   └── index.ts
│
└── ui/                      ← 🎨 基础 UI + 跨切面 (从 shared 拆出)
    ├── components/
    │   ├── ComingSoon.tsx
    │   ├── LanguageToggle.tsx
    │   ├── ThemeToggle.tsx
    │   ├── charts/
    │   └── ui/              ← shadcn 等基础组件
    ├── theme/
    │   ├── ThemeProvider.tsx
    │   └── chart-theme.ts
    ├── i18n/
    │   ├── I18nProvider.tsx
    │   └── messages.ts
    ├── context/
    │   ├── AppContext.tsx    ← 从 shared 移入
    │   └── Providers.tsx    ← 从 shared 移入
    └── index.ts
```

## 文件迁移表

| 原位置 | 目标位置 | 原因 |
|--------|----------|------|
| `chat/book/` | `book-picker/` | 书本选择是独立关注点 |
| `chat/pdf/` | `pdf/` | PDF 阅读是独立关注点 |
| `chat/trace/` | `trace/` | RAG 溯源是独立关注点 |
| `chat/panel/` | `chat/components/` | 重命名，语义更清晰 |
| `chat/UserMenu.tsx` | `layout/UserMenu.tsx` | 用户菜单属于布局 |
| `chat/ResizeHandle.tsx` | `layout/ResizeHandle.tsx` | 拖拽分割属于布局 |
| `shared/api.ts` | `api/engine.ts` | API 层独立 |
| `shared/types.ts` | `api/types.ts` | 跟随 API |
| `shared/AppContext.tsx` | `ui/context/AppContext.tsx` | 应用状态管理 |
| `shared/AuthProvider.tsx` | `auth/AuthProvider.tsx` | 认证相关 |
| `shared/Providers.tsx` | `ui/context/Providers.tsx` | Provider 组合 |
| `shared/ResizeHandle.tsx` | `layout/ResizeHandle.tsx` | 合并重复 |
| `shared/components/SidebarLayout.tsx` | `layout/SidebarLayout.tsx` | 布局组件 |
| `shared/components/DashboardShell.tsx` | `layout/DashboardShell.tsx` | 布局组件 |
| `shared/components/ui/` | `ui/components/ui/` | 基础 UI |
| `shared/components/charts/` | `ui/components/charts/` | 图表 |
| `shared/theme/` | `ui/theme/` | 主题 |
| `shared/i18n/` | `ui/i18n/` | 国际化 |
| `shared/config/` | `ui/config/` | 配置 |
| `models/api.ts` | `models/api/crud.ts` + `health.ts` + `discovery.ts` | SRP 拆分 |

## 执行计划

> [!IMPORTANT]
> 渐进式迁移 — 每步都保证应用可运行

### Phase 1: 无破坏性拆分 (低风险)
1. 创建 `pdf/`, `trace/`, `book-picker/` 新目录
2. 移动文件 + 在旧位置保留 re-export 兼容层
3. 更新 `chat/` 的 import 指向新模块
4. 验证应用正常

### Phase 2: 整理 shared → api/ + ui/ (中风险)
1. 创建 `api/` 和 `ui/` 目录
2. 逐个移动文件
3. 在 `shared/` 保留 re-export 兼容层
4. 全量搜索替换旧 import 路径

### Phase 3: 拆分 models/api.ts (低风险)
1. 将 626 行的 `api.ts` 拆为 3 个文件
2. 通过 `api/index.ts` 保持导出不变

### Phase 4: 清理兼容层 (收尾)
1. 删除 `shared/` 中只剩 re-export 的文件
2. 删除 `chat/` 中移走的子目录
3. 更新所有 import 路径

---

## 模块标准模板

每个 feature 模块应遵循:

```
feature-name/
├── types.ts              ← 类型定义 (必须)
├── api.ts                ← API 调用 (可选)
│   或 api/
│      ├── xxx.ts
│      └── index.ts
├── use[Feature].ts       ← React Hook (可选)
├── [Feature]Context.tsx  ← Context/Provider (可选)
├── components/           ← UI 组件 (可选)
│   └── *.tsx
├── [Feature]Page.tsx     ← 页面级组件 (可选)
└── index.ts              ← barrel export (必须)
```

**规则**:
- ✅ 每个模块只关注一个业务领域
- ✅ 通过 `index.ts` barrel 导出公共接口
- ✅ 类型定义和 API 调用分离
- ❌ 不在模块内放不属于该领域的组件
- ❌ 不创建 "shared" / "common" / "utils" 垃圾桶
