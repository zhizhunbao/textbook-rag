import path from 'path'
import type { CollectionConfig } from 'payload'
import { isAdmin } from '../access/isAdmin'
import { isEditorOrAdmin } from '../access/isEditorOrAdmin'

/**
 * PdfUploads Collection — stores uploaded PDF files for MinerU processing.
 *
 * Slug: pdf-uploads
 * Storage: data/raw_pdfs/ (same directory Engine reads from)
 *
 * Separated from Media (images only) to keep concerns clean:
 *   - Media     → data/media/   (covers, thumbnails, image assets)
 *   - PdfUploads → data/raw_pdfs/ (source PDFs for ingestion pipeline)
 */
export const PdfUploads: CollectionConfig = {
  slug: 'pdf-uploads',
  labels: {
    singular: 'PDF Upload',
    plural: 'PDF Uploads',
  },
  admin: {
    group: 'Content',
    defaultColumns: ['filename', 'createdAt'],
  },
  access: {
    read: isAdmin,  // GO-MU-08: was () => true
    create: isEditorOrAdmin,
    update: isEditorOrAdmin,
    delete: isEditorOrAdmin,
  },
  upload: {
    staticDir: path.resolve(process.cwd(), '../data/raw_pdfs'),
    mimeTypes: ['application/pdf'],
  },
  fields: [
    {
      name: 'alt',
      type: 'text',
      admin: { description: 'Description of the PDF file' },
    },
  ],
}
