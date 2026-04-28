/**
 * evaluation types — 5-dimensional evaluation, question depth, and deduplication.
 * Extended with four-category scoring (EV2-T2/T3).
 *
 * Shared type definitions for the evaluation module.
 */

// ============================================================
// Domain types — Engine API responses
// ============================================================

/** 5-dimensional evaluation score tuple. */
export interface EvalScores {
  faithfulness: number | null
  relevancy: number | null
  correctness: number | null
  context_relevancy: number | null
  answer_relevancy: number | null
}

/** Single query evaluation result from POST /engine/evaluation/single. */
export interface EvalSingleResult {
  query: string
  answer: string
  scores: EvalScores
  feedback: Record<string, string>
}

/** Batch evaluation result from POST /engine/evaluation/batch. */
export interface EvalBatchResult {
  results: EvalSingleResult[]
  count: number
}

/** Cognitive depth label (surface → understanding → synthesis). */
export type DepthLabel = 'surface' | 'understanding' | 'synthesis'

/** Question depth result from POST /engine/evaluation/quality. */
export interface DepthResult {
  question: string
  depth: DepthLabel
  score: number
  reasoning: string
}

/** Question deduplication result from POST /engine/evaluation/dedup. */
export interface DedupResult {
  is_duplicate: boolean
  most_similar: string | null
  similarity_score: number
  suggestion: string
}

/** Question quality scores from history evaluation. */
export interface QuestionScores {
  depth: string | null       // surface / understanding / synthesis
  depth_score: number | null // raw 1-5 scale
  depth_normalized: number | null // 0-1 normalised
}

/** Answer quality scores from history evaluation. */
export interface AnswerScores {
  faithfulness: number | null
  answer_relevancy: number | null
}

/** Citation quality scores from history evaluation. */
export interface CitationScores {
  context_relevancy: number | null
  relevancy: number | null
}

/** Grouped scores from history-based evaluation. */
export interface HistoryEvalScores {
  question: QuestionScores
  answer: AnswerScores
  citation: CitationScores
}

/** Single history evaluation result from POST /evaluation/evaluate-history. */
export interface HistoryEvalSingleResult {
  query_id: number
  question: string
  answer: string
  scores: HistoryEvalScores
  feedback: Record<string, string>
}

/** Batch history evaluation result from POST /evaluation/evaluate-batch. */
export interface HistoryEvalBatchResult {
  results: Array<{
    query_id: number
    question: string
    scores: HistoryEvalScores
  }>
  count: number
  batch_id: string | null
}

/** Query record from GET /evaluation/queries. */
export interface QueryListItem {
  id: number
  question: string
  answer: string
  model: string | null
  createdAt: string
  sessionId: string | null
  sourceCount: number
  /** Raw sources from Payload — SourceInfo-compatible for AnswerBlockRenderer. */
  sources: any[]
}

/** Citation source snippet (legacy, kept for backward compat). */
export interface SourceSnippet {
  book_title: string
  chapter_title: string
  page: number | null
  snippet: string
}

/** Response from GET /evaluation/queries. */
export interface QueryListResponse {
  queries: QueryListItem[]
  count: number
}

/** Session summary for evaluation sidebar. */
export interface SessionListItem {
  id: number
  title: string
  createdAt: string
  queryCount: number
}

// ============================================================
// Domain types — Payload CMS records
// ============================================================

/** Evaluation pass/fail/pending status (EV2-T3-02). */
export type EvalStatus = 'pass' | 'fail' | 'pending'

/** Persisted evaluation result from Payload Evaluations collection. */
export interface EvaluationResult {
  id: number
  query: string
  answer: string | null
  referenceAnswer: string | null

  faithfulness: number | null
  relevancy: number | null
  correctness: number | null
  contextRelevancy: number | null
  answerRelevancy: number | null
  questionDepth: string | null
  questionDepthScore: number | null

  // Four-category aggregates (EV2-T2-04)
  ragScore: number | null
  llmScore: number | null
  answerScore: number | null
  overallScore: number | null

  // Answer sub-dimensions (EV2-T2-04 / EI-T3)
  completeness: number | null
  clarity: number | null
  guidelinesPass: boolean | null
  guidelinesFeedback: string | null

  // Retrieval strategy (EV2-T1 + T2-04)
  retrievalMode: 'hybrid' | 'vector_only' | null
  bm25Hits: number | null
  vectorHits: number | null
  bothHits: number | null

  // IR Retrieval Metrics (EI-T2, needs Golden Dataset)
  hitRate: number | null
  mrr: number | null
  precisionAtK: number | null
  recallAtK: number | null
  ndcg: number | null
  irScore: number | null
  goldenMatchRef: number | null

  // Status (EV2-T3-02)
  status: EvalStatus | null

  feedback: Record<string, string> | null

  model: string | null
  sourceCount: number | null
  batchId: string | null
  queryRef: number | null

  // Evaluation metadata (EUX-T2)
  judgeModel: string | null
  answerModel: string | null
  llmCalls: number | null

  // Improvement suggestions (EUX-T3)
  suggestions: EvalSuggestion[] | null

  // AveragePrecision (EUX-T4)
  averagePrecision: number | null

  createdAt: string
  updatedAt: string
}

/** Improvement suggestion for low-scoring evaluations (EUX-T3). */
export type SuggestionSeverity = 'high' | 'medium' | 'low' | 'info'

export interface EvalSuggestion {
  dimension: string
  severity: SuggestionSeverity
  message_en: string
  message_zh: string
}

// ============================================================
// API types
// ============================================================

/** Client-side aggregated stats from evaluation history. */
export interface EvaluationStats {
  totalEvaluations: number
  avgFaithfulness: number | null
  avgRelevancy: number | null
  avgCorrectness: number | null
  avgContextRelevancy: number | null
  avgAnswerRelevancy: number | null
}

/** Request body for triggering a batch evaluation run. */
export interface BatchEvalRequest {
  bookIds?: string[]
  questionCount?: number
  model?: string
}

/** Status response for an in-progress batch evaluation. */
export interface BatchEvalResponse {
  batchId: string
  status: 'queued' | 'running' | 'done' | 'error'
  evaluated: number
  total: number
}

// ============================================================
// Full evaluation API types (EV2-T2/T3)
// ============================================================

/** Response from POST /engine/evaluation/full-evaluate. */
export interface FullEvalApiResult {
  query_id: number
  question: string
  scores: {
    rag: {
      context_relevancy: number | null
      relevancy: number | null
      aggregate: number | null
    }
    llm: {
      faithfulness: number | null
      aggregate: number | null
    }
    answer: {
      answer_relevancy: number | null
      completeness: number | null
      clarity: number | null
      guidelines_pass: boolean | null
      guidelines_feedback: string | null
      aggregate: number | null
    }
    question: {
      depth: string | null
      depth_score: number | null
    }
    ir: {
      hit_rate: number | null
      mrr: number | null
      precision_at_k: number | null
      recall_at_k: number | null
      ndcg: number | null
      aggregate: number | null
      golden_match_id: number | null
    } | null
  }
  overall_score: number | null
  status: EvalStatus | null
  retrieval: {
    mode: string | null
    bm25_hits: number
    vector_hits: number
    both_hits: number
  }
  feedback: Record<string, string>
}
