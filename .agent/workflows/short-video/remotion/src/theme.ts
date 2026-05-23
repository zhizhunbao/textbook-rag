/* ── 短视频主题 — 多主题预设系统 ── */

/** 单套主题的类型定义 */
export interface ThemeConfig {
  /* ── 背景 ── */
  bgPrimary: string;
  bgSecondary: string;
  bgGradient: string;
  bgCover: string;

  /* ── 主色 ── */
  accent: string;
  accentLight: string;
  accentSecondary: string;
  accentMuted: string;

  /* ── 文字 ── */
  textPrimary: string;
  textSecondary: string;
  textMuted: string;

  /* ── 表格 ── */
  tableHeaderBg: string;
  tableHeaderText: string;
  tableRowOdd: string;
  tableRowEven: string;
  tableBorder: string;

  /* ── 引用块 ── */
  citationBg: string;
  citationBorder: string;
  citationText: string;

  /* ── 字幕条 ── */
  subtitleBg: string;
  subtitleText: string;
  subtitleHighlight: string;

  /* ── 来源水印 ── */
  sourceText: string;

  /* ── 字体 ── */
  fontFamily: string;

  /* ── 尺寸（px） ── */
  width: number;
  totalHeight: number;
  chapterHeight: number;
  slideHeight: number;
  subtitleHeight: number;
}

/* ── 共享尺寸和字体 ── */
const shared = {
  fontFamily: "'Inter', 'Noto Sans SC', system-ui, sans-serif",
  width: 1920,
  totalHeight: 1080,
  chapterHeight: 48,
  slideHeight: 832,
  subtitleHeight: 200,
} as const;

/* ── 主题预设 ── */
export const themePresets: Record<string, ThemeConfig> = {
  /** 默认：深靛蓝 + 金色 (现有风格) */
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

  /** 海洋：深海蓝 + 青色 — 移民/签证 */
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

  /** 日落：深紫红 + 珊瑚橙 — 财务/税务 */
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

  /** 森林：深绿 + 翠绿 — 住房/生活 */
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

  /** 极光：深灰蓝 + 紫蓝 — 教育/技能 */
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

/** 根据主题名获取主题配置，默认 gold */
export function getTheme(name?: string): ThemeConfig {
  return themePresets[name || 'gold'] || themePresets.gold;
}

/* ── 默认主题（向后兼容） ── */
export const theme = themePresets.gold;

/* ── 可复用的样式片段 ── */
export function getBaseStyles(t: ThemeConfig = theme) {
  return {
    /** 幻灯片区域 */
    slideArea: {
      width: t.width,
      height: t.slideHeight,
      position: 'relative' as const,
      overflow: 'hidden' as const,
      background: t.bgGradient,
      padding: '60px 80px 24px',
      fontFamily: t.fontFamily,
      display: 'flex',
      flexDirection: 'column' as const,
      justifyContent: 'flex-start' as const,
      alignItems: 'center' as const,
      textAlign: 'center' as const,
    },

    /** 字幕条 — 深色底 */
    subtitleArea: {
      width: t.width,
      height: t.subtitleHeight,
      background: t.subtitleBg,
      display: 'flex',
      alignItems: 'center' as const,
      justifyContent: 'center' as const,
      fontFamily: t.fontFamily,
    },

    /** 标题 — 居中大字 */
    heading: {
      fontSize: 56,
      fontWeight: 800 as const,
      color: t.textPrimary,
      margin: 0,
      marginBottom: 28,
      lineHeight: 1.2,
      textAlign: 'center' as const,
      letterSpacing: 0.5,
      width: '100%' as const,
    },
  } as const;
}

/** 向后兼容：默认 baseStyles */
export const baseStyles = getBaseStyles(theme);
