/**
 * evaluation API — Unified evaluation hub API wrappers.
 *
 * All API calls for the evaluation module.
 * Engine FastAPI: 5-dim evaluation, question depth, dedup, history evaluation.
 * Payload CMS: evaluation history CRUD, queries listing.
 */

import type {
  EvalSingleResult,
  EvalBatchResult,
  DepthResult,
  DedupResult,
  EvaluationResult,
  EvaluationStats,
  BatchEvalRequest,
  BatchEvalResponse,
  HistoryEvalSingleResult,
  HistoryEvalBatchResult,
  QueryListItem,
  QueryListResponse,
  SessionListItem,
} from './types'

const ENGINE = process.env.NEXT_PUBLIC_ENGINE_URL || 'http://localhost:8001'

// ============================================================
// Helpers
// ============================================================

/** Generic typed fetch wrapper with error handling. */
async function request<T>(url: string, init?: RequestInit): Promise<T> {
  const res = await fetch(url, init)
  if (!res.ok) {
    const body = await res.text()
    throw new Error(`${res.status}: ${body}`)
  }
  return res.json() as Promise<T>
}

// ============================================================
// Engine FastAPI — 5-dimensional evaluation (re-runs RAG)
// ============================================================

/** Evaluate a single query through the full RAG pipeline (5 dimensions). */
export async function evaluateSingle(question: string): Promise<EvalSingleResult> {
  return request<EvalSingleResult>(`${ENGINE}/engine/evaluation/single`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ question }),
  })
}

/** Batch-evaluate multiple queries (5 dimensions). */
export async function evaluateBatch(
  questions: string[],
  referenceAnswers?: string[],
): Promise<EvalBatchResult> {
  return request<EvalBatchResult>(`${ENGINE}/engine/evaluation/batch`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      questions,
      reference_answers: referenceAnswers ?? null,
    }),
  })
}

// ============================================================
// Engine FastAPI — Question quality + dedup
// ============================================================

/** Assess cognitive depth of a question (surface / understanding / synthesis). */
export async function assessQuestionQuality(question: string): Promise<DepthResult> {
  return request<DepthResult>(`${ENGINE}/engine/evaluation/quality`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ question }),
  })
}

/** Check if a question duplicates any in the history set. */
export async function checkQuestionDuplicate(
  question: string,
  historyQuestions: string[],
  threshold?: number,
): Promise<DedupResult> {
  return request<DedupResult>(`${ENGINE}/engine/evaluation/dedup`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      question,
      history_questions: historyQuestions,
      threshold: threshold ?? 0.85,
    }),
  })
}

// ============================================================
// Engine FastAPI — History-based evaluation (no RAG re-run)
// ============================================================

/** Evaluate an existing query by Payload Queries record ID.
 *
 * Uses the full-evaluate endpoint (EV2-T2) which computes all four
 * categories (RAG/LLM/Answer/Question), aggregates, status, and
 * sub-dimensions (completeness, clarity). This replaces the older
 * evaluate-history endpoint which only ran basic evaluators.
 */
export async function evaluateFromHistory(
  queryId: number,
  model?: string,
): Promise<HistoryEvalSingleResult> {
  return request<HistoryEvalSingleResult>(
    `${ENGINE}/engine/evaluation/full-evaluate`,
    {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ query_id: queryId, model: model ?? null }),
    },
  )
}

/** LLM provider info from the engine. */
export interface EvalProvider {
  name: string
  display_name: string
  model: string
  available: boolean
  base_url?: string
  endpoint?: string
}

/** Fetch available LLM providers for evaluation. */
export async function fetchEvalProviders(): Promise<EvalProvider[]> {
  const data = await request<{ providers: EvalProvider[] }>(
    `${ENGINE}/engine/evaluation/providers`,
  )
  return data.providers
}

/** Batch-evaluate the most recent N queries from Payload. */
export async function evaluateBatchFromHistory(
  nRecent: number = 20,
  batchId?: string,
): Promise<HistoryEvalBatchResult> {
  return request<HistoryEvalBatchResult>(
    `${ENGINE}/engine/evaluation/evaluate-batch`,
    {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        n_recent: nRecent,
        batch_id: batchId ?? null,
      }),
    },
  )
}

/** Fetch recent queries available for evaluation.
 *
 * Reads directly from Payload /api/queries (same-origin) instead of
 * routing through the Engine server, so it works even when Engine is offline.
 */
export async function fetchQueriesForEval(
  limit: number = 50,
  userId?: number,
): Promise<QueryListResponse> {
  const params = new URLSearchParams({
    limit: String(limit),
    sort: '-createdAt',
  })
  if (userId) {
    params.set('where[user][equals]', String(userId))
  }
  const data = await request<{ docs: any[]; totalDocs: number }>(
    `/api/queries?${params}`,
  )
  return {
    queries: data.docs.map((d: any) => ({
      id: d.id,
      question: d.question ?? '',
      answer: d.answer ?? '',
      model: d.model ?? null,
      createdAt: d.createdAt ?? '',
      sessionId: d.sessionId ?? null,
      sourceCount: Array.isArray(d.sources) ? d.sources.length : 0,
      // Pass through raw sources for AnswerBlockRenderer compatibility
      sources: d.sources ?? [],
    })),
    count: data.totalDocs,
  }
}

/**
 * Fetch queries for a specific ChatSession by reconstructing Q&A pairs
 * from ChatMessages.
 *
 * ChatMessages stores the correct Payload `session` relationship.
 * When a matching Queries doc exists (by question text), we use its ID
 * so the evaluation endpoint can reference it.
 */
export async function fetchQueriesBySession(
  sessionId: number,
): Promise<QueryListItem[]> {
  // Fetch all messages for this session (sorted chronologically)
  const msgParams = new URLSearchParams({
    'where[session][equals]': String(sessionId),
    sort: 'createdAt',
    limit: '500',
    depth: '0',
  })
  const msgData = await request<{ docs: any[] }>(
    `/api/chat-messages?${msgParams}`,
  )

  if (msgData.docs.length === 0) return []

  // Pair user + assistant messages into QueryListItems
  const items: QueryListItem[] = []
  const msgs = msgData.docs
  for (let i = 0; i < msgs.length; i++) {
    const msg = msgs[i]
    if (msg.role !== 'user') continue

    const nextMsg = msgs[i + 1]
    const answer = nextMsg?.role === 'assistant' ? (nextMsg.content ?? '') : ''
    const sources = nextMsg?.role === 'assistant' ? (nextMsg.sources ?? []) : []

    items.push({
      id: msg.id,
      question: msg.content ?? '',
      answer,
      model: null,
      createdAt: msg.createdAt ?? '',
      sessionId: String(sessionId),
      sourceCount: Array.isArray(sources) ? sources.length : 0,
      sources,
    })
  }

  // Cross-reference with Queries collection for accurate IDs & model info
  // (Evaluation endpoint needs the Queries collection ID)
  try {
    const qParams = new URLSearchParams({
      'where[sessionId][equals]': String(sessionId),
      sort: 'createdAt',
      limit: '200',
    })
    const qData = await request<{ docs: any[] }>(`/api/queries?${qParams}`)
    if (qData.docs.length > 0) {
      const queryMap = new Map<string, any>()
      for (const q of qData.docs) {
        queryMap.set(q.question?.trim(), q)
      }
      for (const item of items) {
        const match = queryMap.get(item.question.trim())
        if (match) {
          item.id = match.id
          item.model = match.model ?? null
          item.sources = match.sources?.length > 0 ? match.sources : item.sources
        }
      }
    }
  } catch {
    // Continue with ChatMessage-based data
  }

  // Deduplicate: if two ChatMessages matched the same Queries doc
  // (e.g. retried question), keep only the latest entry per id
  const seen = new Set<number>()
  const deduped: QueryListItem[] = []
  for (let i = items.length - 1; i >= 0; i--) {
    if (!seen.has(items[i].id)) {
      seen.add(items[i].id)
      deduped.push(items[i])
    }
  }
  deduped.reverse()

  return deduped
}

/** Fetch chat sessions for the evaluation sidebar.
 *
 * Reads from Payload /api/chat-sessions (same-origin).
 * Returns sessions sorted by most recent, with message count per session
 * derived from ChatMessages (user-role only).
 */
export async function fetchSessionsForEval(
  limit: number = 50,
  userId?: number,
): Promise<SessionListItem[]> {
  const params = new URLSearchParams({
    limit: String(limit),
    sort: '-createdAt',
  })
  if (userId) {
    params.set('where[user][equals]', String(userId))
  }
  const data = await request<{ docs: any[]; totalDocs: number }>(
    `/api/chat-sessions?${params}`,
  )

  // Count user-role messages per session via ChatMessages
  const sessionIds = data.docs.map((d: any) => d.id)
  let queryCounts: Record<string, number> = {}

  if (sessionIds.length > 0) {
    try {
      // Fetch user messages for all sessions in one batch
      const msgParams = new URLSearchParams({
        limit: '0',
        'where[role][equals]': 'user',
        'where[session][in]': sessionIds.join(','),
      })
      const msgData = await request<{ docs: any[] }>(
        `/api/chat-messages?${msgParams}`,
      )
      for (const m of msgData.docs) {
        const sid = String(typeof m.session === 'object' ? m.session?.id : m.session)
        queryCounts[sid] = (queryCounts[sid] || 0) + 1
      }
    } catch {
      // ChatMessages unavailable — show 0 counts
    }
  }

  return data.docs.map((d: any) => ({
    id: d.id,
    title: d.title ?? 'Untitled Session',
    createdAt: d.createdAt ?? '',
    queryCount: queryCounts[String(d.id)] || 0,
  }))
}

// ============================================================
// Payload CMS (same-origin) — Evaluation history
// ============================================================

/** Fetch evaluation results from Payload CMS, optionally filtered. */
export async function fetchEvaluations(opts?: {
  batchId?: string
  model?: string
  queryRef?: number
  limit?: number
}): Promise<{ evaluations: EvaluationResult[]; total: number }> {
  const params = new URLSearchParams()
  params.set('limit', String(opts?.limit ?? 100))
  params.set('sort', '-createdAt')

  if (opts?.batchId) params.set('where[batchId][equals]', opts.batchId)
  if (opts?.model) params.set('where[model][equals]', opts.model)
  if (opts?.queryRef) params.set('where[queryRef][equals]', String(opts.queryRef))

  const data = await request<{ docs: any[]; totalDocs: number }>(
    `/api/evaluations?${params}`,
  )
  return {
    evaluations: data.docs.map(mapEvaluation),
    total: data.totalDocs,
  }
}

/** Fetch a single evaluation by Payload ID. */
export async function fetchEvaluation(id: number): Promise<EvaluationResult> {
  const data = await request<any>(`/api/evaluations/${id}`)
  return mapEvaluation(data)
}

// ============================================================
// Aggregated statistics
// ============================================================

/** Compute aggregated evaluation stats (client-side from history). */
export async function fetchEvaluationStats(
  batchId?: string,
): Promise<EvaluationStats> {
  const { evaluations } = await fetchEvaluations({ batchId, limit: 500 })

  if (evaluations.length === 0) {
    return {
      totalEvaluations: 0,
      avgFaithfulness: null,
      avgRelevancy: null,
      avgCorrectness: null,
      avgContextRelevancy: null,
      avgAnswerRelevancy: null,
    }
  }

  const avg = (vals: (number | null)[]) => {
    const valid = vals.filter((v): v is number => v !== null)
    return valid.length > 0 ? valid.reduce((a, b) => a + b, 0) / valid.length : null
  }

  return {
    totalEvaluations: evaluations.length,
    avgFaithfulness: avg(evaluations.map((e) => e.faithfulness)),
    avgRelevancy: avg(evaluations.map((e) => e.relevancy)),
    avgCorrectness: avg(evaluations.map((e) => e.correctness)),
    avgContextRelevancy: avg(evaluations.map((e) => e.contextRelevancy)),
    avgAnswerRelevancy: avg(evaluations.map((e) => e.answerRelevancy)),
  }
}

// ============================================================
// Internal helpers
// ============================================================

/** Map raw Payload CMS document to typed EvaluationResult. */
function mapEvaluation(raw: any): EvaluationResult {
  return {
    id: raw.id,
    query: raw.query ?? '',
    answer: raw.answer ?? null,
    referenceAnswer: raw.referenceAnswer ?? null,
    faithfulness: raw.faithfulness ?? null,
    relevancy: raw.relevancy ?? null,
    correctness: raw.correctness ?? null,
    contextRelevancy: raw.contextRelevancy ?? null,
    answerRelevancy: raw.answerRelevancy ?? null,
    questionDepth: raw.questionDepth ?? null,
    questionDepthScore: raw.questionDepthScore ?? null,
    // Four-category aggregates (EV2-T2-04)
    ragScore: raw.ragScore ?? null,
    llmScore: raw.llmScore ?? null,
    answerScore: raw.answerScore ?? null,
    overallScore: raw.overallScore ?? null,
    // Answer sub-dimensions (EV2-T2-04)
    completeness: raw.completeness ?? null,
    clarity: raw.clarity ?? null,
    // Retrieval strategy (EV2-T1 + T2-04)
    retrievalMode: raw.retrievalMode ?? null,
    bm25Hits: raw.bm25Hits ?? null,
    vectorHits: raw.vectorHits ?? null,
    bothHits: raw.bothHits ?? null,
    // Status (EV2-T3-02)
    status: raw.status ?? null,
    feedback: raw.feedback ?? null,
    model: raw.model ?? null,
    sourceCount: raw.sourceCount ?? null,
    batchId: raw.batchId ?? null,
    queryRef: raw.queryRef ?? null,
    createdAt: raw.createdAt ?? '',
    updatedAt: raw.updatedAt ?? '',
  }
}
