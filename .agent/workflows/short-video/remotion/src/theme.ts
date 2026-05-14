/* ── 短视频主题 — competitor-gold (深靛蓝底+金色强调) ── */

export const theme = {
  /* ── 背景 ── */
  bgPrimary:   '#1a1a35',
  bgSecondary: '#24243e',
  bgGradient:  '#1a1a35',
  bgCover:     '#1a1a35',

  /* ── 金色主色 ── */
  accent:        '#FFD700',
  accentLight:   '#FFE44D',
  accentSecondary: '#00D2FF',
  accentMuted:   '#a0a0b0',

  /* ── 文字 ── */
  textPrimary:   '#ffffff',
  textSecondary: 'rgba(255, 255, 255, 0.85)',
  textMuted:     'rgba(255, 255, 255, 0.25)',

  /* ── 表格 ── */
  tableHeaderBg:   'rgba(255, 215, 0, 0.12)',
  tableHeaderText: '#FFE44D',
  tableRowOdd:     'transparent',
  tableRowEven:    'transparent',
  tableBorder:     'rgba(255, 255, 255, 0.15)',

  /* ── 引用块 ── */
  citationBg:     'rgba(255, 215, 0, 0.06)',
  citationBorder: 'rgba(255, 215, 0, 0.5)',
  citationText:   'rgba(255, 255, 255, 0.7)',

  /* ── 字幕条 ── */
  subtitleBg:        '#1a1a35',
  subtitleText:      'rgba(255, 255, 255, 0.3)',
  subtitleHighlight: '#FFD700',

  /* ── 来源水印 ── */
  sourceText: 'rgba(255, 215, 0, 0.4)',

  /* ── 字体 ── */
  fontFamily: "'Inter', 'Noto Sans SC', system-ui, sans-serif",

  /* ── 尺寸（px） ── */
  width:          1920,
  totalHeight:    1080,
  slideHeight:    880,
  subtitleHeight: 200,
} as const;

/* ── 可复用的样式片段 ── */
export const baseStyles = {
  /** 幻灯片区域 */
  slideArea: {
    width: theme.width,
    height: theme.slideHeight,
    position: 'relative' as const,
    overflow: 'hidden' as const,
    background: theme.bgGradient,
    padding: '60px 80px 24px',
    fontFamily: theme.fontFamily,
    display: 'flex',
    flexDirection: 'column' as const,
    justifyContent: 'center' as const,
    alignItems: 'center' as const,
    textAlign: 'center' as const,
  },

  /** 字幕条 — 深色底 */
  subtitleArea: {
    width: theme.width,
    height: theme.subtitleHeight,
    background: theme.subtitleBg,
    display: 'flex',
    alignItems: 'center' as const,
    justifyContent: 'center' as const,
    fontFamily: theme.fontFamily,
  },

  /** 标题 — 居中大字 */
  heading: {
    fontSize: 48,
    fontWeight: 800 as const,
    color: theme.textPrimary,
    margin: 0,
    marginBottom: 28,
    lineHeight: 1.2,
    textAlign: 'center' as const,
    letterSpacing: 0.5,
    width: '100%' as const,
  },
} as const;
