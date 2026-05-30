/**
 * v2 核心: 逐元素揭示 (Progressive Disclosure) 计算引擎
 *
 * 核心理念: 讲到哪里，画面就出现到哪里
 *
 * 算法:
 *   1. 按 slide_index 分组 timestamps
 *   2. 对每个 slide，根据当前时间确定"已讲过几句"
 *   3. 将"已讲过的句数"映射到 UI 元素的可见性
 */

import type { TimestampEntry, RevealState } from '../types';

/**
 * 计算某个 slide 在当前时间的揭示状态
 *
 * @param timestamps - 所有 timestamps
 * @param slideIndex - 目标 slide 索引
 * @param currentTimeMs - 当前时间（毫秒）
 */
export function getRevealState(
  timestamps: TimestampEntry[],
  slideIndex: number,
  currentTimeMs: number,
): RevealState {
  // 找到属于这个 slide 的所有 timestamp
  const slideTs = timestamps.filter(ts => ts.slide_index === slideIndex);

  if (slideTs.length === 0) {
    return { spokenLines: 0, totalLines: 0, progress: 1, activeLineIndex: -1 };
  }

  const totalLines = slideTs.length;
  let spokenLines = 0;
  let activeLineIndex = -1;

  for (let i = 0; i < slideTs.length; i++) {
    const ts = slideTs[i];
    const startMs = ts.start * 1000;
    const endMs = ts.end * 1000;

    if (currentTimeMs >= startMs) {
      spokenLines = i + 1;
      activeLineIndex = i;
    }
  }

  const progress = totalLines > 0 ? spokenLines / totalLines : 1;

  return { spokenLines, totalLines, progress, activeLineIndex };
}

/**
 * 计算表格行的可见性
 *
 * 策略:
 *   - 标题: slide 出现就立即显示
 *   - 表头: 第 1 句台词开始说时显示
 *   - 表格第 N 行: 尽量均匀分配到台词句数中
 *   - 引用块: 最后 1 句台词时显示
 *
 * @param rowCount - 表格数据行数
 * @param reveal - 当前揭示状态
 * @returns 每行的可见性 (true = 可见)
 */
export function getTableRowVisibility(
  rowCount: number,
  reveal: RevealState,
): boolean[] {
  if (rowCount === 0) return [];

  const { spokenLines, totalLines } = reveal;

  // 如果只有 1 句台词，所有行都在说第 1 句时出现
  if (totalLines <= 1) {
    return new Array(rowCount).fill(spokenLines > 0);
  }

  // 台词中预留: 第 1 句用于标题/引题，最后 1 句用于总结
  // 中间的句子均匀分配给表格行
  const availableSlots = Math.max(1, totalLines - 1); // 跳过第一句
  const result: boolean[] = [];

  for (let r = 0; r < rowCount; r++) {
    // 这一行需要在第几句台词时出现?
    // 均匀分配: 第 r 行 → 第 (1 + r * (availableSlots-1) / (rowCount-1 || 1)) 句
    const triggerLine = rowCount === 1
      ? 2
      : 1 + Math.floor(r * (availableSlots - 1) / Math.max(1, rowCount - 1)) + 1;

    result.push(spokenLines >= triggerLine);
  }

  return result;
}

/**
 * 计算 bullet points 的可见性
 */
export function getPointsVisibility(
  pointCount: number,
  reveal: RevealState,
): boolean[] {
  if (pointCount === 0) return [];
  const { spokenLines, totalLines } = reveal;

  if (totalLines <= 1) {
    return new Array(pointCount).fill(spokenLines > 0);
  }

  const result: boolean[] = [];
  for (let p = 0; p < pointCount; p++) {
    const triggerLine = pointCount === 1
      ? 1
      : 1 + Math.floor(p * (totalLines - 1) / Math.max(1, pointCount - 1));
    result.push(spokenLines >= triggerLine);
  }

  return result;
}

/**
 * 标题是否可见 (slide 一出现就可见)
 */
export function isTitleVisible(reveal: RevealState): boolean {
  return reveal.spokenLines >= 0; // 总是可见
}

/**
 * 表头是否可见 (第 1 句台词开始就可见)
 */
export function isHeaderVisible(reveal: RevealState): boolean {
  return reveal.spokenLines >= 1;
}

/**
 * 引用块是否可见 (最后 1/3 台词时显示)
 */
export function isCitationVisible(reveal: RevealState): boolean {
  return reveal.progress >= 0.7;
}
