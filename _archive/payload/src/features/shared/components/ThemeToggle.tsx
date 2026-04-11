'use client'

import { useTheme } from '@/features/shared/theme'
import { Sun, Moon } from 'lucide-react'
import { useEffect, useState } from 'react'

/**
 * ThemeToggle — 亮色/暗色主题切换按钮
 * 太阳 ↔ 月亮 图标切换（使用 Lucide 图标，视觉更清晰）
 */
export default function ThemeToggle({ className = '', style }: { className?: string; style?: React.CSSProperties }) {
  const { theme, toggleTheme } = useTheme()
  const [mounted, setMounted] = useState(false)

  useEffect(() => setMounted(true), [])

  // Prevent hydration mismatch — render a placeholder until mounted
  if (!mounted) {
    return (
      <button className={`inline-flex items-center justify-center w-8 h-8 rounded-lg ${className}`} style={style}>
        <Sun className="h-4 w-4 opacity-50" />
      </button>
    )
  }

  return (
    <button
      onClick={toggleTheme}
      className={`inline-flex items-center justify-center w-8 h-8 rounded-lg transition-all duration-200 ${className}`}
      style={style}
      title={theme === 'light' ? 'Switch to dark mode' : 'Switch to light mode'}
      aria-label={theme === 'light' ? 'Switch to dark mode' : 'Switch to light mode'}
    >
      {theme === 'light' ? (
        <Moon className="h-4 w-4" />
      ) : (
        <Sun className="h-4 w-4" />
      )}
    </button>
  )
}
