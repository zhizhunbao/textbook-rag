/**
 * consulting-personas/index.ts — Barrel export for 29 consulting persona seeds.
 *
 * Architecture: 8 categories × 29 roles
 * Categories: education / immigration / settlement / healthcare / finance / career / legal / analysis
 *
 * Each persona maps to a dedicated ChromaDB collection (ca_{slug}) for domain-specific RAG.
 */

export type { PersonaSeed } from './types'

// ── Education (5) ────────────────────────────────────────────
import { eduSchoolPlanning } from './education/edu-school-planning'
import { eduVisaCompliance } from './education/edu-visa-compliance'
import { eduAcademicRules } from './education/edu-academic-rules'
import { eduWorkPermit } from './education/edu-work-permit'
import { eduChildEducation } from './education/edu-child-education'

// ── Immigration (3) ─────────────────────────────────────────
import { immPathways } from './immigration/imm-pathways'
import { immPrRenewal } from './immigration/imm-pr-renewal'
import { immFamily } from './immigration/imm-family'

// ── Settlement (5) ──────────────────────────────────────────
import { lifeRental } from './settlement/life-rental'
import { lifeDriving } from './settlement/life-driving'
import { lifeUtilities } from './settlement/life-utilities'
import { lifeHomeBuying } from './settlement/life-home-buying'
import { lifeCar } from './settlement/life-car'

// ── Healthcare (3) ──────────────────────────────────────────
import { healthInsurance } from './healthcare/health-insurance'
import { healthMental } from './healthcare/health-mental'
import { healthChildcare } from './healthcare/health-childcare'

// ── Finance (4) ─────────────────────────────────────────────
import { finBanking } from './finance/fin-banking'
import { finTax } from './finance/fin-tax'
import { finInvestment } from './finance/fin-investment'
import { finCostSaving } from './finance/fin-cost-saving'

// ── Career (4) ──────────────────────────────────────────────
import { careerResume } from './career/career-resume'
import { careerInternship } from './career/career-internship'
import { careerTransition } from './career/career-transition'
import { careerVolunteer } from './career/career-volunteer'

// ── Legal (4) ───────────────────────────────────────────────
import { legalLabor } from './legal/legal-labor'
import { legalDisputes } from './legal/legal-disputes'
import { legalConsumer } from './legal/legal-consumer'
import { legalBasics } from './legal/legal-basics'

// ── Analysis (1) ────────────────────────────────────────────
import { ecdevAnalyst } from './analysis/ecdev-analyst'

// ── Aggregated export ───────────────────────────────────────
export const consultingPersonasData = [
  // Education
  eduSchoolPlanning,
  eduVisaCompliance,
  eduAcademicRules,
  eduWorkPermit,
  eduChildEducation,
  // Immigration
  immPathways,
  immPrRenewal,
  immFamily,
  // Settlement
  lifeRental,
  lifeDriving,
  lifeUtilities,
  lifeHomeBuying,
  lifeCar,
  // Healthcare
  healthInsurance,
  healthMental,
  healthChildcare,
  // Finance
  finBanking,
  finTax,
  finInvestment,
  finCostSaving,
  // Career
  careerResume,
  careerInternship,
  careerTransition,
  careerVolunteer,
  // Legal
  legalLabor,
  legalDisputes,
  legalConsumer,
  legalBasics,
  // Analysis
  ecdevAnalyst,
]
