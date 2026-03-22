'use client'

import { useState, useEffect } from 'react'
import dynamic from 'next/dynamic'
import { AppProvider } from '@/features/shared/AppContext'
import { useAuth } from '@/features/shared/AuthProvider'
import BookSelector from '@/features/book-selector/BookSelector'
import ChatPanel from '@/features/chat/ChatPanel'
import ResizeHandle from './ResizeHandle'
import UserMenu from './UserMenu'

const PdfViewer = dynamic(
  () => import('@/features/pdf-viewer/PdfViewer'),
  { ssr: false, loading: () => <div className="flex h-full items-center justify-center text-slate-500 text-sm">Loading PDF viewer…</div> }
)

/**
 * AskPage — Ask 页面组装组件（feature 模块）
 * 组装 PDF 双栏 + 拖拽 + Chat
 * 负责人可独立修改此模块
 */
export default function AskPage() {
  const { user, status } = useAuth()
  const [leftWidth, setLeftWidth] = useState(800)

  useEffect(() => {
    setLeftWidth(Math.round(window.innerWidth * 0.6))
  }, [])

  useEffect(() => {
    if (status === 'loggedOut') {
      window.location.href = '/login'
    }
  }, [status])

  if (status === undefined) {
    return (
      <div className="flex h-screen items-center justify-center">
        <div className="flex items-center gap-3 text-slate-400">
          <div className="h-5 w-5 animate-spin rounded-full border-2 border-slate-600 border-t-brand-400" />
          <span className="text-sm">Loading…</span>
        </div>
      </div>
    )
  }

  if (!user) return null

  return (
    <AppProvider>
      <div className="flex h-screen flex-col">
        <header className="flex items-center gap-4 border-b border-white/10 bg-surface-900/80 backdrop-blur-sm px-4 py-2.5 shrink-0">
          <h1 className="text-base font-semibold text-white shrink-0 flex items-center gap-2">
            <span className="text-brand-400">📚</span>
            Textbook RAG
            <span className="text-[10px] font-mono text-slate-500 ml-1">v2.0</span>
          </h1>
          <div className="w-80">
            <BookSelector />
          </div>
          <div className="ml-auto">
            <UserMenu />
          </div>
        </header>

        <div className="flex flex-1 min-h-0">
          <div className="h-full overflow-hidden" style={{ width: leftWidth }}>
            <PdfViewer />
          </div>
          <ResizeHandle width={leftWidth} onResize={setLeftWidth} min={320} max={1600} />
          <div className="flex-1 h-full overflow-hidden min-w-[320px]">
            <ChatPanel />
          </div>
        </div>
      </div>
    </AppProvider>
  )
}
