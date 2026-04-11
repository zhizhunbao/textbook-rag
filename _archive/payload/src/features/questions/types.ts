/**
 * Question — AI-generated or user-submitted study question (Payload CMS doc).
 * 存储自动生成或用户提交的学习问题，用于后续分析和复习。
 */
export interface Question {
  id: number
  question: string
  bookId: string
  bookTitle: string | null
  topicHint: string | null
  source: 'ai' | 'manual'
  likes: number
  category: string | null
  subcategory: string | null
  model: string | null
  scoreRelevance: number | null
  scoreClarity: number | null
  scoreDifficulty: number | null
  scoreOverall: number | null
  createdAt: string
}

/**
 * GeneratedQuestion — raw question from LLM generation (engine response shape).
 * LLM 生成返回的原始问题结构，尚未入库。
 */
export interface GeneratedQuestion {
  question: string
  book_id: string
  book_title: string
  topic_hint: string
}

/** Payload REST API response shape for questions collection */
export interface QuestionsApiResponse {
  docs: Array<Record<string, any>>
  totalDocs: number
  totalPages: number
  page: number
}
