import React from 'react';
import { AbsoluteFill, Audio, useCurrentFrame, useVideoConfig, interpolate } from 'remotion';
import { getTheme } from './theme';
import type { VideoProps, TimestampEntry, SlideData } from './types';
import type { ThemeConfig } from './theme';
import { CoverSlide } from './components/CoverSlide';
import { ContentSlide } from './components/ContentSlide';
import { HighlightSlide } from './components/HighlightSlide';
import { SubtitleBar } from './components/SubtitleBar';
import { ChapterTimeline } from './components/ChapterTimeline';

/**
 * 短视频主组件 — 多主题 + 过渡动画
 *
 * 布局: 1920×1080
 * ┌─────────────────────────┐
 * │ 章节时间轴 (1920×48)     │  ← B站风格章节进度
 * ├─────────────────────────┤
 * │   幻灯片区 (1920×832)    │  ← 动态主题色
 * ├─────────────────────────┤
 * │   字幕条   (1920×200)    │  ← TikTok 逐词高亮
 * └─────────────────────────┘
 *
 * 新功能:
 *   - 5 套主题色预设 (storyline 中 **主题色**: xxx)
 *   - Slide 切换淡入淡出过渡 (300ms)
 *   - highlight 类型支持
 */
export const ShortVideo: React.FC<VideoProps> = ({ slides, timestamps, audioUrl, chapters, themeName }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const currentTimeMs = (frame / fps) * 1000;

  // ── 获取主题配置 ──
  const t = getTheme(themeName);

  // ── 确定当前应显示的幻灯片 ──
  const slideIndex = getCurrentSlideIndex(timestamps, currentTimeMs);
  const slideData: SlideData | undefined = slides[slideIndex];

  // ── 计算 slide 切换的过渡动画 ──
  const transitionInfo = getSlideTransition(timestamps, currentTimeMs, fps, slideIndex);

  // ── 自动检测语言（中/英）──
  const allText = timestamps.map(t => t.text).join('');
  const cnChars = allText.replace(/[^\u4e00-\u9fff]/g, '').length;
  const isEnglish = cnChars / Math.max(allText.length, 1) < 0.1;
  const disclaimer = isEnglish
    ? 'For reference only. Not financial or legal advice.'
    : '仅供参考 不构成投资或法律建议';

  return (
    <AbsoluteFill style={{ backgroundColor: t.bgPrimary }}>
      {/* ── 章节时间轴 (顶部 48px) ── */}
      {chapters && chapters.length > 0 && (
        <div style={{
          position: 'absolute', top: 0, left: 0,
          width: t.width, height: t.chapterHeight,
        }}>
          <ChapterTimeline chapters={chapters} theme={t} />
        </div>
      )}

      {/* ── 幻灯片区域 (48px ~ 880px) ── 带淡入淡出过渡 */}
      <div style={{
        position: 'absolute', top: t.chapterHeight, left: 0,
        width: t.width, height: t.slideHeight,
        overflow: 'hidden',
        opacity: transitionInfo.opacity,
      }}>
        {slideData ? renderSlide(slideData, t) : <FallbackSlide theme={t} />}
      </div>

      {/* ── 字幕条 (880px ~ 1080px) ── */}
      <div style={{
        position: 'absolute',
        top: t.chapterHeight + t.slideHeight,
        left: 0,
        width: t.width, height: t.subtitleHeight,
      }}>
        <SubtitleBar timestamps={timestamps} theme={t} />
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
        {/* 免责声明水印 — 字幕区左下角 */}
        <div style={{
          position: 'absolute', bottom: 10, left: 24,
          fontSize: 16,
          color: 'rgba(255, 255, 255, 0.2)',
          fontFamily: "'Inter', 'Noto Sans SC', sans-serif",
        }}>
          {disclaimer}
        </div>
      </div>

      {/* ── 音频轨道 ── */}
      <Audio src={audioUrl} />
    </AbsoluteFill>
  );
};

/* ── 根据 slide type 渲染对应组件 ── */
function renderSlide(slide: SlideData, t: ThemeConfig): React.ReactNode {
  if (slide.type === 'cover') {
    return <CoverSlide
      title={slide.title}
      subtitle={slide.subtitle}
      hookNumber={slide.hookNumber}
      hookUnit={slide.hookUnit}
      source={slide.source}
      theme={t}
    />;
  }
  if (slide.type === 'highlight') {
    return <HighlightSlide
      content={slide.content || slide.title}
      theme={t}
    />;
  }
  return <ContentSlide slide={slide} theme={t} />;
}

/* ── 空白占位 ── */
const FallbackSlide: React.FC<{ theme: ThemeConfig }> = ({ theme: t }) => (
  <div style={{
    width: t.width,
    height: t.slideHeight,
    background: t.bgPrimary,
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

/**
 * 计算 slide 切换过渡动画
 *
 * 在 slide 切换点附近，返回淡入淡出的 opacity 值:
 * - 切换前 150ms: opacity 1 → 0 (fade out)
 * - 切换后 150ms: opacity 0 → 1 (fade in)
 */
function getSlideTransition(
  timestamps: TimestampEntry[],
  currentTimeMs: number,
  fps: number,
  currentSlideIndex: number,
): { opacity: number } {
  const FADE_MS = 200; // 过渡时长

  // 找到下一个 slide 切换点
  for (const ts of timestamps) {
    if (ts.slide_index !== undefined && ts.slide_index !== currentSlideIndex) {
      const switchMs = ts.start * 1000;
      const distToSwitch = switchMs - currentTimeMs;

      // 即将切换 (0 ~ FADE_MS ms 之前): fade out
      if (distToSwitch > 0 && distToSwitch < FADE_MS) {
        return { opacity: distToSwitch / FADE_MS };
      }
    }
  }

  // 找上一个 slide 切换点（fade in）
  let lastSwitchMs = 0;
  for (const ts of timestamps) {
    if (ts.slide_index === currentSlideIndex && ts.start * 1000 <= currentTimeMs) {
      // 这是当前 slide 的第一个 timestamp
      if (lastSwitchMs === 0 || ts.start * 1000 < lastSwitchMs) {
        // 检查是否是 slide 切换点（前一个 timestamp 是不同 slide）
        const tsIdx = timestamps.indexOf(ts);
        if (tsIdx > 0 && timestamps[tsIdx - 1].slide_index !== currentSlideIndex) {
          lastSwitchMs = ts.start * 1000;
        }
      }
    }
  }

  if (lastSwitchMs > 0) {
    const timeSinceSwitch = currentTimeMs - lastSwitchMs;
    if (timeSinceSwitch < FADE_MS) {
      return { opacity: timeSinceSwitch / FADE_MS };
    }
  }

  return { opacity: 1 };
}
