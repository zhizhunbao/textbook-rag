import { useCallback, useRef, useEffect, useState } from "react";

interface Props {
  /** Current width of the panel on the left side of the handle (px). */
  width: number;
  /** Called continuously while dragging with the new width. */
  onResize: (width: number) => void;
  /** Minimum allowed width. */
  min?: number;
  /** Maximum allowed width. */
  max?: number;
}

/**
 * A thin vertical drag-handle that lives between two flex panels.
 * Drag left/right to resize the left panel.
 */
export default function ResizeHandle({
  width,
  onResize,
  min = 100,
  max = 1200,
}: Props) {
  const dragging = useRef(false);
  const startX = useRef(0);
  const startW = useRef(0);
  const [active, setActive] = useState(false);
  const [previewDelta, setPreviewDelta] = useState(0);

  const onMouseDown = useCallback(
    (e: React.MouseEvent) => {
      e.preventDefault();
      dragging.current = true;
      startX.current = e.clientX;
      startW.current = width;
      setPreviewDelta(0);
      setActive(true);
    },
    [width],
  );

  useEffect(() => {
    const onMouseMove = (e: MouseEvent) => {
      if (!dragging.current) return;
      const delta = e.clientX - startX.current;
      const next = Math.max(min, Math.min(max, startW.current + delta));
      setPreviewDelta(next - startW.current);
    };
    const onMouseUp = () => {
      if (dragging.current) {
        const next = Math.max(
          min,
          Math.min(max, startW.current + previewDelta),
        );
        dragging.current = false;
        setPreviewDelta(0);
        setActive(false);
        if (next !== width) {
          onResize(next);
        }
      }
    };
    window.addEventListener("mousemove", onMouseMove);
    window.addEventListener("mouseup", onMouseUp);
    return () => {
      window.removeEventListener("mousemove", onMouseMove);
      window.removeEventListener("mouseup", onMouseUp);
    };
  }, [max, min, onResize, previewDelta, width]);

  return (
    <div
      className={`relative shrink-0 cursor-col-resize select-none transition-colors ${
        active ? "bg-primary" : "bg-border hover:bg-primary/50"
      }`}
      style={{
        width: 4,
        transform: previewDelta === 0 ? undefined : `translateX(${previewDelta}px)`,
        zIndex: active ? 10 : undefined,
      }}
      onMouseDown={onMouseDown}
    />
  );
}
