'use client'

import * as React from 'react'
import { ThemeProvider as NextThemesProvider, useTheme as useNextTheme } from 'next-themes'

export type Theme = 'light' | 'dark'

/**
 * ThemeProvider — 基于 next-themes（shadcn 官方模式）
 *
 * 参考: .github/references/shadcn-ui/apps/v4/components/theme-provider.tsx
 *   - attribute="class"  → 在 <html> 上添加 .dark class
 *   - defaultTheme="system" → 跟随系统偏好
 *   - enableSystem → 启用系统主题检测
 *   - disableTransitionOnChange → 切换时禁用 transition 防闪烁
 */
export function ThemeProvider({ children }: { children: React.ReactNode }) {
  return (
    <NextThemesProvider
      attribute="class"
      defaultTheme="dark"
      enableSystem
      disableTransitionOnChange
      enableColorScheme
    >
      {children}
    </NextThemesProvider>
  )
}

/**
 * useTheme — 获取当前主题 + 切换函数
 * 兼容原有 API：theme, setTheme, toggleTheme
 */
export function useTheme() {
  const { theme, setTheme, resolvedTheme } = useNextTheme()

  const toggleTheme = () => {
    setTheme(resolvedTheme === 'dark' ? 'light' : 'dark')
  }

  return {
    theme: (resolvedTheme ?? 'light') as Theme,
    setTheme: setTheme as (t: Theme) => void,
    toggleTheme,
  }
}
