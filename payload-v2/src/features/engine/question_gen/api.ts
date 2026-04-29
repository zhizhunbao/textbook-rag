/**
 * engine/question_gen/api.ts
 * Aligned with: llama_index.question_gen → engine-v2/question_gen/generator.py
 *               → collections/Questions
 *
 * CRUD operations via Payload CMS and generation triggers via Engine FastAPI.
 */

import type { Question, GeneratedQuestion, QuestionsApiResponse, QuestionSet, GenerateDatasetResponse } from './types'

const ENGINE = process.env.NEXT_PUBLIC_ENGINE_URL || 'http://localhost:8001'

// NOTE: fetchIndexedBooks moved to @/features/shared/books

// ── CRUD (Payload CMS REST API) ─────────────────────────────────────────────

/** Fetch all questions from Payload CMS, sorted by likes desc */
export async function fetchQuestions(limit = 500): Promise<Question[]> {
  const res = await fetch(`/api/questions?limit=${limit}&sort=-likes`)
  if (!res.ok) throw new Error(`Failed to fetch questions: ${res.status}`)

  const data: QuestionsApiResponse = await res.json()
  return data.docs.map(mapDoc)
}

/** Fetch high-quality questions for a set of books */
export async function fetchHighQualityQuestions(
  bookIds: string[],
  limit = 6,
  minScore = 3,
): Promise<Question[]> {
  if (bookIds.length === 0) return []

  // Payload REST: must use where[and] to combine multiple conditions
  const bookFilter = bookIds.length === 1
    ? `where[and][0][bookId][equals]=${encodeURIComponent(bookIds[0])}`
    : bookIds.map((id, i) => `where[and][0][or][${i}][bookId][equals]=${encodeURIComponent(id)}`).join('&')
  const scoreFilter = `where[and][1][scoreOverall][greater_than_equal]=${minScore}`
  const url = `/api/questions?${bookFilter}&${scoreFilter}&sort=-scoreOverall,-likes&limit=${limit}`

  try {
    const res = await fetch(url)
    if (!res.ok) return []
    const data: QuestionsApiResponse = await res.json()
    return data.docs.map(mapDoc)
  } catch {
    return []
  }
}

/** Like a question (increment likes by 1) */
export async function likeQuestion(id: number, currentLikes: number): Promise<void> {
  const res = await fetch(`/api/questions/${id}`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ likes: currentLikes + 1 }),
  })
  if (!res.ok) throw new Error(`Like failed: ${res.status}`)
}

/** Delete a question by ID */
export async function deleteQuestion(id: number): Promise<void> {
  const res = await fetch(`/api/questions/${id}`, { method: 'DELETE' })
  if (!res.ok) throw new Error(`Delete failed: ${res.status}`)
}

/** Delete all questions (bulk delete) */
export async function deleteAllQuestions(ids: number[]): Promise<void> {
  const batchSize = 10
  for (let i = 0; i < ids.length; i += batchSize) {
    const batch = ids.slice(i, i + batchSize)
    await Promise.all(batch.map((id) =>
      fetch(`/api/questions/${id}`, { method: 'DELETE' }).catch(() => {})
    ))
  }
}

/** Persist evaluation results (depth + reasoning) to a question record */
export async function updateQuestionEval(
  id: number,
  data: { evalDepth: string; evalScore: number; evalReasoning: string },
): Promise<void> {
  await fetch(`/api/questions/${id}`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  })
}

// ── Generation (Engine FastAPI) ─────────────────────────────────────────────

/** Trigger question generation via engine LLM */
export async function generateQuestions(
  bookIds: string[],
  count = 6,
  options?: {
    model?: string
    category?: string
    chapterKey?: string
    pageStart?: number
    pageEnd?: number
  },
): Promise<GeneratedQuestion[]> {
  try {
    const body: Record<string, unknown> = { book_ids: bookIds, count }
    if (options?.model) body.model = options.model
    if (options?.category) body.category = options.category
    if (options?.chapterKey) body.chapter_key = options.chapterKey
    if (options?.pageStart != null) body.page_start = options.pageStart
    if (options?.pageEnd != null) body.page_end = options.pageEnd
    const res = await fetch(`${ENGINE}/engine/questions/generate`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    })
    if (!res.ok) {
      const errText = await res.text().catch(() => '')
      console.error('[generateQuestions] Failed:', res.status, errText, 'body sent:', JSON.stringify(body))
      return []
    }
    const data = await res.json()
    return data.questions ?? []
  } catch {
    return []
  }
}

/** Save a generated question to Payload CMS */
export async function saveQuestionToPayload(doc: {
  question: string
  bookId: string
  bookTitle: string
  topicHint: string
  source: 'ai' | 'manual'
  likes: number
  category?: string
  subcategory?: string
  questionCategory?: string
  scoreRelevance?: number
  scoreClarity?: number
  scoreDifficulty?: number
  scoreOverall?: number
  sourcePage?: number
}): Promise<void> {
  await fetch('/api/questions', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(doc),
  })
}

// ── Internal helpers ────────────────────────────────────────────────────────

function mapDoc(d: Record<string, any>): Question {
  return {
    id: d.id,
    question: d.question,
    bookId: d.bookId ?? '',
    bookTitle: d.bookTitle ?? null,
    topicHint: d.topicHint ?? null,
    source: d.source ?? 'ai',
    likes: d.likes ?? 0,
    category: d.category ?? null,
    subcategory: d.subcategory ?? null,
    questionCategory: d.questionCategory ?? null,
    sourcePage: d.sourcePage ?? null,
    model: d.model ?? null,
    scoreRelevance: d.scoreRelevance ?? null,
    scoreClarity: d.scoreClarity ?? null,
    scoreDifficulty: d.scoreDifficulty ?? null,
    scoreOverall: d.scoreOverall ?? null,
    // QD-01 fields
    sourceChunkId: d.sourceChunkId ?? null,
    referenceAnswer: d.referenceAnswer ?? null,
    datasetId: typeof d.datasetId === 'object' ? d.datasetId?.id ?? null : d.datasetId ?? null,
    evalDepth: d.evalDepth ?? null,
    evalScore: d.evalScore ?? null,
    evalReasoning: d.evalReasoning ?? null,
    createdAt: d.createdAt ?? '',
  }
}


// ── QuestionSet CRUD (Payload CMS REST API) — QD-03 ─────────────────────────

/** Fetch all question sets from Payload CMS */
export async function fetchQuestionSets(limit = 50): Promise<QuestionSet[]> {
  const res = await fetch(`/api/question-sets?limit=${limit}&sort=-createdAt`)
  if (!res.ok) throw new Error(`Failed to fetch question sets: ${res.status}`)
  const data = await res.json()
  return (data.docs || []).map((d: Record<string, any>): QuestionSet => ({
    id: d.id,
    name: d.name,
    purpose: d.purpose ?? 'eval',
    bookIds: d.bookIds ?? null,
    generationConfig: d.generationConfig ?? null,
    questionCount: d.questionCount ?? 0,
    status: d.status ?? 'generating',
    createdAt: d.createdAt ?? '',
  }))
}

/** Create a new question set */
export async function createQuestionSet(data: {
  name: string
  purpose?: string
  bookIds?: string[]
  generationConfig?: Record<string, unknown>
}): Promise<QuestionSet> {
  const res = await fetch('/api/question-sets', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  })
  if (!res.ok) throw new Error(`Failed to create question set: ${res.status}`)
  const doc = await res.json()
  return doc.doc
}

/** Fetch questions by dataset ID */
export async function fetchQuestionsByDataset(
  datasetId: number,
  limit = 500,
): Promise<Question[]> {
  const res = await fetch(
    `/api/questions?where[datasetId][equals]=${datasetId}&limit=${limit}&sort=-scoreOverall`,
  )
  if (!res.ok) throw new Error(`Failed to fetch questions by dataset: ${res.status}`)
  const data: QuestionsApiResponse = await res.json()
  return data.docs.map(mapDoc)
}


// ── Dataset generation (Engine FastAPI) — QD-05 ─────────────────────────────

/** Trigger batch question dataset generation via engine */
export async function generateDataset(options: {
  name: string
  purpose?: string
  bookIds?: string[]
  kPerBook?: number
  strategy?: string
}): Promise<GenerateDatasetResponse> {
  const body: Record<string, unknown> = {
    name: options.name,
    purpose: options.purpose ?? 'eval',
    k_per_book: options.kPerBook ?? 10,
    strategy: options.strategy ?? 'stratified',
  }
  if (options.bookIds?.length) body.book_ids = options.bookIds

  const res = await fetch(`${ENGINE}/engine/questions/generate-dataset`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
  if (!res.ok) {
    const errText = await res.text().catch(() => '')
    throw new Error(`generate-dataset failed: ${res.status} ${errText}`)
  }
  return res.json()
}
