import type { CollectionAfterChangeHook } from 'payload'

/**
 * P3-01: Books afterChange hook — triggers Engine ingest pipeline.
 *
 * Fires after a Book is created/updated. If the file field is populated
 * and status is 'pending', creates a PipelineTask and POSTs to Engine.
 */
export const afterChangeHook: CollectionAfterChangeHook = async ({
  doc,
  operation,
  req,
}) => {
  // Only trigger on create, or when file just uploaded
  if (!doc.filename) return doc
  if (doc.status !== 'pending') return doc

  const engineUrl = process.env.ENGINE_URL || 'http://localhost:8000'

  try {
    // 1. Create a PipelineTask record
    const task = await req.payload.create({
      collection: 'pipeline-tasks',
      data: {
        taskType: 'ingest',
        book: doc.id,
        status: 'queued',
        progress: 0,
      },
    })

    // 2. POST to Engine
    const fileUrl = `${process.env.PAYLOAD_PUBLIC_SERVER_URL || 'http://localhost:3000'}/media/${doc.filename}`
    const response = await fetch(`${engineUrl}/engine/ingest`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        book_id: doc.id,
        file_url: fileUrl,
        category: doc.category || 'textbook',
        task_id: task.id,
      }),
    })

    if (!response.ok) {
      throw new Error(`Engine ingest failed: ${response.statusText}`)
    }

    // 3. Update book status to processing
    await req.payload.update({
      collection: 'books',
      id: doc.id,
      data: { status: 'processing' },
    })
  } catch (error) {
    console.error('[Books.afterChange] Ingest trigger failed:', error)
    // Don't throw — hook failure should not block the admin save
  }

  return doc
}
