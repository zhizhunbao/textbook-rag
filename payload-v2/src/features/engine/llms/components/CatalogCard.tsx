'use client'

/**
 * CatalogCard — Curated model card for the Library tab.
 *
 * Displays model metadata from the curated catalog with a "Pull" action.
 * Shows pull progress via SSE streaming.
 *
 * 精选模型卡片 — 显示模型元数据 + 一键 Pull 功能
 */

import { useState, useRef } from 'react'
import {
  Download, Loader2, CheckCircle2, Cpu, Zap, Globe, Clock,
  XCircle, Shield, Star,
} from 'lucide-react'
import { cn } from '@/features/shared/utils'
import type { CatalogModel, PullProgress } from '../types'
import { pullModel, registerModel } from '../api'

// ── Category colors ──────────────────────────────────────────────────────────
const CATEGORY_STYLES: Record<string, { color: string; bg: string }> = {
  recommended: { color: 'text-emerald-400', bg: 'bg-emerald-500/10' },
  reasoning: { color: 'text-amber-400', bg: 'bg-amber-500/10' },
  lightweight: { color: 'text-sky-400', bg: 'bg-sky-500/10' },
  specialized: { color: 'text-purple-400', bg: 'bg-purple-500/10' },
}

interface CatalogCardProps {
  model: CatalogModel
  /** 模型是否已安装 (override) / Whether model is already installed locally */
  isInstalled?: boolean
  /** 模型是否已注册到 CMS / Whether model is already registered in CMS */
  isRegistered?: boolean
  /** Pull 完成后回调 / Callback after pull + register completes */
  onPulled?: () => void
  isZh?: boolean
}

export function CatalogCard({
  model: m,
  isInstalled: isInstalledProp,
  isRegistered = false,
  onPulled,
  isZh = false,
}: CatalogCardProps) {
  // Installed status: API response (m.installed) takes priority, prop as override
  const isInstalled = isInstalledProp ?? m.installed ?? false
  const [pulling, setPulling] = useState(false)
  const [progress, setProgress] = useState<PullProgress | null>(null)
  const [done, setDone] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const controllerRef = useRef<AbortController | null>(null)

  const catStyle = CATEGORY_STYLES[m.category] || CATEGORY_STYLES.recommended

  // ── Pull progress percentage ──────────────────────────────────────────────
  const percent = progress?.completed && progress?.total
    ? Math.round((progress.completed / progress.total) * 100)
    : 0

  // ── Handle pull ───────────────────────────────────────────────────────────
  const handlePull = () => {
    if (pulling || isInstalled || done) return
    setPulling(true)
    setError(null)
    setProgress(null)

    controllerRef.current = pullModel(
      m.name,
      (p) => setProgress(p),
      async () => {
        // Pull done → auto-register to CMS
        try {
          await registerModel({
            name: m.name,
            parameterSize: m.parameterSize,
            family: m.family,
          })
        } catch { /* registration failure is non-blocking */ }
        setPulling(false)
        setDone(true)
        onPulled?.()
      },
      (err) => {
        setPulling(false)
        setError(err)
      },
    )
  }

  const handleCancel = () => {
    controllerRef.current?.abort()
    setPulling(false)
    setProgress(null)
  }

  return (
    <div
      className={cn(
        'rounded-xl border border-border bg-card p-5 transition-all',
        'hover:border-primary/30 hover:shadow-lg hover:shadow-primary/5',
        isInstalled && 'border-emerald-500/20 bg-emerald-500/5',
      )}
    >
      {/* Header */}
      <div className="flex items-start justify-between mb-3">
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-2 mb-1">
            <h3 className="text-sm font-semibold text-foreground truncate">
              {m.displayName}
            </h3>
            <span className={cn('shrink-0 px-1.5 py-0.5 rounded text-[10px] font-medium capitalize', catStyle.bg, catStyle.color)}>
              {m.category}
            </span>
          </div>
          <code className="text-xs text-muted-foreground font-mono">{m.name}</code>
        </div>
        {isInstalled && (
          <CheckCircle2 className="h-4 w-4 text-emerald-500 shrink-0 ml-2" />
        )}
      </div>

      {/* Description */}
      <p className="text-xs text-muted-foreground mb-3 line-clamp-2">
        {m.description}
      </p>

      {/* Specs grid */}
      <div className="grid grid-cols-2 gap-x-4 gap-y-1.5 mb-3">
        <div className="flex items-center gap-1.5 text-xs">
          <Cpu className="h-3 w-3 text-muted-foreground shrink-0" />
          <span className="text-muted-foreground">{isZh ? 'Paramètres' : 'Params'}</span>
          <span className="text-foreground font-medium ml-auto">{m.parameterSize}</span>
        </div>
        <div className="flex items-center gap-1.5 text-xs">
          <Zap className="h-3 w-3 text-muted-foreground shrink-0" />
          <span className="text-muted-foreground">{isZh ? 'Contexte' : 'Context'}</span>
          <span className="text-foreground font-medium ml-auto">
            {m.contextWindow >= 1000 ? `${(m.contextWindow / 1000).toFixed(0)}K` : m.contextWindow || '—'}
          </span>
        </div>
        <div className="flex items-center gap-1.5 text-xs">
          <Globe className="h-3 w-3 text-muted-foreground shrink-0" />
          <span className="text-muted-foreground">{isZh ? 'Langues' : 'Languages'}</span>
          <span className="text-foreground font-medium ml-auto truncate max-w-[80px]">{m.languages || '—'}</span>
        </div>
        <div className="flex items-center gap-1.5 text-xs">
          <Download className="h-3 w-3 text-muted-foreground shrink-0" />
          <span className="text-muted-foreground">{isZh ? 'Téléchargements' : 'Downloads'}</span>
          <span className="text-foreground font-medium ml-auto">
            {m.downloads > 1_000_000
              ? `${(m.downloads / 1_000_000).toFixed(1)}M`
              : m.downloads > 1_000
                ? `${(m.downloads / 1_000).toFixed(0)}K`
                : m.downloads || '—'}
          </span>
        </div>
        <div className="flex items-center gap-1.5 text-xs">
          <Star className="h-3 w-3 text-amber-400 shrink-0" />
          <span className="text-muted-foreground">{isZh ? 'Classement' : 'Ranking'}</span>
          <span className="text-foreground font-medium ml-auto">
            {m.likes > 1_000_000
              ? `${(m.likes / 1_000_000).toFixed(1)}M`
              : m.likes > 1_000
                ? `${(m.likes / 1_000).toFixed(0)}K`
                : m.likes || '—'}
          </span>
        </div>
      </div>

      {/* Advantages */}
      <div className="flex flex-wrap gap-1.5 mb-3">
        {m.advantages.slice(0, 4).map((a, i) => (
          <span key={i} className="px-2 py-0.5 rounded-full text-[10px] bg-secondary text-muted-foreground">
            {a}
          </span>
        ))}
      </div>

      {/* Pull progress bar */}
      {pulling && progress && (
        <div className="mb-3">
          <div className="flex items-center justify-between text-[10px] text-muted-foreground mb-1">
            <span>{progress.status}</span>
            <span>{percent}%</span>
          </div>
          <div className="w-full h-1.5 rounded-full bg-secondary overflow-hidden">
            <div
              className="h-full rounded-full bg-primary transition-all duration-300"
              style={{ width: `${percent}%` }}
            />
          </div>
        </div>
      )}

      {/* Error */}
      {error && (
        <div className="mb-3 px-2.5 py-1.5 rounded-md bg-red-500/5 border border-red-500/10">
          <p className="text-[10px] text-red-400 flex items-center gap-1">
            <XCircle className="h-3 w-3 shrink-0" />
            {error}
          </p>
        </div>
      )}

      {/* Footer actions */}
      <div className="flex items-center justify-between pt-3 border-t border-border">
        <div className="flex items-center gap-1.5 text-xs">
          {m.released && (
            <>
              <Clock className="h-3 w-3 text-muted-foreground" />
              <span className="text-muted-foreground">{m.released}</span>
            </>
          )}
          {m.license && (
            <span className="inline-flex items-center gap-1 ml-2 px-1.5 py-0.5 rounded text-[9px] bg-secondary text-muted-foreground">
              <Shield className="h-2.5 w-2.5" />
              {m.license}
            </span>
          )}
        </div>
        <div>
          {done ? (
            <span className="inline-flex items-center gap-1 px-2.5 py-1 text-[10px] font-medium text-emerald-400">
              <CheckCircle2 className="h-3 w-3" />
              {isZh ? 'Installé' : 'Installed'}
            </span>
          ) : isInstalled ? (
            <span className="inline-flex items-center gap-1 px-2.5 py-1 text-[10px] font-medium text-emerald-400">
              <CheckCircle2 className="h-3 w-3" />
              {isRegistered
                ? (isZh ? 'Enregistré' : 'Registered')
                : (isZh ? 'Installé' : 'Installed')}
            </span>
          ) : pulling ? (
            <button
              onClick={handleCancel}
              className="inline-flex items-center gap-1 px-2.5 py-1 rounded-md text-[10px] font-medium text-red-400 hover:bg-red-500/10 transition-colors"
            >
              <XCircle className="h-3 w-3" />
              {isZh ? 'Annuler' : 'Cancel'}
            </button>
          ) : (
            <button
              onClick={handlePull}
              className={cn(
                'inline-flex items-center gap-1 px-2.5 py-1 rounded-md text-[10px] font-medium transition-colors',
                'bg-primary/10 text-primary hover:bg-primary/20 border border-primary/20',
              )}
            >
              <Download className="h-3 w-3" />
              {isZh ? 'Télécharger' : 'Pull'}
            </button>
          )}
        </div>
      </div>
    </div>
  )
}
