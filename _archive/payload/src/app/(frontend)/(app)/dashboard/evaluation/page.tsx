'use client'

import ComingSoon from '@/features/shared/components/ComingSoon'
import { LineChart } from 'lucide-react'

export default function Page() {
  return (
    <ComingSoon
      title="质量评估"
      description="RAG 回答质量 6 维度评分"
      icon={LineChart}
      iconColor="text-emerald-400"
    />
  )
}
