/**
 * UrlImportCard — URL input card for server-side PDF download.
 *
 * Now integrates ClassifyDialog: after URL paste, shows the LLM
 * classification dialog for user confirmation before import.
 *
 * Ref: AQ-01 — acquisition module creation
 *      AQ-05 — LLM auto-classification integration
 */

'use client'

import { useState, useCallback } from 'react'
import { Link2, CheckCircle, AlertCircle, Loader2, X } from 'lucide-react'
import { useI18n } from '@/features/shared/i18n'
import { useUrlImport } from '../useUrlImport'
import { cn } from '@/features/shared/utils'
import ClassifyDialog from './ClassifyDialog'

// ============================================================
// Types
// ============================================================
interface UrlImportCardProps {
  /** Called after a successful import — parent should refresh. */
  onImportComplete?: () => void
}

// ============================================================
// Component
// ============================================================
export default function UrlImportCard({
  onImportComplete,
}: UrlImportCardProps) {
  const { locale } = useI18n()
  const isZh = locale === 'zh'

  // ==========================================================
  // State
  // ==========================================================
  const [urlValue, setUrlValue] = useState('')
  const [done, setDone] = useState(false)
  const [showClassify, setShowClassify] = useState(false)
  const [pendingUrl, setPendingUrl] = useState('')
  const [derivedTitle, setDerivedTitle] = useState('')
  const [derivedFilename, setDerivedFilename] = useState<string | undefined>()

  const { importFromUrl, importing, progress, error, stage, reset } = useUrlImport({
    onSuccess: () => {
      setDone(true)
      setTimeout(() => {
        setDone(false)
        reset()
        onImportComplete?.()
      }, 2000)
    },
    onError: () => {
      // error state handled by hook
    },
  })

  // ==========================================================
  // Handlers
  // ==========================================================
  const handleSubmit = useCallback(() => {
    const trimmed = urlValue.trim()
    if (!trimmed) return

    // Derive title from URL for ClassifyDialog
    try {
      const parsed = new URL(trimmed)
      const pathParts = parsed.pathname.split('/')
      const lastSegment = pathParts[pathParts.length - 1] || 'imported-pdf'
      const title = decodeURIComponent(lastSegment)
        .replace(/\.pdf$/i, '')
        .replace(/[-_]/g, ' ')
      setDerivedTitle(title)
      setDerivedFilename(lastSegment)
    } catch {
      setDerivedTitle(trimmed)
      setDerivedFilename(undefined)
    }

    setPendingUrl(trimmed)
    setShowClassify(true)
    setUrlValue('')
  }, [urlValue])

  const handleClassifyConfirm = useCallback((data: {
    title: string
    category: string
    subcategory: string
  }) => {
    setShowClassify(false)
    importFromUrl(pendingUrl, data.category, data.title, data.subcategory)
    setPendingUrl('')
  }, [pendingUrl, importFromUrl])

  const handleClassifyCancel = useCallback(() => {
    setShowClassify(false)
    setPendingUrl('')
  }, [])

  const handleKeyDown = useCallback((e: React.KeyboardEvent) => {
    if (e.key === 'Enter') {
      e.preventDefault()
      handleSubmit()
    }
  }, [handleSubmit])

  const dismissError = useCallback(() => {
    reset()
  }, [reset])

  // ==========================================================
  // Render
  // ==========================================================
  return (
    <>
      <div className={cn(
        'rounded-xl border-2 border-dashed transition-all duration-200 h-full min-h-[200px]',
        'flex flex-col items-center justify-center',
        importing && 'border-primary/50 bg-primary/5',
        done && 'border-emerald-500/50 bg-emerald-500/5',
        error && !importing && !done && 'border-destructive/50 bg-destructive/5',
        !importing && !done && !error && 'border-border hover:border-primary/30 hover:bg-secondary/30',
      )}>
        <div className="flex flex-col items-center justify-center gap-2 px-6 py-6 w-full">
          {/* Idle */}
          {!importing && !done && !error && (
            <>
              <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-muted">
                <Link2 className="h-6 w-6 text-muted-foreground" />
              </div>
              <p className="text-sm font-medium text-foreground text-center">
                {isZh ? '粘贴 PDF 链接' : 'Paste a PDF link'}
              </p>
              <div className="flex gap-2 w-full max-w-sm">
                <input
                  type="url"
                  value={urlValue}
                  onChange={(e) => setUrlValue(e.target.value)}
                  onKeyDown={handleKeyDown}
                  placeholder="https://example.com/book.pdf"
                  className={cn(
                    'flex-1 rounded-lg border bg-background px-3 py-2 text-sm',
                    'placeholder:text-muted-foreground/50',
                    'focus:outline-none focus:ring-2 focus:ring-primary/30 focus:border-primary',
                  )}
                />
                <button
                  type="button"
                  onClick={handleSubmit}
                  disabled={!urlValue.trim()}
                  className={cn(
                    'rounded-lg px-4 py-2 text-sm font-medium transition-colors',
                    'bg-primary text-primary-foreground hover:bg-primary/90',
                    'disabled:opacity-50 disabled:cursor-not-allowed',
                  )}
                >
                  {isZh ? '导入' : 'Import'}
                </button>
              </div>
              <p className="text-xs text-muted-foreground/60 text-center">
                {isZh ? 'Engine 会服务端下载，无需跨域' : 'Downloaded server-side, no CORS limits'}
              </p>
            </>
          )}

          {/* Importing */}
          {importing && (
            <>
              <Loader2 className="h-6 w-6 text-primary animate-spin" />
              <div className="text-center w-full max-w-xs">
                <p className="text-sm font-medium text-foreground">
                  {isZh ? '正在导入...' : 'Importing...'}
                </p>
                {stage && (
                  <p className="text-xs text-muted-foreground mt-0.5">{stage}</p>
                )}
                <div className="mt-2 h-1.5 w-full rounded-full bg-muted overflow-hidden">
                  <div
                    className="h-full rounded-full bg-primary transition-all duration-300 ease-out"
                    style={{ width: `${progress}%` }}
                  />
                </div>
                <p className="mt-1 text-xs text-muted-foreground tabular-nums">{progress}%</p>
              </div>
            </>
          )}

          {/* Done */}
          {done && (
            <>
              <CheckCircle className="h-6 w-6 text-emerald-500" />
              <p className="text-sm font-medium text-emerald-600 dark:text-emerald-400">
                {isZh ? '导入成功！正在处理...' : 'Import complete! Processing...'}
              </p>
            </>
          )}

          {/* Error */}
          {error && !importing && !done && (
            <>
              <AlertCircle className="h-6 w-6 text-destructive" />
              <p className="text-sm font-medium text-destructive max-w-xs text-center">{error}</p>
              <button
                type="button"
                onClick={dismissError}
                className="mt-1 flex items-center gap-1 text-xs text-muted-foreground hover:text-foreground transition-colors"
              >
                <X className="h-3 w-3" />
                {isZh ? '关闭' : 'Dismiss'}
              </button>
            </>
          )}
        </div>
      </div>

      {/* ClassifyDialog */}
      {showClassify && (
        <ClassifyDialog
          initialTitle={derivedTitle}
          filename={derivedFilename}
          onConfirm={handleClassifyConfirm}
          onCancel={handleClassifyCancel}
        />
      )}
    </>
  )
}
