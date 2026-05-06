'use client'

import { useI18n } from '@/features/shared/i18n'

/**
 * LanguageToggle — English / Chinese switch button
 * Can be placed anywhere, click to toggle language.
 */
export default function LanguageToggle({ className = '', style }: { className?: string; style?: React.CSSProperties }) {
  const { locale, toggleLocale } = useI18n()

  return (
    <button
      onClick={toggleLocale}
      className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold transition-all duration-200 ${className}`}
      style={style}
      title={locale === 'en' ? '切换到中文' : 'Switch to English'}
      aria-label={locale === 'en' ? '切换到中文' : 'Switch to English'}
    >
      <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <circle cx="12" cy="12" r="10" />
        <line x1="2" y1="12" x2="22" y2="12" />
        <path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z" />
      </svg>
      {locale === 'en' ? 'ZH' : 'EN'}
    </button>
  )
}

