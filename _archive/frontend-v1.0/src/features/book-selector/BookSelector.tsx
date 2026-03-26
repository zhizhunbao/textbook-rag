import { useEffect } from "react";
import { fetchBooks } from "../../api/client";
import { useAppDispatch, useAppState } from "../../context/AppContext";

export default function BookSelector() {
  const { books, currentBookId } = useAppState();
  const dispatch = useAppDispatch();

  useEffect(() => {
    if (books.length > 0) return;
    fetchBooks().then((b) => dispatch({ type: "SET_BOOKS", books: b }));
  }, [books.length, dispatch]);

  return (
    <select
      className="w-full rounded border border-gray-300 bg-white px-3 py-2 text-sm focus:border-blue-500 focus:outline-none"
      value={currentBookId ?? ""}
      onChange={(e) => {
        const v = e.target.value;
        dispatch({ type: "SET_BOOK", bookId: v ? Number(v) : null });
      }}
    >
      <option value="">Select a textbook…</option>
      {books.map((b) => (
        <option key={b.id} value={b.id}>
          {b.title}
        </option>
      ))}
    </select>
  );
}
