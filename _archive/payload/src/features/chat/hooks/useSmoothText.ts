/**
 * useSmoothText — smooth character-by-character text reveal (à la Coze/GPT).
 *
 * Inspired by @bytedance/calypso's useSmoothText:
 * - Full text is buffered elsewhere (parent state or ref).
 * - This hook "releases" characters one-by-one at a configurable speed,
 *   creating the typewriter / GPT-like smooth streaming effect.
 * - When `isStreaming` is false the remaining text is flushed immediately.
 */
import { useState, useEffect, useRef, useCallback } from "react";

interface UseSmoothTextOptions {
  /** The full accumulated text (may still be growing). */
  text: string;
  /** Whether tokens are still arriving. */
  isStreaming: boolean;
  /** Base milliseconds between each character reveal. Default 12ms. */
  speed?: number;
}

export function useSmoothText({
  text,
  isStreaming,
  speed = 12,
}: UseSmoothTextOptions) {
  const [displayText, setDisplayText] = useState("");
  const posRef = useRef(0); // how many chars already revealed
  const rafRef = useRef<number | null>(null);
  const lastFrameRef = useRef(0);

  // Adaptive speed: when there's a large buffer pending, release faster
  const getCharsPerFrame = useCallback(
    (pending: number) => {
      if (pending > 200) return 8; // way behind — catch up fast
      if (pending > 80) return 4;
      if (pending > 30) return 2;
      return 1;
    },
    [],
  );

  useEffect(() => {
    // When streaming ends, flush all remaining text immediately
    if (!isStreaming) {
      if (rafRef.current !== null) {
        cancelAnimationFrame(rafRef.current);
        rafRef.current = null;
      }
      posRef.current = text.length;
      setDisplayText(text);
      return;
    }

    // Animation loop — reveal characters smoothly
    const step = (now: number) => {
      const elapsed = now - lastFrameRef.current;
      if (elapsed >= speed) {
        lastFrameRef.current = now;
        const pending = text.length - posRef.current;
        if (pending > 0) {
          const chars = getCharsPerFrame(pending);
          const newPos = Math.min(posRef.current + chars, text.length);
          posRef.current = newPos;
          setDisplayText(text.slice(0, newPos));
        }
      }
      rafRef.current = requestAnimationFrame(step);
    };

    rafRef.current = requestAnimationFrame(step);

    return () => {
      if (rafRef.current !== null) {
        cancelAnimationFrame(rafRef.current);
        rafRef.current = null;
      }
    };
  }, [text, isStreaming, speed, getCharsPerFrame]);

  // Reset when text is cleared (new conversation)
  useEffect(() => {
    if (text === "") {
      posRef.current = 0;
      setDisplayText("");
    }
  }, [text]);

  const isRevealing = isStreaming && posRef.current < text.length;

  return { displayText, isRevealing };
}
