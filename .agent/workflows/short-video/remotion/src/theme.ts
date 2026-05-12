/* ── 短视频深色主题 (参考 remotion-templates 标准配色) ── */

export const theme = {
  /* ── 背景 (模板标准: #111827 → #1f2937) ── */
  bgPrimary:   '#111827',
  bgSecondary: '#1f2937',
  bgGradient:  'linear-gradient(180deg, #111827 0%, #1f2937 100%)',
  bgCover:     'linear-gradient(135deg, #111827 0%, #1a2744 50%, #111827 100%)',

  /* ── 蓝色主色 (模板标准: #3b82f6) ── */
  blue:        '#3b82f6',
  blueLight:   '#60a5fa',
  blueMuted:   '#9ca3af',

  /* ── 文字 ── */
  textPrimary:   '#ffffff',
  textSecondary: 'rgba(255, 255, 255, 0.8)',
  textMuted:     'rgba(255, 255, 255, 0.25)',

  /* ── 表格 ── */
  tableHeaderBg:   'rgba(59, 130, 246, 0.2)',
  tableHeaderText: '#60a5fa',
  tableRowOdd:     'rgba(255, 255, 255, 0.04)',
  tableRowEven:    'rgba(255, 255, 255, 0.02)',
  tableBorder:     'rgba(255, 255, 255, 0.06)',

  /* ── 引用块 ── */
  citationBg:     'rgba(255, 255, 255, 0.05)',
  citationBorder: 'rgba(59, 130, 246, 0.5)',
  citationText:   'rgba(255, 255, 255, 0.65)',

  /* ── 字幕条 ── */
  subtitleBg:        'rgba(0, 0, 0, 0.6)',
  subtitleText:      'rgba(255, 255, 255, 0.3)',
  subtitleHighlight: '#ffffff',

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
  /** 幻灯片区域 — 全部居中，上下摞起来 */
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

  /** 字幕条 — 半透明黑底 */
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
    fontSize: 52,
    fontWeight: 800 as const,
    color: theme.textPrimary,
    margin: 0,
    marginBottom: 32,
    lineHeight: 1.2,
    textAlign: 'center' as const,
    letterSpacing: 0.5,
    width: '100%' as const,
  },
} as const;
