/**
 * panel/ModeToggle.tsx
 * Answer / Trace 模式切换按钮
 */
export default function ModeToggle({
  mode,
  onChange,
}: {
  mode: "answer" | "trace";
  onChange: (mode: "answer" | "trace") => void;
}) {
  return (
    <div className="inline-flex rounded-md border border-border bg-card p-1">
      {(["answer", "trace"] as const).map((option) => {
        const active = mode === option;
        return (
          <button
            key={option}
            type="button"
            onClick={() => onChange(option)}
            className={`rounded px-2.5 py-1 text-xs font-medium transition ${
              active
                ? "bg-primary text-primary-foreground"
                : "text-muted-foreground hover:bg-muted"
            }`}
          >
            {option === "answer" ? "Answer" : "Trace"}
          </button>
        );
      })}
    </div>
  );
}
