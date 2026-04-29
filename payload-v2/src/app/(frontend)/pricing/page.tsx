/**
 * /pricing - Public Free vs Pro plan comparison.
 *
 * Thin shell: only imports and renders the feature page component.
 */

import type { Metadata } from 'next'
import { PricingPage } from '@/features/billing/PricingPage'

export const metadata: Metadata = {
  title: 'Pricing',
  description: 'Compare ConsultRAG Free and Pro plans for AI consulting with private document RAG.',
  openGraph: {
    title: 'ConsultRAG Pricing',
    description: 'Compare ConsultRAG Free and Pro plans for AI consulting with private document RAG.',
    url: 'https://consultrag.com/pricing',
  },
}

// ============================================================
// Page
// ============================================================
export default function Page() {
  return <PricingPage />
}
