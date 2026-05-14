/* ── 烬火流光 Ember Glow ── */
PALETTES['ember-glow'] = {
  id: 'ember-glow', name: '烬火流光 Ember Glow',
  description: '温暖电影感 — 橙金渐变、暖色光晕、质感纹理',
  palette: {
    name: '烬火流光',
    bgPrimary: '#1a1008', bgSecondary: '#2a1a0e',
    bgGradient: 'linear-gradient(180deg, #1a1008 0%, #2a1a0e 100%)',
    bgCover: 'radial-gradient(ellipse at 50% 60%, rgba(251,146,60,0.12) 0%, transparent 70%), linear-gradient(135deg, #1a1008 0%, #2a1a0e 50%, #1a1008 100%)',
    accent: '#f97316', accentLight: '#fb923c', accentSecondary: '#fbbf24', accentMuted: '#a3a3a3',
    textPrimary: '#fef3c7', textSecondary: 'rgba(254,243,199,0.85)', textMuted: 'rgba(254,243,199,0.25)',
    tableHeaderBg: 'rgba(249,115,22,0.15)', tableHeaderText: '#fb923c',
    tableRowOdd: 'rgba(249,115,22,0.05)', tableRowEven: 'rgba(251,191,36,0.04)',
    citationBg: 'rgba(249,115,22,0.08)', citationBorder: 'rgba(249,115,22,0.5)', citationText: 'rgba(254,243,199,0.65)',
    subtitleBg: '#1a1008', subtitleText: '#fef3c7', sourceText: 'rgba(251,146,60,0.4)',
  },
  typography: { titleWeight: 800, coverTitleSize: 72, coverSubtitleSize: 28, bodyFontFamily: "'Inter', 'Noto Sans SC', Georgia, serif" },
  decorations: { warmGlow: true, grainTexture: true, gradientBorders: true },
};
