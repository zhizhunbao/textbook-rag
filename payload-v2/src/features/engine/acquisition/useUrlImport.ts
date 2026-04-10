/**
 * useUrlImport — URL-based PDF import hook (extracted from readers/useUpload).
 *
 * Usage: const { importFromUrl, importing, progress, error, reset } = useUrlImport({ onSuccess })
 *
 * Flow:
 *   1. Create Book record (status: pending)
 *   2. POST to Engine /ingest with external PDF URL
 *   3. Engine downloads PDF server-side → MinerU parse → ingest
 *
 * Ref: AQ-02 — split useUpload into useFileUpload + useUrlImport
 */

'use client'

import { useState, useCallback } from 'react'
import type { BookCategory, UrlImportState } from './types'
import { authFetch } from '@/features/shared/authFetch'

// ============================================================
// Constants
// ============================================================
const ENGINE_URL = process.env.NEXT_PUBLIC_ENGINE_URL || 'http://localhost:8001'

// ============================================================
// Types
// ============================================================
export interface UrlImportOptions {
  /** Called after a successful import with the new book ID. */
  onSuccess?: (bookId: number) => void
  /** Called when an error occurs. */
  onError?: (error: string) => void
}

// ============================================================
// Hook
// ============================================================
export function useUrlImport(options?: UrlImportOptions) {

  // ==========================================================
  // State
  // ==========================================================
  const [state, setState] = useState<UrlImportState>({
    importing: false,
    progress: 0,
    error: null,
    url: null,
    stage: null,
  })

  // ==========================================================
  // Reset
  // ==========================================================
  const reset = useCallback(() => {
    setState({ importing: false, progress: 0, error: null, url: null, stage: null })
  }, [])

  // ==========================================================
  // Import from URL — Engine downloads PDF server-side
  // ==========================================================
  const importFromUrl = useCallback(async (
    url: string,
    category?: BookCategory,
    titleOverride?: string,
    subcategory?: string,
  ) => {
    // Validate URL
    const trimmed = url.trim()
    if (!trimmed) {
      const msg = 'Please enter a URL.'
      setState((s) => ({ ...s, error: msg }))
      options?.onError?.(msg)
      return
    }

    // Basic URL validation
    let parsed: URL
    try {
      parsed = new URL(trimmed)
    } catch {
      const msg = 'Invalid URL format.'
      setState((s) => ({ ...s, error: msg }))
      options?.onError?.(msg)
      return
    }

    // Derive a title from URL path (unless overridden by ClassifyDialog)
    const pathParts = parsed.pathname.split('/')
    const lastSegment = pathParts[pathParts.length - 1] || 'imported-pdf'
    const bookTitle = titleOverride ?? decodeURIComponent(lastSegment)
      .replace(/\.pdf$/i, '')
      .replace(/[-_]/g, ' ')

    setState({ importing: true, progress: 10, error: null, url: trimmed, stage: 'Creating book record...' })

    try {
      // Step 1: Create a Book record in Payload CMS
      setState((s) => ({ ...s, progress: 20, stage: 'Creating book record...' }))

      const bookData: Record<string, unknown> = {
        title: bookTitle,
        category: category ?? 'textbooks',
        status: 'pending',
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
        throw new Error(`Failed to create book: ${createRes.status} — ${errBody}`)
      }

      const bookDoc = await createRes.json()
      const bookId = bookDoc.doc?.id ?? bookDoc.id

      // Step 2: Call Engine /ingest directly with the external URL
      // Engine will download the PDF server-side (no CORS / size limits)
      setState((s) => ({ ...s, progress: 40, stage: 'Sending to Engine for download...' }))

      const ingestRes = await fetch(`${ENGINE_URL}/engine/ingest`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          book_id: bookId,
          pdf_url: trimmed,
          category: category ?? 'textbooks',
          title: bookTitle,
        }),
      })

      if (!ingestRes.ok) {
        const errText = await ingestRes.text()
        throw new Error(`Engine ingest failed: ${ingestRes.status} — ${errText}`)
      }

      // Step 3: Update book status to processing
      setState((s) => ({ ...s, progress: 60, stage: 'Downloading & processing with MinerU...' }))

      await authFetch(`/api/books/${bookId}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ status: 'processing' }),
      })

      // Done — Engine is processing in background
      setState({ importing: false, progress: 100, error: null, url: trimmed, stage: 'Processing with MinerU...' })
      options?.onSuccess?.(bookId)
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Import from URL failed'
      setState((s) => ({ ...s, importing: false, error: message, stage: null }))
      options?.onError?.(message)
    }
  }, [options])

  return {
    importFromUrl,
    importing: state.importing,
    progress: state.progress,
    error: state.error,
    url: state.url,
    stage: state.stage,
    reset,
  }
}
