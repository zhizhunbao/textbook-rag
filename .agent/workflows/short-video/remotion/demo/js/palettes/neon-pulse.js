/* ── 霓虹脉冲 Neon Pulse ── */
PALETTES['neon-pulse'] = {
  id: 'neon-pulse', name: '霓虹脉冲 Neon Pulse',
  description: '赛博朋克风格 — 霓虹渐变、发光边框、扫描线纹理',
  palette: {
    name: '霓虹脉冲',
    bgPrimary: '#0a0a12', bgSecondary: '#12121e',
    bgGradient: 'linear-gradient(180deg, #0a0a12 0%, #12121e 60%, #0a0a12 100%)',
    bgCover: 'linear-gradient(135deg, #0a0a12 0%, #1a0a2e 40%, #0a1a2e 60%, #0a0a12 100%)',
    accent: '#00f0ff', accentLight: '#80f8ff', accentSecondary: '#ff00aa', accentMuted: '#666680',
    textPrimary: '#ffffff', textSecondary: 'rgba(255,255,255,0.85)', textMuted: 'rgba(255,255,255,0.3)',
    tableHeaderBg: 'rgba(0,240,255,0.12)', tableHeaderText: '#00f0ff',
    tableRowOdd: 'rgba(0,240,255,0.04)', tableRowEven: 'rgba(255,0,170,0.03)',
    citationBg: 'rgba(0,240,255,0.06)', citationBorder: 'rgba(0,240,255,0.6)', citationText: 'rgba(255,255,255,0.7)',
    subtitleBg: '#0a0a12', subtitleText: '#ffffff', sourceText: 'rgba(0,240,255,0.4)',
  },
  typography: { titleWeight: 900, coverTitleSize: 76, coverSubtitleSize: 26, bodyFontFamily: "'Inter', 'Noto Sans SC', monospace" },
  decorations: { scanlines: true, glowBorder: true, cornerMarks: true },
};
