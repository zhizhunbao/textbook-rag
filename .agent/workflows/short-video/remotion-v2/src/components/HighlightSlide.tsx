import React from 'react';
import { useCurrentFrame, useVideoConfig, interpolate, spring } from 'remotion';
import type { ThemeConfig } from '../theme';
import { getBaseStyles } from '../theme';

/**
 * 全屏金句页 — 大博主风格
 *
 * 字体: Noto Sans SC Black (900) — 最大冲击力
 * 布局: 深色背景 + 居中大字 (72px) + 发光脉冲
 */
export const HighlightSlide: React.FC<{
  content: string;
  theme: ThemeConfig;
}> = ({ content, theme: t }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  // 文字淡入 + 缩放弹性
  const scale = spring({
    frame,
    fps,
    config: { damping: 12, stiffness: 80, mass: 0.8 },
  });

  const opacity = interpolate(frame, [0, 15], [0, 1], {
    extrapolateRight: 'clamp',
  });

  // 发光脉冲动画
  const glowIntensity = interpolate(
    Math.sin(frame / fps * 2 * Math.PI * 0.5),
    [-1, 1],
    [30, 60],
  );

  const styles = getBaseStyles(t);

  return (
    <div style={{
      ...styles.slideArea,
      justifyContent: 'center',
      alignItems: 'center',
      background: t.bgCover,
    }}>
      <div style={{
        transform: `scale(${scale})`,
        opacity,
        textAlign: 'center',
        maxWidth: '85%',
      }}>
        {/* 装饰线 — 上 */}
        <div style={{
          width: 80,
          height: 3,
          background: t.accent,
          margin: '0 auto 40px',
          borderRadius: 2,
          opacity: 0.6,
        }} />

        {/* 金句文字 — Noto Sans SC Black */}
        <p style={{
          fontSize: 72,
          fontWeight: 900,
          fontFamily: t.fontHeading,
          lineHeight: 1.4,
          color: t.accent,
          margin: 0,
          textShadow: `0 0 ${glowIntensity}px ${t.accent}40`,
          letterSpacing: 2,
        }}>
          <span dangerouslySetInnerHTML={{ __html: boldToWhite(content, t) }} />
        </p>

        {/* 装饰线 — 下 */}
        <div style={{
          width: 80,
          height: 3,
          background: t.accent,
          margin: '40px auto 0',
          borderRadius: 2,
          opacity: 0.6,
        }} />
      </div>
    </div>
  );
};

/** **text** → 白色加粗（在金色主文字中突出） */
function boldToWhite(text: string, t: ThemeConfig): string {
  return text.replace(
    /\*\*(.+?)\*\*/g,
    `<strong style="color:${t.textPrimary};font-weight:900">$1</strong>`,
  );
}
