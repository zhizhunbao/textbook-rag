import { useState } from "react";
import type { ChatSession } from "./useChatHistory";

interface Props {
  sessions: ChatSession[];
  activeSessionId: string | null;
  onSelect: (session: ChatSession) => void;
  onDelete: (sessionId: string) => void;
  onClear: () => void;
  onNewChat: () => void;
}

/** Group sessions by day label */
function groupByDay(sessions: ChatSession[]) {
  const now = new Date();
  const todayStr = now.toDateString();
  const yesterday = new Date(now);
  yesterday.setDate(yesterday.getDate() - 1);
  const yesterdayStr = yesterday.toDateString();

  const groups: { label: string; items: ChatSession[] }[] = [];
  const map = new Map<string, ChatSession[]>();

  for (const s of sessions) {
    const d = new Date(s.updatedAt);
    let label: string;
    if (d.toDateString() === todayStr) label = "Today";
    else if (d.toDateString() === yesterdayStr) label = "Yesterday";
    else {
      const diffDays = Math.floor((now.getTime() - d.getTime()) / 86400000);
      if (diffDays < 7) label = "This Week";
      else if (diffDays < 30) label = "This Month";
      else label = d.toLocaleDateString(undefined, { year: "numeric", month: "short" });
    }
    if (!map.has(label)) map.set(label, []);
    map.get(label)!.push(s);
  }

  for (const [label, items] of map) {
    groups.push({ label, items });
  }
  return groups;
}

export default function ChatHistoryPanel({
  sessions,
  activeSessionId,
  onSelect,
  onDelete,
  onClear,
  onNewChat,
}: Props) {
  const [hoveredId, setHoveredId] = useState<string | null>(null);
  const [confirmClear, setConfirmClear] = useState(false);

  const groups = groupByDay(sessions);

  return (
    <div className="flex h-full flex-col bg-muted/30 border-r border-border">
      {/* Header */}
      <div className="shrink-0 flex items-center gap-2 px-3 py-3 border-b border-border">
        <svg
          className="h-4 w-4 shrink-0 text-muted-foreground"
          fill="none"
          stroke="currentColor"
          strokeWidth={1.8}
          viewBox="0 0 24 24"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            d="M12 6.042A8.967 8.967 0 0 0 6 3.75c-1.052 0-2.062.18-3 .512v14.25A8.987 8.987 0 0 1 6 18c2.305 0 4.408.867 6 2.292m0-14.25a8.966 8.966 0 0 1 6-2.292c1.052 0 2.062.18 3 .512v14.25A8.987 8.987 0 0 0 18 18a8.967 8.967 0 0 0-6 2.292m0-14.25v14.25"
          />
        </svg>
        <span className="flex-1 text-xs font-semibold text-foreground uppercase tracking-wide">
          Chat History
        </span>
        {sessions.length > 0 && (
          <button
            type="button"
            onClick={() => setConfirmClear(true)}
            className="text-[10px] text-muted-foreground hover:text-destructive transition-colors"
            title="Clear all history"
          >
            Clear
          </button>
        )}
      </div>

      {/* New Chat button */}
      <div className="shrink-0 px-3 py-2 border-b border-border">
        <button
          type="button"
          onClick={onNewChat}
          className="flex w-full items-center gap-2 rounded-lg border border-dashed border-border px-3 py-2 text-xs font-medium text-muted-foreground hover:border-primary hover:bg-accent hover:text-foreground transition-all"
        >
          <svg
            className="h-3.5 w-3.5"
            fill="none"
            stroke="currentColor"
            strokeWidth={2}
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              d="M12 4.5v15m7.5-7.5h-15"
            />
          </svg>
          New Chat
        </button>
      </div>

      {/* Session list */}
      <div className="flex-1 overflow-y-auto">
        {sessions.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-12 px-4 text-center">
            <svg
              className="h-8 w-8 text-muted-foreground/50 mb-3"
              fill="none"
              stroke="currentColor"
              strokeWidth={1.5}
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                d="M8.625 12a.375.375 0 1 1-.75 0 .375.375 0 0 1 .75 0Zm0 0H8.25m4.125 0a.375.375 0 1 1-.75 0 .375.375 0 0 1 .75 0Zm0 0H12m4.125 0a.375.375 0 1 1-.75 0 .375.375 0 0 1 .75 0Zm0 0h-.375M21 12c0 4.556-4.03 8.25-9 8.25a9.764 9.764 0 0 1-2.555-.337A5.972 5.972 0 0 1 5.41 20.97a5.969 5.969 0 0 1-.474-.065 4.48 4.48 0 0 0 .978-2.025c.09-.457-.133-.901-.467-1.226C3.93 16.178 3 14.189 3 12c0-4.556 4.03-8.25 9-8.25s9 3.694 9 8.25Z"
              />
            </svg>
            <p className="text-xs text-muted-foreground">No conversations yet</p>
          </div>
        ) : (
          <div className="py-1">
            {groups.map(({ label, items }) => (
              <div key={label}>
                <div className="sticky top-0 z-10 bg-background/90 backdrop-blur-sm px-3 py-1.5">
                  <span className="text-[10px] font-semibold uppercase tracking-wider text-muted-foreground">
                    {label}
                  </span>
                </div>
                {items.map((session) => {
                  const isActive = session.id === activeSessionId;
                  const isHovered = hoveredId === session.id;
                  return (
                    <div
                      key={session.id}
                      className="relative group px-2"
                      onMouseEnter={() => setHoveredId(session.id)}
                      onMouseLeave={() => setHoveredId(null)}
                    >
                      <button
                        type="button"
                        onClick={() => onSelect(session)}
                        className={`w-full rounded-lg px-2.5 py-2.5 text-left transition-colors ${
                          isActive
                            ? "bg-primary text-primary-foreground"
                            : "text-foreground hover:bg-accent"
                        }`}
                      >
                        <div className="flex items-start gap-2">
                          <svg
                            className={`mt-0.5 h-3.5 w-3.5 shrink-0 ${isActive ? "text-primary-foreground/80" : "text-muted-foreground"}`}
                            fill="none"
                            stroke="currentColor"
                            strokeWidth={1.8}
                            viewBox="0 0 24 24"
                          >
                            <path
                              strokeLinecap="round"
                              strokeLinejoin="round"
                              d="M8 10h.01M12 10h.01M16 10h.01M9 16H5a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2v8a2 2 0 0 1-2 2h-4l-3 3-3-3Z"
                            />
                          </svg>
                          <div className="min-w-0 flex-1 pr-5">
                            <p
                              className={`truncate text-xs font-medium leading-snug ${
                                isActive ? "text-primary-foreground" : "text-foreground"
                              }`}
                            >
                              {session.title}
                            </p>
                            {session.mode === "consulting" ? (
                              <p
                                className={`mt-0.5 truncate text-[10px] ${
                                  isActive ? "text-primary-foreground/70" : "text-muted-foreground"
                                }`}
                              >
                                Consulting{session.personaName ? ` · ${session.personaName}` : ""}
                              </p>
                            ) : session.bookTitles.length > 0 && (
                              <p
                                className={`mt-0.5 truncate text-[10px] ${
                                  isActive ? "text-primary-foreground/70" : "text-muted-foreground"
                                }`}
                              >
                                {session.bookTitles.slice(0, 2).join(", ")}
                                {session.bookTitles.length > 2 &&
                                  ` +${session.bookTitles.length - 2}`}
                              </p>
                            )}
                            <p
                              className={`mt-0.5 text-[10px] ${
                                isActive ? "text-primary-foreground/70" : "text-muted-foreground"
                              }`}
                            >
                              {session.messages.length} messages
                            </p>
                          </div>
                        </div>
                      </button>

                      {/* Delete button */}
                      {(isHovered || isActive) && (
                        <button
                          type="button"
                          onClick={(e) => {
                            e.stopPropagation();
                            onDelete(session.id);
                          }}
                          className={`absolute right-3 top-1/2 -translate-y-1/2 flex h-5 w-5 items-center justify-center rounded transition-colors ${
                            isActive
                              ? "text-primary-foreground/70 hover:text-primary-foreground"
                              : "text-muted-foreground hover:text-destructive hover:bg-destructive/10"
                          }`}
                          title="Delete this conversation"
                        >
                          <svg
                            className="h-3.5 w-3.5"
                            fill="none"
                            stroke="currentColor"
                            strokeWidth={2}
                            viewBox="0 0 24 24"
                          >
                            <path
                              strokeLinecap="round"
                              strokeLinejoin="round"
                              d="M6 18 18 6M6 6l12 12"
                            />
                          </svg>
                        </button>
                      )}
                    </div>
                  );
                })}
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Confirm clear overlay */}
      {confirmClear && (
        <div className="absolute inset-0 z-20 flex flex-col items-center justify-center gap-4 bg-background/90 backdrop-blur-sm px-6 text-center">
          <p className="text-sm font-semibold text-foreground">Clear all history?</p>
          <p className="text-xs text-muted-foreground">This cannot be undone.</p>
          <div className="flex gap-3">
            <button
              type="button"
              onClick={() => setConfirmClear(false)}
              className="rounded-lg border border-border px-4 py-2 text-sm text-foreground hover:bg-accent"
            >
              Cancel
            </button>
            <button
              type="button"
              onClick={() => {
                onClear();
                setConfirmClear(false);
              }}
              className="rounded-lg bg-destructive px-4 py-2 text-sm font-semibold text-destructive-foreground hover:bg-destructive/90"
            >
              Clear All
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
