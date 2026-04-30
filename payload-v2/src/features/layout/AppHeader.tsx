'use client'

import CountrySelector from '@/features/shared/components/CountrySelector'
import LanguageToggle from '@/features/shared/components/LanguageToggle'
import ThemeToggle from '@/features/shared/components/ThemeToggle'
import UserMenu from './UserMenu'

/**
 * AppHeader — 顶部栏：国家 + 语言 + 主题 + 用户下拉菜单
 */
export default function AppHeader() {
  return (
    <header className="flex items-center justify-end gap-2 px-4 h-12 shrink-0 bg-card border-b border-border transition-colors">
      {/* Country selector */}
      <CountrySelector className="text-muted-foreground hover:bg-secondary" />

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
