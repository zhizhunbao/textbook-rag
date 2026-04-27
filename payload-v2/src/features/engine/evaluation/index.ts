/**
 * evaluation — barrel export.
 *
 * This is the ONLY public API surface for this module.
 */

// ============================================================
// Data layer
// ============================================================
export * from './types'
export * from './api'

// ============================================================
// UI components
// ============================================================
export { default as EvaluationPage } from './components/EvaluationPage'
export { default as EvalScoreCard } from './components/EvalScoreCard'
export { default as TracePanel } from './components/TracePanel'
export { default as ThinkingProcessPanel } from './components/ThinkingProcessPanel'
export { TraceStat, TracePromptBlock, TraceHitList, formatScore } from './components/TraceComponents'
