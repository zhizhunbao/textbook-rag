import React from 'react';
import { useCurrentFrame, useVideoConfig } from 'remotion';
import { theme, baseStyles } from '../theme';
import type { TimestampEntry } from '../types';

/**
 * EE 风格字幕条 — 整句显示
 *
 * - 底部 200px 独立区域
 * - 显示当前完整句子，白色大字居中
 * - 长字幕自动换行
 * - 显示时自动去除中文标点
 */

const MAX_CHARS_PER_LINE = 16; // 每行最多字符数

export const SubtitleBar: React.FC<{
  timestamps: TimestampEntry[];
}> = ({ timestamps }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const currentTimeMs = (frame / fps) * 1000;

  // 找到当前应显示的句子
  const segment = getCurrentSegment(timestamps, currentTimeMs);
  if (!segment) return <div style={baseStyles.subtitleArea} />;

  // 去标点
  const cleanText = removePunctuation(segment.text);

  // 将文本按字符数分行
  const lines = splitTextIntoLines(cleanText, MAX_CHARS_PER_LINE);

  return (
    <div style={baseStyles.subtitleArea}>
      <div style={{
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        gap: 8,
        padding: '0 80px',
      }}>
        {lines.map((line, i) => (
          <div
            key={`${segment.index}-${i}`}
            style={{
              fontSize: 52,
              fontWeight: 700,
              fontFamily: theme.fontFamily,
              color: theme.subtitleHighlight,
              lineHeight: 1.3,
              textAlign: 'center',
            }}
          >
            {line}
          </div>
        ))}
      </div>
    </div>
  );
};

/**
 * 将文本按字符数拆分成多行
 */
function splitTextIntoLines(text: string, maxChars: number): string[] {
  const lines: string[] = [];
  let remaining = text;

  while (remaining.length > 0) {
    if (remaining.length <= maxChars) {
      lines.push(remaining);
      break;
    }
    // 在 maxChars 处截断
    lines.push(remaining.slice(0, maxChars));
    remaining = remaining.slice(maxChars);
  }
  return lines;
}

/**
 * 根据当前时间找到应显示的字幕段
 * 字幕持续到下一条出现（无空白间隙）
 */
function getCurrentSegment(
  timestamps: TimestampEntry[],
  currentTimeMs: number,
): TimestampEntry | null {
  if (timestamps.length === 0) return null;

  // 还没开始
  if (currentTimeMs < timestamps[0].start * 1000) return null;

  // 找最后一个 start <= currentTime 的段
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

/**
 * 去除中文标点（保留英文和数字）
 * 语音保留标点控制语调，字幕显示更干净
 */
function removePunctuation(text: string): string {
  return text.replace(/[，。！？、；：""''（）《》【】…—·\u3000]/g, '');
}
