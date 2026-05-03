/**
 * i18n/request.ts — next-intl request configuration.
 *
 * Runs on every request to determine the locale and load the
 * corresponding message JSON files. Locale is resolved from:
 *   1. Cookie `locale` (set by LanguageSelector)
 *   2. Default: 'en'
 *
 * Messages are split by module (common, live, etc.) so each page
 * only loads what it needs while sharing common keys.
 */

import { getRequestConfig } from 'next-intl/server'
import { cookies } from 'next/headers'

const SUPPORTED_LOCALES = ['en', 'zh'] as const
type SupportedLocale = (typeof SUPPORTED_LOCALES)[number]
const DEFAULT_LOCALE: SupportedLocale = 'en'

export default getRequestConfig(async () => {
  const store = await cookies()
  const raw = store.get('locale')?.value
  const locale: SupportedLocale =
    raw && SUPPORTED_LOCALES.includes(raw as SupportedLocale)
      ? (raw as SupportedLocale)
      : DEFAULT_LOCALE

  // Merge per-module JSON files into a single messages object.
  // Each module becomes a namespace: useTranslations('live'), useTranslations('common')
  const common = (await import(`../../messages/${locale}/common.json`)).default
  const live = (await import(`../../messages/${locale}/live.json`)).default

  return {
    locale,
    messages: { common, live },
  }
})
