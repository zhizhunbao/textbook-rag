import {
  createContext,
  useContext,
  useReducer,
  useEffect,
  type Dispatch,
  type ReactNode,
} from "react";
import type { BookSummary, SourceInfo } from "../types/api";

/* ── State ── */

export interface AppState {
  books: BookSummary[];
  currentBookId: number | null;
  currentPage: number;
  selectedSource: SourceInfo | null;
  pdfVariant: "origin" | "layout";
  showToc: boolean;
}

const initialState: AppState = {
  books: [],
  currentBookId: null,
  currentPage: 1,
  selectedSource: null,
  pdfVariant: "origin",
  showToc: false,
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
      currentPage: typeof saved.currentPage === "number" ? saved.currentPage : 1,
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
        currentPage: state.currentPage,
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
  | { type: "SET_PDF_VARIANT"; variant: "origin" | "layout" }
  | { type: "TOGGLE_TOC" };

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
      };
    case "SET_PAGE":
      return { ...state, currentPage: action.page };
    case "SELECT_SOURCE":
      return {
        ...state,
        selectedSource: action.source,
        currentBookId: action.source?.book_id ?? state.currentBookId,
        currentPage: action.source?.page_number ?? state.currentPage,
      };
    case "SET_PDF_VARIANT":
      return { ...state, pdfVariant: action.variant };
    case "TOGGLE_TOC":
      return { ...state, showToc: !state.showToc };
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
  }, [state.currentBookId, state.currentPage, state.pdfVariant]);

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
