import { useEffect, useState } from "react";
import type { SourceInfo } from "@/features/shared/types";
import { useAppDispatch } from "@/features/shared/AppContext";

interface Props {
  source: SourceInfo;
  index: number;
  isActive: boolean;
}

export default function SourceCard({ source, index, isActive }: Props) {
  const dispatch = useAppDispatch();
  const [expanded, setExpanded] = useState(false);

  useEffect(() => {
    if (isActive) {
      setExpanded(true);
    }
  }, [isActive]);

  return (
    <div
      className={`rounded-xl border text-xs transition ${
        isActive
          ? "border-blue-400 bg-blue-50 shadow-sm"
          : "border-slate-200 bg-white hover:border-blue-300 hover:shadow-sm"
      }`}
    >
      <div className="flex items-start gap-2 px-3 py-2.5">
        <span className="mt-0.5 inline-flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-blue-100 text-[10px] font-bold text-blue-700">
          {index + 1}
        </span>

        <button
          onClick={() => dispatch({ type: "SELECT_SOURCE", source })}
          className="min-w-0 flex-1 text-left"
        >
          <div className="truncate font-semibold text-slate-800">
            {source.book_title}
          </div>
          <div className="mt-0.5 flex items-center gap-2 text-slate-500">
            {source.chapter_title && (
              <span className="truncate">{source.chapter_title}</span>
            )}
            <span className="shrink-0 text-slate-400">p.{source.page_number}</span>
          </div>
        </button>

        <button
          onClick={() => setExpanded((prev) => !prev)}
          className="mt-0.5 shrink-0 text-slate-400 hover:text-slate-600"
          title={expanded ? "Collapse" : "Expand snippet"}
        >
          {expanded ? "▲" : "▼"}
        </button>
      </div>

      {expanded && (
        <div
          className={`border-t px-3 py-2 leading-relaxed ${
            isActive
              ? "border-blue-200 bg-blue-50/70 text-blue-900"
              : "border-slate-100 text-slate-600"
          }`}
        >
          {source.snippet}
        </div>
      )}
    </div>
  );
}
