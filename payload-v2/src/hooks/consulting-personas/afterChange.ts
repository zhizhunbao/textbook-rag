/**
 * afterChange hook for ConsultingPersonas — Auto-initialize ChromaDB collection.
 *
 * Trigger: afterChange (on create)
 * When a new persona is created, calls the Engine API to ensure
 * the ChromaDB collection exists. Failure logs but does not block.
 */

import type { CollectionAfterChangeHook } from 'payload'

const ENGINE_URL = process.env.NEXT_PUBLIC_ENGINE_URL || 'http://localhost:8001'

// ============================================================
// Hook
// ============================================================
export const afterChange: CollectionAfterChangeHook = async ({
  doc,
  operation,
}) => {
  if (operation === 'create' && doc.slug) {
    try {
      const res = await fetch(
        `${ENGINE_URL}/engine/consulting/status/${doc.slug}`,
        { method: 'GET' },
      )
      if (res.ok) {
        console.log(
          `[ConsultingPersonas] Initialized collection for ${doc.slug}`,
        )
      } else {
        console.warn(
          `[ConsultingPersonas] Collection init returned ${res.status} for ${doc.slug}`,
        )
      }
    } catch (err) {
      console.warn(
        `[ConsultingPersonas] Failed to init collection for ${doc.slug}:`,
        err,
      )
    }
  }

  return doc
}
