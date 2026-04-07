import type { CollectionAfterChangeHook } from 'payload'

/**
 * Books afterChange hook — triggers Engine ingest pipeline.
 *
 * Fires after a Book is created/updated. When pdfMedia is populated
 * and status is 'pending', creates an IngestTask and POSTs to Engine
 * to start the MinerU parse → ingestion pipeline.
 *
 * Ref: HF-02 — fix trigger condition (pdfMedia instead of filename)
 *              + fix ENGINE_URL default port (8001)
 */

const ENGINE = process.env.NEXT_PUBLIC_ENGINE_URL || 'http://localhost:8001'

export const afterChangeHook: CollectionAfterChangeHook = async ({
  doc,
  previousDoc,
  operation,
  req,
}) => {
  // ── Guard: only trigger when pdfMedia is freshly set on a pending book ──
  // Skip if no PDF uploaded
  if (!doc.pdfMedia) return doc
  // Skip if status is not pending (already processing/indexed)
  if (doc.status !== 'pending') return doc
  // Skip on create — pdfMedia is linked via a subsequent PATCH
  // (useUpload: Step 1 create → Step 2 upload media → Step 3 PATCH pdfMedia)
  // On update: only trigger if pdfMedia just changed
  if (operation === 'update' && previousDoc?.pdfMedia === doc.pdfMedia) return doc

  // Resolve the PDF media URL for Engine to download
  const pdfMediaId = typeof doc.pdfMedia === 'object' ? doc.pdfMedia.id : doc.pdfMedia
  let pdfFilename: string | undefined

  try {
    // Fetch media doc to get filename
    const mediaDoc = await req.payload.findByID({
      collection: 'pdf-uploads',
      id: pdfMediaId,
    })
    pdfFilename = mediaDoc?.filename as string | undefined
  } catch {
    req.payload.logger.error(`[Books.afterChange] Failed to fetch media ${pdfMediaId}`)
    return doc
  }

  if (!pdfFilename) {
    req.payload.logger.error(`[Books.afterChange] Media ${pdfMediaId} has no filename`)
    return doc
  }

  req.payload.logger.info(
    `[Books.afterChange] Triggering ingest for book ${doc.id} (${doc.title}), PDF: ${pdfFilename}`
  )

  try {
    // 1. Create an IngestTask record
    const task = await req.payload.create({
      collection: 'ingest-tasks',
      overrideAccess: true,
      data: {
        taskType: 'ingest',
        book: doc.id,
        status: 'queued',
        progress: 0,
      },
    })

    // 2. POST to Engine ingest endpoint (pdf_filename — Engine reads from shared data/raw_pdfs/)
    const response = await fetch(`${ENGINE}/engine/ingest`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        book_id: doc.id,
        pdf_filename: pdfFilename,
        category: doc.category || 'textbook',
        task_id: task.id,
        title: doc.title,
      }),
    })

    if (!response.ok) {
      const errText = await response.text()
      throw new Error(`Engine ingest returned ${response.status}: ${errText}`)
    }

    // 3. Update book status to processing
    await req.payload.update({
      collection: 'books',
      id: doc.id,
      overrideAccess: true,
      data: { status: 'processing' },
    })

    req.payload.logger.info(`[Books.afterChange] Ingest triggered successfully, task=${task.id}`)
  } catch (error) {
    req.payload.logger.error(
      `[Books.afterChange] Ingest trigger failed: ${error instanceof Error ? error.message : String(error)}`
    )
    // Don't throw — hook failure should not block the admin save
  }

  return doc
}
