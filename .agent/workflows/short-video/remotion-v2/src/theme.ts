/* ── 短视频 v2 主题 — 大博主字体方案 ── */

export interface ThemeConfig {
  bgPrimary: string;
  bgSecondary: string;
  bgGradient: string;
  bgCover: string;
  accent: string;
  accentLight: string;
  accentSecondary: string;
  accentMuted: string;
  textPrimary: string;
  textSecondary: string;
  textMuted: string;
  tableHeaderBg: string;
  tableHeaderText: string;
  tableRowOdd: string;
  tableRowEven: string;
  tableBorder: string;
  citationBg: string;
  citationBorder: string;
  citationText: string;
  subtitleBg: string;
  subtitleText: string;
  subtitleHighlight: string;
  sourceText: string;

  /* ── 字体 — 分场景 ── */
  /** 数字/英文标题: Montserrat Black — 几何感强，数字醒目 */
  fontNumber: string;
  /** 中文标题: Noto Sans SC Black — 笔画饱满，力量感 */
  fontHeading: string;
  /** 正文/表格: Noto Sans SC Medium — 清晰易读 */
  fontBody: string;
  /** 字幕: Noto Sans SC Bold — 醒目但不抢幻灯片 */
  fontSubtitle: string;
  /** 向后兼容: 默认 fontFamily (正文) */
  fontFamily: string;

  /* ── 尺寸（px） ── */
  width: number;
  totalHeight: number;
  chapterHeight: number;
  slideHeight: number;
  subtitleHeight: number;
}

/* ── 字体栈 ── */
const fonts = {
  /** 数字/英文标题 — Montserrat 几何无衬线，数字特别好看 */
  number:   "'Montserrat', 'Noto Sans SC', system-ui, sans-serif",
  /** 中文大标题 — Noto Sans SC 搭配 900 weight */
  heading:  "'Noto Sans SC', 'Montserrat', system-ui, sans-serif",
  /** 正文/表格 — 易读为主 */
  body:     "'Noto Sans SC', 'Montserrat', system-ui, sans-serif",
  /** 字幕条 */
  subtitle: "'Noto Sans SC', 'Montserrat', system-ui, sans-serif",
} as const;

/* ── 共享尺寸 ── */
const shared = {
  fontNumber: fonts.number,
  fontHeading: fonts.heading,
  fontBody: fonts.body,
  fontSubtitle: fonts.subtitle,
  fontFamily: fonts.body,  // 向后兼容
  width: 1920,
  totalHeight: 1080,
  chapterHeight: 48,
  slideHeight: 872,
  subtitleHeight: 160,
} as const;

export const themePresets: Record<string, ThemeConfig> = {
  gold: {
    ...shared,
    bgPrimary: '#1a1a35', bgSecondary: '#24243e', bgGradient: '#1a1a35', bgCover: '#1a1a35',
    accent: '#FFD700', accentLight: '#FFE44D', accentSecondary: '#00D2FF', accentMuted: '#a0a0b0',
    textPrimary: '#ffffff', textSecondary: 'rgba(255, 255, 255, 0.85)', textMuted: 'rgba(255, 255, 255, 0.25)',
    tableHeaderBg: 'rgba(255, 215, 0, 0.12)', tableHeaderText: '#FFE44D',
    tableRowOdd: 'transparent', tableRowEven: 'transparent', tableBorder: 'rgba(255, 255, 255, 0.15)',
    citationBg: 'rgba(255, 215, 0, 0.06)', citationBorder: 'rgba(255, 215, 0, 0.5)', citationText: 'rgba(255, 255, 255, 0.7)',
    subtitleBg: '#1a1a35', subtitleText: 'rgba(255, 255, 255, 0.3)', subtitleHighlight: '#FFD700',
    sourceText: 'rgba(255, 215, 0, 0.4)',
  },
  ocean: {
    ...shared,
    bgPrimary: '#0a1628', bgSecondary: '#0f1f3d', bgGradient: '#0a1628', bgCover: '#0a1628',
    accent: '#00D4AA', accentLight: '#33EEBB', accentSecondary: '#0095FF', accentMuted: '#6a8faa',
    textPrimary: '#ffffff', textSecondary: 'rgba(255, 255, 255, 0.85)', textMuted: 'rgba(255, 255, 255, 0.25)',
    tableHeaderBg: 'rgba(0, 212, 170, 0.12)', tableHeaderText: '#33EEBB',
    tableRowOdd: 'transparent', tableRowEven: 'transparent', tableBorder: 'rgba(255, 255, 255, 0.15)',
    citationBg: 'rgba(0, 212, 170, 0.06)', citationBorder: 'rgba(0, 212, 170, 0.5)', citationText: 'rgba(255, 255, 255, 0.7)',
    subtitleBg: '#0a1628', subtitleText: 'rgba(255, 255, 255, 0.3)', subtitleHighlight: '#00D4AA',
    sourceText: 'rgba(0, 212, 170, 0.4)',
  },
  sunset: {
    ...shared,
    bgPrimary: '#2a1020', bgSecondary: '#351530', bgGradient: '#2a1020', bgCover: '#2a1020',
    accent: '#FF6B6B', accentLight: '#FF8E8E', accentSecondary: '#FFB347', accentMuted: '#a07080',
    textPrimary: '#ffffff', textSecondary: 'rgba(255, 255, 255, 0.85)', textMuted: 'rgba(255, 255, 255, 0.25)',
    tableHeaderBg: 'rgba(255, 107, 107, 0.12)', tableHeaderText: '#FF8E8E',
    tableRowOdd: 'transparent', tableRowEven: 'transparent', tableBorder: 'rgba(255, 255, 255, 0.15)',
    citationBg: 'rgba(255, 107, 107, 0.06)', citationBorder: 'rgba(255, 107, 107, 0.5)', citationText: 'rgba(255, 255, 255, 0.7)',
    subtitleBg: '#2a1020', subtitleText: 'rgba(255, 255, 255, 0.3)', subtitleHighlight: '#FF6B6B',
    sourceText: 'rgba(255, 107, 107, 0.4)',
  },
  forest: {
    ...shared,
    bgPrimary: '#0a1f1a', bgSecondary: '#102e25', bgGradient: '#0a1f1a', bgCover: '#0a1f1a',
    accent: '#4ECCA3', accentLight: '#6EE7B7', accentSecondary: '#38BDF8', accentMuted: '#6aa090',
    textPrimary: '#ffffff', textSecondary: 'rgba(255, 255, 255, 0.85)', textMuted: 'rgba(255, 255, 255, 0.25)',
    tableHeaderBg: 'rgba(78, 204, 163, 0.12)', tableHeaderText: '#6EE7B7',
    tableRowOdd: 'transparent', tableRowEven: 'transparent', tableBorder: 'rgba(255, 255, 255, 0.15)',
    citationBg: 'rgba(78, 204, 163, 0.06)', citationBorder: 'rgba(78, 204, 163, 0.5)', citationText: 'rgba(255, 255, 255, 0.7)',
    subtitleBg: '#0a1f1a', subtitleText: 'rgba(255, 255, 255, 0.3)', subtitleHighlight: '#4ECCA3',
    sourceText: 'rgba(78, 204, 163, 0.4)',
  },
  aurora: {
    ...shared,
    bgPrimary: '#1a1a2e', bgSecondary: '#222244', bgGradient: '#1a1a2e', bgCover: '#1a1a2e',
    accent: '#6C63FF', accentLight: '#8B83FF', accentSecondary: '#E040FB', accentMuted: '#8080a0',
    textPrimary: '#ffffff', textSecondary: 'rgba(255, 255, 255, 0.85)', textMuted: 'rgba(255, 255, 255, 0.25)',
    tableHeaderBg: 'rgba(108, 99, 255, 0.12)', tableHeaderText: '#8B83FF',
    tableRowOdd: 'transparent', tableRowEven: 'transparent', tableBorder: 'rgba(255, 255, 255, 0.15)',
    citationBg: 'rgba(108, 99, 255, 0.06)', citationBorder: 'rgba(108, 99, 255, 0.5)', citationText: 'rgba(255, 255, 255, 0.7)',
    subtitleBg: '#1a1a2e', subtitleText: 'rgba(255, 255, 255, 0.3)', subtitleHighlight: '#6C63FF',
    sourceText: 'rgba(108, 99, 255, 0.4)',
  },
};

export function getTheme(name?: string): ThemeConfig {
  return themePresets[name || 'gold'] || themePresets.gold;
}

export const theme = themePresets.gold;

export function getBaseStyles(t: ThemeConfig = theme) {
  return {
    slideArea: {
      width: t.width,
      height: t.slideHeight,
      position: 'relative' as const,
      overflow: 'hidden' as const,
      background: t.bgGradient,
      padding: '60px 80px 24px',
      fontFamily: t.fontBody,
      display: 'flex',
      flexDirection: 'column' as const,
      justifyContent: 'flex-start' as const,
      alignItems: 'center' as const,
      textAlign: 'center' as const,
    },
    subtitleArea: {
      width: t.width,
      height: t.subtitleHeight,
      background: t.subtitleBg,
      display: 'flex',
      alignItems: 'center' as const,
      justifyContent: 'center' as const,
      fontFamily: t.fontSubtitle,
    },
    /** 标题 — 居中大字，中文用 Black weight */
    heading: {
      fontSize: 56,
      fontWeight: 900 as const,  // Black weight
      fontFamily: t.fontHeading,
      color: t.textPrimary,
      margin: 0,
      marginBottom: 28,
      lineHeight: 1.2,
      textAlign: 'center' as const,
      letterSpacing: 1,
      width: '100%' as const,
    },
  } as const;
}

export const baseStyles = getBaseStyles(theme);
