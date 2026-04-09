import fs from 'fs'
import path from 'path'
import type { CollectionAfterChangeHook } from 'payload'

/**
 * Books afterChange hook — moves uploaded PDF into category subdirectory.
 *
 * Fires after a Book is created/updated. When pdfMedia is populated,
 * moves the uploaded PDF from data/raw_pdfs/ root into
 * data/raw_pdfs/{category}/ subdirectory.
 *
 * NOTE: Does NOT auto-trigger MinerU or ingest pipeline.
 * Pipeline is triggered manually by the user from the Pipeline Tab.
 *
 * Ref: HF-02 — fix upload directory structure
 */

const RAW_PDF_DIR = path.resolve(process.cwd(), '../data/raw_pdfs')

export const afterChangeHook: CollectionAfterChangeHook = async ({
  doc,
  previousDoc,
  operation,
  req,
}) => {
  // ── Guard: only act when pdfMedia is freshly set ──
  if (!doc.pdfMedia) return doc
  if (operation === 'update' && previousDoc?.pdfMedia === doc.pdfMedia) return doc

  // Resolve the PDF media filename
  const pdfMediaId = typeof doc.pdfMedia === 'object' ? doc.pdfMedia.id : doc.pdfMedia
  let pdfFilename: string | undefined

  try {
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

  // ── Move PDF to category subdirectory if it's in the root ──
  const category = doc.category || 'textbook'
  const srcPath = path.join(RAW_PDF_DIR, pdfFilename)
  const destDir = path.join(RAW_PDF_DIR, category)
  const destPath = path.join(destDir, pdfFilename)

  try {
    // Only move if file exists in root and not already in the category dir
    if (fs.existsSync(srcPath) && srcPath !== destPath) {
      // Create category subdirectory if needed
      fs.mkdirSync(destDir, { recursive: true })
      fs.renameSync(srcPath, destPath)
      req.payload.logger.info(
        `[Books.afterChange] Moved PDF: ${pdfFilename} → ${category}/${pdfFilename}`
      )
    }
  } catch (err) {
    req.payload.logger.warn(
      `[Books.afterChange] Failed to move PDF to category dir: ${err instanceof Error ? err.message : String(err)}`
    )
    // Non-fatal — file is still accessible from the root
  }

  req.payload.logger.info(
    `[Books.afterChange] Book ${doc.id} (${doc.title}) ready — pipeline NOT auto-triggered`
  )

  return doc
}
