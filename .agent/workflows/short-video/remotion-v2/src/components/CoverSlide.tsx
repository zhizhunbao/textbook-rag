import React from 'react';
import type { ThemeConfig } from '../theme';
import { getBaseStyles } from '../theme';

/**
 * 封面页 — 简洁版，无动画特效
 *
 * 布局:
 *   钩子大数字 (Montserrat Black)
 *   钩子单位
 *   主标题 (Noto Sans SC Black)
 *   副标题
 */
export const CoverSlide: React.FC<{
  title: string;
  subtitle?: string;
  hookNumber?: string;
  hookUnit?: string;
  source?: string;
  theme: ThemeConfig;
}> = ({ title, subtitle, hookNumber, hookUnit, source, theme: t }) => {
  const styles = getBaseStyles(t);

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
        {/* 钩子大数字 */}
        {hookNumber && (
          <div style={{
            fontSize: 200, fontWeight: 900,
            fontFamily: t.fontNumber,
            color: t.accent,
            lineHeight: 1, marginBottom: 8,
            letterSpacing: -4,
          }}>
            {hookNumber}
          </div>
        )}

        {/* 钩子单位 */}
        {hookUnit && (
          <div style={{
            fontSize: 34, color: t.accentLight,
            fontFamily: t.fontNumber,
            fontWeight: 600, letterSpacing: 4,
            textTransform: 'uppercase' as const,
            marginBottom: 20,
          }}>
            {hookUnit}
          </div>
        )}

        {/* 主标题 */}
        <h1 style={{
          fontSize: 80, fontWeight: 900, lineHeight: 1.15,
          fontFamily: t.fontHeading,
          color: t.textPrimary,
          letterSpacing: 2, margin: 0,
          textAlign: 'center',
        }}>
          {title}
        </h1>

        {/* 副标题 */}
        {subtitle && (
          <p style={{
            fontSize: 32, color: t.accentLight,
            fontFamily: t.fontBody,
            fontWeight: 500,
            marginTop: 20, letterSpacing: 1,
            textAlign: 'center',
          }}>
            {subtitle}
          </p>
        )}
      </div>
    </div>
  );
};
