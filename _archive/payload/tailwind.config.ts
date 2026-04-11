import type { Config } from 'tailwindcss'

const config: Config = {
  content: [
    './src/**/*.{js,ts,jsx,tsx,mdx}',
  ],
  theme: {
    extend: {
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
        mono: ['JetBrains Mono', 'Fira Code', 'monospace'],
      },
      colors: {
        surface: {
          50:  '#f8f9fc',
          100: '#f0f2f8',
          200: '#e4e7f0',
          300: '#c9cfe0',
          700: '#3b4060',
          800: '#252840',
          900: '#161826',
          950: '#0d0f1a',
        },
        brand: {
          300: '#93c5fd',
          400: '#60a5fa',
          500: '#3b82f6',
          600: '#2563eb',
          700: '#1d4ed8',
        },
        accent: {
          400: '#a78bfa',
          500: '#8b5cf6',
        },
        warn: '#f59e0b',
        danger: '#ef4444',
        success: '#10b981',
      },
    },
  },
  plugins: [],
}

export default config
