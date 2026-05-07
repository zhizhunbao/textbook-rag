"use client";

import { useState } from "react";
import Markdown from "react-markdown";

interface TranslateButtonProps {
  content: string;
  className?: string;
}

const ENGINE = process.env.NEXT_PUBLIC_ENGINE_URL || 'http://localhost:8001';

/**
 * Bidirectional translate toggle — tiny caret icon at bottom-right.
 * English content → Chinese, Chinese content → English.
 * Click once to translate, click again to hide.
 */
export default function TranslateButton({ content, className = "" }: TranslateButtonProps) {
  const [isTranslating, setIsTranslating] = useState(false);
  const [translatedText, setTranslatedText] = useState<string | null>(null);

  const handleTranslate = async () => {
    if (translatedText) {
      setTranslatedText(null);
      return;
    }

    if (!content?.trim()) return;

    setIsTranslating(true);
    try {
      const res = await fetch(`${ENGINE}/engine/translate`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        credentials: "include",
        body: JSON.stringify({ text: content }),
      });
      if (res.ok) {
        const data = await res.json();
        setTranslatedText(data.translation);
      } else {
        setTranslatedText("Translation failed.");
      }
    } catch (err) {
      console.error(err);
      setTranslatedText("Translation error.");
    } finally {
      setIsTranslating(false);
    }
  }

  return (
    <div className={`${className}`}>
      {/* Caret icon — bottom-right, toggles translation */}
      <div className="flex justify-end">
        <button
          type="button"
          onClick={handleTranslate}
          disabled={isTranslating}
          className={`
            inline-flex items-center justify-center
            w-4 h-4 rounded-sm
            transition-all duration-150
            disabled:opacity-30 disabled:cursor-wait
            ${translatedText
              ? "text-blue-500/60 hover:text-blue-500"
              : "text-muted-foreground/25 hover:text-muted-foreground/50"
            }
          `}
          title={translatedText ? "Hide translation" : "Translate"}
        >
          {isTranslating ? (
            <svg className="animate-spin h-2.5 w-2.5" viewBox="0 0 16 16" fill="none">
              <circle cx="8" cy="8" r="6" stroke="currentColor" strokeWidth="2" strokeOpacity="0.25" />
              <path d="M14 8a6 6 0 0 0-6-6" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
            </svg>
          ) : (
            <svg className="h-2.5 w-2.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
              <path d="m5 8 6 6" />
              <path d="m4 14 6-6 2-3" />
              <path d="M2 5h12" />
              <path d="M7 2h1" />
              <path d="m22 22-5-10-5 10" />
              <path d="M14 18h6" />
            </svg>
          )}
        </button>
      </div>

      {/* Translation card */}
      {translatedText && (
        <div className="mt-1 rounded-lg bg-blue-500/[0.04] border border-blue-500/10 px-3 py-2 text-[13px] leading-relaxed text-foreground/85 animate-in fade-in slide-in-from-top-1 duration-150">
          <Markdown
            components={{
              p({ children }) {
                return <p className="my-0.5 leading-relaxed">{children}</p>;
              },
            }}
          >
            {translatedText}
          </Markdown>
        </div>
      )}
    </div>
  );
}
