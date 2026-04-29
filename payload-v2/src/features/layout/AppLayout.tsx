'use client'

import { usePathname } from 'next/navigation'
import AppSidebar from './AppSidebar'
import AppHeader from './AppHeader'

/** 不需要 sidebar/header 的公开页面路径 */
const PUBLIC_PATHS = ['/', '/login', '/register']

/**
 * AppLayout — Sidebar + Header + Content 统一布局
 * 公开页面（首页、登录页）跳过 sidebar/header，直接全屏渲染
 * 其余页面（问答、资料库、Dashboard）使用完整布局
 */
export default function AppLayout({ children }: { children: React.ReactNode }) {
  const pathname = usePathname()
  const isPublic = PUBLIC_PATHS.includes(pathname)

  if (isPublic) {
    return <>{children}</>
  }

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
