'use client'

import { useState, useEffect, useCallback, Suspense } from 'react'
import dynamic from 'next/dynamic'
import { useRouter, useSearchParams } from 'next/navigation'
import { AppProvider } from '@/features/shared/AppContext'
import { useAppState, useAppDispatch } from '@/features/shared/AppContext'
import { useAuth } from '@/features/shared/AuthProvider'
import BookPicker from './book/BookPicker'
import ChatPanel from './panel/ChatPanel'
import ResizeHandle from './ResizeHandle'
import { useChatHistoryContext } from './history/ChatHistoryContext'
import { fetchBooks } from '@/features/shared/api'

const PdfViewer = dynamic(
  () => import('@/features/chat/pdf/PdfViewer'),
  { ssr: false, loading: () => <div className="flex h-full items-center justify-center text-muted-foreground text-sm">Loading PDF viewer…</div> }
)

/** Inner layout — runs inside AppProvider + ChatHistoryProvider */
function ChatPageInner() {
  const { sessionStarted, sessionBookIds, books, currentBookId } = useAppState()
  const dispatch = useAppDispatch()
  const router = useRouter()
  const searchParams = useSearchParams()
  const [leftWidth, setLeftWidth] = useState(800)

  const { getSession, activeSessionId, setActiveSessionId } = useChatHistoryContext()

  useEffect(() => {
    setLeftWidth(Math.round(window.innerWidth * 0.45))
  }, [])

  useEffect(() => {
    if (books.length === 0) {
      fetchBooks().then((b) => {
        dispatch({ type: "SET_BOOKS", books: b });
      }).catch(console.error);
    }
  }, [books.length, dispatch]);

  /** Handle ?session=<id> — restore an old session */
  useEffect(() => {
    const sessionParam = searchParams.get('session')
    if (!sessionParam) return
    const session = getSession(sessionParam)
    if (session) {
      dispatch({ type: 'START_SESSION', bookIds: session.sessionBookIds })
      setActiveSessionId(session.id)
    }
    router.replace('/chat')
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [searchParams])

  /** Handle ?new=1 — reset to book picker */
  useEffect(() => {
    if (searchParams.get('new') !== '1') return
    dispatch({ type: 'RESET_SESSION' })
    setActiveSessionId(null)
    router.replace('/chat')
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [searchParams])

  const sessionBooks = books.filter((b) => sessionBookIds.includes(b.id))

  return (
    <div className="flex h-full flex-1 min-h-0">
      {!sessionStarted ? (
        <div className="flex-1 min-w-0 h-full">
          <BookPicker />
        </div>
      ) : (
        <>
          {/* ── PDF Column ── */}
          <div className="h-full flex flex-col overflow-hidden" style={{ width: leftWidth }}>
            {/* Multi-book PDF tab switcher */}
            {sessionBooks.length > 1 && (
              <div className="shrink-0 flex items-center gap-0 overflow-x-auto border-b border-border bg-card px-2">
                {sessionBooks.map((book) => {
                  const active = book.id === currentBookId
                  return (
                    <button
                      key={book.id}
                      type="button"
                      onClick={() => dispatch({ type: 'SET_BOOK', bookId: book.id })}
                      className={`shrink-0 flex items-center gap-1.5 border-b-2 px-3 py-2 text-xs font-medium transition-colors whitespace-nowrap ${
                        active
                          ? 'border-foreground text-foreground'
                          : 'border-transparent text-muted-foreground hover:text-foreground'
                      }`}
                      title={book.title}
                    >
                      <svg className="h-3.5 w-3.5 shrink-0" fill="none" stroke="currentColor" strokeWidth={1.8} viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" d="M12 6.042A8.967 8.967 0 0 0 6 3.75c-1.052 0-2.062.18-3 .512v14.25A8.987 8.987 0 0 1 6 18c2.305 0 4.408.867 6 2.292m0-14.25a8.966 8.966 0 0 1 6-2.292c1.052 0 2.062.18 3 .512v14.25A8.987 8.987 0 0 0 18 18a8.967 8.967 0 0 0-6 2.292m0-14.25v14.25" />
                      </svg>
                      <span className="max-w-[100px] truncate">{book.title}</span>
                    </button>
                  )
                })}
              </div>
            )}
            <div className="flex-1 min-h-0 overflow-hidden">
              <PdfViewer />
            </div>
          </div>

          <ResizeHandle width={leftWidth} onResize={setLeftWidth} min={280} max={1400} />

          {/* ── Chat Panel ── */}
          <div className="flex-1 h-full overflow-hidden min-w-[300px]">
            <ChatPanel
              activeSessionId={activeSessionId}
              onSessionCreated={setActiveSessionId}
            />
          </div>
        </>
      )}
    </div>
  )
}

/**
 * ChatPage — 问答页面
 * Guard: requires auth; login → /library; shows BookPicker until session started.
 */
export default function ChatPage() {
  const { status } = useAuth()

  useEffect(() => {
    if (status === 'loggedOut') {
      window.location.href = '/login'
    }
  }, [status])

  if (status === undefined) {
    return (
      <div className="flex h-full items-center justify-center">
        <div className="flex items-center gap-3 text-slate-400">
          <div className="h-5 w-5 animate-spin rounded-full border-2 border-slate-600 border-t-brand-400" />
          <span className="text-sm">Loading…</span>
        </div>
      </div>
    )
  }

  if (status === 'loggedOut') return null

  return (
    <AppProvider>
      <Suspense>
        <ChatPageInner />
      </Suspense>
    </AppProvider>
  )
}
