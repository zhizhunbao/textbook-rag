'use client'

import LanguageToggle from '@/features/shared/components/LanguageToggle'
import ThemeToggle from '@/features/shared/components/ThemeToggle'
import UserMenu from '@/features/chat/UserMenu'

/**
 * AppHeader — 顶部栏：语言切换 + 主题切换 + 用户下拉菜单
 * 精简设计：图标 + 头像，点击头像展开详细菜单
 */
export default function AppHeader() {
  return (
    <header className="flex items-center justify-end gap-2 px-4 h-12 shrink-0 bg-card border-b border-border transition-colors">
      {/* Language toggle */}
      <LanguageToggle className="text-muted-foreground hover:bg-secondary" />

      {/* Theme toggle */}
      <ThemeToggle className="text-muted-foreground hover:bg-secondary" />

      {/* Divider */}
      <div className="w-px h-5 bg-border" />

      {/* User dropdown menu */}
      <UserMenu />
    </header>
  )
}
