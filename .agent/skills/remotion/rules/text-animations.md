---
name: text-animations
description: Typography and text animation patterns for Remotion.
metadata:
  tags: typography, text, typewriter, highlighter
---

## Text animations

Based on `useCurrentFrame()`, reduce the string character by character to create a typewriter effect.

## Typewriter Effect

Always use string slicing for typewriter effects. Never use per-character opacity.

```tsx
import { useCurrentFrame, useVideoConfig } from "remotion";

export const Typewriter: React.FC<{ text: string }> = ({ text }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  // Characters per second
  const charsPerSecond = 20;
  const charsToShow = Math.floor((frame / fps) * charsPerSecond);
  const displayText = text.slice(0, charsToShow);

  return (
    <div style={{ fontFamily: "monospace", fontSize: 48 }}>
      {displayText}
      {charsToShow < text.length && (
        <span
          style={{
            opacity: Math.round(frame / 15) % 2 === 0 ? 1 : 0,
          }}
        >
          |
        </span>
      )}
    </div>
  );
};
```

## Word Highlighting

Animate word highlights like with a highlighter pen. Use `interpolate` to grow a background highlight behind individual words based on the current frame.
