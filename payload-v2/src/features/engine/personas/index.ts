/**
 * personas — barrel export.
 *
 * This is the ONLY public API surface for this module.
 */

// ============================================================
// Exports
// ============================================================
export { default as PersonasPage } from './components/PersonasPage'
export { default as PersonaCard } from './components/PersonaCard'
export { default as PersonaIngestPanel } from './components/PersonaIngestPanel'
export type { PersonaWithStats, PersonaKbStatus, PersonaIngestResponse } from './types'
export { usePersonaAdmin } from './usePersonaAdmin'
