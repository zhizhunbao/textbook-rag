import type { ReactNode } from "react";
import Markdown from "react-markdown";
import rehypeRaw from "rehype-raw";
import type { SourceInfo } from "@/features/shared/types";
import { useAppDispatch } from "@/features/shared/AppContext";

interface Props {
  role: "user" | "assistant";
  content: string;
  sources?: SourceInfo[];
  onRetry?: (content: string) => void;
}

function injectCitationLinks(text: string, maxCitation: number): string {
  return text.replace(
    /\[(\d+)\]/g,
    (_, n) => {
      const index = Number.parseInt(n, 10);
      if (index >= 1 && index <= maxCitation) {
        return `<cite data-ref="${n}">[${n}]</cite>`;
      }

      return `<span data-invalid-cite="${n}" title="Citation ${n} is not available in this response"><sup>[${n}]</sup></span>`;
    },
  );
}

export default function MessageBubble({ role, content, sources, onRetry }: Props) {
  const isUser = role === "user";
  const dispatch = useAppDispatch();

  // Build a map from citation_index → source for correct lookup
  const citationMap = new Map<number, SourceInfo>();
  let maxCitation = 0;
  if (sources) {
    for (const s of sources) {
      const ci = (s as any).citation_index as number | undefined;
      if (ci != null) {
        citationMap.set(ci, s);
        maxCitation = Math.max(maxCitation, ci);
      }
    }
    // Fallback: if no citation_index, use legacy array-based mapping
    if (citationMap.size === 0) {
      maxCitation = sources.length;
      for (let i = 0; i < sources.length; i++) {
        citationMap.set(i + 1, sources[i]);
      }
    }
  }

  const handleCitationClick = (citationIndex: number) => {
    const source = citationMap.get(citationIndex);
    if (!source) return;
    dispatch({
      type: "SELECT_SOURCE",
      source: {
        ...source,
        citation_label: `[${citationIndex}]`,
      },
    });
  };

  return (
    <div className={`flex items-start gap-3 ${isUser ? "justify-end" : "justify-start"}`}>
      {!isUser && (
        <div className="mt-1 flex h-8 w-8 shrink-0 items-center justify-center rounded-2xl bg-primary text-primary-foreground shadow-sm">
          <svg className="h-4 w-4" fill="none" stroke="currentColor" strokeWidth={1.8} viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" d="M8 10h.01M12 10h.01M16 10h.01M9 16H5a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2v8a2 2 0 0 1-2 2h-4l-3 3-3-3Z" />
          </svg>
        </div>
      )}

      <div className={`max-w-[86%] ${isUser ? "order-first" : ""}`}>
        <div className={`mb-1 text-[11px] font-medium uppercase tracking-[0.16em] ${isUser ? "text-right text-blue-500" : "text-muted-foreground"}`}>
          {isUser ? "You" : "Textbook RAG"}
        </div>
        <div
          className={`rounded-[22px] px-4 py-3 text-sm shadow-sm ${
            isUser
              ? "rounded-tr-md bg-blue-600 text-white"
              : "rounded-tl-md border border-border bg-card/92 text-card-foreground"
          }`}
        >
          {isUser ? (
            <div className="whitespace-pre-wrap leading-6">{content}</div>
          ) : (
            <Markdown
              rehypePlugins={[rehypeRaw]}
              components={{
                h2({ children }) {
                  return <h2 className="mt-4 mb-2 text-base font-bold text-foreground">{children}</h2>;
                },
                h3({ children }) {
                  return <h3 className="mt-3 mb-1.5 text-[0.94rem] font-semibold text-foreground">{children}</h3>;
                },
                p({ children }) {
                  return <p className="my-2 leading-7 text-foreground">{children}</p>;
                },
                ul({ children }) {
                  return <ul className="my-2 list-disc space-y-1 pl-5 text-foreground">{children}</ul>;
                },
                ol({ children }) {
                  return <ol className="my-2 list-decimal space-y-1 pl-5 text-foreground">{children}</ol>;
                },
                li({ children }) {
                  return <li className="leading-7">{children}</li>;
                },
                strong({ children }) {
                  return <strong className="font-semibold text-foreground">{children}</strong>;
                },
                code({ children }) {
                  return <code className="rounded bg-muted px-1.5 py-0.5 text-[0.92em] text-foreground">{children}</code>;
                },
                span({
                  children,
                  ...props
                }: {
                  children?: ReactNode;
                  "data-invalid-cite"?: string;
                  title?: string;
                }) {
                  if (props["data-invalid-cite"]) {
                    return (
                      <span
                        className="inline-flex items-center text-[0.72em] font-semibold text-muted-foreground align-super"
                        title={props.title}
                      >
                        {children}
                      </span>
                    );
                  }

                  return <span>{children}</span>;
                },
                a({ href, children }: { href?: string; children?: ReactNode }) {
                  return (
                    <a href={href} className="text-blue-600 underline decoration-blue-200 underline-offset-2 hover:text-blue-800">
                      {children}
                    </a>
                  );
                },
                cite({
                  children,
                  ...props
                }: {
                  children?: ReactNode;
                  "data-ref"?: string;
                }) {
                  const ref = props["data-ref"];
                  if (ref) {
                    const citIndex = Number.parseInt(ref, 10);
                    return (
                      <button
                        type="button"
                        className="inline-flex cursor-pointer items-center border-0 bg-transparent p-0 text-[0.72em] font-semibold text-blue-600 align-super hover:text-blue-800"
                        onClick={() => handleCitationClick(citIndex)}
                      >
                        {children}
                      </button>
                    );
                  }
                  return <cite>{children}</cite>;
                },
              }}
            >
              {injectCitationLinks(content, maxCitation)}
            </Markdown>
          )}
        </div>

        {/* Retry button for user messages */}
        {isUser && onRetry && (
          <div className="mt-1 flex justify-end">
            <button
              type="button"
              onClick={() => onRetry(content)}
              className="inline-flex items-center gap-1 rounded-lg px-2 py-1 text-[11px] text-muted-foreground transition-colors hover:bg-accent hover:text-foreground"
              title="Re-ask this question"
            >
              <svg className="h-3 w-3" fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" d="M16.023 9.348h4.992v-.001M2.985 19.644v-4.992m0 0h4.992m-4.993 0 3.181 3.183a8.25 8.25 0 0 0 13.803-3.7M4.031 9.865a8.25 8.25 0 0 1 13.803-3.7l3.181 3.182" />
              </svg>
              Retry
            </button>
          </div>
        )}
      </div>

      {isUser && (
        <div className="mt-1 flex h-8 w-8 shrink-0 items-center justify-center rounded-2xl bg-primary/10 text-primary shadow-sm ring-1 ring-primary/20">
          <svg className="h-4 w-4" fill="none" stroke="currentColor" strokeWidth={1.8} viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" d="M15.75 6.75a3.75 3.75 0 1 1-7.5 0 3.75 3.75 0 0 1 7.5 0ZM4.5 20.118a7.5 7.5 0 0 1 15 0A17.933 17.933 0 0 1 12 21.75a17.933 17.933 0 0 1-7.5-1.632Z" />
          </svg>
        </div>
      )}
    </div>
  );
}
