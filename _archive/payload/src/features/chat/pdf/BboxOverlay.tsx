import type { Ref } from "react";

interface Props {
  bbox: { x0: number; y0: number; x1: number; y1: number };
  pageWidth: number;
  pageHeight: number;
  renderedWidth: number;
  renderedHeight: number;
  coordWidth?: number;
  coordHeight?: number;
  overlayRef?: Ref<HTMLDivElement>;
  citationLabel?: string;
}

export default function BboxOverlay({
  bbox,
  pageWidth,
  pageHeight,
  renderedWidth,
  renderedHeight,
  coordWidth,
  coordHeight,
  overlayRef,
  citationLabel,
}: Props) {
  const scaleX = renderedWidth / (coordWidth ?? pageWidth);
  const scaleY = renderedHeight / (coordHeight ?? pageHeight);

  const style: React.CSSProperties = {
    position: "absolute",
    left: bbox.x0 * scaleX,
    top: bbox.y0 * scaleY,
    width: (bbox.x1 - bbox.x0) * scaleX,
    height: (bbox.y1 - bbox.y0) * scaleY,
    pointerEvents: "none",
    borderRadius: 6,
    background: "rgba(59, 130, 246, 0.12)",
    boxShadow: "inset 0 0 0 1px rgba(59, 130, 246, 0.18)",
  };

  const badgeStyle: React.CSSProperties = {
    position: "absolute",
    top: 4,
    left: -38,
    display: "inline-flex",
    alignItems: "center",
    borderRadius: 9999,
    padding: "2px 7px",
    fontSize: 10,
    fontWeight: 700,
    letterSpacing: "0.04em",
    boxShadow: "0 4px 10px rgba(15, 23, 42, 0.14)",
  };

  return (
    <div ref={overlayRef} style={style}>
      <div
        style={{
          position: "absolute",
          left: -8,
          top: 0,
          bottom: 0,
          width: 4,
          borderRadius: 9999,
          background: "rgba(37, 99, 235, 0.82)",
        }}
      />
      <div
        style={{
          ...badgeStyle,
          background: "rgba(15, 23, 42, 0.9)",
          color: "#eff6ff",
        }}
      >
        {citationLabel ?? "Citation"}
      </div>
    </div>
  );
}
