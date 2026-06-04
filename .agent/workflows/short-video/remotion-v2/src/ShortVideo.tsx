import React from 'react';
import { AbsoluteFill, Audio, useCurrentFrame, useVideoConfig, interpolate } from 'remotion';
import { getTheme } from './theme';
import type { VideoProps, TimestampEntry, SlideData, RevealState } from './types';
import type { ThemeConfig } from './theme';
import { CoverSlide } from './components/CoverSlide';
import { ContentSlide } from './components/ContentSlide';
import { HighlightSlide } from './components/HighlightSlide';
import { EvidenceSlide } from './components/EvidenceSlide';
import { SubtitleBar } from './components/SubtitleBar';
import { ChapterTimeline } from './components/ChapterTimeline';
import { getRevealState } from './utils/progressive';
import { ensureFontsLoaded } from './fonts';

/**
 * v2.4 短视频主组件 — 直切过渡
 *
 * 核心变化 vs v2.3:
 *   1. 去掉 crossfade 淡入淡出，slide 切换为瞬切 (像 PPT)
 *   2. 保留 ContentSlide 完整表格渲染
 *   3. 保留 RevealState 逐元素揭示
 *   4. 保留卡拉OK逐词高亮字幕
 */
export const ShortVideo: React.FC<VideoProps> = ({ slides, timestamps, audioUrl, chapters, themeName }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const currentTimeMs = (frame / fps) * 1000;

  const t = getTheme(themeName);

  // ── 确保 Google Fonts 已加载 (Montserrat + Noto Sans SC heavy weights) ──
  ensureFontsLoaded();

  // ── 确定当前 slide ──
  const slideIndex = getCurrentSlideIndex(timestamps, currentTimeMs);
  const slideData: SlideData | undefined = slides[slideIndex];

  // ── v2 核心: 计算当前 slide 的揭示状态 ──
  const reveal = getRevealState(timestamps, slideIndex, currentTimeMs);

  // ── slide 切换过渡 (crossfade) ──
  const transitionInfo = getSlideTransition(timestamps, currentTimeMs, slideIndex);

  // ── 语言检测 ──
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

      {/* ── 幻灯片区域 ── 带 crossfade 过渡 */}
      <div style={{
        position: 'absolute', top: t.chapterHeight, left: 0,
        width: t.width, height: t.slideHeight,
        overflow: 'hidden',
        opacity: transitionInfo.opacity,
      }}>
        {slideData ? renderSlide(slideData, t, reveal) : <FallbackSlide theme={t} />}
      </div>

      {/* ── v2 字幕条 — 卡拉OK逐词高亮 ── */}
      <div style={{
        position: 'absolute',
        top: t.chapterHeight + t.slideHeight,
        left: 0,
        width: t.width, height: t.subtitleHeight,
      }}>
        <SubtitleBar timestamps={timestamps} theme={t} />
        {/* 品牌水印 */}
        {slideData?.source && (
          <div style={{
            position: 'absolute', bottom: 10, right: 24,
            fontSize: 20,
            color: 'rgba(255, 255, 255, 0.3)',
            fontFamily: t.fontNumber,
          }}>
            {slideData.source}
          </div>
        )}
        {/* 免责声明 */}
        <div style={{
          position: 'absolute', bottom: 10, left: 24,
          fontSize: 16,
          color: 'rgba(255, 255, 255, 0.2)',
          fontFamily: t.fontBody,
        }}>
          {disclaimer}
        </div>
      </div>

      {/* ── 音频 ── */}
      <Audio src={audioUrl} />
    </AbsoluteFill>
  );
};

/* ── 根据 slide type 渲染 ── */
function renderSlide(slide: SlideData, t: ThemeConfig, reveal: RevealState): React.ReactNode {
  if (slide.type === 'cover') {
    // cover 有截图：先展示封面标题，到第3句台词才切到证据截图
    // triggerLine 通常是 1 (第一个引用)，但 cover 需要先展示标题钩子
    // 至少等到第 3 句台词开始说时再切 (给标题足够展示时间)
    if (slide.cropImages && slide.cropImages.length > 0) {
      const coverMinTrigger = Math.max(slide.cropImages[0].triggerLine, 3);
      if (reveal.spokenLines >= coverMinTrigger) {
        return <EvidenceSlide
          title={slide.title}
          cropImages={slide.cropImages}
          theme={t}
          reveal={reveal}
        />;
      }
    }
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
  // 有截图证据的 slide → EvidenceSlide
  if (slide.cropImages && slide.cropImages.length > 0) {
    return <EvidenceSlide
      title={slide.title}
      cropImages={slide.cropImages}
      theme={t}
      reveal={reveal}
    />;
  }
  // 其他类型用 ContentSlide
  return <ContentSlide slide={slide} theme={t} />;
}

const FallbackSlide: React.FC<{ theme: ThemeConfig }> = ({ theme: t }) => (
  <div style={{
    width: t.width,
    height: t.slideHeight,
    background: t.bgPrimary,
  }} />
);

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
 * slide 切换过渡 — 直切 (no fade)
 *
 * v2.5: 去掉 fade out/in，消除切换时的黑屏闪烁。
 * 幻灯片瞬间切换，像 PPT 一样。
 */
function getSlideTransition(
  _timestamps: TimestampEntry[],
  _currentTimeMs: number,
  _currentSlideIndex: number,
): { opacity: number } {
  return { opacity: 1 };
}
