/**
 * data-sources-persona/healthcare.ts — Data sources for 3 healthcare personas.
 */
import type { PersonaDataSource } from './types'

export const healthcareSources: PersonaDataSource[] = [
  // ── health-insurance (2) ──────────────────────────────────
  {
    nameEn: 'OHIP Application',
    nameZh: '安省医保 (OHIP) 申请',
    description: 'How to apply for OHIP and get an Ontario health card.',
    discoveryUrl: 'https://www.ontario.ca/page/apply-ohip-and-get-health-card',
    type: 'web_scrape',
    enabled: true,
    autoSync: true,
    syncInterval: 'monthly',
    _personaSlug: 'health-insurance',
  },
  {
    nameEn: 'Ontario UHIP for International Students',
    nameZh: '安省留学生医保 (UHIP)',
    description: 'University Health Insurance Plan — coverage for international students.',
    discoveryUrl: 'https://uhip.ca/',
    type: 'web_scrape',
    enabled: true,
    autoSync: true,
    syncInterval: 'monthly',
    _personaSlug: 'health-insurance',
  },
  // ── health-mental (2) ─────────────────────────────────────
  {
    nameEn: 'CMHA Ontario Mental Health',
    nameZh: '加拿大心理健康协会安省分会 (CMHA)',
    description: 'Canadian Mental Health Association Ontario — resources and programs.',
    discoveryUrl: 'https://ontario.cmha.ca/',
    type: 'web_scrape',
    enabled: true,
    autoSync: true,
    syncInterval: 'monthly',
    _personaSlug: 'health-mental',
  },
  {
    nameEn: 'Ontario Mental Health Support',
    nameZh: '安省心理健康服务',
    description: 'Ontario government mental health services and support programs.',
    discoveryUrl: 'https://www.ontario.ca/page/mental-health-services',
    type: 'web_scrape',
    enabled: true,
    autoSync: true,
    syncInterval: 'monthly',
    _personaSlug: 'health-mental',
  },
  // ── health-childcare (2) ──────────────────────────────────
  {
    nameEn: 'Ontario Child Care Subsidies',
    nameZh: '安省托儿费补贴',
    description: 'Ontario child care fee subsidies and eligibility.',
    discoveryUrl: 'https://www.ontario.ca/page/child-care-subsidies',
    type: 'web_scrape',
    enabled: true,
    autoSync: true,
    syncInterval: 'monthly',
    _personaSlug: 'health-childcare',
  },
  {
    nameEn: 'Canada Child Benefit',
    nameZh: '加拿大儿童福利金 (CCB)',
    description: 'Canada Child Benefit — eligibility, amounts, and payment schedule.',
    discoveryUrl: 'https://www.canada.ca/en/revenue-agency/services/child-family-benefits/canada-child-benefit-overview.html',
    type: 'web_scrape',
    enabled: true,
    autoSync: true,
    syncInterval: 'monthly',
    _personaSlug: 'health-childcare',
  },
]
