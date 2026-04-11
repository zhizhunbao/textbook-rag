import { useState, useCallback, useEffect } from "react";
import type { SourceInfo, QueryTrace } from "@/features/shared/types";

/* ── Types ── */

export interface HistoryMessage {
  role: "user" | "assistant";
  content: string;
  sources?: SourceInfo[];
  trace?: QueryTrace;
}

export interface ChatSession {
  id: string;
  /** Title derived from the first user message */
  title: string;
  /** Book IDs locked to this session */
  sessionBookIds: number[];
  /** Human-readable book titles (for display without AppState) */
  bookTitles: string[];
  messages: HistoryMessage[];
  createdAt: number;
  updatedAt: number;
}

const STORAGE_KEY = "textbook-rag-chat-history";
const MAX_SESSIONS = 50;

/* ── Helpers ── */

function loadSessions(): ChatSession[] {
  if (typeof window === "undefined") return [];
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    return raw ? (JSON.parse(raw) as ChatSession[]) : [];
  } catch {
    return [];
  }
}

function saveSessions(sessions: ChatSession[]) {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(sessions));
  } catch {
    /* quota exceeded */
  }
}

function makeTitle(firstMessage: string): string {
  const trimmed = firstMessage.trim().replace(/\s+/g, " ");
  return trimmed.length > 60 ? trimmed.slice(0, 57) + "…" : trimmed;
}

/* ── Hook ── */

export function useChatHistory() {
  const [sessions, setSessions] = useState<ChatSession[]>([]);
  const [isMounted, setIsMounted] = useState(false);

  /** Load sessions only on client to avoid hydration mismatch */
  useEffect(() => {
    setSessions(loadSessions());
    setIsMounted(true);
  }, []);

  /** Persist whenever sessions change */
  useEffect(() => {
    if (isMounted) saveSessions(sessions);
  }, [sessions, isMounted]);

  /** Create a brand-new session (called when first user message is sent) */
  const createSession = useCallback(
    (opts: {
      sessionBookIds: number[];
      bookTitles: string[];
      firstMessage: string;
    }): string => {
      const id = `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;
      const now = Date.now();
      const session: ChatSession = {
        id,
        title: makeTitle(opts.firstMessage),
        sessionBookIds: opts.sessionBookIds,
        bookTitles: opts.bookTitles,
        messages: [],
        createdAt: now,
        updatedAt: now,
      };
      setSessions((prev) => [session, ...prev].slice(0, MAX_SESSIONS));
      return id;
    },
    [],
  );

  /** Append messages to an existing session */
  const appendMessages = useCallback(
    (sessionId: string, newMessages: HistoryMessage[]) => {
      setSessions((prev) =>
        prev.map((s) =>
          s.id === sessionId
            ? {
                ...s,
                messages: [...s.messages, ...newMessages],
                updatedAt: Date.now(),
              }
            : s,
        ),
      );
    },
    [],
  );

  /** Replace messages for a session (for optimistic updates) */
  const replaceMessages = useCallback(
    (sessionId: string, messages: HistoryMessage[]) => {
      setSessions((prev) =>
        prev.map((s) =>
          s.id === sessionId
            ? { ...s, messages, updatedAt: Date.now() }
            : s,
        ),
      );
    },
    [],
  );

  /** Delete a session */
  const deleteSession = useCallback((sessionId: string) => {
    setSessions((prev) => prev.filter((s) => s.id !== sessionId));
  }, []);

  /** Clear all history */
  const clearHistory = useCallback(() => {
    setSessions([]);
  }, []);

  /** Get one session by id */
  const getSession = useCallback(
    (sessionId: string) => sessions.find((s) => s.id === sessionId) ?? null,
    [sessions],
  );

  return {
    sessions,
    createSession,
    appendMessages,
    replaceMessages,
    deleteSession,
    clearHistory,
    getSession,
  };
}
