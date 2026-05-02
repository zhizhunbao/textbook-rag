/**
 * data-sources-persona/career.ts — Data sources for 4 career + 1 analysis personas.
 */
import type { PersonaDataSource } from './types'

export const careerSources: PersonaDataSource[] = [
  // ── career-resume (2) ─────────────────────────────────────
  {
    nameEn: 'Job Bank Canada',
    nameZh: '加拿大政府求职银行',
    description: 'Government of Canada Job Bank — job search, resume tips, labour market.',
    discoveryUrl: 'https://www.jobbank.gc.ca/',
    type: 'web_scrape',
    enabled: true,
    autoSync: true,
    syncInterval: 'weekly',
    _personaSlug: 'career-resume',
  },
  {
    nameEn: 'IRCC Working in Canada',
    nameZh: 'IRCC 在加拿大工作准备',
    description: 'IRCC guide to preparing for work in Canada — credentials, job search.',
    discoveryUrl: 'https://www.canada.ca/en/immigration-refugees-citizenship/services/new-immigrants/prepare-life-canada/prepare-work.html',
    type: 'web_scrape',
    enabled: true,
    autoSync: true,
    syncInterval: 'monthly',
    _personaSlug: 'career-resume',
  },
  // ── career-internship (2) ─────────────────────────────────
  {
    nameEn: 'Ontario Co-op Education Tax Credit',
    nameZh: '安省合作教育税收抵免',
    description: 'Ontario co-op education tax credit for employers hiring students.',
    discoveryUrl: 'https://www.ontario.ca/page/co-op-education-tax-credit',
    type: 'web_scrape',
    enabled: true,
    autoSync: true,
    syncInterval: 'monthly',
    _personaSlug: 'career-internship',
  },
  {
    nameEn: 'Canada Summer Jobs Program',
    nameZh: '加拿大暑期工作项目 (CSJ)',
    description: 'Federal Canada Summer Jobs — subsidized employment for youth.',
    discoveryUrl: 'https://www.canada.ca/en/employment-social-development/services/funding/canada-summer-jobs.html',
    type: 'web_scrape',
    enabled: true,
    autoSync: true,
    syncInterval: 'monthly',
    _personaSlug: 'career-internship',
  },
  // ── career-transition (2) ─────────────────────────────────
  {
    nameEn: 'IRCC Foreign Credential Assessment',
    nameZh: 'IRCC 海外学历认证',
    description: 'How to get foreign credentials assessed and recognized in Canada.',
    discoveryUrl: 'https://www.canada.ca/en/immigration-refugees-citizenship/services/new-immigrants/prepare-life-canada/prepare-work/credential-assessment.html',
    type: 'web_scrape',
    enabled: true,
    autoSync: true,
    syncInterval: 'monthly',
    _personaSlug: 'career-transition',
  },
  {
    nameEn: 'Ontario Bridge Training Programs',
    nameZh: '安省桥梁培训项目',
    description: 'Ontario bridge training — help internationally trained professionals.',
    discoveryUrl: 'https://www.ontario.ca/page/adult-learning-ontario-bridge-training',
    type: 'web_scrape',
    enabled: true,
    autoSync: true,
    syncInterval: 'monthly',
    _personaSlug: 'career-transition',
  },
  // ── career-volunteer (2) ──────────────────────────────────
  {
    nameEn: 'Volunteer Canada',
    nameZh: '加拿大志愿者协会',
    description: 'Volunteer Canada — find volunteer opportunities and resources.',
    discoveryUrl: 'https://volunteer.ca/',
    type: 'web_scrape',
    enabled: true,
    autoSync: true,
    syncInterval: 'monthly',
    _personaSlug: 'career-volunteer',
  },
  {
    nameEn: 'CharityVillage Volunteer Search',
    nameZh: 'CharityVillage 志愿岗位搜索',
    description: 'Search volunteer positions across Canada by location and cause.',
    discoveryUrl: 'https://charityvillage.com/search/volunteer/',
    type: 'web_scrape',
    enabled: true,
    autoSync: true,
    syncInterval: 'monthly',
    _personaSlug: 'career-volunteer',
  },
]
