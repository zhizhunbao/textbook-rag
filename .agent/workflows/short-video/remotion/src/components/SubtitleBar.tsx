import React from 'react';
import { useCurrentFrame, useVideoConfig } from 'remotion';
import { theme, baseStyles } from '../theme';
import type { TimestampEntry } from '../types';

/**
 * 字幕条 — 每条 timestamp 直接显示，自适应字号
 */
export const SubtitleBar: React.FC<{
  timestamps: TimestampEntry[];
}> = ({ timestamps }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const currentTimeMs = (frame / fps) * 1000;

  const segment = getCurrentSegment(timestamps, currentTimeMs);
  if (!segment) return <div style={baseStyles.subtitleArea} />;

  const displayText = formatSubtitle(segment.text);
  const fontSize = 44; // 固定字号，避免字幕忽大忽小

  return (
    <div style={baseStyles.subtitleArea}>
      <div style={{
        fontSize,
        fontWeight: 700,
        fontFamily: theme.fontFamily,
        color: theme.subtitleHighlight,
        lineHeight: 1.4,
        textAlign: 'center',
        padding: '0 60px',
        maxWidth: '100%',
        whiteSpace: 'normal',
        wordBreak: 'keep-all',      // 中文按词组断行，不劈字
        overflowWrap: 'break-word', // 超长英文单词兜底换行
        display: '-webkit-box',
        WebkitLineClamp: 2,         // 最多两行
        WebkitBoxOrient: 'vertical' as const,
        overflow: 'hidden',
      }}>
        {displayText}
      </div>
    </div>
  );
};

/** 列举标点→空格，句末/装饰标点→删除，中英文间加空格 */
function formatSubtitle(text: string): string {
  let s = text.replace(/\*\*(.+?)\*\*/g, '$1');
  // 列举类标点 → 空格（防止 BMO、CIBC 合并）
  s = s.replace(/[、，,]/g, ' ');
  // 句末 / 装饰类标点 → 删除
  s = s.replace(/[。！？；：""''（）《》【】…—·\u3000]/g, '');
  // 中英文之间加空格
  s = s.replace(/([\u4e00-\u9fff])([A-Za-z0-9$])/g, '$1 $2');
  s = s.replace(/([A-Za-z0-9%])(?=[\u4e00-\u9fff])/g, '$1 ');
  // 连续空格合并
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
