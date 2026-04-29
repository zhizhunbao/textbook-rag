/**
 * /consulting — Compatibility redirect to unified Chat consulting mode.
 *
 * Consulting conversations are managed by the main Chat module.
 */

'use client'

import { useEffect } from 'react'
import { useRouter } from 'next/navigation'

export default function ConsultingRoute() {
  const router = useRouter()

  useEffect(() => {
    router.replace('/chat?mode=consulting')
  }, [router])

  return (
    <div className="flex h-full items-center justify-center">
      <div className="flex items-center gap-3 text-muted-foreground">
        <div className="h-5 w-5 animate-spin rounded-full border-2 border-border border-t-primary" />
        <span className="text-sm">Opening consulting chat...</span>
      </div>
    </div>
  )
}
