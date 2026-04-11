/**
 * chartTheme - Shared Recharts color palette and visual configuration
 *
 * @module shared/config
 */
export const chartTheme = {
  colors: {
    primary: '#2563eb',
    secondary: '#16a34a',
    tertiary: '#dc2626',
    quaternary: '#ca8a04',
    quinary: '#9333ea',
    background: '#ffffff',
    text: '#1f2937',
    grid: '#e5e7eb',
    muted: '#6b7280',
  },
  seriesColors: ['#2563eb', '#16a34a', '#dc2626', '#ca8a04', '#9333ea', '#0891b2'],
  fonts: {
    family: 'Inter, system-ui, sans-serif',
    size: {
      small: 10,
      normal: 12,
      large: 14,
    },
  },
  chart: {
    margin: { top: 5, right: 30, left: 20, bottom: 5 },
    height: 300,
  },
} as const;

export type ChartTheme = typeof chartTheme;
