'use client'

import { Suspense } from 'react'
import RetrieverTestPage from '@/features/engine/retrievers/components/RetrieverTestPage'

export default function Page() {
  return (
    <Suspense>
      <RetrieverTestPage />
    </Suspense>
  )
}
