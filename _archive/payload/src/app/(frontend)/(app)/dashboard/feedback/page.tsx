'use client'

import ComingSoon from '@/features/shared/components/ComingSoon'
import { ThumbsUp } from 'lucide-react'

export default function Page() {
  return (
    <ComingSoon
      title="反馈管理"
      description="用户 👍👎 汇总、差评分析"
      icon={ThumbsUp}
      iconColor="text-amber-400"
    />
  )
}
