/**
 * collections/endpoints/import-url.ts
 * Payload Custom Endpoint: POST /api/books/import-url
 *
 * Registers a discovered PDF URL as a new Book record in Payload.
 * Does NOT trigger Engine ingestion — that's a separate step via PipelineTab.
 *
 * Handles:
 *   - Category mapping: DataSource category (city) → Book category (ecdev)
 *   - Smart title generation: "economic_update_q1_2025_en.pdf" → "Ed Update Q1 2025"
 *   - Auto subcategory inference from filename patterns
 *
 * Request body:
 *   { url: string, category?: string, title?: string, subcategory?: string }
 *
 * Response:
 *   { success: true, bookId: number }
 *   { success: true, bookId: number, skipped: true }  (already exists)
 *   { success: false, error: string }
 */

import type { Endpoint } from 'payload'

// DataSource category → Book category mapping
// Only remap categories that need a different name; others keep as-is
const CATEGORY_MAP: Record<string, string> = {
  city: 'ecdev',
}

/**
 * Generate a clean, human-readable title from a PDF filename.
 * e.g. "economic_update_q1_2025_en.pdf" → "Ed Update Q1 2025"
 */
function generateTitle(filename: string): string {
  const stem = filename
    .replace(/\.pdf$/i, '')
    .replace(/[-_]/g, ' ')
    .trim()

  // ED Update pattern: "economic update qN YYYY en"
  const edMatch = stem.match(/economic\s+update\s+q(\d)\s+(\d{4})/i)
  if (edMatch) {
    return `Ed Update Q${edMatch[1]} ${edMatch[2]}`
  }

  // OREB pattern: "oreb market report YYYY"
  const orebMatch = stem.match(/oreb\s+(.*)/i)
  if (orebMatch) {
    return `OREB ${orebMatch[1].trim().replace(/\b\w/g, (c) => c.toUpperCase())}`
  }

  // Generic: title-case
  return stem.replace(/\b\w/g, (c) => c.toUpperCase())
}

/**
 * Infer subcategory from filename pattern.
 */
function inferSubcategory(filename: string): string {
  const lower = filename.toLowerCase()
  if (/economic.update.q\d/i.test(lower)) return 'Quarterly Reports'
  if (/oreb|market.report|housing/i.test(lower)) return 'Market Analysis'
  if (/tourism|visitor|hotel/i.test(lower)) return 'Tourism'
  if (/vacancy|commercial|retail/i.test(lower)) return 'Commercial'
  return ''
}

export const importUrlEndpoint: Endpoint = {
  handler: async (req) => {
    try {
      const { payload } = req

      // Parse request body
      const body = await req.json?.() ?? {}
      const { url, category, title, subcategory, fileSize } = body as {
        url?: string
        category?: string
        title?: string
        subcategory?: string
        fileSize?: number
      }

      if (!url || typeof url !== 'string') {
        return Response.json(
          { success: false, error: 'Missing required field: url' },
          { status: 400 },
        )
      }

      // Extract filename from URL
      let filename = 'imported-pdf'
      try {
        const parsed = new URL(url)
        const pathParts = parsed.pathname.split('/')
        filename = decodeURIComponent(pathParts[pathParts.length - 1] || 'imported-pdf')
      } catch { /* use default */ }

      // Generate title: use provided title, or derive from filename
      const bookTitle = title || generateTitle(filename)

      // Map DataSource category → Book category
      const bookCategory = CATEGORY_MAP[category || ''] || category || 'ecdev'

      // Infer subcategory from filename if not provided
      const bookSubcategory = subcategory || inferSubcategory(filename)

      // Use filename stem as engineBookId (matches engine pdf lookup)
      const filenameStem = filename.replace(/\.pdf$/i, '')
      const engineBookId = filenameStem

      // Dedup: check if a book with this engineBookId already exists
      const existing = await payload.find({
        collection: 'books',
        where: { engineBookId: { equals: engineBookId } },
        limit: 1,
      })

      if (existing.docs.length > 0) {
        return Response.json({
          success: true,
          bookId: existing.docs[0].id,
          skipped: true,
          message: 'Book already imported',
        })
      }

      // Create Book record (status: pending, no ingestion triggered)
      const bookData: Record<string, unknown> = {
        engineBookId,
        title: bookTitle,
        category: bookCategory,
        status: 'pending',
        metadata: {
          sourceUrl: url,
          pdfFilename: filename,
          fileSize: fileSize || 0,
        },
      }
      if (bookSubcategory) {
        bookData.subcategory = bookSubcategory
      }

      const bookDoc = await payload.create({
        collection: 'books',
        data: bookData,
      })

      return Response.json({ success: true, bookId: bookDoc.id })
    } catch (err) {
      const message = err instanceof Error ? err.message : String(err)
      return Response.json({ success: false, error: message }, { status: 500 })
    }
  },
  method: 'post',
  path: '/import-url',
}

