'use client'

import { useState, useEffect, useCallback, Suspense, useRef } from 'react'
import dynamic from 'next/dynamic'
import { useRouter, useSearchParams } from 'next/navigation'
import { AppProvider } from '@/features/shared/AppContext'
import { useAppState, useAppDispatch } from '@/features/shared/AppContext'
import { useAuth } from '@/features/shared/AuthProvider'
import { BookPicker } from '@/features/engine/readers'
import ChatPanel from './panel/ChatPanel'
import QuestionsSidebar from './panel/QuestionsSidebar'
import ConsultingSidebar from './panel/ConsultingSidebar'
import ResizeHandle from '@/features/shared/ResizeHandle'
import { useChatHistoryContext } from './history/ChatHistoryContext'
import { fetchIndexedBooks } from '@/features/shared/books'

const PdfViewer = dynamic(
  () => import('@/features/shared/pdf/PdfViewer'),
  { ssr: false, loading: () => <div className="flex h-full items-center justify-center text-muted-foreground text-sm">Loading PDF viewer…</div> }
)

// ============================================================
// PDF Tab types
// ============================================================
interface PdfTab {
  /** Payload CMS book id */
  bookId: number
  /** Display title */
  title: string
  /** Page to show on open */
  page: number
}

/** Inner layout — runs inside AppProvider + ChatHistoryProvider */
function ChatPageInner() {
  const { sessionStarted, sessionBookIds, books, currentBookId, selectedSource } = useAppState()
  const dispatch = useAppDispatch()
  const router = useRouter()
  const searchParams = useSearchParams()
  const [showQuestions, setShowQuestions] = useState(true)
  const [sidebarWidth, setSidebarWidth] = useState(300)
  /** PDF tabs — each element is an open PDF viewer tab */
  const [pdfTabs, setPdfTabs] = useState<PdfTab[]>([])
  const [activeTabBookId, setActiveTabBookId] = useState<number | null>(null)
  const [pdfWidth, setPdfWidth] = useState(600)
  const initialMode = searchParams.get('mode') === 'consulting' ? 'consulting' : 'rag'
  // C4-06: Track consulting persona for sidebar (only set when mode=consulting)
  const [consultingPersonaSlug, setConsultingPersonaSlug] = useState<string | null>(null)
  const [consultingPersonaName, setConsultingPersonaName] = useState<string | null>(null)
  /** Ref to ChatPanel's submitQuestion so the sidebar can call it directly */
  const submitRef = useRef<((q: string) => void) | null>(null)

  const { getSession, activeSessionId, setActiveSessionId } = useChatHistoryContext()

  useEffect(() => {
    if (books.length === 0) {
      fetchIndexedBooks().then((b) => {
        dispatch({ type: "SET_BOOKS", books: b });
      }).catch(console.error);
    }
  }, [books.length, dispatch]);

  /**
   * DM-T1-01: Auto-start session with ALL indexed books.
   * When books are loaded and no session is active, skip the BookPicker
   * and immediately enter chat mode scanning all documents.
   */
  useEffect(() => {
    if (books.length > 0 && !sessionStarted && !searchParams.get('session') && !searchParams.get('books')) {
      dispatch({ type: 'START_SESSION', bookIds: books.map((b) => b.id) });
    }
  }, [books.length, sessionStarted, dispatch, searchParams]);

  /** Handle ?session=<id> — restore an old session */
  useEffect(() => {
    const sessionParam = searchParams.get('session')
    if (!sessionParam) return
    const session = getSession(sessionParam)
    if (!session) return // Sessions not loaded yet — wait for next re-render
    dispatch({ type: 'START_SESSION', bookIds: session.sessionBookIds })
    setActiveSessionId(session.id)
    router.replace('/chat')
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [searchParams, getSession])

  /** Handle ?new=1 — start a fresh conversation with all books */
  useEffect(() => {
    if (searchParams.get('new') !== '1') return
    dispatch({ type: 'RESET_SESSION' })
    setActiveSessionId(null)
    setPdfTabs([])
    setActiveTabBookId(null)
    router.replace('/chat')
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [searchParams])

  /**
   * Handle ?books=id1,id2,id3 — start a scoped session with specific books.
   * Used by Files tab "New Chat" action to scope chat to selected documents.
   * Also auto-opens PDF viewers for all selected books.
   */
  const booksParamHandled = useRef(false)
  useEffect(() => {
    const booksParam = searchParams.get('books')
    if (!booksParam || booksParamHandled.current) return
    const ids = booksParam.split(',').map(Number).filter((n) => !isNaN(n) && n > 0)
    if (ids.length === 0) return
    // Wait until books are loaded so we can resolve titles for PDF tabs
    if (books.length === 0) return
    booksParamHandled.current = true

    setActiveSessionId(null)
    dispatch({ type: 'START_SESSION', bookIds: ids })

    // Auto-open PDF tabs for each selected book
    const tabs: PdfTab[] = ids
      .map((id) => {
        const book = books.find((b) => b.id === id)
        if (!book) return null
        return { bookId: id, title: book.title, page: 1 }
      })
      .filter((t): t is PdfTab => t !== null)

    setPdfTabs(tabs)
    if (tabs.length > 0) {
      setActiveTabBookId(tabs[0].bookId)
      dispatch({ type: 'SET_BOOK', bookId: tabs[0].bookId })
    }

    router.replace('/chat')
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [searchParams, books.length])


  /**
   * Auto-open / switch PDF tab when a citation source is selected.
   * If the book already has a tab, switch to it; otherwise add a new tab.
   */
  useEffect(() => {
    if (!selectedSource || !currentBookId) return

    const bookMatch = books.find((b) => b.id === currentBookId)
    const title = bookMatch?.title ?? 'Document'

    setPdfTabs((prev) => {
      const existing = prev.find((t) => t.bookId === currentBookId)
      if (existing) {
        // Update page for existing tab
        return prev.map((t) =>
          t.bookId === currentBookId
            ? { ...t, page: selectedSource.page_number }
            : t
        )
      }
      // Add new tab
      return [
        ...prev,
        { bookId: currentBookId, title, page: selectedSource.page_number },
      ]
    })
    setActiveTabBookId(currentBookId)
  }, [selectedSource, currentBookId, books])

  /** Switch active tab → also update AppContext so PdfViewer renders the correct book */
  const switchTab = useCallback(
    (bookId: number) => {
      setActiveTabBookId(bookId)
      dispatch({ type: 'SET_BOOK', bookId })
    },
    [dispatch],
  )

  /** Close a single tab; if it was the active one, switch to the nearest tab */
  const closeTab = useCallback(
    (bookId: number) => {
      setPdfTabs((prev) => {
        const idx = prev.findIndex((t) => t.bookId === bookId)
        const next = prev.filter((t) => t.bookId !== bookId)

        if (next.length === 0) {
          // No more tabs — hide the panel
          setActiveTabBookId(null)
          return next
        }

        // If we're closing the active tab, switch to the nearest
        if (bookId === activeTabBookId) {
          const newIdx = Math.min(idx, next.length - 1)
          const newActive = next[newIdx].bookId
          setActiveTabBookId(newActive)
          dispatch({ type: 'SET_BOOK', bookId: newActive })
        }

        return next
      })
    },
    [activeTabBookId, dispatch],
  )

  const showPdf = pdfTabs.length > 0

  const sessionBooks = books.filter((b) => sessionBookIds.includes(b.id))

  return (
    <div className="flex h-full flex-1 min-h-0">
      {!sessionStarted && books.length === 0 ? (
        /* Fallback: show BookPicker only when no books are indexed at all */
        <div className="flex-1 min-w-0 h-full">
          <BookPicker />
        </div>
      ) : !sessionStarted ? (
        /* Loading — books exist but auto-start hasn't fired yet */
        <div className="flex-1 flex items-center justify-center">
          <div className="flex items-center gap-3 text-muted-foreground">
            <div className="h-5 w-5 animate-spin rounded-full border-2 border-border border-t-primary" />
            <span className="text-sm">Loading documents…</span>
          </div>
        </div>
      ) : (
        <>
          {/* ── PDF Column with tabs (visible when any citation opened) ── */}
          {showPdf && (
            <>
              <div className="h-full flex flex-col overflow-hidden" style={{ width: pdfWidth }}>
                {/* Tab bar */}
                <div className="shrink-0 flex items-center border-b border-border bg-card">
                  <div className="flex-1 min-w-0 flex items-center overflow-x-auto">
                  {pdfTabs.map((tab) => {
                    const isActive = tab.bookId === activeTabBookId
                    return (
                      <div
                        key={tab.bookId}
                        className={`group flex items-center gap-1.5 px-3 py-2 cursor-pointer border-r border-border text-xs font-medium transition-colors shrink-0 max-w-[180px] ${
                          isActive
                            ? 'bg-background text-foreground border-b-2 border-b-primary'
                            : 'bg-card text-muted-foreground hover:bg-muted/50'
                        }`}
                        onClick={() => switchTab(tab.bookId)}
                        title={tab.title}
                      >
                        <svg className="h-3 w-3 shrink-0 text-primary/70" fill="none" stroke="currentColor" strokeWidth={1.8} viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" d="M19.5 14.25v-2.625a3.375 3.375 0 0 0-3.375-3.375h-1.5A1.125 1.125 0 0 1 13.5 7.125v-1.5a3.375 3.375 0 0 0-3.375-3.375H8.25m2.25 0H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 0 0-9-9Z" />
                        </svg>
                        <span className="truncate flex-1">{tab.title}</span>
                        <button
                          type="button"
                          onClick={(e) => {
                            e.stopPropagation()
                            closeTab(tab.bookId)
                          }}
                          className="flex items-center justify-center h-4 w-4 rounded-sm opacity-0 group-hover:opacity-100 hover:bg-muted-foreground/20 transition-all shrink-0"
                          title="Close tab"
                        >
                          <svg className="h-3 w-3" fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" d="M6 18 18 6M6 6l12 12" />
                          </svg>
                        </button>
                      </div>
                    )
                  })}
                  </div>
                  {/* Close all — pinned right, never scrolls away */}
                  <button
                    type="button"
                    onClick={() => { setPdfTabs([]); setActiveTabBookId(null) }}
                    className="shrink-0 flex items-center justify-center h-7 w-7 rounded-md text-muted-foreground hover:bg-muted hover:text-foreground transition-colors mx-1 border-l border-border"
                    title="Close all PDFs"
                  >
                    <svg className="h-3.5 w-3.5" fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" d="M6 18 18 6M6 6l12 12" />
                    </svg>
                  </button>
                </div>
                {/* PDF content */}
                <div className="flex-1 min-h-0 overflow-hidden">
                  <PdfViewer />
                </div>
              </div>

              <ResizeHandle width={pdfWidth} onResize={setPdfWidth} min={280} max={1400} />
            </>
          )}

          {/* ── Consulting Sidebar — temporarily hidden (DEV-MODE) ── */}
          {/* consultingPersonaSlug && (
            <>
              <ConsultingSidebar
                personaSlug={consultingPersonaSlug}
                personaName={consultingPersonaName}
                onClose={() => setConsultingPersonaSlug(null)}
                style={{ width: sidebarWidth }}
              />
              <ResizeHandle width={sidebarWidth} onResize={setSidebarWidth} min={220} max={400} />
            </>
          ) */}

          {/* ── Chat Panel (centered when PDF is hidden) ── */}
          <div className="flex-1 h-full overflow-hidden min-w-[300px]">
            <ChatPanel
              activeSessionId={activeSessionId}
              onSessionCreated={setActiveSessionId}
              submitRef={submitRef}
              showQuestions={showQuestions}
              onToggleQuestions={() => setShowQuestions((v) => !v)}
              initialMode={initialMode}
              onConsultingPersonaChange={(slug, name) => {
                setConsultingPersonaSlug(slug)
                setConsultingPersonaName(name ?? null)
              }}
            />
          </div>

          {/* ── Questions Sidebar (right, resizable) — shown in RAG mode ── */}
          {showQuestions && (
            <>
              <ResizeHandle width={sidebarWidth} onResize={setSidebarWidth} min={220} max={480} invert />
              <QuestionsSidebar
                bookIds={sessionBooks.map((b) => b.book_id)}
                isScoped={sessionBookIds.length > 0 && sessionBookIds.length < books.length}
                personaSlug={consultingPersonaSlug}
                onSelect={(q) => {
                  submitRef.current?.(q)
                }}
                onClose={() => setShowQuestions(false)}
                style={{ width: sidebarWidth }}
              />
            </>
          )}
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
