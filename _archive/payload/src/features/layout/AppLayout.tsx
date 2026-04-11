'use client'

import AppSidebar from './AppSidebar'
import AppHeader from './AppHeader'

/**
 * AppLayout — Sidebar + Header + Content 统一布局
 * 用于所有需要侧边栏的页面（问答、资料库、Dashboard）
 *
 * 使用纯 CSS 变量驱动主题，不依赖 useTheme() — 防止刷新时 hydration 不匹配
 * bg-background 对应 var(--background)，由 :root / .dark 选择器控制
 */
export default function AppLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex h-screen w-screen overflow-hidden bg-background transition-colors">
      <AppSidebar />
      <div className="flex-1 min-w-0 flex flex-col overflow-hidden">
        <AppHeader />
        <main className="flex-1 min-h-0 overflow-hidden">
          {children}
        </main>
      </div>
    </div>
  )
}
