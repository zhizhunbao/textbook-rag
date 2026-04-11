import {
  createContext,
  useContext,
  useReducer,
  useEffect,
  type Dispatch,
  type ReactNode,
} from "react";
import type { BookSummary, SourceInfo } from "./types";

/* ── State ── */

export interface AppState {
  books: BookSummary[];
  currentBookId: number | null;
  /** Books locked for the current chat session (multi-select) */
  sessionBookIds: number[];
  /** Whether a session has been started (books were selected and locked) */
  sessionStarted: boolean;
  currentPage: number;
  selectedSource: SourceInfo | null;
  selectedSourceNonce: number;
  selectedModel: string;
  selectedProvider: string;
  chatMode: "answer" | "trace";
  pdfVariant: "origin" | "layout";
  showToc: boolean;
}

const initialState: AppState = {
  books: [],
  currentBookId: null,
  sessionBookIds: [],
  sessionStarted: false,
  currentPage: 1,
  selectedSource: null,
  selectedSourceNonce: 0,
  selectedModel: "llama3.2:3b",
  selectedProvider: "ollama",
  chatMode: "answer",
  pdfVariant: "origin",
  showToc: true,
};

/* ── Persistence helpers ── */

const STORAGE_KEY = "textbook-rag-state";

function loadPersistedState(): Partial<AppState> {
  try {
    const raw = sessionStorage.getItem(STORAGE_KEY);
    if (!raw) return {};
    const saved = JSON.parse(raw);
    return {
      currentBookId: typeof saved.currentBookId === "number" ? saved.currentBookId : null,
      sessionBookIds: Array.isArray(saved.sessionBookIds) ? saved.sessionBookIds.filter((x: unknown) => typeof x === "number") : [],
      sessionStarted: saved.sessionStarted === true,
      currentPage: typeof saved.currentPage === "number" ? saved.currentPage : 1,
      selectedModel:
        typeof saved.selectedModel === "string" && saved.selectedModel.trim()
          ? saved.selectedModel
          : initialState.selectedModel,
      selectedProvider:
        typeof saved.selectedProvider === "string" && saved.selectedProvider.trim()
          ? saved.selectedProvider
          : initialState.selectedProvider,
      chatMode: saved.chatMode === "trace" ? "trace" : "answer",
      pdfVariant: saved.pdfVariant === "layout" ? "layout" : "origin",
    };
  } catch {
    return {};
  }
}

function persistState(state: AppState) {
  try {
    sessionStorage.setItem(
      STORAGE_KEY,
      JSON.stringify({
        currentBookId: state.currentBookId,
        sessionBookIds: state.sessionBookIds,
        sessionStarted: state.sessionStarted,
        currentPage: state.currentPage,
        selectedModel: state.selectedModel,
        selectedProvider: state.selectedProvider,
        chatMode: state.chatMode,
        pdfVariant: state.pdfVariant,
      }),
    );
  } catch { /* quota exceeded — ignore */ }
}

/* ── Actions ── */

type Action =
  | { type: "SET_BOOKS"; books: BookSummary[] }
  | { type: "SET_BOOK"; bookId: number | null }
  | { type: "SET_PAGE"; page: number }
  | { type: "SELECT_SOURCE"; source: SourceInfo | null }
  | { type: "SET_MODEL"; model: string; provider?: string }
  | { type: "SET_CHAT_MODE"; mode: "answer" | "trace" }
  | { type: "SET_PDF_VARIANT"; variant: "origin" | "layout" }
  | { type: "TOGGLE_TOC" }
  /** Lock books for this session and start the conversation */
  | { type: "START_SESSION"; bookIds: number[] }
  /** Exit the session — return to book picker */
  | { type: "RESET_SESSION" };

function reducer(state: AppState, action: Action): AppState {
  switch (action.type) {
    case "SET_BOOKS":
      return { ...state, books: action.books };
    case "SET_BOOK":
      return {
        ...state,
        currentBookId: action.bookId,
        currentPage: 1,
        selectedSource: null,
        selectedSourceNonce: 0,
      };
    case "SET_PAGE":
      return { ...state, currentPage: action.page };
    case "SELECT_SOURCE": {
      // Resolve engine book_id_string → Payload CMS id
      let resolvedBookId = state.currentBookId;
      if (action.source?.book_id_string) {
        const match = state.books.find((b) => b.book_id === action.source!.book_id_string);
        if (match) resolvedBookId = match.id;
      }
      return {
        ...state,
        selectedSource: action.source,
        selectedSourceNonce: state.selectedSourceNonce + 1,
        currentBookId: resolvedBookId,
        currentPage: action.source?.page_number ?? state.currentPage,
      };
    }
    case "SET_MODEL":
      return { ...state, selectedModel: action.model, selectedProvider: action.provider ?? state.selectedProvider };
    case "SET_CHAT_MODE":
      return { ...state, chatMode: action.mode };
    case "SET_PDF_VARIANT":
      return { ...state, pdfVariant: action.variant };
    case "TOGGLE_TOC":
      return { ...state, showToc: !state.showToc };
    case "START_SESSION":
      return {
        ...state,
        sessionBookIds: action.bookIds,
        sessionStarted: true,
        currentBookId: action.bookIds[0] ?? null,
        currentPage: 1,
        selectedSource: null,
        selectedSourceNonce: 0,
      };
    case "RESET_SESSION":
      return {
        ...state,
        sessionBookIds: [],
        sessionStarted: false,
        currentBookId: null,
        currentPage: 1,
        selectedSource: null,
        selectedSourceNonce: 0,
      };
    default:
      return state;
  }
}

/* ── Context ── */

const StateCtx = createContext<AppState>(initialState);
const DispatchCtx = createContext<Dispatch<Action>>(() => {});

export function AppProvider({ children }: { children: ReactNode }) {
  const [state, dispatch] = useReducer(reducer, initialState, (init) => ({
    ...init,
    ...loadPersistedState(),
  }));

  useEffect(() => {
    persistState(state);
  }, [state.currentBookId, state.sessionBookIds, state.sessionStarted, state.currentPage, state.pdfVariant, state.selectedModel, state.selectedProvider, state.chatMode]);

  return (
    <StateCtx.Provider value={state}>
      <DispatchCtx.Provider value={dispatch}>{children}</DispatchCtx.Provider>
    </StateCtx.Provider>
  );
}

export function useAppState() {
  return useContext(StateCtx);
}

export function useAppDispatch() {
  return useContext(DispatchCtx);
}
