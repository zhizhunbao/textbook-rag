/**
 * features/engine/index.ts
 * Engine data layer — barrel export
 *
 * Maps 1:1 to engine-v2 sub-packages and llama_index.core.* modules.
 * Each sub-module provides types, API wrappers, and hooks for its domain.
 *
 * ┌──────────────────────────┬──────────────────────────┬────────────────────────┐
 * │ LlamaIndex Module        │ engine-v2 Package        │ features/engine/       │
 * ├──────────────────────────┼──────────────────────────┼────────────────────────┤
 * │ llama_index.readers      │ engine-v2/readers/       │ engine/readers/        │
 * │ llama_index.ingestion    │ engine-v2/ingestion/     │ engine/ingestion/      │
 * │ llama_index.retrievers   │ engine-v2/retrievers/    │ engine/retrievers/     │
 * │ llama_index.resp_synth   │ engine-v2/resp_synth/    │ engine/resp_synth/     │
 * │ llama_index.query_engine │ engine-v2/query_engine/  │ engine/query_engine/   │
 * │ llama_index.llms         │ engine-v2/llms/          │ engine/llms/           │
 * │ llama_index.evaluation   │ engine-v2/evaluation/    │ engine/evaluation/     │
 * │ llama_index.question_gen │ engine-v2/question_gen/  │ engine/question_gen/   │
 * └──────────────────────────┴──────────────────────────┴────────────────────────┘
 */

// ── 1. Readers ──────────────────────────────────────────────────────────────
export * from './readers'

// ── 2. Ingestion (frontend deleted — functionality moved to acquisition) ──
// Backend: engine_v2/ingestion/ still exists. Frontend UI: engine/acquisition/

// ── 3. Retrievers ───────────────────────────────────────────────────────────
export * from './retrievers'

// ── 4. Response Synthesizers ────────────────────────────────────────────────
export * from './response_synthesizers'

// ── 5. Query Engine ─────────────────────────────────────────────────────────
export * from './query_engine'

// ── 6. LLMs ─────────────────────────────────────────────────────────────────
export * from './llms'

// ── 7. Evaluation ───────────────────────────────────────────────────────────
export * from './evaluation'

// ── 8. Question Generation ──────────────────────────────────────────────────
export * from './question_gen'

// ── 9. Personas (Consulting Admin) ──────────────────────────────────────────
export * from './personas'
