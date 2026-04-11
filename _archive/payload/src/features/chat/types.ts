import type { SourceInfo, QueryTrace } from "@/features/shared/types";

export interface Message {
  role: "user" | "assistant";
  content: string;
  sources?: SourceInfo[];
  trace?: QueryTrace;
}

export const NEAR_BOTTOM_THRESHOLD = 160;
