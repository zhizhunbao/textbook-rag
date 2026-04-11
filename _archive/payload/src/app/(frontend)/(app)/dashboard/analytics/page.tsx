'use client'

import ComingSoon from '@/features/shared/components/ComingSoon'
import { BarChart3 } from 'lucide-react'

export default function Page() {
  return (
    <ComingSoon
      title="使用统计"
      description="查询量、活跃用户、热门书籍分析"
      icon={BarChart3}
      iconColor="text-blue-400"
    />
  )
}
