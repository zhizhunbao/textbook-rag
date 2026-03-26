'use client'

import { useEffect, useState, useMemo } from 'react'
import {
  FileText, Loader2, AlertCircle, RefreshCw, CheckCircle2,
  Lightbulb, BookOpen, BarChart3, Minimize2, Star,
  List,
} from 'lucide-react'
import { cn } from '@/features/shared/utils'
import { SidebarLayout, type SidebarItem } from '@/features/shared/components/SidebarLayout'

interface PromptMode {
  id: number
  name: string
  slug: string
  description: string
  systemPrompt: string
  icon?: string
  isDefault: boolean
}

const ICON_MAP: Record<string, React.ElementType> = {
  lightbulb: Lightbulb,
  book: BookOpen,
  chart: BarChart3,
  minimize: Minimize2,
  'bar-chart': BarChart3,
}

const MODE_COLORS = [
  { border: 'border-blue-500/30', bg: 'bg-blue-500/10', text: 'text-blue-400' },
  { border: 'border-amber-500/30', bg: 'bg-amber-500/10', text: 'text-amber-400' },
  { border: 'border-purple-500/30', bg: 'bg-purple-500/10', text: 'text-purple-400' },
  { border: 'border-emerald-500/30', bg: 'bg-emerald-500/10', text: 'text-emerald-400' },
  { border: 'border-rose-500/30', bg: 'bg-rose-500/10', text: 'text-rose-400' },
]

export default function Page() {
  const [modes, setModes] = useState<PromptMode[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [selected, setSelected] = useState<number | null>(null)

  const fetchModes = async () => {
    setLoading(true)
    setError(null)
    try {
      const res = await fetch('/api/prompt-modes?limit=100')
      const data = await res.json()
      const docs = data.docs || []
      setModes(docs)
      if (docs.length > 0 && selected === null) {
        setSelected(docs[0].id)
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { fetchModes() }, [])

  const activeMode = modes.find((m) => m.id === selected) || null

  // ── Sidebar items ──────────────────────────────────────────────────────────
  const sidebarItems = useMemo<SidebarItem[]>(() => {
    return modes.map((mode, idx) => {
      const color = MODE_COLORS[idx % MODE_COLORS.length]
      const IconComp = ICON_MAP[mode.icon || ''] || FileText
      return {
        key: String(mode.id),
        label: mode.name,
        icon: (
          <IconComp className={cn('h-4 w-4 shrink-0', selected === mode.id ? color.text : '')} />
        ),
        highlight: mode.isDefault,
      }
    })
  }, [modes, selected])

  return (
    <SidebarLayout
      title="Prompt 管理"
      icon={<FileText className="h-4 w-4 text-rose-400" />}
      sidebarItems={sidebarItems}
      activeFilter={selected != null ? String(selected) : ''}
      onFilterChange={(key) => setSelected(Number(key))}
      sidebarWidth="w-48"
      sidebarFooter={
        <p className="text-[10px] text-muted-foreground">共 {modes.length} 种模式</p>
      }
      loading={loading}
      loadingText="加载 Prompt 模式..."
      error={error}
      onRetry={fetchModes}
      toolbar={
        <button onClick={fetchModes} className="p-2 rounded-lg text-muted-foreground hover:bg-secondary hover:text-foreground transition-colors">
          <RefreshCw className="h-4 w-4" />
        </button>
      }
    >
      {activeMode ? (
        <div>
          {/* Header */}
          <div className="flex items-center justify-between mb-6">
            <div className="flex items-center gap-3">
              {(() => {
                const idx = modes.findIndex((m) => m.id === activeMode.id)
                const color = MODE_COLORS[idx % MODE_COLORS.length]
                const IconComp = ICON_MAP[activeMode.icon || ''] || FileText
                return (
                  <div className={cn('w-10 h-10 rounded-xl flex items-center justify-center', color.bg)}>
                    <IconComp className={cn('h-5 w-5', color.text)} />
                  </div>
                )
              })()}
              <div>
                <div className="flex items-center gap-2">
                  <h1 className="text-lg font-bold text-foreground">{activeMode.name}</h1>
                  {activeMode.isDefault && (
                    <span className="px-1.5 py-0.5 rounded text-[10px] font-medium bg-amber-500/10 text-amber-400 border border-amber-500/20 flex items-center gap-0.5">
                      <Star className="h-2.5 w-2.5" />默认
                    </span>
                  )}
                </div>
                <div className="flex items-center gap-2 mt-0.5">
                  <code className="text-xs text-muted-foreground font-mono bg-secondary px-1.5 py-0.5 rounded">{activeMode.slug}</code>
                </div>
              </div>
            </div>
          </div>

          {/* Description */}
          <div className="mb-6">
            <h2 className="text-xs font-medium text-muted-foreground uppercase tracking-wider mb-2">描述</h2>
            <p className="text-sm text-foreground/80 bg-card rounded-lg border border-border p-4">
              {activeMode.description}
            </p>
          </div>

          {/* System Prompt */}
          <div>
            <h2 className="text-xs font-medium text-muted-foreground uppercase tracking-wider mb-2">System Prompt</h2>
            <pre className="text-sm text-foreground/80 bg-card rounded-lg border border-border p-4 whitespace-pre-wrap font-mono leading-relaxed max-h-[60vh] overflow-y-auto">
              {activeMode.systemPrompt}
            </pre>
          </div>
        </div>
      ) : (
        <div className="flex flex-col items-center justify-center h-full py-20">
          <List className="h-10 w-10 text-muted-foreground mb-3" />
          <p className="text-sm text-muted-foreground">选择左侧的 Prompt 模式查看详情</p>
        </div>
      )}
    </SidebarLayout>
  )
}
