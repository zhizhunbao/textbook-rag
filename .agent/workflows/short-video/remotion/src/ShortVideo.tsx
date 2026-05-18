import React from 'react';
import { AbsoluteFill, Audio, useCurrentFrame, useVideoConfig } from 'remotion';
import { theme } from './theme';
import type { VideoProps, TimestampEntry, SlideData } from './types';
import { CoverSlide } from './components/CoverSlide';
import { ContentSlide } from './components/ContentSlide';
import { SubtitleBar } from './components/SubtitleBar';
import { ChapterTimeline } from './components/ChapterTimeline';

/**
 * 短视频主组件 (Light Mode)
 *
 * 布局: 1920×1080
 * ┌─────────────────────────┐
 * │ 章节时间轴 (1920×48)     │  ← B站风格章节进度
 * ├─────────────────────────┤
 * │   幻灯片区 (1920×832)    │  ← 白底蓝金风格
 * ├─────────────────────────┤
 * │   字幕条   (1920×200)    │  ← TikTok 逐词高亮
 * └─────────────────────────┘
 */
export const ShortVideo: React.FC<VideoProps> = ({ slides, timestamps, audioUrl, chapters }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const currentTimeMs = (frame / fps) * 1000;

  // ── 确定当前应显示的幻灯片 ──
  const slideIndex = getCurrentSlideIndex(timestamps, currentTimeMs);
  const slideData: SlideData | undefined = slides[slideIndex];

  return (
    <AbsoluteFill style={{ backgroundColor: theme.bgPrimary }}>
      {/* ── 章节时间轴 (顶部 48px) ── 绝对定位，互不覆盖 */}
      {chapters && chapters.length > 0 && (
        <div style={{
          position: 'absolute', top: 0, left: 0,
          width: theme.width, height: theme.chapterHeight,
        }}>
          <ChapterTimeline chapters={chapters} />
        </div>
      )}

      {/* ── 幻灯片区域 (48px ~ 880px) ── */}
      <div style={{
        position: 'absolute', top: theme.chapterHeight, left: 0,
        width: theme.width, height: theme.slideHeight,
        overflow: 'hidden',
      }}>
        {slideData ? renderSlide(slideData) : <FallbackSlide />}
      </div>

      {/* ── 字幕条 (880px ~ 1080px) ── */}
      <div style={{
        position: 'absolute',
        top: theme.chapterHeight + theme.slideHeight,
        left: 0,
        width: theme.width, height: theme.subtitleHeight,
      }}>
        <SubtitleBar timestamps={timestamps} />
        {/* 品牌水印 — 字幕区右下角 */}
        {slideData?.source && (
          <div style={{
            position: 'absolute', bottom: 10, right: 24,
            fontSize: 20,
            color: 'rgba(255, 255, 255, 0.3)',
            fontFamily: "'Inter', 'Noto Sans SC', monospace",
          }}>
            {slideData.source}
          </div>
        )}
      </div>

      {/* ── 音频轨道 ── */}
      <Audio src={audioUrl} />
    </AbsoluteFill>
  );
};

/* ── 根据 slide type 渲染对应组件 ── */
function renderSlide(slide: SlideData): React.ReactNode {
  if (slide.type === 'cover') {
    return <CoverSlide
      title={slide.title}
      subtitle={slide.subtitle}
      hookNumber={slide.hookNumber}
      hookUnit={slide.hookUnit}
      source={slide.source}
    />;
  }
  return <ContentSlide slide={slide} />;
}

/* ── 空白占位 ── */
const FallbackSlide: React.FC = () => (
  <div style={{
    width: theme.width,
    height: theme.slideHeight,
    background: theme.bgPrimary,
  }} />
);

/**
 * 根据当前时间确定幻灯片索引
 */
function getCurrentSlideIndex(timestamps: TimestampEntry[], currentTimeMs: number): number {
  if (timestamps.length === 0) return 0;
  let slideIdx = 0;
  for (const ts of timestamps) {
    if (ts.start * 1000 > currentTimeMs) break;
    slideIdx = ts.slide_index ?? slideIdx;
  }
  return slideIdx;
}

