/** Question group for persona-scoped suggested questions. */
export interface QuestionCategory {
  id: string
  label: string
  icon: string
  questions: string[]
}

/** Shared type for all consulting persona seed entries. */
export interface PersonaSeed {
  [key: string]: unknown
  name: string
  slug: string
  country: string
  category: string
  icon: string
  description: string
  chromaCollection: string
  isEnabled: boolean
  sortOrder: number
  systemPrompt: string
  greeting: string
  /** Optional persona-scoped suggested questions, grouped by topic. */
  suggestedQuestions?: QuestionCategory[]
}
