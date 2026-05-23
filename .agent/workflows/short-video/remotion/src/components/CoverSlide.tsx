import React from 'react';
import { useCurrentFrame, useVideoConfig, interpolate, spring } from 'remotion';
import type { ThemeConfig } from '../theme';
import { getBaseStyles } from '../theme';

/**
 * 封面页 — 带弹性动画
 *
 * 动画:
 *   钩子大数字: spring 弹出 + 发光脉冲
 *   标题: 从下方滑入 + fade in
 *   副标题: 延迟 fade in
 */
export const CoverSlide: React.FC<{
  title: string;
  subtitle?: string;
  hookNumber?: string;
  hookUnit?: string;
  source?: string;
  theme: ThemeConfig;
}> = ({ title, subtitle, hookNumber, hookUnit, source, theme: t }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const styles = getBaseStyles(t);

  // ── 钩子数字弹出动画 ──
  const numberScale = spring({
    frame,
    fps,
    config: { damping: 10, stiffness: 100, mass: 0.6 },
  });

  const numberOpacity = interpolate(frame, [0, 8], [0, 1], {
    extrapolateRight: 'clamp',
  });

  // 发光强度脉冲
  const glowIntensity = interpolate(
    Math.sin(frame / fps * 2 * Math.PI * 0.3),
    [-1, 1],
    [40, 80],
  );

  // ── 单位文字 fade in ──
  const unitOpacity = interpolate(frame, [8, 18], [0, 1], {
    extrapolateRight: 'clamp',
  });

  // ── 标题从下方滑入 ──
  const titleY = interpolate(frame, [10, 25], [30, 0], {
    extrapolateRight: 'clamp',
  });
  const titleOpacity = interpolate(frame, [10, 25], [0, 1], {
    extrapolateRight: 'clamp',
  });

  // ── 副标题延迟 fade in ──
  const subOpacity = interpolate(frame, [20, 35], [0, 1], {
    extrapolateRight: 'clamp',
  });

  return (
    <div style={{
      ...styles.slideArea,
      background: t.bgCover,
      justifyContent: 'center',
      alignItems: 'center',
      textAlign: 'center',
    }}>
      <div style={{
        display: 'flex', flexDirection: 'column',
        alignItems: 'center', justifyContent: 'center', width: '100%',
      }}>
        {/* 钩子大数字 — 弹出 + 发光 */}
        {hookNumber && (
          <div style={{
            fontSize: 200, fontWeight: 900,
            color: t.accent,
            lineHeight: 1, marginBottom: 8,
            textShadow: `0 0 ${glowIntensity}px ${t.accent}40`,
            transform: `scale(${numberScale})`,
            opacity: numberOpacity,
          }}>
            {hookNumber}
          </div>
        )}

        {/* 钩子单位 */}
        {hookUnit && (
          <div style={{
            fontSize: 32, color: t.accentLight,
            fontWeight: 600, letterSpacing: 3, marginBottom: 16,
            opacity: unitOpacity,
          }}>
            {hookUnit}
          </div>
        )}

        {/* 主标题 — 从下方滑入 */}
        <h1 style={{
          fontSize: 80, fontWeight: 800, lineHeight: 1.15,
          color: t.textPrimary,
          letterSpacing: 1, margin: 0,
          textAlign: 'center',
          transform: `translateY(${titleY}px)`,
          opacity: titleOpacity,
        }}>
          {title}
        </h1>

        {/* 副标题 — 延迟 fade in */}
        {subtitle && (
          <p style={{
            fontSize: 32, color: t.accentLight,
            marginTop: 20, fontWeight: 400, letterSpacing: 1,
            textAlign: 'center',
            opacity: subOpacity,
          }}>
            {subtitle}
          </p>
        )}
      </div>
    </div>
  );
};
