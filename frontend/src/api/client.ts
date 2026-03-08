import type {
  BookDetail,
  BookSummary,
  QueryRequest,
  QueryResponse,
  TocEntry,
} from "../types/api";

const BASE = "/api/v1";

async function request<T>(url: string, init?: RequestInit): Promise<T> {
  const res = await fetch(url, init);
  if (!res.ok) {
    const body = await res.text();
    throw new Error(`${res.status}: ${body}`);
  }
  return res.json() as Promise<T>;
}

export async function fetchBooks(): Promise<BookSummary[]> {
  return request<BookSummary[]>(`${BASE}/books`);
}

export async function fetchBook(bookId: number): Promise<BookDetail> {
  return request<BookDetail>(`${BASE}/books/${bookId}`);
}

export async function fetchToc(bookId: number): Promise<TocEntry[]> {
  return request<TocEntry[]>(`${BASE}/books/${bookId}/toc`);
}

export function getPdfUrl(bookId: number, variant: "origin" | "layout" = "origin"): string {
  return `${BASE}/books/${bookId}/pdf?variant=${variant}`;
}

export async function fetchSuggestions(bookId: number): Promise<string[]> {
  return request<string[]>(`${BASE}/books/${bookId}/suggestions`);
}

export async function queryTextbook(
  req: QueryRequest,
): Promise<QueryResponse> {
  return request<QueryResponse>(`${BASE}/query`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(req),
  });
}
