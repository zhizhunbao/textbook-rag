/**
 * data-sources-persona/legal.ts — Data sources for 4 legal personas.
 */
import type { PersonaDataSource } from './types'

export const legalSources: PersonaDataSource[] = [
  // ── legal-labor (2) ───────────────────────────────────────
  {
    nameEn: 'Ontario Employment Standards Act',
    nameZh: '安省就业标准法 (ESA)',
    description: 'Ontario ESA policy manual — wages, hours, termination, leaves.',
    discoveryUrl: 'https://www.ontario.ca/document/employment-standard-act-policy-and-interpretation-manual',
    type: 'web_scrape',
    enabled: true,
    autoSync: true,
    syncInterval: 'monthly',
    _personaSlug: 'legal-labor',
  },
  {
    nameEn: 'Ontario Minimum Wage',
    nameZh: '安省最低工资标准',
    description: 'Current minimum wage rates and rules in Ontario.',
    discoveryUrl: 'https://www.ontario.ca/page/minimum-wage-workers',
    type: 'web_scrape',
    enabled: true,
    autoSync: true,
    syncInterval: 'monthly',
    _personaSlug: 'legal-labor',
  },
  // ── legal-disputes (2) ────────────────────────────────────
  {
    nameEn: 'Ontario Small Claims Court',
    nameZh: '安省小额索赔法院',
    description: 'Ontario Small Claims Court — how to sue or respond to a claim.',
    discoveryUrl: 'https://www.ontario.ca/page/suing-and-being-sued',
    type: 'web_scrape',
    enabled: true,
    autoSync: true,
    syncInterval: 'monthly',
    _personaSlug: 'legal-disputes',
  },
  {
    nameEn: 'Ontario Human Rights Commission',
    nameZh: '安省人权委员会 (OHRC)',
    description: 'Ontario Human Rights Commission — discrimination, harassment, accommodation.',
    discoveryUrl: 'https://www.ohrc.on.ca/',
    type: 'web_scrape',
    enabled: true,
    autoSync: true,
    syncInterval: 'monthly',
    _personaSlug: 'legal-disputes',
  },
  // ── legal-consumer (2) ────────────────────────────────────
  {
    nameEn: 'Ontario Consumer Protection',
    nameZh: '安省消费者权益保护',
    description: 'Ontario consumer rights — contracts, refunds, cooling-off periods.',
    discoveryUrl: 'https://www.ontario.ca/page/your-rights-when-signing-contract',
    type: 'web_scrape',
    enabled: true,
    autoSync: true,
    syncInterval: 'monthly',
    _personaSlug: 'legal-consumer',
  },
  {
    nameEn: 'Ontario Consumer Protection Act',
    nameZh: '安省消费者保护法 (CPA)',
    description: 'Consumer Protection Ontario — scams, complaints, and enforcement.',
    discoveryUrl: 'https://www.ontario.ca/page/consumer-protection-ontario',
    type: 'web_scrape',
    enabled: true,
    autoSync: true,
    syncInterval: 'monthly',
    _personaSlug: 'legal-consumer',
  },
  // ── legal-basics (2) ──────────────────────────────────────
  {
    nameEn: 'CLEO Community Legal Education',
    nameZh: '社区法律教育中心 (CLEO)',
    description: 'CLEO — free legal information for Ontario residents.',
    discoveryUrl: 'https://www.cleo.on.ca/en',
    type: 'web_scrape',
    enabled: true,
    autoSync: true,
    syncInterval: 'monthly',
    _personaSlug: 'legal-basics',
  },
  {
    nameEn: 'Legal Aid Ontario',
    nameZh: '安省法律援助 (LAO)',
    description: 'Legal Aid Ontario — free legal services for low-income residents.',
    discoveryUrl: 'https://www.legalaid.on.ca/',
    type: 'web_scrape',
    enabled: true,
    autoSync: true,
    syncInterval: 'monthly',
    _personaSlug: 'legal-basics',
  },
]
