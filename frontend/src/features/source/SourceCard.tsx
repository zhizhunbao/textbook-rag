import { useState } from "react";
import type { SourceInfo } from "../../types/api";
import { useAppDispatch } from "../../context/AppContext";

interface Props {
  source: SourceInfo;
  index: number;
  isActive: boolean;
}

export default function SourceCard({ source, index, isActive }: Props) {
  const dispatch = useAppDispatch();
  const [expanded, setExpanded] = useState(false);

  return (
    <div
      className={`rounded-lg border text-xs transition ${
        isActive
          ? "border-blue-400 bg-blue-50 shadow-sm"
          : "border-gray-200 bg-white hover:border-blue-300 hover:shadow-sm"
      }`}
    >
      <button
        onClick={() => dispatch({ type: "SELECT_SOURCE", source })}
        className="flex w-full items-start gap-2 px-3 py-2 text-left"
      >
        <span className="shrink-0 mt-0.5 inline-flex h-5 w-5 items-center justify-center rounded-full bg-blue-100 text-blue-700 text-[10px] font-bold">
          {index + 1}
        </span>
        <div className="min-w-0 flex-1">
          <div className="font-semibold text-gray-800 truncate">
            {source.book_title}
          </div>
          <div className="flex items-center gap-2 text-gray-500 mt-0.5">
            {source.chapter_title && (
              <span className="truncate">{source.chapter_title}</span>
            )}
            <span className="shrink-0 text-gray-400">p.{source.page_number}</span>
          </div>
        </div>
        <button
          onClick={(e) => { e.stopPropagation(); setExpanded(!expanded); }}
          className="shrink-0 mt-0.5 text-gray-400 hover:text-gray-600"
          title={expanded ? "Collapse" : "Expand snippet"}
        >
          {expanded ? "▲" : "▼"}
        </button>
      </button>
      {expanded && (
        <div className="border-t border-gray-100 px-3 py-2 text-gray-600 leading-relaxed">
          {source.snippet}
        </div>
      )}
    </div>
  );
}
