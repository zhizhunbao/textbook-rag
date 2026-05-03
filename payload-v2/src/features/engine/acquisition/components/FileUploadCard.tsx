/**
 * FileUploadCard — Drag-drop + file picker card for PDF upload.
 *
 * Now integrates ClassifyDialog: after file selection, shows the
 * LLM classification dialog for user confirmation before upload.
 *
 * Ref: AQ-01 — acquisition module creation
 *      AQ-05 — LLM auto-classification integration
 */

'use client'

import { useState, useCallback, useRef, type DragEvent, type ChangeEvent } from 'react'
import { Upload, FileUp, X, CheckCircle, AlertCircle, Loader2 } from 'lucide-react'
import { useI18n } from '@/features/shared/i18n'
import { useFileUpload } from '../useFileUpload'
import { cn } from '@/features/shared/utils'
import ClassifyDialog from './ClassifyDialog'

// ============================================================
// Types
// ============================================================
interface FileUploadCardProps {
  /** Called after a successful upload — parent should refresh. */
  onUploadComplete?: () => void
}

type DropState = 'idle' | 'drag-over' | 'classify' | 'uploading' | 'success' | 'error'

// ============================================================
// Component
// ============================================================
export default function FileUploadCard({
  onUploadComplete,
}: FileUploadCardProps) {
  const { locale } = useI18n()
  const isZh = locale === 'zh'
  const fileInputRef = useRef<HTMLInputElement>(null)

  // ==========================================================
  // State
  // ==========================================================
  const [dropState, setDropState] = useState<DropState>('idle')
  const [dragCounter, setDragCounter] = useState(0)
  const [pendingFile, setPendingFile] = useState<File | null>(null)

  const { upload, uploading, progress, error, fileName, stage, reset } = useFileUpload({
    onSuccess: () => {
      setDropState('success')
      setTimeout(() => {
        setDropState('idle')
        reset()
        onUploadComplete?.()
      }, 2000)
    },
    onError: () => {
      setDropState('error')
    },
  })

  // ==========================================================
  // File selection → show ClassifyDialog
  // ==========================================================
  const handleFileSelected = useCallback((file: File) => {
    setPendingFile(file)
    setDropState('classify')
  }, [])

  // ==========================================================
  // ClassifyDialog confirm → start upload with chosen metadata
  // ==========================================================
  const handleClassifyConfirm = useCallback((data: {
    title: string
    category: string
    subcategory: string
  }) => {
    if (!pendingFile) return

    setDropState('uploading')
    upload({
      file: pendingFile,
      title: data.title,
      category: data.category,
      subcategory: data.subcategory,
    })
    setPendingFile(null)
  }, [pendingFile, upload])

  const handleClassifyCancel = useCallback(() => {
    setPendingFile(null)
    setDropState('idle')
  }, [])

  // ==========================================================
  // Drag handlers
  // ==========================================================
  const handleDragEnter = useCallback((e: DragEvent) => {
    e.preventDefault()
    e.stopPropagation()
    setDragCounter((c) => c + 1)
    setDropState('drag-over')
  }, [])

  const handleDragLeave = useCallback((e: DragEvent) => {
    e.preventDefault()
    e.stopPropagation()
    setDragCounter((c) => {
      const next = c - 1
      if (next <= 0) setDropState('idle')
      return Math.max(0, next)
    })
  }, [])

  const handleDragOver = useCallback((e: DragEvent) => {
    e.preventDefault()
    e.stopPropagation()
  }, [])

  const handleDrop = useCallback(
    (e: DragEvent) => {
      e.preventDefault()
      e.stopPropagation()
      setDragCounter(0)
      const files = e.dataTransfer.files
      if (files.length > 0) {
        handleFileSelected(files[0])
      } else {
        setDropState('idle')
      }
    },
    [handleFileSelected],
  )

  // ==========================================================
  // File input handler
  // ==========================================================
  const handleFileSelect = useCallback(
    (e: ChangeEvent<HTMLInputElement>) => {
      const files = e.target.files
      if (files && files.length > 0) {
        handleFileSelected(files[0])
      }
      e.target.value = ''
    },
    [handleFileSelected],
  )

  const openFilePicker = useCallback(() => {
    fileInputRef.current?.click()
  }, [])

  const dismissError = useCallback(() => {
    setDropState('idle')
    reset()
  }, [reset])

  // ==========================================================
  // Derive title from filename
  // ==========================================================
  const deriveTitle = (file: File) =>
    file.name.replace(/\.pdf$/i, '').replace(/[-_]/g, ' ')

  // ==========================================================
  // Render
  // ==========================================================
  const isActive = dropState === 'drag-over'
  const isUploading = dropState === 'uploading' || uploading
  const isSuccess = dropState === 'success'
  const isError = dropState === 'error'
  const isClassifying = dropState === 'classify'

  return (
    <>
      <div
        onDragEnter={handleDragEnter}
        onDragLeave={handleDragLeave}
        onDragOver={handleDragOver}
        onDrop={handleDrop}
        className={cn(
          'relative rounded-xl border-2 border-dashed transition-all duration-200 h-full min-h-[200px]',
          'flex flex-col items-center justify-center',
          isActive && 'border-primary bg-primary/5 scale-[1.01]',
          isUploading && 'border-primary/50 bg-primary/5',
          isSuccess && 'border-emerald-500/50 bg-emerald-500/5',
          isError && 'border-destructive/50 bg-destructive/5',
          isClassifying && 'border-primary/30 bg-primary/5',
          !isActive && !isUploading && !isSuccess && !isError && !isClassifying && 'border-border hover:border-primary/30 hover:bg-secondary/30',
        )}
      >
        {/* Hidden file input */}
        <input
          ref={fileInputRef}
          type="file"
          accept=".pdf,application/pdf"
          onChange={handleFileSelect}
          className="hidden"
          aria-label="Upload PDF"
        />

        <div className="flex flex-col items-center justify-center gap-2 px-6 py-6">
          {/* Idle / Drag-over */}
          {!isUploading && !isSuccess && !isError && !isClassifying && (
            <>
              <div className={cn(
                'flex h-12 w-12 items-center justify-center rounded-xl transition-colors',
                isActive ? 'bg-primary/10' : 'bg-muted',
              )}>
                {isActive
                  ? <FileUp className="h-6 w-6 text-primary animate-bounce" />
                  : <Upload className="h-6 w-6 text-muted-foreground" />}
              </div>
              <div className="text-center">
                <p className="text-sm font-medium text-foreground">
                  {isActive
                    ? (isZh ? '释放文件以上传' : 'Drop file to upload')
                    : (isZh ? '拖放 PDF 文件到此处' : 'Drag & drop a PDF here')}
                </p>
                <p className="mt-1 text-xs text-muted-foreground">
                  {isZh ? '或' : 'or'}{' '}
                  <button
                    type="button"
                    onClick={openFilePicker}
                    className="text-primary hover:underline font-medium"
                  >
                    {isZh ? '点击选择文件' : 'click to browse'}
                  </button>
                  <span className="ml-1.5 text-muted-foreground/60">
                    (PDF, max 200 MB)
                  </span>
                </p>
              </div>
            </>
          )}

          {/* Classifying — waiting for dialog */}
          {isClassifying && (
            <>
              <Loader2 className="h-6 w-6 text-primary animate-spin" />
              <p className="text-sm font-medium text-foreground">
                {isZh ? '正在分析文件...' : 'Analyzing file...'}
              </p>
            </>
          )}

          {/* Uploading */}
          {isUploading && (
            <>
              <Loader2 className="h-6 w-6 text-primary animate-spin" />
              <div className="text-center w-full max-w-xs">
                <p className="text-sm font-medium text-foreground truncate">
                  {isZh ? '正在上传' : 'Uploading'}: {fileName}
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

          {/* Success */}
          {isSuccess && (
            <>
              <CheckCircle className="h-6 w-6 text-emerald-500" />
              <p className="text-sm font-medium text-emerald-600 dark:text-emerald-400">
                {isZh ? '上传成功！正在处理...' : 'Upload complete! Processing...'}
              </p>
            </>
          )}

          {/* Error */}
          {isError && (
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

      {/* ClassifyDialog (portal-like, rendered outside the card) */}
      {isClassifying && pendingFile && (
        <ClassifyDialog
          initialTitle={deriveTitle(pendingFile)}
          filename={pendingFile.name}
          onConfirm={handleClassifyConfirm}
          onCancel={handleClassifyCancel}
        />
      )}
    </>
  )
}
