import { useEffect, useState, useMemo } from "react";
import { Library, Layers } from "lucide-react";
import { fetchIndexedBooks, useBookSidebar, getCategoryConfig, buildCategoryIcons, type BookBase } from "@/features/shared/books";
import { useAppDispatch, useAppState } from "@/features/shared/AppContext";
import { cn } from "@/features/shared/utils";
import { SidebarLayout, type ViewMode } from "@/features/shared/components/SidebarLayout";

/**
 * BookPicker — pre-session book selection with SidebarLayout
 *
 * - Sidebar: Category → Subcategory hierarchy
 * - Main area: Card view / List view toggle
 * - Footer: "Start Chat" CTA
 */



export default function BookPicker() {
  const { books } = useAppState();
  const dispatch = useAppDispatch();
  const [loadingBooks, setLoadingBooks] = useState(books.length === 0);
  const [selected, setSelected] = useState<Set<number>>(new Set());
  const [filter, setFilter] = useState<string>("all");
  const [viewMode, setViewMode] = useState<ViewMode>("cards");

  useEffect(() => {
    if (books.length > 0) {
      setLoadingBooks(false);
      return;
    }
    fetchIndexedBooks()
      .then((b) => {
        dispatch({ type: "SET_BOOKS", books: b });
        setLoadingBooks(false);
      })
      .catch(() => setLoadingBooks(false));
  }, [books.length, dispatch]);

  function toggle(id: number) {
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  }

  function startSession() {
    if (selected.size === 0) return;
    dispatch({ type: "START_SESSION", bookIds: [...selected] });
  }

  // ── Dynamic category icons from actual book data ─────────────────────────
  const categoryIcons = useMemo(() => {
    const cats = [...new Set(books.map((b) => b.category || 'textbooks'))]
    return buildCategoryIcons(cats)
  }, [books])

  // ── Book sidebar (via shared hook) ──────────────────────────────────────────
  const { sidebarItems, filterBooks } = useBookSidebar(books, {
    mode: 'by-category',
    allLabel: 'All Books',
    allIcon: <Layers className="h-4 w-4 shrink-0" />,
    categoryIcons,
  });

  // ── Filtered books ─────────────────────────────────────────────────────────
  const displayBooks = useMemo(() => filterBooks(filter), [filter, filterBooks]);

  const canStart = selected.size > 0;

  return (
    <SidebarLayout
      title="Choose Books"
      icon={<Library className="h-4 w-4 text-primary" />}
      sidebarItems={sidebarItems}
      activeFilter={filter}
      onFilterChange={setFilter}
      sidebarWidth="w-48"
      showViewToggle
      viewMode={viewMode}
      onViewModeChange={setViewMode}
      sidebarFooter={
        <p className="text-[10px] text-muted-foreground">
          {selected.size > 0
            ? `${selected.size} book${selected.size > 1 ? "s" : ""} selected`
            : "Select books to start"}
        </p>
      }
      subtitle={`${displayBooks.length} book${displayBooks.length !== 1 ? "s" : ""}`}
      loading={loadingBooks}
      loadingText="Loading books..."
      toolbar={
        <SelectAllButton
          books={displayBooks}
          selected={selected}
          onSelectChange={setSelected}
        />
      }
      footer={
        <div className="shrink-0 border-t border-border bg-card/90 backdrop-blur px-6 py-3">
          <div className="mx-auto flex max-w-4xl items-center gap-4">
            <div className="flex-1 text-sm text-muted-foreground">
              {selected.size === 0
                ? "Select at least one book to continue"
                : `${selected.size} book${selected.size > 1 ? "s" : ""} selected`}
            </div>
            <button
              type="button"
              onClick={startSession}
              disabled={!canStart}
              className={cn(
                "inline-flex items-center gap-2 rounded-xl px-6 py-2.5 text-sm font-semibold shadow-sm transition",
                canStart
                  ? "bg-primary text-primary-foreground hover:bg-primary/90"
                  : "bg-muted text-muted-foreground cursor-not-allowed shadow-none",
              )}
            >
              <svg className="h-4 w-4" fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" d="M8.625 12a.375.375 0 1 1-.75 0 .375.375 0 0 1 .75 0Zm0 0H8.25m4.125 0a.375.375 0 1 1-.75 0 .375.375 0 0 1 .75 0Zm0 0H12m4.125 0a.375.375 0 1 1-.75 0 .375.375 0 0 1 .75 0Zm0 0h-.375M21 12c0 4.556-4.03 8.25-9 8.25a9.764 9.764 0 0 1-2.555-.337A5.972 5.972 0 0 1 5.41 20.97a5.969 5.969 0 0 1-.474-.065 4.48 4.48 0 0 0 .978-2.025c.09-.457-.133-.901-.467-1.226C3.93 16.178 3 14.189 3 12c0-4.556 4.03-8.25 9-8.25s9 3.694 9 8.25Z" />
              </svg>
              Start Chat
            </button>
          </div>
        </div>
      }
    >
      {displayBooks.length === 0 ? (
        <div className="flex flex-col items-center py-20">
          <Library className="h-10 w-10 text-muted-foreground/40 mb-3" />
          <p className="text-sm text-muted-foreground">No books in this category</p>
        </div>
      ) : viewMode === "cards" ? (
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {displayBooks.map((book) => (
            <BookCard key={book.id} book={book} checked={selected.has(book.id)} onToggle={toggle} />
          ))}
        </div>
      ) : (
        <BookTable books={displayBooks} selected={selected} onToggle={toggle} />
      )}
    </SidebarLayout>
  );
}

// ═══════════════════════════════════════════════════════════════════════════════
// Sub-components
// ═══════════════════════════════════════════════════════════════════════════════

/** Select/Deselect all button for toolbar */
function SelectAllButton({
  books,
  selected,
  onSelectChange,
}: {
  books: BookBase[];
  selected: Set<number>;
  onSelectChange: (s: Set<number>) => void;
}) {
  const allSelected = books.length > 0 && books.every((b) => selected.has(b.id));
  return (
    <button
      type="button"
      onClick={() => {
        const next = new Set(selected);
        if (allSelected) books.forEach((b) => next.delete(b.id));
        else books.forEach((b) => next.add(b.id));
        onSelectChange(next);
      }}
      className="text-xs text-muted-foreground hover:text-foreground transition-colors"
    >
      {allSelected ? "Deselect all" : "Select all"}
    </button>
  );
}

/** Card view item */
function BookCard({
  book,
  checked,
  onToggle,
}: {
  book: BookBase;
  checked: boolean;
  onToggle: (id: number) => void;
}) {
  const catCfg = getCategoryConfig(book.category || "textbook");
  return (
    <button
      type="button"
      onClick={() => onToggle(book.id)}
      className={cn(
        "group flex items-start gap-3 rounded-xl border-2 p-4 text-left transition-all",
        checked
          ? "border-primary bg-primary/5"
          : "border-border bg-card hover:border-primary/30 hover:shadow-sm",
      )}
    >
      {/* Checkbox */}
      <div
        className={cn(
          "mt-0.5 flex h-4 w-4 shrink-0 items-center justify-center rounded border-2 transition-colors",
          checked
            ? "border-primary bg-primary"
            : "border-muted-foreground/30 group-hover:border-muted-foreground/50",
        )}
      >
        {checked && (
          <svg className="h-2.5 w-2.5 text-primary-foreground" fill="none" stroke="currentColor" strokeWidth={3} viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" d="m4.5 12.75 6 6 9-13.5" />
          </svg>
        )}
      </div>
      <div className="min-w-0 flex-1">
        <div className="text-sm font-semibold leading-snug text-foreground">{book.title}</div>
        {book.authors && (
          <div className="text-[11px] text-muted-foreground mt-0.5 truncate">{book.authors}</div>
        )}
        <div className="mt-1.5 flex flex-wrap gap-1.5 text-[11px] text-muted-foreground">
          {catCfg && (
            <span className={cn("rounded px-1.5 py-0.5 bg-secondary", catCfg.color)}>
              {catCfg.label}
            </span>
          )}
          {book.subcategory && (
            <span className="rounded px-1.5 py-0.5 bg-secondary">{book.subcategory}</span>
          )}
          {book.chunk_count > 0 && (
            <span className="rounded px-1.5 py-0.5 bg-secondary">{book.chunk_count} chunks</span>
          )}
        </div>
      </div>
    </button>
  );
}

/** List/Table view */
function BookTable({
  books,
  selected,
  onToggle,
}: {
  books: BookBase[];
  selected: Set<number>;
  onToggle: (id: number) => void;
}) {
  return (
    <div className="rounded-xl border border-border overflow-hidden">
      <table className="w-full text-sm">
        <thead>
          <tr className="bg-card/80 border-b border-border">
            <th className="w-10 px-4 py-2.5" />
            <th className="text-left px-4 py-2.5 text-xs font-medium text-muted-foreground uppercase tracking-wider">Title</th>
            <th className="text-left px-4 py-2.5 text-xs font-medium text-muted-foreground uppercase tracking-wider">Authors</th>
            <th className="text-left px-4 py-2.5 text-xs font-medium text-muted-foreground uppercase tracking-wider">Category</th>
            <th className="text-left px-4 py-2.5 text-xs font-medium text-muted-foreground uppercase tracking-wider">Subcategory</th>
            <th className="text-right px-4 py-2.5 text-xs font-medium text-muted-foreground uppercase tracking-wider">Chunks</th>
          </tr>
        </thead>
        <tbody>
          {books.map((book) => {
            const checked = selected.has(book.id);
            const catCfg = getCategoryConfig(book.category || "textbook");
            return (
              <tr
                key={book.id}
                onClick={() => onToggle(book.id)}
                className={cn(
                  "border-b border-border/50 cursor-pointer transition-colors",
                  checked ? "bg-primary/5" : "hover:bg-card/50",
                )}
              >
                <td className="px-4 py-3">
                  <div
                    className={cn(
                      "flex h-4 w-4 items-center justify-center rounded border-2 transition-colors",
                      checked ? "border-primary bg-primary" : "border-muted-foreground/30",
                    )}
                  >
                    {checked && (
                      <svg className="h-2.5 w-2.5 text-primary-foreground" fill="none" stroke="currentColor" strokeWidth={3} viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" d="m4.5 12.75 6 6 9-13.5" />
                      </svg>
                    )}
                  </div>
                </td>
                <td className="px-4 py-3">
                  <span className="text-sm font-medium text-foreground">{book.title}</span>
                </td>
                <td className="px-4 py-3 text-xs text-muted-foreground">{book.authors || "—"}</td>
                <td className="px-4 py-3">
                  {catCfg && (
                    <span className={cn("px-2 py-0.5 rounded-full text-[10px] font-medium bg-secondary", catCfg.color)}>
                      {catCfg.label}
                    </span>
                  )}
                </td>
                <td className="px-4 py-3 text-xs text-foreground">{book.subcategory || "—"}</td>
                <td className="px-4 py-3 text-xs text-foreground text-right">{book.chunk_count}</td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
