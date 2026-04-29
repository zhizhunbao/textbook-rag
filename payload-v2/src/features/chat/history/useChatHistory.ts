/**
 * useChatHistory — Payload-only chat history hook.
 *
 * All sessions and messages are persisted to Payload CMS
 * (ChatSessions + ChatMessages collections). No localStorage.
 */

import { useState, useCallback, useEffect, useRef } from "react";
import type { SourceInfo, QueryTrace } from "@/features/shared/types";
import {
  fetchSessions as fetchServerSessions,
  createServerSession,
  deleteServerSession,
  deleteAllServerSessions,
  appendServerMessages,
  fetchMessages as fetchServerMessages,
  type PayloadChatSession,
  type ChatMode,
} from "./api";

/* ── Types ── */

export interface HistoryMessage {
  role: "user" | "assistant";
  content: string;
  sources?: SourceInfo[];
  trace?: QueryTrace;
  queryId?: number;
  timestamp?: string;
}

export interface ChatSession {
  id: string;
  /** Payload CMS document ID */
  serverId: number;
  /** Title derived from the first user message */
  title: string;
  /** Book IDs locked to this session */
  sessionBookIds: number[];
  /** Human-readable book titles (for display without AppState) */
  bookTitles: string[];
  /** Session mode, shared by normal RAG and consulting conversations. */
  mode: ChatMode;
  /** Consulting persona used by this session, when mode is consulting. */
  personaId?: number | null;
  personaSlug?: string | null;
  personaName?: string | null;
  messages: HistoryMessage[];
  createdAt: number;
  updatedAt: number;
}

const MAX_SESSIONS = 50;

/* ── Helpers ── */

function makeTitle(firstMessage: string): string {
  const trimmed = firstMessage.trim().replace(/\s+/g, " ");
  return trimmed.length > 60 ? trimmed.slice(0, 57) + "…" : trimmed;
}

/** Convert a Payload session doc to a local ChatSession shape. */
function serverToLocal(
  doc: PayloadChatSession,
  messages: HistoryMessage[] = [],
): ChatSession {
  return {
    id: String(doc.id),
    serverId: doc.id,
    title: doc.title,
    sessionBookIds: doc.bookIds ?? [],
    bookTitles: doc.bookTitles ?? [],
    mode: doc.mode ?? "rag",
    personaId: typeof doc.persona === "number" ? doc.persona : doc.persona?.id ?? null,
    personaSlug: doc.personaSlug ?? (typeof doc.persona === "object" ? doc.persona?.slug ?? null : null),
    personaName: typeof doc.persona === "object" ? doc.persona?.name ?? null : null,
    messages,
    createdAt: new Date(doc.createdAt).getTime(),
    updatedAt: new Date(doc.updatedAt).getTime(),
  };
}

/* ── Hook ── */

export function useChatHistory(userId?: number | null) {
  const [sessions, setSessions] = useState<ChatSession[]>([]);
  const isLoggedIn = typeof userId === "number" && userId > 0;
  const initialLoadDone = useRef(false);

  /** Load sessions from Payload on mount */
  useEffect(() => {
    if (!isLoggedIn || initialLoadDone.current) return;
    initialLoadDone.current = true;

    fetchServerSessions(MAX_SESSIONS)
      .then((serverDocs) => {
        const loaded = serverDocs
          .map((doc) => serverToLocal(doc))
          .sort((a, b) => b.updatedAt - a.updatedAt)
          .slice(0, MAX_SESSIONS);
        setSessions(loaded);
      })
      .catch((err) => {
        console.warn("[ChatHistory] Failed to fetch sessions:", err);
      });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isLoggedIn]);

  /**
   * Create a new session. Returns the Payload session ID as a string.
   * This is async because it waits for the Payload API to respond.
   */
  const createSession = useCallback(
    async (opts: {
      sessionBookIds: number[];
      bookTitles: string[];
      firstMessage: string;
      mode?: ChatMode;
      personaId?: number | null;
      personaSlug?: string | null;
      personaName?: string | null;
    }): Promise<string> => {
      if (!isLoggedIn || !userId) {
        throw new Error("Cannot create session: user not logged in");
      }

      const title = makeTitle(opts.firstMessage);

      const doc = await createServerSession({
        userId,
        title,
        mode: opts.mode ?? "rag",
        personaId: opts.personaId ?? null,
        personaSlug: opts.personaSlug ?? null,
        bookIds: opts.sessionBookIds,
        bookTitles: opts.bookTitles,
      });

      const session = serverToLocal(doc);
      session.sessionBookIds = opts.sessionBookIds;
      session.bookTitles = opts.bookTitles;
      session.mode = opts.mode ?? "rag";
      session.personaId = opts.personaId ?? null;
      session.personaSlug = opts.personaSlug ?? null;
      session.personaName = opts.personaName ?? null;

      setSessions((prev) => [session, ...prev].slice(0, MAX_SESSIONS));

      return session.id; // String(doc.id)
    },
    [isLoggedIn, userId],
  );

  /** Append messages to an existing session (local state + Payload). */
  const appendMessages = useCallback(
    (sessionId: string, newMessages: HistoryMessage[]) => {
      // Update local state for immediate UI
      setSessions((prev) =>
        prev.map((s) => {
          if (s.id === sessionId) {
            return {
              ...s,
              messages: [...s.messages, ...newMessages],
              updatedAt: Date.now(),
            };
          }
          return s;
        }),
      );

      // Persist to Payload (sessionId IS the Payload ID as string)
      if (!isLoggedIn) return;
      const numericId = Number(sessionId);
      if (!numericId) return;

      appendServerMessages(numericId, newMessages).catch((err) => {
        console.warn("[ChatHistory] appendServerMessages failed:", err);
      });
    },
    [isLoggedIn],
  );

  /** Replace messages for a session (for optimistic updates). */
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

  /** Delete a session. */
  const deleteSession = useCallback(
    (sessionId: string) => {
      setSessions((prev) => prev.filter((s) => s.id !== sessionId));

      if (!isLoggedIn) return;
      const numericId = Number(sessionId);
      if (!numericId) return;

      deleteServerSession(numericId).catch((err) => {
        console.warn("[ChatHistory] deleteServerSession failed:", err);
      });
    },
    [isLoggedIn],
  );

  /** Clear all history — deletes from both local state and Payload. */
  const clearHistory = useCallback(() => {
    setSessions([]);

    if (!isLoggedIn) return;
    deleteAllServerSessions().catch((err) => {
      console.warn("[ChatHistory] deleteAllServerSessions failed:", err);
    });
  }, [isLoggedIn]);

  /** Get one session by id. */
  const getSession = useCallback(
    (sessionId: string) => sessions.find((s) => s.id === sessionId) ?? null,
    [sessions],
  );

  /**
   * Lazy-load messages for a session from Payload.
   * If messages are already cached in state, returns immediately.
   */
  const loadSessionMessages = useCallback(
    async (sessionId: string): Promise<HistoryMessage[]> => {
      const session = sessions.find((s) => s.id === sessionId);
      if (!session) return [];

      // Already have messages cached
      if (session.messages.length > 0) return session.messages;

      // Load from Payload
      if (!isLoggedIn) return [];
      try {
        const docs = await fetchServerMessages(session.serverId);
        const msgs: HistoryMessage[] = docs.map((d) => ({
          role: d.role,
          content: d.content,
          sources: d.sources ?? undefined,
          trace: d.trace ?? undefined,
          queryId: d.queryId ?? undefined,
          timestamp: d.createdAt ?? undefined,
        }));

        // Cache in state
        setSessions((prev) =>
          prev.map((s) =>
            s.id === sessionId ? { ...s, messages: msgs } : s,
          ),
        );

        return msgs;
      } catch {
        return [];
      }
    },
    [sessions, isLoggedIn],
  );

  /**
   * Update the queryId on the last assistant message in a session.
   * Called when Queries POST resolves with the doc ID (async after message creation).
   */
  const updateLastAssistantQueryId = useCallback(
    (sessionId: string, queryId: number) => {
      // Update local state
      setSessions((prev) =>
        prev.map((s) => {
          if (s.id !== sessionId) return s;
          const msgs = [...s.messages];
          for (let i = msgs.length - 1; i >= 0; i--) {
            if (msgs[i].role === 'assistant') {
              msgs[i] = { ...msgs[i], queryId };
              break;
            }
          }
          return { ...s, messages: msgs };
        }),
      );

      // Persist to Payload — find the last assistant ChatMessage for this session
      if (!isLoggedIn) return;
      const numericId = Number(sessionId);
      if (!numericId) return;

      // Fetch the latest assistant message and patch its queryId
      fetch(`/api/chat-messages?where[session][equals]=${numericId}&where[role][equals]=assistant&sort=-createdAt&limit=1&depth=0`, {
        credentials: 'include',
      })
        .then((r) => r.json())
        .then((data: { docs: { id: number }[] }) => {
          if (data.docs?.[0]?.id) {
            fetch(`/api/chat-messages/${data.docs[0].id}`, {
              method: 'PATCH',
              headers: { 'Content-Type': 'application/json' },
              credentials: 'include',
              body: JSON.stringify({ queryId }),
            }).catch(() => { /* ignore */ });
          }
        })
        .catch(() => { /* ignore */ });
    },
    [isLoggedIn],
  );

  return {
    sessions,
    createSession,
    appendMessages,
    replaceMessages,
    deleteSession,
    clearHistory,
    getSession,
    loadSessionMessages,
    updateLastAssistantQueryId,
  };
}
