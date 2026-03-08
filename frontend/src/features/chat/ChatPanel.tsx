import { useState, useRef, useCallback, useEffect, type FormEvent } from "react";
import { queryTextbook, fetchSuggestions } from "../../api/client";
import { useAppState } from "../../context/AppContext";
import type { QueryResponse, SourceInfo } from "../../types/api";
import Loading from "../../components/Loading";
import MessageBubble from "./MessageBubble";
import SourceCard from "../source/SourceCard";

interface Message {
  role: "user" | "assistant";
  content: string;
  sources?: SourceInfo[];
}

const FALLBACK_SUGGESTIONS = [
  "What are the main topics covered in this book?",
  "What are the prerequisites for this book?",
  "Summarize the most important takeaways.",
  "What practical examples does this book provide?",
];

/* ── Suggestion card icons (simple SVGs) ── */
const ICONS = [
  // lightbulb
  <svg key="i0" className="h-5 w-5 text-amber-500" fill="none" stroke="currentColor" strokeWidth={1.5} viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" d="M12 18v-5.25m0 0a6.01 6.01 0 0 0 1.5-.189m-1.5.189a6.01 6.01 0 0 1-1.5-.189m3.75 7.478a12.06 12.06 0 0 1-4.5 0m3.75 2.383a14.406 14.406 0 0 1-3 0M9.75 17.25h4.5M12 3v.75m4.243 1.007-.53.53M20.25 12H21m-3.257 4.243.53.53M3.75 12H3m3.257-4.243-.53-.53M7.757 4.757l-.53-.53" /></svg>,
  // academic cap
  <svg key="i1" className="h-5 w-5 text-blue-500" fill="none" stroke="currentColor" strokeWidth={1.5} viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" d="M4.26 10.147a60.438 60.438 0 0 0-.491 6.347A48.62 48.62 0 0 1 12 20.904a48.62 48.62 0 0 1 8.232-4.41 60.46 60.46 0 0 0-.491-6.347m-15.482 0a50.636 50.636 0 0 0-2.658-.813A59.906 59.906 0 0 1 12 3.493a59.903 59.903 0 0 1 10.399 5.84c-.896.248-1.783.52-2.658.814m-15.482 0A50.717 50.717 0 0 1 12 13.489a50.702 50.702 0 0 1 7.74-3.342" /></svg>,
  // book open
  <svg key="i2" className="h-5 w-5 text-emerald-500" fill="none" stroke="currentColor" strokeWidth={1.5} viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" d="M12 6.042A8.967 8.967 0 0 0 6 3.75c-1.052 0-2.062.18-3 .512v14.25A8.987 8.987 0 0 1 6 18c2.305 0 4.408.867 6 2.292m0-14.25a8.966 8.966 0 0 1 6-2.292c1.052 0 2.062.18 3 .512v14.25A8.987 8.987 0 0 0 18 18a8.967 8.967 0 0 0-6 2.292m0-14.25v14.25" /></svg>,
  // code bracket
  <svg key="i3" className="h-5 w-5 text-violet-500" fill="none" stroke="currentColor" strokeWidth={1.5} viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" d="M17.25 6.75 22.5 12l-5.25 5.25m-10.5 0L1.5 12l5.25-5.25m7.5-3-4.5 16.5" /></svg>,
];

export default function ChatPanel() {
  const { currentBookId, selectedSource, books } = useAppState();
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [suggestions, setSuggestions] = useState<string[]>(FALLBACK_SUGGESTIONS);
  const bottomRef = useRef<HTMLDivElement>(null);

  const currentBook = books.find((b) => b.id === currentBookId);

  // Fetch book-specific suggestions when book changes
  useEffect(() => {
    if (!currentBookId) {
      setSuggestions(FALLBACK_SUGGESTIONS);
      return;
    }
    fetchSuggestions(currentBookId)
      .then((s) => setSuggestions(s.length ? s : FALLBACK_SUGGESTIONS))
      .catch(() => setSuggestions(FALLBACK_SUGGESTIONS));
  }, [currentBookId]);

  const submitQuestion = useCallback(
    async (q: string) => {
      if (!q.trim()) return;

      setInput("");
      setError(null);
      setMessages((prev) => [...prev, { role: "user", content: q }]);
      setLoading(true);

      try {
        const filters = currentBookId
          ? { book_ids: [currentBookId] }
          : undefined;
        const res: QueryResponse = await queryTextbook({
          question: q,
          filters,
          top_k: 5,
        });
        setMessages((prev) => [
          ...prev,
          { role: "assistant", content: res.answer, sources: res.sources },
        ]);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Unknown error");
      } finally {
        setLoading(false);
        setTimeout(
          () => bottomRef.current?.scrollIntoView({ behavior: "smooth" }),
          50,
        );
      }
    },
    [currentBookId],
  );

  function handleSubmit(e: FormEvent) {
    e.preventDefault();
    submitQuestion(input.trim());
  }

  return (
    <div className="flex h-full flex-col bg-white">
      {/* Messages */}
      <div className="flex-1 overflow-y-auto">
        {messages.length === 0 && !loading ? (
          /* ── GPT-style welcome ── */
          <div className="flex h-full flex-col items-center justify-center px-6">
            <div className="mb-2 text-4xl">📚</div>
            <h2 className="mb-1 text-xl font-semibold text-gray-800">
              {currentBook ? currentBook.title : "Textbook RAG"}
            </h2>
            <p className="mb-8 max-w-md text-center text-sm text-gray-400">
              {currentBook
                ? `Ask anything about this book — ${currentBook.page_count} pages, ${currentBook.chapter_count} chapters`
                : "Select a textbook, then ask a question"}
            </p>
            <div className="grid w-full max-w-lg grid-cols-2 gap-3">
              {suggestions.map((q, i) => (
                <button
                  key={q}
                  onClick={() => submitQuestion(q)}
                  className="group flex items-start gap-3 rounded-xl border border-gray-200 bg-gray-50/60 p-3.5 text-left text-sm text-gray-600 transition hover:border-blue-300 hover:bg-blue-50/60 hover:shadow-sm"
                >
                  <span className="mt-0.5 shrink-0">{ICONS[i % ICONS.length]}</span>
                  <span className="line-clamp-2 group-hover:text-blue-700">{q}</span>
                </button>
              ))}
            </div>
          </div>
        ) : (
          /* ── Conversation ── */
          <div className="space-y-4 p-4">
            {messages.map((m, i) => (
              <div key={i} className="space-y-2">
                <MessageBubble role={m.role} content={m.content} sources={m.sources} />
                {m.sources && m.sources.length > 0 && (
                  <div className="ml-2 mt-2">
                    <div className="mb-1.5 flex items-center gap-1 text-xs text-gray-400">
                      <svg className="h-3.5 w-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.747 0 3.332.477 4.5 1.253v13C19.832 18.477 18.247 18 16.5 18c-1.746 0-3.332.477-4.5 1.253" />
                      </svg>
                      <span>References — click to view in PDF</span>
                    </div>
                    <div className="space-y-1.5">
                    {m.sources.map((s, j) => (
                      <SourceCard
                        key={s.source_id}
                        source={s}
                        index={j}
                        isActive={selectedSource?.source_id === s.source_id}
                      />
                    ))}
                    </div>
                  </div>
                )}
              </div>
            ))}
            {loading && <Loading />}
            {error && (
              <div className="rounded bg-red-50 p-3 text-sm text-red-600">{error}</div>
            )}
            <div ref={bottomRef} />
          </div>
        )}
      </div>

      {/* Input */}
      <form onSubmit={handleSubmit} className="border-t bg-white px-4 py-3">
        <div className="mx-auto flex max-w-2xl gap-2">
          <input
            type="text"
            className="flex-1 rounded-xl border border-gray-300 px-4 py-2.5 text-sm shadow-sm focus:border-blue-400 focus:outline-none focus:ring-1 focus:ring-blue-400"
            placeholder={currentBook ? `Ask about ${currentBook.title}…` : "Type your question…"}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            disabled={loading}
          />
          <button
            type="submit"
            disabled={loading || !input.trim()}
            className="rounded-xl bg-blue-600 px-5 py-2.5 text-sm font-medium text-white shadow-sm hover:bg-blue-700 disabled:opacity-40"
          >
            <svg className="h-4 w-4" fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" d="M6 12 3.269 3.125A59.769 59.769 0 0 1 21.485 12 59.768 59.768 0 0 1 3.27 20.875L5.999 12Zm0 0h7.5" />
            </svg>
          </button>
        </div>
      </form>
    </div>
  );
}
