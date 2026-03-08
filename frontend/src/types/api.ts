/* ── API response types ── */

export interface BookSummary {
  id: number;
  book_id: string;
  title: string;
  authors: string;
  page_count: number;
  chapter_count: number;
  chunk_count: number;
}

export interface ChapterInfo {
  id: number;
  chapter_key: string;
  title: string;
  start_page: number | null;
}

export interface BookDetail extends BookSummary {
  chapters: ChapterInfo[];
}

export interface TocEntry {
  id: number;
  level: number;
  number: string;
  title: string;
  pdf_page: number;
}

export interface SourceInfo {
  source_id: string;
  book_id: number;
  book_title: string;
  chapter_title: string | null;
  page_number: number;
  snippet: string;
  bbox: { x0: number; y0: number; x1: number; y1: number } | null;
  confidence: number;
}

export interface RetrievalStats {
  fts_hits: number;
  vector_hits: number;
  fused_count: number;
}

export interface QueryResponse {
  answer: string;
  sources: SourceInfo[];
  retrieval_stats: RetrievalStats;
}

export interface QueryFilters {
  book_ids?: number[];
  chapter_ids?: number[];
  content_types?: string[];
}

export interface QueryRequest {
  question: string;
  filters?: QueryFilters;
  top_k?: number;
}
