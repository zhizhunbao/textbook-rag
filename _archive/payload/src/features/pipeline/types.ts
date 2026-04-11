/**
 * Pipeline feature types
 *
 * 管理书本处理流水线的类型定义
 * Types for managing the book processing pipeline
 */

/** Pipeline task types matching PipelineTasks collection */
export type TaskType = 'ingest' | 'vectorize' | 'reindex' | 'full'

/** Task status matching PipelineTasks collection */
export type TaskStatus = 'queued' | 'running' | 'done' | 'error'

/** A pipeline task record from Payload */
export interface PipelineTask {
  id: number
  taskType: TaskType
  book: number | { id: number; title?: string }
  status: TaskStatus
  progress: number
  log: string | null
  error: string | null
  startedAt: string | null
  finishedAt: string | null
  createdAt: string
  updatedAt: string
}

/** Request to trigger a pipeline run */
export interface TriggerPipelineRequest {
  bookId: number
  taskType: TaskType
}

/** Response from engine sync endpoint */
export interface SyncResult {
  created: number
  updated: number
  errors: string[]
  total: number
}

/** Preview data for a single pipeline stage */
export interface StagePreview {
  stage: string
  label: string
  labelEn: string
  status: 'done' | 'pending' | 'missing' | 'error'
  input: { type: string; description: string; preview?: Record<string, unknown>[] }
  output: { type: string; description: string; preview?: Record<string, unknown>[] }
}

/** Full pipeline preview for a book */
export interface PipelinePreview {
  bookId: string
  title: string
  status: string
  stages: StagePreview[]
}

