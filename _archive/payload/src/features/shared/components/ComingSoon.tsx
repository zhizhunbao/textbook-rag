'use client'

import { type LucideIcon, Construction } from 'lucide-react'

/**
 * ComingSoon — 通用"即将上线"占位页面
 * 用于尚未实现的路由，避免 404 / 报错
 */
interface ComingSoonProps {
  /** 页面标题 */
  title: string
  /** 简短描述 */
  description?: string
  /** 图标（lucide-react） */
  icon?: LucideIcon
  /** 图标颜色类名 */
  iconColor?: string
}

export default function ComingSoon({
  title,
  description,
  icon: Icon = Construction,
  iconColor = 'text-brand-400',
}: ComingSoonProps) {
  return (
    <div className="flex h-full items-center justify-center">
      <div className="text-center space-y-4 max-w-sm">
        {/* Icon */}
        <div className="w-16 h-16 rounded-2xl bg-primary/10 flex items-center justify-center mx-auto">
          <Icon className={`h-8 w-8 ${iconColor}`} />
        </div>

        {/* Title & description */}
        <div>
          <h2 className="text-lg font-semibold text-foreground">{title}</h2>
          {description && (
            <p className="text-sm text-muted-foreground mt-1">{description}</p>
          )}
        </div>

        {/* Status badge */}
        <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full bg-muted text-muted-foreground text-xs font-medium">
          <span className="relative flex h-2 w-2">
            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-amber-400 opacity-75" />
            <span className="relative inline-flex rounded-full h-2 w-2 bg-amber-500" />
          </span>
          开发中 · Coming Soon
        </div>
      </div>
    </div>
  )
}
