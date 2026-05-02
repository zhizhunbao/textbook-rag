/**
 * data-sources-persona/finance.ts — Data sources for 4 finance personas.
 */
import type { PersonaDataSource } from './types'

export const financeSources: PersonaDataSource[] = [
  // ── fin-banking (2) ───────────────────────────────────────
  {
    nameEn: 'FCAC Banking Basics',
    nameZh: '加拿大金融消费者保护局 — 银行入门',
    description: 'Financial Consumer Agency — banking basics, account types, fees.',
    discoveryUrl: 'https://www.canada.ca/en/financial-consumer-agency/services/banking.html',
    type: 'web_scrape',
    enabled: true,
    autoSync: true,
    syncInterval: 'monthly',
    _personaSlug: 'fin-banking',
  },
  {
    nameEn: 'FCAC Opening a Bank Account',
    nameZh: 'FCAC 开户指南',
    description: 'How to open a bank account in Canada — ID requirements and process.',
    discoveryUrl: 'https://www.canada.ca/en/financial-consumer-agency/services/banking/opening-bank-account.html',
    type: 'web_scrape',
    enabled: true,
    autoSync: true,
    syncInterval: 'monthly',
    _personaSlug: 'fin-banking',
  },
  // ── fin-tax (2) ───────────────────────────────────────────
  {
    nameEn: 'CRA Individual Tax',
    nameZh: 'CRA 个人所得税',
    description: 'CRA personal income tax — filing, deductions, credits.',
    discoveryUrl: 'https://www.canada.ca/en/revenue-agency/services/tax/individuals.html',
    type: 'web_scrape',
    enabled: true,
    autoSync: true,
    syncInterval: 'weekly',
    _personaSlug: 'fin-tax',
  },
  {
    nameEn: 'CRA Newcomers Tax Guide',
    nameZh: 'CRA 新移民报税指南',
    description: 'Tax information for newcomers to Canada — first-year filing guide.',
    discoveryUrl: 'https://www.canada.ca/en/revenue-agency/services/tax/international-non-residents/individuals-leaving-entering-canada-non-residents/newcomers-canada-immigrants.html',
    type: 'web_scrape',
    enabled: true,
    autoSync: true,
    syncInterval: 'monthly',
    _personaSlug: 'fin-tax',
  },
  // ── fin-investment (2) ────────────────────────────────────
  {
    nameEn: 'OSC Investor Education',
    nameZh: '安省证券委员会投资者教育 (OSC)',
    description: 'Ontario Securities Commission — investor education and protection.',
    discoveryUrl: 'https://www.osc.ca/en/investors',
    type: 'web_scrape',
    enabled: true,
    autoSync: true,
    syncInterval: 'monthly',
    _personaSlug: 'fin-investment',
  },
  {
    nameEn: 'FCAC Investing Basics',
    nameZh: 'FCAC 储蓄与投资基础',
    description: 'FCAC savings and investments — TFSA, RRSP, GICs, mutual funds.',
    discoveryUrl: 'https://www.canada.ca/en/financial-consumer-agency/services/savings-investments.html',
    type: 'web_scrape',
    enabled: true,
    autoSync: true,
    syncInterval: 'monthly',
    _personaSlug: 'fin-investment',
  },
  // ── fin-cost-saving (2) ───────────────────────────────────
  {
    nameEn: 'Ontario Trillium Benefit',
    nameZh: '安省延龄草福利金 (OTB)',
    description: 'Ontario Trillium Benefit — energy, property tax, and sales tax credits.',
    discoveryUrl: 'https://www.ontario.ca/page/ontario-trillium-benefit',
    type: 'web_scrape',
    enabled: true,
    autoSync: true,
    syncInterval: 'monthly',
    _personaSlug: 'fin-cost-saving',
  },
  {
    nameEn: 'Canada GST/HST Credit',
    nameZh: '加拿大消费税退税 (GST/HST Credit)',
    description: 'GST/HST credit — eligibility and payment amounts for low-income individuals.',
    discoveryUrl: 'https://www.canada.ca/en/revenue-agency/services/child-family-benefits/goods-services-tax-harmonized-sales-tax-gst-hst-credit.html',
    type: 'web_scrape',
    enabled: true,
    autoSync: true,
    syncInterval: 'monthly',
    _personaSlug: 'fin-cost-saving',
  },
]
