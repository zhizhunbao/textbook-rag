import React from 'react';
import { useCurrentFrame, useVideoConfig } from 'remotion';
import type { ThemeConfig } from '../theme';
import type { ChapterInfo } from '../types';

/**
 * 章节时间轴 — B站风格 (v2: 与 v1 基本相同)
 */
export const ChapterTimeline: React.FC<{
  chapters: ChapterInfo[];
  theme: ThemeConfig;
}> = ({ chapters, theme: t }) => {
  const frame = useCurrentFrame();
  const { fps, durationInFrames } = useVideoConfig();
  const currentTimeSec = frame / fps;
  const totalDurationSec = durationInFrames / fps;

  if (!chapters || chapters.length === 0) return null;

  let currentChapterIdx = 0;
  for (let i = chapters.length - 1; i >= 0; i--) {
    if (currentTimeSec >= chapters[i].startSec) {
      currentChapterIdx = i;
      break;
    }
  }

  return (
    <div style={{
      width: t.width,
      height: t.chapterHeight,
      background: 'rgba(10, 10, 25, 0.95)',
      display: 'flex',
      flexDirection: 'column',
      position: 'relative',
      fontFamily: t.fontBody,
      overflow: 'hidden',
    }}>
      <div style={{
        display: 'flex',
        flex: 1,
        alignItems: 'center',
        justifyContent: 'center',
        padding: '0 4px',
        gap: 2,
      }}>
        {chapters.map((ch, i) => {
          const endSec = i < chapters.length - 1
            ? chapters[i + 1].startSec
            : totalDurationSec;
          const durSec = endSec - ch.startSec;
          const isCurrent = i === currentChapterIdx;
          const isPast = i < currentChapterIdx;

          let segProgress = 0;
          if (isCurrent) {
            segProgress = Math.min(1, (currentTimeSec - ch.startSec) / durSec);
          }

          const shortLabel = ch.title.length <= 4
            ? ch.title
            : ch.title.split(/[：:]/)[0].replace(/[（(][一二三四五六七八九十\d]+[）)]/g, '').trim();

          return (
            <div key={i} style={{
              flex: '1 0 auto',
              height: '100%',
              position: 'relative',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              borderRadius: 4,
              padding: '0 6px',
            }}>
              <div style={{
                position: 'absolute',
                inset: 0,
                background: isPast
                  ? `${t.accent}26`
                  : isCurrent
                    ? `${t.accent}14`
                    : 'rgba(255, 255, 255, 0.04)',
                borderRadius: 4,
              }} />

              {isCurrent && (
                <div style={{
                  position: 'absolute',
                  left: 0, top: 0, bottom: 0,
                  width: `${segProgress * 100}%`,
                  background: `linear-gradient(90deg, ${t.accent}40, ${t.accent}26)`,
                  borderRadius: 4,
                }} />
              )}

              {i > 0 && (
                <div style={{
                  position: 'absolute',
                  left: 0, top: '20%', bottom: '20%',
                  width: 1,
                  background: 'rgba(255, 255, 255, 0.12)',
                }} />
              )}

              <span style={{
                position: 'relative',
                fontSize: 20,
                fontWeight: isCurrent ? 700 : 500,
                color: isCurrent
                  ? t.accent
                  : isPast
                    ? `${t.accent}99`
                    : 'rgba(255, 255, 255, 0.45)',
                letterSpacing: 0.5,
                whiteSpace: 'nowrap',
                textShadow: isCurrent ? `0 0 12px ${t.accent}30` : 'none',
              }}>
                {shortLabel}
              </span>

              {isCurrent && (
                <div style={{
                  position: 'absolute',
                  bottom: 2,
                  left: `${segProgress * 100}%`,
                  width: 6,
                  height: 6,
                  borderRadius: '50%',
                  background: t.accent,
                  transform: 'translateX(-50%)',
                  boxShadow: `0 0 8px ${t.accent}`,
                }} />
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
};
