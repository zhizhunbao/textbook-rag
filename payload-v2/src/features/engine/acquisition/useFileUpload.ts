/**
 * useFileUpload — PDF file upload hook (extracted from readers/useUpload).
 *
 * Usage: const { upload, uploading, progress, error, reset } = useFileUpload({ onSuccess })
 *
 * Flow:
 *   1. Create Book record (status: pending)
 *   2. Upload PDF to PdfUploads collection → data/raw_pdfs/
 *   3. PATCH book with pdfMedia → afterChange moves PDF to category subdir
 *
 * NOTE: Pipeline (MinerU + ingestion) is NOT auto-triggered.
 * User must manually start it from the Pipeline Tab.
 *
 * Ref: AQ-02 — split useUpload into useFileUpload + useUrlImport
 */

'use client'

import { useState, useCallback } from 'react'
import type { BookCategory, FileUploadPayload, FileUploadState } from './types'
import { authFetch } from '@/features/shared/authFetch'

// ============================================================
// Constants
// ============================================================
const MAX_FILE_SIZE = 200 * 1024 * 1024 // 200 MB
const ACCEPTED_MIME = 'application/pdf'

// ============================================================
// Types
// ============================================================
export interface FileUploadOptions {
  /** Called after a successful upload with the new book ID. */
  onSuccess?: (bookId: number) => void
  /** Called when an error occurs. */
  onError?: (error: string) => void
}

// ============================================================
// Validation
// ============================================================
function validateFile(file: File): string | null {
  if (file.type !== ACCEPTED_MIME) {
    return `Invalid file type: ${file.type}. Only PDF files are accepted.`
  }
  if (file.size > MAX_FILE_SIZE) {
    const sizeMb = (file.size / 1024 / 1024).toFixed(1)
    return `File too large: ${sizeMb} MB. Maximum is ${MAX_FILE_SIZE / 1024 / 1024} MB.`
  }
  if (file.size === 0) {
    return 'File is empty.'
  }
  return null
}

// ============================================================
// Hook
// ============================================================
export function useFileUpload(options?: FileUploadOptions) {

  // ==========================================================
  // State
  // ==========================================================
  const [state, setState] = useState<FileUploadState>({
    uploading: false,
    progress: 0,
    error: null,
    fileName: null,
    stage: null,
  })

  // ==========================================================
  // Reset
  // ==========================================================
  const reset = useCallback(() => {
    setState({ uploading: false, progress: 0, error: null, fileName: null, stage: null })
  }, [])

  // ==========================================================
  // Upload — 3-step Payload flow
  // ==========================================================
  const upload = useCallback(async ({ file, title, category, subcategory }: FileUploadPayload) => {
    // Validate
    const validationError = validateFile(file)
    if (validationError) {
      setState((s) => ({ ...s, error: validationError }))
      options?.onError?.(validationError)
      return
    }

    setState({ uploading: true, progress: 10, error: null, fileName: file.name, stage: 'Creating book record...' })

    try {
      // Derive a book title from filename if not provided
      const bookTitle = title ?? file.name.replace(/\.pdf$/i, '').replace(/[-_]/g, ' ')

      // ── Duplicate check: warn if a book with the same title exists ──
      setState((s) => ({ ...s, progress: 15, stage: 'Checking for duplicates...' }))
      try {
        const checkRes = await authFetch(
          `/api/books?where[title][equals]=${encodeURIComponent(bookTitle)}&limit=1`,
        )
        if (checkRes.ok) {
          const checkData = await checkRes.json()
          const existing = checkData.docs ?? checkData
          if (Array.isArray(existing) && existing.length > 0) {
            const confirmed = window.confirm(
              `"${bookTitle}" already exists (status: ${existing[0].status}). Upload anyway?`
            )
            if (!confirmed) {
              setState({ uploading: false, progress: 0, error: null, fileName: null, stage: null })
              return
            }
          }
        }
      } catch {
        // Non-critical — continue even if check fails
      }

      // Step 1: Create a Book record in Payload CMS (20%)
      setState((s) => ({ ...s, progress: 20, stage: 'Creating book record...' }))

      const bookData: Record<string, unknown> = {
        title: bookTitle,
        category: category ?? 'textbook',
        status: 'pending',
        metadata: { fileSize: file.size },
      }
      if (subcategory) {
        bookData.subcategory = subcategory
      }

      const createRes = await authFetch('/api/books', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(bookData),
      })

      if (!createRes.ok) {
        const errBody = await createRes.text()
        throw new Error(`Failed to create book record: ${createRes.status} — ${errBody}`)
      }

      const bookDoc = await createRes.json()
      const bookId = bookDoc.doc?.id ?? bookDoc.id

      // Step 2: Upload PDF to PdfUploads collection → data/raw_pdfs/ (50%)
      setState((s) => ({ ...s, progress: 50, stage: 'Uploading PDF...' }))

      const formData = new FormData()
      formData.append('file', file)
      formData.append('alt', `${bookTitle} PDF`)

      const mediaRes = await authFetch('/api/pdf-uploads', {
        method: 'POST',
        body: formData,
      })

      if (!mediaRes.ok) {
        throw new Error(`Failed to upload PDF: ${mediaRes.status}`)
      }

      const mediaDoc = await mediaRes.json()
      const mediaId = mediaDoc.doc?.id ?? mediaDoc.id

      // Step 3: Link PDF media to book via pdfMedia field (80%)
      // afterChange hook will move PDF to category subdir (no pipeline triggered)
      setState((s) => ({ ...s, progress: 80, stage: 'Linking PDF to book...' }))

      const linkRes = await authFetch(`/api/books/${bookId}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          pdfMedia: mediaId,
          status: 'pending',
        }),
      })

      if (!linkRes.ok) {
        throw new Error(`Failed to link PDF to book: ${linkRes.status}`)
      }

      // Done — PDF uploaded and linked, user can trigger pipeline from Pipeline Tab
      setState({ uploading: false, progress: 100, error: null, fileName: file.name, stage: 'Upload complete' })
      options?.onSuccess?.(bookId)
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Upload failed'
      setState((s) => ({ ...s, uploading: false, error: message, stage: null }))
      options?.onError?.(message)
    }
  }, [options])

  return {
    upload,
    uploading: state.uploading,
    progress: state.progress,
    error: state.error,
    fileName: state.fileName,
    stage: state.stage,
    reset,
  }
}
