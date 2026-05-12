import React from 'react';
import { AbsoluteFill, Audio, useCurrentFrame, useVideoConfig } from 'remotion';
import { theme } from './theme';
import type { VideoProps, TimestampEntry, SlideData } from './types';
import { CoverSlide } from './components/CoverSlide';
import { ContentSlide } from './components/ContentSlide';
import { SubtitleBar } from './components/SubtitleBar';

/**
 * 短视频主组件 (Light Mode)
 *
 * 布局: 1920×1080
 * ┌─────────────────────────┐
 * │   幻灯片区 (1920×880)    │  ← 白底蓝金风格
 * ├─────────────────────────┤
 * │   字幕条   (1920×200)    │  ← TikTok 逐词高亮
 * └─────────────────────────┘
 */
export const ShortVideo: React.FC<VideoProps> = ({ slides, timestamps, audioUrl }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const currentTimeMs = (frame / fps) * 1000;

  // ── 确定当前应显示的幻灯片 ──
  const slideIndex = getCurrentSlideIndex(timestamps, currentTimeMs);
  const slideData: SlideData | undefined = slides[slideIndex];

  return (
    <AbsoluteFill style={{ backgroundColor: theme.bgPrimary }}>
      {/* ── 幻灯片区域 (上方 880px) ── */}
      <div style={{ width: theme.width, height: theme.slideHeight }}>
        {slideData ? renderSlide(slideData) : <FallbackSlide />}
      </div>

      {/* ── 字幕条 (下方 200px) ── */}
      <SubtitleBar timestamps={timestamps} />

      {/* ── 音频轨道 ── */}
      <Audio src={audioUrl} />
    </AbsoluteFill>
  );
};

/* ── 根据 slide type 渲染对应组件 ── */
function renderSlide(slide: SlideData): React.ReactNode {
  if (slide.type === 'cover') {
    return <CoverSlide title={slide.title} subtitle={slide.subtitle} source={slide.source} />;
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
