/**
 * 中英文混排文本分词工具 (v1 保持不变)
 */

import type { WordToken } from '../types';

/**
 * 将一句话拆分为 WordToken 数组
 * "搞懂CRS评分500分" → ["搞","懂","CRS","评","分","500","分"]
 */
export function splitToWords(text: string): WordToken[] {
  const tokens: WordToken[] = [];
  let i = 0;
  const chars = [...text];

  while (i < chars.length) {
    const ch = chars[i];

    if (/\s/.test(ch)) {
      i++;
      continue;
    }

    if (/[a-zA-Z0-9]/.test(ch)) {
      let word = '';
      while (i < chars.length && /[a-zA-Z0-9.%$,]/.test(chars[i])) {
        word += chars[i];
        i++;
      }
      tokens.push({ text: word, index: tokens.length });
      continue;
    }

    tokens.push({ text: ch, index: tokens.length });
    i++;
  }

  return tokens;
}

/**
 * 给定句子的起止时间 + 分词结果，计算第 currentTimeMs 时应高亮到第几个词
 */
export function getHighlightIndex(
  tokens: WordToken[],
  sentenceStartMs: number,
  sentenceEndMs: number,
  currentTimeMs: number,
): number {
  if (tokens.length === 0) return -1;
  if (currentTimeMs <= sentenceStartMs) return 0;
  if (currentTimeMs >= sentenceEndMs) return tokens.length - 1;

  const totalChars = tokens.reduce((sum, t) => sum + t.text.length, 0);
  const elapsed = currentTimeMs - sentenceStartMs;
  const duration = sentenceEndMs - sentenceStartMs;

  let accumulated = 0;
  for (let idx = 0; idx < tokens.length; idx++) {
    accumulated += tokens[idx].text.length;
    const threshold = (accumulated / totalChars) * duration;
    if (elapsed < threshold) return idx;
  }

  return tokens.length - 1;
}
