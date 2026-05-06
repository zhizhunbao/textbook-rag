import type { SourceInfo, QueryTrace } from "@/features/shared/types";
import type { LlmTelemetry } from "@/features/engine/query_engine/types";
import type { HighlightKeyword, NumericHighlight } from "@/features/shared/consultingApi";

export interface Message {
  role: "user" | "assistant";
  content: string;
  sources?: SourceInfo[];
  trace?: QueryTrace;
  /** LLM model name that generated this response (assistant messages only). */
  model?: string;
  /** Payload Queries record ID — populated after query is logged (assistant messages). */
  queryId?: number;
  /** ISO 8601 timestamp of when the message was created. */
  timestamp?: string;
  /** LLM token usage telemetry (assistant messages only). */
  telemetry?: LlmTelemetry;
  /** Backend-extracted, source-cross-referenced keywords for highlighting (assistant messages). */
  highlightKeywords?: HighlightKeyword[];
  /** Backend-extracted numeric highlights with source verification (assistant messages). */
  numericHighlights?: NumericHighlight[];
  /** Backend-extracted answer-derived keywords for citation panel highlighting. */
  answerHighlightKeywords?: HighlightKeyword[];
}

export const NEAR_BOTTOM_THRESHOLD = 160;
