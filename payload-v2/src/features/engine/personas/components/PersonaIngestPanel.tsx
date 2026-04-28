/**
 * PersonaIngestPanel — PDF upload panel for persona knowledge base.
 *
 * Admin selects PDF files and uploads them to a persona's ChromaDB collection.
 * Features:
 *   - File picker (PDF only)
 *   - Sequential upload with progress
 *   - Completion stats display
 */

'use client'

import { useState, useRef } from 'react'
import { cn } from '@/features/shared/utils'
import { ingestPersonaPdf } from '../api'
import type { PersonaWithStats } from '../types'

// ── Types ──

interface UploadItem {
  filename: string
  status: 'pending' | 'uploading' | 'done' | 'error'
  message?: string
}

// ── Component ──

interface PersonaIngestPanelProps {
  persona: PersonaWithStats
  onIngestComplete?: () => void
}

export default function PersonaIngestPanel({
  persona,
  onIngestComplete,
}: PersonaIngestPanelProps) {
  const [uploads, setUploads] = useState<UploadItem[]>([])
  const [isUploading, setIsUploading] = useState(false)
  const fileInputRef = useRef<HTMLInputElement>(null)

  const handleFileSelect = async (
    e: React.ChangeEvent<HTMLInputElement>,
  ) => {
    const files = e.target.files
    if (!files || files.length === 0) return

    const items: UploadItem[] = Array.from(files).map((f) => ({
      filename: f.name,
      status: 'pending',
    }))
    setUploads(items)
    setIsUploading(true)

    // Sequential upload
    for (let i = 0; i < items.length; i++) {
      setUploads((prev) =>
        prev.map((u, idx) =>
          idx === i ? { ...u, status: 'uploading' } : u,
        ),
      )

      try {
        const result = await ingestPersonaPdf({
          personaSlug: persona.slug,
          pdfFilename: items[i].filename,
        })

        setUploads((prev) =>
          prev.map((u, idx) =>
            idx === i
              ? {
                  ...u,
                  status: result.status === 'accepted' ? 'done' : 'error',
                  message:
                    result.status === 'accepted'
                      ? `Queued → ${result.collection_name}`
                      : result.message ?? 'Failed',
                }
              : u,
          ),
        )
      } catch (err) {
        setUploads((prev) =>
          prev.map((u, idx) =>
            idx === i
              ? {
                  ...u,
                  status: 'error',
                  message:
                    err instanceof Error ? err.message : 'Upload failed',
                }
              : u,
          ),
        )
      }
    }

    setIsUploading(false)
    onIngestComplete?.()

    // Reset file input
    if (fileInputRef.current) fileInputRef.current.value = ''
  }

  const doneCount = uploads.filter((u) => u.status === 'done').length
  const errorCount = uploads.filter((u) => u.status === 'error').length

  return (
    <div className="rounded-xl border border-border bg-card p-4 space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-semibold text-foreground">
          Upload PDFs to Knowledge Base
        </h3>
        <span className="text-xs text-muted-foreground font-mono">
          {persona.chromaCollection}
        </span>
      </div>

      {/* File picker */}
      <div className="relative">
        <input
          ref={fileInputRef}
          type="file"
          accept=".pdf"
          multiple
          onChange={(e) => void handleFileSelect(e)}
          disabled={isUploading}
          className="absolute inset-0 w-full h-full opacity-0 cursor-pointer disabled:cursor-not-allowed"
        />
        <div
          className={cn(
            'flex flex-col items-center gap-2 py-8 rounded-lg border-2 border-dashed transition-colors',
            isUploading
              ? 'border-muted cursor-not-allowed opacity-60'
              : 'border-border hover:border-primary/40 cursor-pointer',
          )}
        >
          <svg
            width="32"
            height="32"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="1.5"
            strokeLinecap="round"
            strokeLinejoin="round"
            className="text-muted-foreground"
          >
            <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
            <polyline points="17,8 12,3 7,8" />
            <line x1="12" y1="3" x2="12" y2="15" />
          </svg>
          <p className="text-sm text-muted-foreground">
            {isUploading ? 'Uploading...' : 'Drop PDF files here or click to browse'}
          </p>
          <p className="text-xs text-muted-foreground/60">
            Only .pdf files accepted
          </p>
        </div>
      </div>

      {/* Upload list */}
      {uploads.length > 0 && (
        <div className="space-y-2">
          <div className="flex items-center justify-between text-xs text-muted-foreground">
            <span>
              {doneCount}/{uploads.length} complete
              {errorCount > 0 && (
                <span className="text-red-400 ml-2">
                  {errorCount} failed
                </span>
              )}
            </span>
            {!isUploading && (
              <button
                type="button"
                onClick={() => setUploads([])}
                className="text-xs text-muted-foreground hover:text-foreground transition-colors"
              >
                Clear
              </button>
            )}
          </div>

          <div className="space-y-1.5 max-h-48 overflow-y-auto">
            {uploads.map((item, idx) => (
              <div
                key={`${item.filename}-${idx}`}
                className="flex items-center gap-2 px-3 py-2 rounded-lg bg-muted/50 text-xs"
              >
                {/* Status icon */}
                {item.status === 'pending' && (
                  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="text-muted-foreground shrink-0">
                    <circle cx="12" cy="12" r="10" />
                  </svg>
                )}
                {item.status === 'uploading' && (
                  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="text-primary animate-spin shrink-0">
                    <path d="M21 12a9 9 0 1 1-6.22-8.56" />
                  </svg>
                )}
                {item.status === 'done' && (
                  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="text-emerald-500 shrink-0">
                    <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14" />
                    <polyline points="22,4 12,14.01 9,11.01" />
                  </svg>
                )}
                {item.status === 'error' && (
                  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="text-red-400 shrink-0">
                    <circle cx="12" cy="12" r="10" />
                    <line x1="15" y1="9" x2="9" y2="15" />
                    <line x1="9" y1="9" x2="15" y2="15" />
                  </svg>
                )}

                {/* Filename */}
                <span className="flex-1 truncate text-foreground">
                  {item.filename}
                </span>

                {/* Status message */}
                {item.message && (
                  <span
                    className={cn(
                      'text-[10px] shrink-0',
                      item.status === 'error'
                        ? 'text-red-400'
                        : 'text-muted-foreground',
                    )}
                  >
                    {item.message}
                  </span>
                )}
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
