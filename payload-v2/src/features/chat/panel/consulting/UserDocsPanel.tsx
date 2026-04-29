/**
 * UserDocsPanel — File upload and document list for user private consulting docs.
 *
 * Layout:
 *   - Header with persona name + total stats
 *   - Drag-and-drop PDF upload zone
 *   - Document list with status badges (pending/processing/indexed/error)
 *   - Delete button per document with confirm
 */

'use client'

import { useState, useRef, useCallback } from 'react'
import { cn } from '@/features/shared/utils'
import { useAuth } from '@/features/shared/AuthProvider'
import { useUserDocs, type UserDoc, type UserDocStatus } from './useUserDocs'

// ── Status badge config ──

const STATUS_CONFIG: Record<UserDocStatus, {
  label: string
  bg: string
  text: string
  dot: string
}> = {
  pending: {
    label: 'Pending',
    bg: 'bg-muted',
    text: 'text-muted-foreground',
    dot: 'bg-muted-foreground',
  },
  processing: {
    label: 'Processing',
    bg: 'bg-amber-500/10',
    text: 'text-amber-400',
    dot: 'bg-amber-500 animate-pulse',
  },
  indexed: {
    label: 'Indexed',
    bg: 'bg-emerald-500/10',
    text: 'text-emerald-400',
    dot: 'bg-emerald-500',
  },
  error: {
    label: 'Error',
    bg: 'bg-red-500/10',
    text: 'text-red-400',
    dot: 'bg-red-500',
  },
}

// ── Component ──

interface UserDocsPanelProps {
  personaSlug?: string
  personaName?: string
  className?: string
}

export default function UserDocsPanel({
  personaSlug,
  personaName,
  className,
}: UserDocsPanelProps) {
  const { user } = useAuth()
  const { docs, loading, error, upload, remove, refetch } =
    useUserDocs(personaSlug)
  const [uploading, setUploading] = useState(false)
  const [confirmDeleteId, setConfirmDeleteId] = useState<number | null>(null)
  const fileInputRef = useRef<HTMLInputElement>(null)

  const totalChunks = docs.reduce(
    (sum, d) => sum + (d.liveChunkCount || d.chunkCount),
    0,
  )

  // ── Upload limits (C5-06) ──
  const MAX_FILE_SIZE = 50 * 1024 * 1024 // 50 MB
  const MAX_DOCS_PER_PERSONA = 20
  const [uploadError, setUploadError] = useState<string | null>(null)

  // Handle file selection — upload via Payload then trigger Engine ingest
  const handleFileSelect = useCallback(
    async (e: React.ChangeEvent<HTMLInputElement>) => {
      const files = e.target.files
      if (!files || files.length === 0 || !user?.id) return

      setUploadError(null)

      // C5-06: Validate limits
      const remaining = MAX_DOCS_PER_PERSONA - docs.length
      if (remaining <= 0) {
        setUploadError(`Document limit reached (max ${MAX_DOCS_PER_PERSONA} per persona).`)
        if (fileInputRef.current) fileInputRef.current.value = ''
        return
      }
      if (files.length > remaining) {
        setUploadError(`Can only upload ${remaining} more document(s) (max ${MAX_DOCS_PER_PERSONA}).`)
        if (fileInputRef.current) fileInputRef.current.value = ''
        return
      }

      for (const file of Array.from(files)) {
        if (file.type !== 'application/pdf' && !file.name.toLowerCase().endsWith('.pdf')) {
          setUploadError(`"${file.name}" is not a PDF file. Only .pdf files are accepted.`)
          if (fileInputRef.current) fileInputRef.current.value = ''
          return
        }
        if (file.size > MAX_FILE_SIZE) {
          const sizeMB = (file.size / 1024 / 1024).toFixed(1)
          setUploadError(`"${file.name}" is ${sizeMB} MB — max allowed is 50 MB.`)
          if (fileInputRef.current) fileInputRef.current.value = ''
          return
        }
      }

      setUploading(true)

      for (const file of Array.from(files)) {
        try {
          // Step 1: Upload file to Payload CMS
          const formData = new FormData()
          formData.append('file', file)
          formData.append('user', String(user.id))

          // Resolve persona ID
          const slug = personaSlug || getCurrentPersonaSlug()
          if (slug) {
            const personaRes = await fetch(
              `/api/consulting-personas?where[slug][equals]=${slug}&limit=1`,
              { credentials: 'include' },
            )
            const personaData = await personaRes.json()
            const personaId = personaData?.docs?.[0]?.id
            if (personaId) formData.append('persona', String(personaId))
          }

          const uploadRes = await fetch('/api/user-documents', {
            method: 'POST',
            credentials: 'include',
            body: formData,
          })

          if (!uploadRes.ok) {
            console.warn('Failed to upload:', file.name)
            continue
          }

          const uploadedDoc = await uploadRes.json()

          // Step 2: Trigger Engine ingest
          await upload({
            docId: uploadedDoc.doc?.id ?? uploadedDoc.id,
            pdfFilename: file.name,
            personaSlug: slug || '',
          })
        } catch (err) {
          console.warn('Upload error:', file.name, err)
        }
      }

      setUploading(false)
      if (fileInputRef.current) fileInputRef.current.value = ''
    },
    [user?.id, personaSlug, upload, docs.length],
  )

  // Get current persona slug from auth user
  function getCurrentPersonaSlug(): string {
    if (
      user?.selectedPersona &&
      typeof user.selectedPersona === 'object'
    ) {
      return (user.selectedPersona as { slug: string }).slug
    }
    return ''
  }

  // Handle delete
  const handleDelete = useCallback(
    async (docId: number) => {
      try {
        await remove(docId)
      } catch (err) {
        console.warn('Delete error:', err)
      }
      setConfirmDeleteId(null)
    },
    [remove],
  )

  // ── Loading state ──
  if (loading && docs.length === 0) {
    return (
      <div className={cn('rounded-xl border border-border bg-card p-6', className)}>
        <div className="flex items-center gap-2 text-sm text-muted-foreground">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="animate-spin">
            <path d="M21 12a9 9 0 1 1-6.22-8.56" />
          </svg>
          Loading documents...
        </div>
      </div>
    )
  }

  return (
    <div className={cn('rounded-xl border border-border bg-card', className)}>
      {/* Header */}
      <div className="flex items-center justify-between p-4 border-b border-border">
        <div>
          <h3 className="text-sm font-semibold text-foreground flex items-center gap-2">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" className="text-primary">
              <path d="M14.5 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7.5L14.5 2z" />
              <polyline points="14,2 14,8 20,8" />
            </svg>
            My Documents
            {personaName && (
              <span className="text-muted-foreground font-normal">
                ({personaName})
              </span>
            )}
          </h3>
          <p className="text-xs text-muted-foreground mt-0.5">
            {docs.length} document(s) · {totalChunks} total chunks
          </p>
        </div>
        <button
          type="button"
          onClick={() => void refetch()}
          disabled={loading}
          className="p-1.5 rounded-lg text-muted-foreground hover:bg-muted hover:text-foreground transition-colors"
        >
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className={cn(loading && 'animate-spin')}>
            <polyline points="23,4 23,10 17,10" />
            <polyline points="1,20 1,14 7,14" />
            <path d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15" />
          </svg>
        </button>
      </div>

      {/* Upload zone */}
      <div className="p-4">
        <div className="relative">
          <input
            ref={fileInputRef}
            type="file"
            accept=".pdf"
            multiple
            onChange={(e) => void handleFileSelect(e)}
            disabled={uploading}
            className="absolute inset-0 w-full h-full opacity-0 cursor-pointer disabled:cursor-not-allowed"
          />
          <div
            className={cn(
              'flex flex-col items-center gap-2 py-6 rounded-lg border-2 border-dashed transition-colors',
              uploading
                ? 'border-muted cursor-not-allowed opacity-60'
                : 'border-border hover:border-primary/40 cursor-pointer',
            )}
          >
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" className="text-muted-foreground">
              <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
              <polyline points="17,8 12,3 7,8" />
              <line x1="12" y1="3" x2="12" y2="15" />
            </svg>
            <p className="text-xs text-muted-foreground">
              {uploading ? 'Uploading...' : `Drop PDFs here or click to upload (max 50 MB)`}
            </p>
            <p className="text-[10px] text-muted-foreground/60">
              {docs.length}/{MAX_DOCS_PER_PERSONA} documents used
            </p>
          </div>
        </div>
      </div>

      {/* Upload validation error (C5-06) */}
      {uploadError && (
        <div className="mx-4 mb-2 px-3 py-2 rounded-lg bg-amber-500/10 text-xs text-amber-400">
          {uploadError}
        </div>
      )}

      {/* Fetch error */}
      {error && (
        <div className="mx-4 mb-4 px-3 py-2 rounded-lg bg-red-500/10 text-xs text-red-400">
          {error}
        </div>
      )}

      {/* Document list */}
      {docs.length > 0 && (
        <div className="border-t border-border">
          {docs.map((doc) => (
            <DocRow
              key={doc.id}
              doc={doc}
              isConfirming={confirmDeleteId === doc.id}
              onDeleteRequest={() => setConfirmDeleteId(doc.id)}
              onDeleteConfirm={() => void handleDelete(doc.id)}
              onDeleteCancel={() => setConfirmDeleteId(null)}
            />
          ))}
        </div>
      )}

      {/* Empty state */}
      {docs.length === 0 && !loading && (
        <div className="p-6 text-center">
          <p className="text-xs text-muted-foreground">
            No documents uploaded yet. Upload a PDF to get started.
          </p>
        </div>
      )}
    </div>
  )
}

// ── Document row sub-component ──

function DocRow({
  doc,
  isConfirming,
  onDeleteRequest,
  onDeleteConfirm,
  onDeleteCancel,
}: {
  doc: UserDoc
  isConfirming: boolean
  onDeleteRequest: () => void
  onDeleteConfirm: () => void
  onDeleteCancel: () => void
}) {
  const status = STATUS_CONFIG[doc.status]
  const chunks = doc.liveChunkCount || doc.chunkCount

  return (
    <div className="flex items-center gap-3 px-4 py-3 border-b border-border/50 last:border-0 hover:bg-muted/30 transition-colors">
      {/* File icon */}
      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" className="text-muted-foreground shrink-0">
        <path d="M14.5 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7.5L14.5 2z" />
        <polyline points="14,2 14,8 20,8" />
      </svg>

      {/* Filename + meta */}
      <div className="flex-1 min-w-0">
        <p className="text-sm text-foreground truncate">{doc.filename}</p>
        <div className="flex items-center gap-2 mt-0.5">
          <span className={cn(
            'inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-[10px] font-medium',
            status.bg, status.text,
          )}>
            <span className={cn('w-1.5 h-1.5 rounded-full', status.dot)} />
            {status.label}
          </span>
          {chunks > 0 && (
            <span className="text-[10px] text-muted-foreground">
              {chunks} chunks
            </span>
          )}
        </div>
      </div>

      {/* Delete */}
      {isConfirming ? (
        <div className="flex items-center gap-1.5">
          <button
            type="button"
            onClick={onDeleteConfirm}
            className="px-2 py-1 rounded text-[10px] font-medium bg-red-500/10 text-red-400 hover:bg-red-500/20 transition-colors"
          >
            Delete
          </button>
          <button
            type="button"
            onClick={onDeleteCancel}
            className="px-2 py-1 rounded text-[10px] font-medium bg-muted text-muted-foreground hover:text-foreground transition-colors"
          >
            Cancel
          </button>
        </div>
      ) : (
        <button
          type="button"
          onClick={onDeleteRequest}
          className="p-1 rounded text-muted-foreground hover:text-red-400 transition-colors"
          title="Delete document"
        >
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
            <polyline points="3,6 5,6 21,6" />
            <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2" />
          </svg>
        </button>
      )}
    </div>
  )
}
