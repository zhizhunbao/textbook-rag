/**
 * data-sources-persona/immigration.ts — Data sources for 3 immigration personas.
 */
import type { PersonaDataSource } from './types'

export const immigrationSources: PersonaDataSource[] = [
  // ── imm-pathways (3) ──────────────────────────────────────
  {
    nameEn: 'IRCC Express Entry',
    nameZh: 'IRCC 快速通道 (Express Entry)',
    description: 'Federal Express Entry immigration program — eligibility, CRS, draws.',
    discoveryUrl: 'https://www.canada.ca/en/immigration-refugees-citizenship/services/immigrate-canada/express-entry.html',
    type: 'web_scrape',
    enabled: true,
    autoSync: true,
    syncInterval: 'weekly',
    _personaSlug: 'imm-pathways',
  },
  {
    nameEn: 'Ontario Immigrant Nominee Program',
    nameZh: '安省省提名移民项目 (OINP)',
    description: 'Ontario PNP streams — Human Capital, Employer Job Offer, Masters/PhD.',
    discoveryUrl: 'https://www.ontario.ca/page/ontario-immigrant-nominee-program-oinp',
    type: 'web_scrape',
    enabled: true,
    autoSync: true,
    syncInterval: 'weekly',
    _personaSlug: 'imm-pathways',
  },
  {
    nameEn: 'IRCC CRS Comprehensive Ranking',
    nameZh: 'IRCC 综合排名系统 (CRS) 评分标准',
    description: 'CRS scoring criteria and point breakdown for Express Entry.',
    discoveryUrl: 'https://www.canada.ca/en/immigration-refugees-citizenship/services/immigrate-canada/express-entry/eligibility/criteria-comprehensive-ranking-system.html',
    type: 'web_scrape',
    enabled: true,
    autoSync: true,
    syncInterval: 'monthly',
    _personaSlug: 'imm-pathways',
  },
  // ── imm-pr-renewal (2) ────────────────────────────────────
  {
    nameEn: 'IRCC PR Card Renewal',
    nameZh: 'IRCC 永居卡 (PR Card) 续签',
    description: 'Permanent resident card renewal, replacement, and residency obligation.',
    discoveryUrl: 'https://www.canada.ca/en/immigration-refugees-citizenship/services/new-immigrants/pr-card.html',
    type: 'web_scrape',
    enabled: true,
    autoSync: true,
    syncInterval: 'monthly',
    _personaSlug: 'imm-pr-renewal',
  },
  {
    nameEn: 'IRCC PR Residency Obligation',
    nameZh: 'IRCC 永居身份居住义务',
    description: 'Understanding PR status and residency obligations.',
    discoveryUrl: 'https://www.canada.ca/en/immigration-refugees-citizenship/services/new-immigrants/pr-card/understand-pr-status.html',
    type: 'web_scrape',
    enabled: true,
    autoSync: true,
    syncInterval: 'monthly',
    _personaSlug: 'imm-pr-renewal',
  },
  // ── imm-family (2) ────────────────────────────────────────
  {
    nameEn: 'IRCC Family Sponsorship',
    nameZh: 'IRCC 家庭团聚担保移民',
    description: 'Sponsor a family member — spouse, parent, grandparent, child.',
    discoveryUrl: 'https://www.canada.ca/en/immigration-refugees-citizenship/services/immigrate-canada/family-sponsorship.html',
    type: 'web_scrape',
    enabled: true,
    autoSync: true,
    syncInterval: 'weekly',
    _personaSlug: 'imm-family',
  },
  {
    nameEn: 'IRCC Parents Grandparents Program',
    nameZh: 'IRCC 父母祖父母团聚项目 (PGP)',
    description: 'Parents and Grandparents Program sponsorship requirements.',
    discoveryUrl: 'https://www.canada.ca/en/immigration-refugees-citizenship/services/immigrate-canada/family-sponsorship/sponsor-parents-grandparents.html',
    type: 'web_scrape',
    enabled: true,
    autoSync: true,
    syncInterval: 'monthly',
    _personaSlug: 'imm-family',
  },
]
