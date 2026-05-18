import React from 'react';
import { useCurrentFrame, useVideoConfig } from 'remotion';
import { theme } from '../theme';
import type { ChapterInfo } from '../types';

/**
 * 章节时间轴 — B站风格
 *
 * 布局: 固定在视频最顶部，1920×48
 * ┌──[免费卡]──[中端卡]──[高端卡]──[Costco]──[五坑]──[总结]──┐
 *
 * - 每个章节按时长比例占宽度
 * - 当前章节高亮金色
 * - 已过章节半透明
 * - 底部有时间进度条
 */
export const ChapterTimeline: React.FC<{
  chapters: ChapterInfo[];
}> = ({ chapters }) => {
  const frame = useCurrentFrame();
  const { fps, durationInFrames } = useVideoConfig();
  const currentTimeSec = frame / fps;
  const totalDurationSec = durationInFrames / fps;

  if (!chapters || chapters.length === 0) return null;

  // 计算每个章节的宽度比例
  const totalDur = totalDurationSec;

  // 确定当前章节
  let currentChapterIdx = 0;
  for (let i = chapters.length - 1; i >= 0; i--) {
    if (currentTimeSec >= chapters[i].startSec) {
      currentChapterIdx = i;
      break;
    }
  }

  // 全局进度比例
  const globalProgress = Math.min(1, currentTimeSec / totalDur);

  return (
    <div style={{
      width: theme.width,
      height: theme.chapterHeight,
      background: 'rgba(10, 10, 25, 0.95)',
      display: 'flex',
      flexDirection: 'column',
      position: 'relative',
      fontFamily: theme.fontFamily,
      overflow: 'hidden',

    }}>
      {/* ── 章节段 ── */}
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
            : totalDur;
          const durSec = endSec - ch.startSec;
          const widthPct = (durSec / totalDur) * 100;

          const isCurrent = i === currentChapterIdx;
          const isPast = i < currentChapterIdx;

          // 当前章节内的进度
          let segProgress = 0;
          if (isCurrent) {
            segProgress = Math.min(1, (currentTimeSec - ch.startSec) / durSec);
          }

          // 简称：取 storyline 标题中冒号后的部分，再截短
          const shortLabel = getShortLabel(ch.title, i);

          return (
            <div key={i} style={{
              flex: '1 0 auto',
              height: '100%',
              position: 'relative',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              borderRadius: 4,
              cursor: 'default',
              padding: '0 6px',
            }}>
              {/* 背景 */}
              <div style={{
                position: 'absolute',
                inset: 0,
                background: isPast
                  ? `rgba(255, 215, 0, 0.15)`
                  : isCurrent
                    ? `rgba(255, 215, 0, 0.08)`
                    : 'rgba(255, 255, 255, 0.04)',
                borderRadius: 4,
              }} />

              {/* 当前章节进度填充 */}
              {isCurrent && (
                <div style={{
                  position: 'absolute',
                  left: 0, top: 0, bottom: 0,
                  width: `${segProgress * 100}%`,
                  background: 'linear-gradient(90deg, rgba(255,215,0,0.25), rgba(255,215,0,0.15))',
                  borderRadius: 4,
                }} />
              )}

              {/* 左侧竖线分隔 */}
              {i > 0 && (
                <div style={{
                  position: 'absolute',
                  left: 0, top: '20%', bottom: '20%',
                  width: 1,
                  background: 'rgba(255, 255, 255, 0.12)',
                }} />
              )}

              {/* 章节标签 — 不截断，文字撑宽 */}
              <span style={{
                position: 'relative',
                fontSize: 20,
                fontWeight: isCurrent ? 700 : 500,
                color: isCurrent
                  ? theme.accent
                  : isPast
                    ? 'rgba(255, 215, 0, 0.6)'
                    : 'rgba(255, 255, 255, 0.45)',
                letterSpacing: 0.5,
                whiteSpace: 'nowrap',
                textShadow: isCurrent ? `0 0 12px ${theme.accent}30` : 'none',
              }}>
                {shortLabel}
              </span>

              {/* 当前章节指示点 */}
              {isCurrent && (
                <div style={{
                  position: 'absolute',
                  bottom: 2,
                  left: `${segProgress * 100}%`,
                  width: 6,
                  height: 6,
                  borderRadius: '50%',
                  background: theme.accent,
                  transform: 'translateX(-50%)',
                  boxShadow: `0 0 8px ${theme.accent}`,
                }} />
              )}
            </div>
          );
        })}
      </div>


    </div>
  );
};

/**
 * 从 storyline 标题生成短标签（通用逻辑）
 * 1. 取冒号前半部分
 * 2. 去掉序号后缀 （一）（二）
 * 3. 超长则截断
 */
function getShortLabel(title: string, _index: number): string {
  // "开场" 等已被 render.mjs 预处理的简短标题直接返回
  if (title.length <= 4) return title;

  // 取冒号前半
  let label = title.split(/[：:]/)[0].trim();

  // 去掉序号后缀 （一）（二）(1)(2) 等
  label = label
    .replace(/[（(][一二三四五六七八九十\d]+[）)]/g, '')
    .trim();

  // 不截断 — 文字撑宽 section
  return label;
}

