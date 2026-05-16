import React from 'react';
import { theme, baseStyles } from '../theme';

/**
 * 封面页 — competitor-gold 风格
 *
 * 布局:
 *   钩子大数字 (200px 金色)
 *   钩子单位 (32px)
 *   主标题 (80px 白色)
 *   副标题 (32px 金色淡)
 */
export const CoverSlide: React.FC<{
  title: string;
  subtitle?: string;
  hookNumber?: string;
  hookUnit?: string;
  source?: string;
}> = ({ title, subtitle, hookNumber, hookUnit, source }) => (
  <div style={{
    ...baseStyles.slideArea,
    background: theme.bgCover,
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
          color: theme.accent,
          lineHeight: 1, marginBottom: 8,
          textShadow: `0 0 60px ${theme.accent}40`,
        }}>
          {hookNumber}
        </div>
      )}

      {/* 钩子单位 */}
      {hookUnit && (
        <div style={{
          fontSize: 32, color: theme.accentLight,
          fontWeight: 600, letterSpacing: 3, marginBottom: 16,
        }}>
          {hookUnit}
        </div>
      )}

      {/* 主标题 */}
      <h1 style={{
        fontSize: 80, fontWeight: 800, lineHeight: 1.15,
        color: theme.textPrimary,
        letterSpacing: 1, margin: 0,
        textAlign: 'center',
      }}>
        {title}
      </h1>

      {/* 副标题 */}
      {subtitle && (
        <p style={{
          fontSize: 32, color: theme.accentLight,
          marginTop: 20, fontWeight: 400, letterSpacing: 1,
          textAlign: 'center',
        }}>
          {subtitle}
        </p>
      )}
    </div>

    {/* 来源 URL 水印 */}
    {source && (
      <div style={{
        position: 'absolute', top: 20, right: 30,
        fontSize: 24, color: theme.sourceText,
        fontFamily: "'Inter', monospace",
      }}>
        {source}
      </div>
    )}
  </div>
);
