'use client'

import { Cpu } from 'lucide-react'
import { useI18n } from '@/features/shared/i18n/I18nProvider'

/**
 * Query Engine admin page — placeholder for v2 query_engine module.
 * TODO: Add query pipeline configuration, debugging tools, etc.
 */
export default function Page() {
  const { locale } = useI18n()
  const isZh = locale === 'zh'

  return (
    <div className="p-8 max-w-4xl mx-auto">
      <div className="flex items-center gap-3 mb-2">
        <Cpu className="h-5 w-5 text-primary" />
        <h1 className="text-xl font-bold text-foreground">
          {isZh ? '查询引擎' : 'Query Engine'}
        </h1>
      </div>
      <p className="text-sm text-muted-foreground mb-8">
        {isZh
          ? '查询管道配置与调试 — 对应 engine_v2/query_engine 模块'
          : 'Query pipeline configuration & debugging — maps to engine_v2/query_engine'}
      </p>

      <div className="rounded-xl border border-border bg-card p-12 text-center">
        <Cpu className="h-10 w-10 text-muted-foreground/30 mx-auto mb-4" />
        <p className="text-sm text-muted-foreground">
          {isZh ? '即将上线' : 'Coming soon'}
        </p>
      </div>
    </div>
  )
}
