# `shared` — 公共基础设施

> 跨模块共享的 Context、Provider、Hook、组件、类型、工具。

```
Func
全局状态
认证守卫
国际化支
主题切换
文档共享
打字动效

Noun
App
Auth
User
Provider
I18n
Locale
Theme
Book
Sidebar
Layout
Config
```

```
shared
└── payload-v2/src/features/shared/
    ├── AppContext.tsx                       全局状态 Context + Reducer
    ├── AuthProvider.tsx                     JWT 认证 Context + useAuth
    ├── Providers.tsx                        顶层 Provider 组合
    ├── ResizeHandle.tsx                     可拖拽分隔条
    ├── types.ts                            SourceInfo 等共享类型
    ├── utils.ts                            cn() 等工具函数
    ├── books/\n    │   ├── types.ts                        BookBase 类型\n    │   ├── api.ts                          fetchBooks API\n    │   ├── useBooks.ts                     书籍列表 hook\n    │   ├── useBookSidebar.ts              分类侧栏 hook\n    │   └── index.ts                        barrel export
    ├── components/
    │   ├── SidebarLayout.tsx               通用侧栏布局 (12 KB)
    │   ├── ComingSoon.tsx                  占位页组件
    │   ├── DashboardShell.tsx              仪表盘壳
    │   ├── LanguageToggle.tsx              语言切换
    │   ├── ThemeToggle.tsx                 主题切换
    │   ├── charts/                         图表组件
    │   └── ui/                             基础 UI 原子组件
    ├── hooks/
    │   └── useSmoothText.ts               打字机效果 hook
    ├── i18n/
    │   ├── I18nProvider.tsx                国际化 Context
    │   ├── messages.ts                     中英文消息
    │   └── index.ts                        barrel export
    ├── theme/                              主题配置
    └── config/                             全局配置
```
