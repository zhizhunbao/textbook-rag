/**
 * Pipeline feature — API layer
 *
 * 管道操作 API：触发 ingest、重建向量、同步到 Payload
 * Pipeline operations: trigger ingest, rebuild vectors, sync to Payload
 */

import type { PipelineTask, TriggerPipelineRequest, SyncResult } from './types'

const ENGINE = process.env.NEXT_PUBLIC_ENGINE_URL || 'http://localhost:8000'

// ── Helpers ─────────────────────────────────────────────────────────────────

async function request<T>(url: string, init?: RequestInit): Promise<T> {
  const res = await fetch(url, init)
  if (!res.ok) {
    const body = await res.text()
    throw new Error(`${res.status}: ${body}`)
  }
  return res.json() as Promise<T>
}

// ── 1. Pipeline Tasks (Payload CMS) ─────────────────────────────────────────

/** Create a pipeline task and trigger engine ingest */
export async function triggerPipeline(req: TriggerPipelineRequest): Promise<PipelineTask> {
  // Step 1: Create PipelineTask in Payload
  const taskResp = await fetch('/api/pipeline-tasks', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    credentials: 'include',
    body: JSON.stringify({
      taskType: req.taskType,
      book: req.bookId,
      status: 'queued',
      progress: 0,
      startedAt: new Date().toISOString(),
    }),
  })

  if (!taskResp.ok) {
    const body = await taskResp.text()
    throw new Error(`Failed to create pipeline task: ${taskResp.status} ${body}`)
  }

  const taskData = await taskResp.json()
  const task: PipelineTask = taskData.doc || taskData

  // Step 2: Get book details (need engineBookId for engine API)
  const bookResp = await fetch(`/api/books/${req.bookId}`)
  if (!bookResp.ok) throw new Error('Failed to fetch book')
  const book = await bookResp.json()

  // Step 3: Trigger engine endpoint based on task type
  const engineBody =
    req.taskType === 'reindex'
      ? {
          book_id: book.engineBookId || '',
          payload_book_id: req.bookId,
          task_id: task.id,
        }
      : {
          book_id: req.bookId,
          file_url: book.engineBookId || '',
          category: book.category || 'textbook',
          task_id: task.id,
        }

  const engineEndpoint = req.taskType === 'reindex' ? 'reindex' : 'ingest'
  const engineResp = await fetch(`${ENGINE}/engine/${engineEndpoint}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(engineBody),
  })

  if (!engineResp.ok) {
    // Update task to error
    await fetch(`/api/pipeline-tasks/${task.id}`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      credentials: 'include',
      body: JSON.stringify({ status: 'error', error: 'Engine ingest failed' }),
    })
    throw new Error('Engine ingest trigger failed')
  }

  // Step 4: Update book status to processing
  await fetch(`/api/books/${req.bookId}`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    credentials: 'include',
    body: JSON.stringify({ status: 'processing' }),
  })

  return task
}

/** Fetch pipeline tasks for a specific book */
export async function fetchBookTasks(bookId: number): Promise<PipelineTask[]> {
  const resp = await fetch(
    `/api/pipeline-tasks?where[book][equals]=${bookId}&sort=-createdAt&limit=10`,
    { credentials: 'include' }
  )
  if (!resp.ok) return []
  const data = await resp.json()
  return data.docs || []
}

/** Fetch a single task by ID (for polling) */
export async function fetchTask(taskId: number): Promise<PipelineTask | null> {
  try {
    const resp = await fetch(`/api/pipeline-tasks/${taskId}`, { credentials: 'include' })
    if (!resp.ok) return null
    return await resp.json()
  } catch {
    return null
  }
}

// ── 2. Engine Sync (Engine FastAPI) ─────────────────────────────────────────

/** Trigger a full sync from Engine SQLite → Payload CMS */
export async function triggerEngineSync(): Promise<SyncResult> {
  return request<SyncResult>(`${ENGINE}/engine/sync-to-payload`, {
    method: 'POST',
  })
}

// ── 3. Reindex (Engine FastAPI) ─────────────────────────────────────────────

/** Re-index all books (rebuild vectors) — calls build_vectors equivalent */
export async function triggerReindex(bookId?: string): Promise<{ status: string }> {
  const body: Record<string, unknown> = {}
  if (bookId) body.book_id = bookId
  return request<{ status: string }>(`${ENGINE}/engine/reindex`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
}

// ── 4. Pipeline Preview (Payload API) ───────────────────────────────────────

import type { PipelinePreview } from './types'

/** Fetch pipeline stage preview for a book */
export async function fetchPipelinePreview(engineBookId: string): Promise<PipelinePreview> {
  return request<PipelinePreview>(`/api/pipeline-preview?bookId=${encodeURIComponent(engineBookId)}`)
}

