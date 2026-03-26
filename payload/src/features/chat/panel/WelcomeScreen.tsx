/**
 * panel/WelcomeScreen.tsx
 * 聊天空状态 — AI 自动生成的学习问题卡片 + 手动建议 fallback
 *
 * Flow:
 *   1. 进入 session → 立即用 LLM 从选定书籍生成问题
 *   2. 生成中展示 shimmer loading skeleton
 *   3. 生成完毕展示可点击的问题卡片 (含 topic hint 标签)
 *   4. 点击 → 自动触发 submitQuestion → 走正常 RAG 流程 → citation 可定位
 */
import { useState, useEffect } from "react";
import type { BookSummary } from "@/features/shared/types";
import { fetchGeneratedQuestions, type GeneratedQuestion } from "@/features/shared/api";
import { Database, Layers, Bot, Sparkles, Check, Loader2 } from "lucide-react";

/* ── Color palette for topic hints ── */
const TOPIC_COLORS = [
  "bg-blue-100 text-blue-700 dark:bg-blue-900/40 dark:text-blue-300",
  "bg-emerald-100 text-emerald-700 dark:bg-emerald-900/40 dark:text-emerald-300",
  "bg-amber-100 text-amber-700 dark:bg-amber-900/40 dark:text-amber-300",
  "bg-purple-100 text-purple-700 dark:bg-purple-900/40 dark:text-purple-300",
  "bg-rose-100 text-rose-700 dark:bg-rose-900/40 dark:text-rose-300",
  "bg-sky-100 text-sky-700 dark:bg-sky-900/40 dark:text-sky-300",
];

const CARD_ICONS = [
  // lightbulb
  <svg key="i0" className="h-4 w-4 shrink-0" fill="none" stroke="currentColor" strokeWidth={1.5} viewBox="0 0 24 24">
    <path strokeLinecap="round" strokeLinejoin="round" d="M12 18v-5.25m0 0a6.01 6.01 0 0 0 1.5-.189m-1.5.189a6.01 6.01 0 0 1-1.5-.189m3.75 7.478a12.06 12.06 0 0 1-4.5 0m3.75 2.383a14.406 14.406 0 0 1-3 0M9.75 17.25h4.5M12 3v.75m4.243 1.007-.53.53M20.25 12H21m-3.257 4.243.53.53M3.75 12H3m3.257-4.243-.53-.53M7.757 4.757l-.53-.53" />
  </svg>,
  // academic cap
  <svg key="i1" className="h-4 w-4 shrink-0" fill="none" stroke="currentColor" strokeWidth={1.5} viewBox="0 0 24 24">
    <path strokeLinecap="round" strokeLinejoin="round" d="M4.26 10.147a60.438 60.438 0 0 0-.491 6.347A48.62 48.62 0 0 1 12 20.904a48.62 48.62 0 0 1 8.232-4.41 60.46 60.46 0 0 0-.491-6.347m-15.482 0a50.636 50.636 0 0 0-2.658-.813A59.906 59.906 0 0 1 12 3.493a59.903 59.903 0 0 1 10.399 5.84c-.896.248-1.783.52-2.658.814m-15.482 0A50.717 50.717 0 0 1 12 13.489a50.702 50.702 0 0 1 7.74-3.342" />
  </svg>,
  // book
  <svg key="i2" className="h-4 w-4 shrink-0" fill="none" stroke="currentColor" strokeWidth={1.5} viewBox="0 0 24 24">
    <path strokeLinecap="round" strokeLinejoin="round" d="M12 6.042A8.967 8.967 0 0 0 6 3.75c-1.052 0-2.062.18-3 .512v14.25A8.987 8.987 0 0 1 6 18c2.305 0 4.408.867 6 2.292m0-14.25a8.966 8.966 0 0 1 6-2.292c1.052 0 2.062.18 3 .512v14.25A8.987 8.987 0 0 0 18 18a8.967 8.967 0 0 0-6 2.292m0-14.25v14.25" />
  </svg>,
  // code
  <svg key="i3" className="h-4 w-4 shrink-0" fill="none" stroke="currentColor" strokeWidth={1.5} viewBox="0 0 24 24">
    <path strokeLinecap="round" strokeLinejoin="round" d="M17.25 6.75 22.5 12l-5.25 5.25m-10.5 0L1.5 12l5.25-5.25m7.5-3-4.5 16.5" />
  </svg>,
  // magnifying glass
  <svg key="i4" className="h-4 w-4 shrink-0" fill="none" stroke="currentColor" strokeWidth={1.5} viewBox="0 0 24 24">
    <path strokeLinecap="round" strokeLinejoin="round" d="m21 21-5.197-5.197m0 0A7.5 7.5 0 1 0 5.196 5.196a7.5 7.5 0 0 0 10.607 10.607Z" />
  </svg>,
  // sparkles
  <svg key="i5" className="h-4 w-4 shrink-0" fill="none" stroke="currentColor" strokeWidth={1.5} viewBox="0 0 24 24">
    <path strokeLinecap="round" strokeLinejoin="round" d="M9.813 15.904 9 18.75l-.813-2.846a4.5 4.5 0 0 0-3.09-3.09L2.25 12l2.846-.813a4.5 4.5 0 0 0 3.09-3.09L9 5.25l.813 2.846a4.5 4.5 0 0 0 3.09 3.09L15.75 12l-2.846.813a4.5 4.5 0 0 0-3.09 3.09ZM18.259 8.715 18 9.75l-.259-1.035a3.375 3.375 0 0 0-2.455-2.456L14.25 6l1.036-.259a3.375 3.375 0 0 0 2.455-2.456L18 2.25l.259 1.035a3.375 3.375 0 0 0 2.455 2.456L21.75 6l-1.036.259a3.375 3.375 0 0 0-2.455 2.456Z" />
  </svg>,
];

interface Props {
  sessionBooks: BookSummary[];
  loading: boolean;
  onSubmitQuestion: (question: string) => void;
  onRunDemo: () => void;
}

export default function WelcomeScreen({
  sessionBooks,
  loading,
  onSubmitQuestion,
  onRunDemo,
}: Props) {
  const [aiQuestions, setAiQuestions] = useState<GeneratedQuestion[]>([]);
  const [generating, setGenerating] = useState(true);
  const [generated, setGenerated] = useState(false);
  const [failed, setFailed] = useState(false);

  const bookIds = sessionBooks.map((b) => b.book_id);

  // Auto-fetch AI questions when session books change
  const doGenerate = () => {
    setGenerating(true);
    setGenerated(false);
    setFailed(false);

    fetchGeneratedQuestions(bookIds, 6).then((qs) => {
      setAiQuestions(qs);
      setGenerating(false);
      setGenerated(true);
      if (qs.length === 0) setFailed(true);

      // Save to Payload Questions collection (fire-and-forget)
      for (const q of qs) {
        const matchedBook = sessionBooks.find((b) => b.book_id === q.book_id);
        fetch('/api/questions', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            question: q.question,
            bookId: q.book_id,
            bookTitle: q.book_title,
            topicHint: q.topic_hint,
            source: 'ai',
            likes: 0,
            category: matchedBook?.category || 'textbook',
            subcategory: matchedBook?.subcategory || '',
          }),
        }).catch(() => { /* silently fail */ });
      }
    });
  };

  useEffect(() => {
    if (bookIds.length === 0) return;
    doGenerate();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [bookIds.join(",")]);

  const showAiQuestions = generated && aiQuestions.length > 0;

  return (
    <div className="mx-auto flex max-w-2xl flex-col items-center gap-6 py-8">
      {/* Big avatar + greeting */}
      <div className="flex flex-col items-center gap-3 text-center">
        <div className="flex h-14 w-14 items-center justify-center rounded-2xl bg-primary text-primary-foreground shadow-lg">
          <svg className="h-7 w-7" fill="none" stroke="currentColor" strokeWidth={1.5} viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" d="M8 10h.01M12 10h.01M16 10h.01M9 16H5a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2v8a2 2 0 0 1-2 2h-4l-3 3-3-3Z" />
          </svg>
        </div>
        <div>
          <h3 className="text-lg font-bold text-foreground">
            Hi! What would you like to know?
          </h3>
          <p className="mt-1 text-sm text-muted-foreground">
            Ask anything — answers are grounded in your selected{" "}
            {sessionBooks.length === 1 ? "book" : `${sessionBooks.length} books`}.
          </p>
        </div>
      </div>

      {/* ── AI-generated questions section ── */}
      {generating && (
        <GenerationProgress />
      )}

      {showAiQuestions && (
        <div className="w-full">
          <div className="mb-3 flex items-center gap-2 text-xs font-medium text-muted-foreground">
            <svg className="h-4 w-4 text-primary" fill="none" stroke="currentColor" strokeWidth={1.8} viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" d="M9.813 15.904 9 18.75l-.813-2.846a4.5 4.5 0 0 0-3.09-3.09L2.25 12l2.846-.813a4.5 4.5 0 0 0 3.09-3.09L9 5.25l.813 2.846a4.5 4.5 0 0 0 3.09 3.09L15.75 12l-2.846.813a4.5 4.5 0 0 0-3.09 3.09ZM18.259 8.715 18 9.75l-.259-1.035a3.375 3.375 0 0 0-2.455-2.456L14.25 6l1.036-.259a3.375 3.375 0 0 0 2.455-2.456L18 2.25l.259 1.035a3.375 3.375 0 0 0 2.455 2.456L21.75 6l-1.036.259a3.375 3.375 0 0 0-2.455 2.456Z" />
            </svg>
            <span>AI-suggested questions based on your books</span>
          </div>
          <div className="grid w-full gap-2 sm:grid-cols-2">
            {aiQuestions.map((q, index) => (
              <button
                key={`ai-${index}`}
                onClick={() => onSubmitQuestion(q.question)}
                disabled={loading}
                className="group rounded-xl border border-border bg-card px-3 py-3 text-left shadow-sm transition-all hover:border-primary/30 hover:shadow-md hover:-translate-y-0.5 disabled:opacity-50 disabled:hover:translate-y-0"
              >
                <div className="flex items-start gap-3">
                  <span className="mt-0.5 shrink-0 rounded-lg bg-muted p-1.5 text-muted-foreground transition-colors group-hover:bg-primary/10 group-hover:text-primary">
                    {CARD_ICONS[index % CARD_ICONS.length]}
                  </span>
                  <div className="min-w-0 flex-1">
                    {q.topic_hint && (
                      <span className={`mb-1 inline-block rounded-full px-2 py-0.5 text-[10px] font-semibold ${TOPIC_COLORS[index % TOPIC_COLORS.length]}`}>
                        {q.topic_hint}
                      </span>
                    )}
                    <p className="text-sm leading-snug text-muted-foreground group-hover:text-foreground">
                      {q.question}
                    </p>
                  </div>
                </div>
              </button>
            ))}
          </div>
        </div>
      )}

      {/* ── Generation failed — retry button ── */}
      {!generating && failed && (
        <div className="flex w-full flex-col items-center gap-3 rounded-xl border border-dashed border-border bg-muted/30 py-6">
          <svg className="h-6 w-6 text-muted-foreground" fill="none" stroke="currentColor" strokeWidth={1.5} viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v3.75m9-.75a9 9 0 1 1-18 0 9 9 0 0 1 18 0Zm-9 3.75h.008v.008H12v-.008Z" />
          </svg>
          <p className="text-sm text-muted-foreground">Could not generate questions from your books.</p>
          <button
            type="button"
            onClick={doGenerate}
            className="flex items-center gap-2 rounded-lg bg-primary px-4 py-2 text-sm font-medium text-primary-foreground transition hover:bg-primary/90"
          >
            <svg className="h-4 w-4" fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" d="M16.023 9.348h4.992v-.001M2.985 19.644v-4.992m0 0h4.992m-4.993 0 3.181 3.183a8.25 8.25 0 0 0 13.803-3.7M4.031 9.865a8.25 8.25 0 0 1 13.803-3.7l3.181 3.182m0-4.991v4.99" />
            </svg>
            Try Again
          </button>
        </div>
      )}

      {/* ── Regenerate button + Demo ── */}
      <div className="flex items-center gap-3">
        {generated && !failed && (
          <button
            type="button"
            onClick={doGenerate}
            disabled={generating || loading}
            className="flex items-center gap-2 rounded-xl border border-border bg-card px-4 py-2.5 text-sm font-medium text-muted-foreground transition hover:border-primary/30 hover:text-foreground disabled:opacity-50"
          >
            <svg className="h-4 w-4" fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" d="M16.023 9.348h4.992v-.001M2.985 19.644v-4.992m0 0h4.992m-4.993 0 3.181 3.183a8.25 8.25 0 0 0 13.803-3.7M4.031 9.865a8.25 8.25 0 0 1 13.803-3.7l3.181 3.182m0-4.991v4.99" />
            </svg>
            Regenerate
          </button>
        )}

        <button
          type="button"
          onClick={onRunDemo}
          disabled={loading}
          className="flex items-center gap-2 rounded-xl border-2 border-dashed border-primary/30 bg-primary/5 px-5 py-2.5 text-sm font-medium text-primary transition hover:border-primary/50 hover:bg-primary/10 disabled:opacity-50"
        >
          <svg className="h-4 w-4" fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" d="M5.25 5.653c0-.856.917-1.398 1.667-.986l11.54 6.347a1.125 1.125 0 0 1 0 1.972l-11.54 6.347a1.125 1.125 0 0 1-1.667-.986V5.653Z" />
          </svg>
          Quick Demo
        </button>
      </div>
    </div>
  );
}

// ═══════════════════════════════════════════════════════════════════════════════
// Step-by-step progress tracker with SVG icons + per-step timing
// ═══════════════════════════════════════════════════════════════════════════════


interface StepDef {
  label: string;
  icon: React.ElementType;
  autoAdvanceMs: number; // 0 = wait for parent unmount
}

const GENERATION_STEPS: StepDef[] = [
  { label: "Sampling chunks from books", icon: Database, autoAdvanceMs: 1500 },
  { label: "Building prompt context",    icon: Layers,   autoAdvanceMs: 2000 },
  { label: "Calling LLM model",          icon: Bot,      autoAdvanceMs: 0 },
  { label: "Parsing & formatting",       icon: Sparkles, autoAdvanceMs: 1000 },
];

function GenerationProgress() {
  const [currentStep, setCurrentStep] = useState(0);
  const [totalElapsed, setTotalElapsed] = useState(0);
  const [stepTimestamps, setStepTimestamps] = useState<number[]>(() => [Date.now()]);
  const startRef = useState(() => Date.now())[0];

  // Auto-advance timed steps
  useEffect(() => {
    const step = GENERATION_STEPS[currentStep];
    if (!step || step.autoAdvanceMs === 0) return;

    const timer = setTimeout(() => {
      if (currentStep < GENERATION_STEPS.length - 1) {
        setStepTimestamps((prev) => [...prev, Date.now()]);
        setCurrentStep((s) => s + 1);
      }
    }, step.autoAdvanceMs);
    return () => clearTimeout(timer);
  }, [currentStep]);

  // Total elapsed counter
  useEffect(() => {
    const iv = setInterval(() => setTotalElapsed(Math.floor((Date.now() - startRef) / 1000)), 200);
    return () => clearInterval(iv);
  }, [startRef]);

  // Per-step durations
  const stepDurations = GENERATION_STEPS.map((_, i) => {
    if (i >= stepTimestamps.length) return null; // not started
    const start = stepTimestamps[i];
    const end = i + 1 < stepTimestamps.length ? stepTimestamps[i + 1] : Date.now();
    return ((end - start) / 1000).toFixed(1);
  });

  const pct = Math.min(((currentStep + 0.5) / GENERATION_STEPS.length) * 100, 95);

  return (
    <div className="w-full max-w-md mx-auto">
      {/* Header */}
      <div className="mb-3 flex items-center justify-between">
        <div className="flex items-center gap-2 text-xs font-medium text-muted-foreground">
          <Loader2 className="h-3.5 w-3.5 animate-spin text-primary" />
          <span>Generating study questions…</span>
        </div>
        <span className="text-[11px] tabular-nums font-mono text-muted-foreground">
          {totalElapsed}s
        </span>
      </div>

      {/* Progress bar */}
      <div className="mb-4 h-1.5 w-full rounded-full bg-muted overflow-hidden">
        <div
          className="h-full rounded-full bg-primary transition-all duration-500 ease-out"
          style={{ width: `${pct}%` }}
        />
      </div>

      {/* Steps */}
      <div className="space-y-1">
        {GENERATION_STEPS.map((step, i) => {
          const isDone = i < currentStep;
          const isActive = i === currentStep;
          const Icon = step.icon;
          const duration = stepDurations[i];

          return (
            <div
              key={i}
              className={`flex items-center gap-3 rounded-lg px-3 py-2.5 transition-all duration-300 ${
                isActive
                  ? "bg-primary/5 border border-primary/20 shadow-sm"
                  : isDone
                  ? "bg-transparent"
                  : "bg-transparent opacity-40"
              }`}
            >
              {/* Step number circle or status */}
              <div className="relative w-6 h-6 flex items-center justify-center shrink-0">
                {isDone ? (
                  <div className="w-6 h-6 rounded-full bg-emerald-500/15 flex items-center justify-center">
                    <Check className="h-3.5 w-3.5 text-emerald-500" strokeWidth={3} />
                  </div>
                ) : isActive ? (
                  <div className="w-6 h-6 rounded-full border-2 border-primary/30 flex items-center justify-center">
                    <div className="h-3 w-3 rounded-full border-2 border-primary border-t-transparent animate-spin" />
                  </div>
                ) : (
                  <div className="w-6 h-6 rounded-full bg-muted flex items-center justify-center">
                    <span className="text-[10px] font-bold text-muted-foreground">{i + 1}</span>
                  </div>
                )}
              </div>

              {/* Icon */}
              <Icon className={`h-4 w-4 shrink-0 ${
                isDone ? "text-emerald-500" : isActive ? "text-primary" : "text-muted-foreground"
              }`} />

              {/* Label */}
              <span className={`text-xs flex-1 ${
                isActive ? "text-foreground font-medium" : isDone ? "text-muted-foreground" : "text-muted-foreground"
              }`}>
                {step.label}
              </span>

              {/* Duration */}
              {duration && (
                <span className={`text-[10px] tabular-nums font-mono px-1.5 py-0.5 rounded ${
                  isDone
                    ? "text-emerald-500 bg-emerald-500/10"
                    : isActive
                    ? "text-primary bg-primary/10"
                    : "text-muted-foreground"
                }`}>
                  {duration}s
                </span>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
