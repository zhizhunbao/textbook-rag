import React from 'react';
import { theme, baseStyles } from '../theme';

/**
 * 封面页 — 居中大标题
 */
export const CoverSlide: React.FC<{ title: string; subtitle?: string; source: string }> = ({
  title, subtitle, source,
}) => (
  <div style={{
    ...baseStyles.slideArea,
    justifyContent: 'center',
    alignItems: 'center',
    textAlign: 'center',
  }}>
    <h1 style={{
      fontSize: 72, fontWeight: 800, lineHeight: 1.2,
      color: theme.textPrimary,
      letterSpacing: 1, margin: 0,
      textAlign: 'center',
    }}>
      {title}
    </h1>

    {subtitle && (
      <p style={{
        fontSize: 30, color: theme.blueMuted,
        marginTop: 24, fontWeight: 400, letterSpacing: 1,
        textAlign: 'center',
      }}>
        {subtitle}
      </p>
    )}

    {/* 来源 URL — 底部居中显示完整 */}
    {source && (
      <div style={{
        fontSize: 18,
        color: 'rgba(255, 255, 255, 0.35)',
        marginTop: 32,
        textAlign: 'center',
        wordBreak: 'break-all' as const,
        maxWidth: '90%',
        lineHeight: 1.4,
        fontFamily: "'Inter', monospace",
      }}>
        {source}
      </div>
    )}
  </div>
);
