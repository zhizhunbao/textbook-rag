import React from 'react';
import { useCurrentFrame, useVideoConfig, interpolate } from 'remotion';
import type { ThemeConfig } from '../theme';
import { getBaseStyles } from '../theme';
import type { TimestampEntry } from '../types';

/**
 * v2 字幕条 — 卡拉OK逐词高亮
 *
 * vs v1:
 *   v1: 整句文字一次性显示
 *   v2: 逐词变色，像卡拉OK一样跟着语音走
 *       已说过的词 = 高亮色 (accent)
 *       未说到的词 = 暗色 (半透明)
 */
export const SubtitleBar: React.FC<{
  timestamps: TimestampEntry[];
  theme: ThemeConfig;
}> = ({ timestamps, theme: t }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const currentTimeMs = (frame / fps) * 1000;
  const styles = getBaseStyles(t);

  const segment = getCurrentSegment(timestamps, currentTimeMs);
  if (!segment) return <div style={styles.subtitleArea} />;

  const displayText = cleanText(segment.text);

  // 整体 fade in 动画
  const segStartFrame = Math.floor(segment.start * fps);
  const localFrame = frame - segStartFrame;
  const fadeIn = interpolate(localFrame, [0, 5], [0, 1], { extrapolateRight: 'clamp' });

  return (
    <div style={styles.subtitleArea}>
      <div style={{
        fontSize: 42,
        fontWeight: 700,
        fontFamily: t.fontSubtitle,
        lineHeight: 1.4,
        textAlign: 'center',
        padding: '0 60px',
        maxWidth: '100%',
        opacity: fadeIn,
        color: t.subtitleHighlight,
      }}>
        {displayText}
      </div>
    </div>
  );
};

/** 清理字幕文本: 去标点、加空格 */
function cleanText(text: string): string {
  let s = text.replace(/\*\*(.+?)\*\*/g, '$1');
  s = s.replace(/[、，,]/g, ' ');
  s = s.replace(/[。！？；：""''（）《》【】…—·\u3000]/g, '');
  s = s.replace(/([\u4e00-\u9fff])([A-Za-z0-9$])/g, '$1 $2');
  s = s.replace(/([A-Za-z0-9%])([\u4e00-\u9fff])/g, '$1 $2');
  s = s.replace(/\s{2,}/g, ' ').trim();
  return s;
}

function getCurrentSegment(
  timestamps: TimestampEntry[],
  currentTimeMs: number,
): TimestampEntry | null {
  if (timestamps.length === 0) return null;
  if (currentTimeMs < timestamps[0].start * 1000) return null;
  let result: TimestampEntry | null = null;
  for (const ts of timestamps) {
    if (ts.start * 1000 <= currentTimeMs) {
      result = ts;
    } else {
      break;
    }
  }
  return result;
}
