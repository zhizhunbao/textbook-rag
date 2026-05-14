/* ── 霜冻玻璃 Frost Glass ── */
PALETTES['frost-glass'] = {
  id: 'frost-glass', name: '霜冻玻璃 Frost Glass',
  description: '玻璃拟态风格 — 模糊背景、半透明面板、柔和光效',
  palette: {
    name: '霜冻玻璃',
    bgPrimary: '#0f172a', bgSecondary: '#1e293b',
    bgGradient: 'linear-gradient(135deg, #0f172a 0%, #1e293b 50%, #0f172a 100%)',
    bgCover: 'radial-gradient(ellipse at 30% 40%, rgba(99,102,241,0.15) 0%, transparent 60%), linear-gradient(135deg, #0f172a 0%, #1e293b 100%)',
    accent: '#818cf8', accentLight: '#a5b4fc', accentSecondary: '#c084fc', accentMuted: '#94a3b8',
    textPrimary: '#f1f5f9', textSecondary: 'rgba(241,245,249,0.8)', textMuted: 'rgba(241,245,249,0.25)',
    tableHeaderBg: 'rgba(129,140,248,0.15)', tableHeaderText: '#a5b4fc',
    tableRowOdd: 'rgba(255,255,255,0.03)', tableRowEven: 'rgba(129,140,248,0.04)',
    citationBg: 'rgba(255,255,255,0.04)', citationBorder: 'rgba(129,140,248,0.5)', citationText: 'rgba(241,245,249,0.65)',
    subtitleBg: '#0f172a', subtitleText: '#f1f5f9', sourceText: 'rgba(165,180,252,0.4)',
  },
  typography: { titleWeight: 700, coverTitleSize: 70, coverSubtitleSize: 28, bodyFontFamily: "'Inter', 'Noto Sans SC', system-ui, sans-serif" },
  decorations: { glassPanels: true, blurOrbs: true, softShadows: true },
};
