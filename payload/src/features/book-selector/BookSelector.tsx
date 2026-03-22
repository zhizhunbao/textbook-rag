import { useEffect, useState } from "react";
import { fetchBooks } from "@/features/shared/api";
import { useAppDispatch, useAppState } from "@/features/shared/AppContext";

export default function BookSelector() {
  const { books, currentBookId } = useAppState();
  const dispatch = useAppDispatch();
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (books.length > 0) return;
    fetchBooks()
      .then((b) => dispatch({ type: "SET_BOOKS", books: b }))
      .catch((err) => {
        console.warn("fetchBooks failed:", err);
        setError("API unavailable");
      });
  }, [books.length, dispatch]);

  return (
    <select
      className="w-full rounded border border-gray-600 bg-surface-800 px-3 py-2 text-sm text-slate-200 focus:border-brand-500 focus:outline-none"
      value={currentBookId ?? ""}
      onChange={(e) => {
        const v = e.target.value;
        dispatch({ type: "SET_BOOK", bookId: v ? Number(v) : null });
      }}
    >
      <option value="">{error ? `⚠ ${error}` : "Select a textbook…"}</option>
      {books.map((b) => (
        <option key={b.id} value={b.id}>
          {b.title}
        </option>
      ))}
    </select>
  );
}
