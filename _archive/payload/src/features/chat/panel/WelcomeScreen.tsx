/**
 * panel/WelcomeScreen.tsx
 * 聊天空状态 — 从 questions 模块拉取高质量问题 + fallback 到实时生成
 *
 * Flow (v2 — questions 模块自包含):
 *   1. 进入 session → 先从 Payload 拉已评分的高质量问题
 *   2. 如果已有高质量问题 → 直接展示（瞬间加载，无需等 LLM）
 *   3. 如果没有 → fallback 到 useQuestionGeneration 实时生成
 *   4. 点击 → 自动触发 submitQuestion → 走正常 RAG 流程
 */
import { useState, useEffect } from "react";
import type { BookSummary } from "@/features/shared/types";
import {
  fetchHighQualityQuestions,
  QuestionCards,
  GenerationProgress,
  useQuestionGeneration,
} from "@/features/questions";
import type { Question } from "@/features/questions";

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
  const bookIds = sessionBooks.map((b) => b.book_id);

  /* ── 1. Try fetching pre-scored high-quality questions from Payload ── */
  const [hqQuestions, setHqQuestions] = useState<Question[]>([]);
  const [hqLoading, setHqLoading] = useState(true);
  const [hqTried, setHqTried] = useState(false);

  useEffect(() => {
    if (bookIds.length === 0) return;
    setHqLoading(true);
    fetchHighQualityQuestions(bookIds, 6, 3)
      .then((qs) => {
        setHqQuestions(qs);
        setHqLoading(false);
        setHqTried(true);
      })
      .catch(() => {
        setHqLoading(false);
        setHqTried(true);
      });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [bookIds.join(",")]);

  /* ── 2. Fallback: generate on the fly if no high-quality questions exist ── */
  const needsFallback = hqTried && hqQuestions.length === 0;
  const gen = useQuestionGeneration(
    needsFallback ? sessionBooks : [], // only trigger if no HQ questions
    3,
  );

  /* ── Decide what to show ── */
  const hasHQ = hqQuestions.length > 0;
  const showGenProgress = !hasHQ && needsFallback && gen.generating;
  const showGenCards = !hasHQ && needsFallback && gen.generated && gen.questions.length > 0;

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

      {/* ── Loading state (fast Payload fetch) ── */}
      {hqLoading && (
        <div className="flex items-center gap-2 text-xs text-muted-foreground">
          <div className="h-3 w-3 rounded-full border-2 border-primary border-t-transparent animate-spin" />
          <span>Loading suggested questions…</span>
        </div>
      )}

      {/* ── High-quality questions from Payload (instant) ── */}
      {hasHQ && (
        <QuestionCards
          questions={hqQuestions}
          onSelect={onSubmitQuestion}
          disabled={loading}
          header="Top questions from your books"
        />
      )}

      {/* ── Fallback: generation progress ── */}
      {showGenProgress && <GenerationProgress />}

      {/* ── Fallback: freshly generated question cards ── */}
      {showGenCards && (
        <QuestionCards
          questions={gen.questions}
          onSelect={onSubmitQuestion}
          disabled={loading}
        />
      )}

      {/* ── Regenerate button + Demo ── */}
      <div className="flex items-center gap-3">
        {(hasHQ || showGenCards) && (
          <button
            type="button"
            onClick={gen.regenerate}
            disabled={gen.generating || loading}
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
