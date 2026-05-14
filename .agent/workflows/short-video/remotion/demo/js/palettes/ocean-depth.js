/* ── 深海蔚蓝 Ocean Depth ── */
PALETTES['ocean-depth'] = {
  id: 'ocean-depth', name: '深海蔚蓝 Ocean Depth',
  description: '海洋深度感 — 蓝绿渐变、波纹纹理、水下光线',
  palette: {
    name: '深海蔚蓝',
    bgPrimary: '#0a1628', bgSecondary: '#0f2040',
    bgGradient: 'linear-gradient(180deg, #0a1628 0%, #0f2040 60%, #0a1628 100%)',
    bgCover: 'radial-gradient(ellipse at 50% 80%, rgba(6,182,212,0.1) 0%, transparent 60%), linear-gradient(180deg, #0a1628 0%, #0f2040 100%)',
    accent: '#06b6d4', accentLight: '#22d3ee', accentSecondary: '#2dd4bf', accentMuted: '#64748b',
    textPrimary: '#e0f2fe', textSecondary: 'rgba(224,242,254,0.85)', textMuted: 'rgba(224,242,254,0.25)',
    tableHeaderBg: 'rgba(6,182,212,0.15)', tableHeaderText: '#22d3ee',
    tableRowOdd: 'rgba(6,182,212,0.04)', tableRowEven: 'rgba(45,212,191,0.04)',
    citationBg: 'rgba(6,182,212,0.06)', citationBorder: 'rgba(6,182,212,0.5)', citationText: 'rgba(224,242,254,0.65)',
    subtitleBg: '#0a1628', subtitleText: '#e0f2fe', sourceText: 'rgba(34,211,238,0.4)',
  },
  typography: { titleWeight: 700, coverTitleSize: 70, coverSubtitleSize: 30, bodyFontFamily: "'Inter', 'Noto Sans SC', system-ui, sans-serif" },
  decorations: { caustics: true, wavePattern: true, depthFade: true },
};
