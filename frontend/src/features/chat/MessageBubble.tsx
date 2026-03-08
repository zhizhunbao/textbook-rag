import Markdown from "react-markdown";
import rehypeRaw from "rehype-raw";
import type { SourceInfo } from "../../types/api";
import { useAppDispatch } from "../../context/AppContext";
import type { ReactNode } from "react";

interface Props {
  role: "user" | "assistant";
  content: string;
  sources?: SourceInfo[];
}

/**
 * Pre-process the answer text: turn `[1]`, `[2]` etc. into clickable
 * superscript citation links that react-markdown renders via rehype-raw.
 */
function injectCitationLinks(text: string): string {
  return text.replace(/\[(\d+)\]/g, (_, n) =>
    `<a href="#cite-${n}"><sup>[${n}]</sup></a>`,
  );
}

export default function MessageBubble({ role, content, sources }: Props) {
  const isUser = role === "user";
  const dispatch = useAppDispatch();

  const handleCitationClick = (index: number) => {
    if (!sources || index < 0 || index >= sources.length) return;
    dispatch({ type: "SELECT_SOURCE", source: sources[index] });
  };

  return (
    <div className={`flex ${isUser ? "justify-end" : "justify-start"}`}>
      <div
        className={`max-w-[85%] rounded-lg px-4 py-2 text-sm ${
          isUser
            ? "bg-blue-600 text-white"
            : "bg-gray-50 text-gray-800 prose prose-sm prose-gray max-w-none prose-p:my-2 prose-headings:my-3 prose-headings:text-gray-900 prose-ul:my-2 prose-li:my-0.5 prose-strong:text-gray-900"
        }`}
      >
        {isUser ? (
          content
        ) : (
          <Markdown
            rehypePlugins={[rehypeRaw]}
            components={{
              a({ href, children }: { href?: string; children?: ReactNode }) {
                const m = href?.match(/^#cite-(\d+)$/);
                if (m) {
                  const idx = parseInt(m[1], 10) - 1;
                  return (
                    <a
                      href="#"
                      className="inline-flex items-center text-blue-600 hover:text-blue-800 cursor-pointer no-underline font-semibold text-[0.7em] align-super"
                      onClick={(e) => {
                        e.preventDefault();
                        handleCitationClick(idx);
                      }}
                    >
                      {children}
                    </a>
                  );
                }
                return <a href={href}>{children}</a>;
              },
            }}
          >
            {injectCitationLinks(content)}
          </Markdown>
        )}
      </div>
    </div>
  );
}
