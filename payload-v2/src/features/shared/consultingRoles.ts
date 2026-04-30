/**
 * consultingRoles.ts — Shared category + role definitions for the consulting platform.
 *
 * Single source of truth used by:
 *  - HomePage (Expert Center section)
 *  - OnboardingPage (role selection)
 *
 * Avatar paths correspond to files in /public/avatars/.
 */

// ── Category definition ──

export interface CategoryDef {
  value: string
  label: string
  color: string
  ringColor: string
  bgColor: string
  textColor: string
}

export const CATEGORIES: CategoryDef[] = [
  { value: 'analysis', label: 'Analysis', color: 'from-sky-500 to-blue-600', ringColor: 'ring-sky-400/50', bgColor: 'bg-sky-500/10', textColor: 'text-sky-600 dark:text-sky-300' },
  { value: 'education', label: 'Education', color: 'from-indigo-500 to-blue-500', ringColor: 'ring-indigo-400/50', bgColor: 'bg-indigo-500/10', textColor: 'text-indigo-600 dark:text-indigo-300' },
  { value: 'immigration', label: 'Immigration', color: 'from-blue-500 to-cyan-500', ringColor: 'ring-blue-400/50', bgColor: 'bg-blue-500/10', textColor: 'text-blue-600 dark:text-blue-300' },
  { value: 'settlement', label: 'Settlement', color: 'from-emerald-500 to-teal-500', ringColor: 'ring-emerald-400/50', bgColor: 'bg-emerald-500/10', textColor: 'text-emerald-600 dark:text-emerald-300' },
  { value: 'healthcare', label: 'Healthcare', color: 'from-rose-500 to-pink-500', ringColor: 'ring-rose-400/50', bgColor: 'bg-rose-500/10', textColor: 'text-rose-600 dark:text-rose-300' },
  { value: 'finance', label: 'Finance', color: 'from-amber-500 to-orange-500', ringColor: 'ring-amber-400/50', bgColor: 'bg-amber-500/10', textColor: 'text-amber-600 dark:text-amber-300' },
  { value: 'career', label: 'Career', color: 'from-violet-500 to-purple-500', ringColor: 'ring-violet-400/50', bgColor: 'bg-violet-500/10', textColor: 'text-violet-600 dark:text-violet-300' },
  { value: 'legal', label: 'Legal', color: 'from-slate-500 to-gray-600', ringColor: 'ring-slate-400/50', bgColor: 'bg-slate-500/10', textColor: 'text-slate-600 dark:text-slate-300' },
]

// ── Role definition ──

export interface RoleDef {
  slug: string
  name: string
  category: string
  description: string
  enabled: boolean
  avatar?: string
}

export const ALL_ROLES: RoleDef[] = [
  // Education
  { slug: 'edu-school-planning', name: 'School & Program Planning', category: 'education', description: 'DLI school comparison, program selection, and tuition analysis', enabled: true, avatar: '/avatars/education.png' },
  { slug: 'edu-visa-compliance', name: 'Study Visa & Compliance', category: 'education', description: 'Study permit applications, renewals, and common refusal reasons', enabled: true, avatar: '/avatars/immigration.png' },
  { slug: 'edu-academic-rules', name: 'Academic Rules & Graduation', category: 'education', description: 'Course planning, GPA requirements, and graduation rules', enabled: true, avatar: '/avatars/academic-rules.png' },
  { slug: 'edu-work-permit', name: 'Post-Grad Work Permit', category: 'education', description: 'PGWP applications and on/off-campus work rules', enabled: true, avatar: '/avatars/work-permit.png' },
  { slug: 'edu-child-education', name: 'Child Education & K-12', category: 'education', description: 'K-12 school selection, ESL programs, and extracurriculars', enabled: true, avatar: '/avatars/child-education.png' },
  // Immigration
  { slug: 'imm-pathways', name: 'Immigration Pathways', category: 'immigration', description: 'Express Entry, PNP, LMIA, and CRS scoring', enabled: true, avatar: '/avatars/immigration.png' },
  { slug: 'imm-pr-renewal', name: 'PR & Citizenship', category: 'immigration', description: 'PR card renewal, citizenship test, and residency obligations', enabled: true, avatar: '/avatars/pr-citizenship.png' },
  { slug: 'imm-family', name: 'Family Sponsorship', category: 'immigration', description: 'Spousal sponsorship, parent reunification, and Super Visa', enabled: true, avatar: '/avatars/family-sponsorship.png' },
  // Settlement
  { slug: 'life-rental', name: 'Rental & Lease', category: 'settlement', description: 'Tenancy Act, standard lease terms, and rent increase limits', enabled: true, avatar: '/avatars/housing.png' },
  { slug: 'life-driving', name: "Driver's License & Traffic", category: 'settlement', description: 'G1/G2/G license tests and international license exchange', enabled: true, avatar: '/avatars/transportation.png' },
  { slug: 'life-utilities', name: 'Utilities & Bills', category: 'settlement', description: 'Electricity, gas, water setup, and internet plan comparisons', enabled: true, avatar: '/avatars/living.png' },
  { slug: 'life-home-buying', name: 'Home Buying & Property', category: 'settlement', description: 'First-time home buying, inspections, and mortgages', enabled: true, avatar: '/avatars/home-buying.png' },
  { slug: 'life-car', name: 'Vehicle & Auto Insurance', category: 'settlement', description: 'Car buying, insurance comparison, and maintenance', enabled: true, avatar: '/avatars/vehicle-insurance.png' },
  // Healthcare
  { slug: 'health-insurance', name: 'Health Insurance & Medical', category: 'healthcare', description: 'OHIP registration, family doctor, and walk-in clinics', enabled: true, avatar: '/avatars/healthcare.png' },
  { slug: 'health-mental', name: 'Mental Health & Support', category: 'healthcare', description: 'Mental health resources, EAP programs, and crisis hotlines', enabled: true, avatar: '/avatars/mental-health.png' },
  { slug: 'health-childcare', name: 'Maternal & Child Health', category: 'healthcare', description: 'Prenatal care, child vaccinations, and daycare subsidies', enabled: true, avatar: '/avatars/maternal-child.png' },
  // Finance
  { slug: 'fin-banking', name: 'Banking & Credit Building', category: 'finance', description: 'Bank account opening, credit cards, and credit score building', enabled: true, avatar: '/avatars/finance.png' },
  { slug: 'fin-tax', name: 'Tax Filing & Benefits', category: 'finance', description: 'T4/T1 tax filing, GST/HST rebates, and government benefits', enabled: true, avatar: '/avatars/tax-filing.png' },
  { slug: 'fin-investment', name: 'Insurance & Investment', category: 'finance', description: 'TFSA/RRSP investing, insurance planning, and remittance', enabled: true, avatar: '/avatars/investment.png' },
  { slug: 'fin-cost-saving', name: 'Cost-Saving & Deals', category: 'finance', description: 'Grocery comparisons, cashback programs, and budget tips', enabled: true, avatar: '/avatars/cost-saving.png' },
  // Career
  { slug: 'career-resume', name: 'Resume & Job Search', category: 'career', description: 'Canadian resume format, ATS optimization, and LinkedIn SEO', enabled: true, avatar: '/avatars/career.png' },
  { slug: 'career-internship', name: 'Internship & Part-Time', category: 'career', description: 'Co-op programs, part-time channels, and work permit rules', enabled: true, avatar: '/avatars/internship.png' },
  { slug: 'career-transition', name: 'Career Transition', category: 'career', description: 'Skills assessment, bridge programs, and industry analysis', enabled: true, avatar: '/avatars/career-transition.png' },
  { slug: 'career-volunteer', name: 'Volunteering & Profile', category: 'career', description: 'Volunteer opportunities, references, and community involvement', enabled: true, avatar: '/avatars/volunteering.png' },
  // Legal
  { slug: 'legal-labor', name: 'Labor Rights & Standards', category: 'legal', description: 'Employment Standards Act, minimum wage, and overtime rules', enabled: true, avatar: '/avatars/lawyer.png' },
  { slug: 'legal-disputes', name: 'Rental & Workplace Disputes', category: 'legal', description: 'LTB complaints, labor arbitration, and small claims court', enabled: true, avatar: '/avatars/legal-disputes.png' },
  { slug: 'legal-consumer', name: 'Consumer Rights', category: 'legal', description: 'Refund policies, complaint channels, and scam prevention', enabled: true, avatar: '/avatars/consumer-rights.png' },
  { slug: 'legal-basics', name: 'Legal Basics & Resources', category: 'legal', description: 'Canadian legal system overview and legal aid resources', enabled: true, avatar: '/avatars/legal-basics.png' },
  // Analysis
  { slug: 'ecdev-analyst', name: 'Ottawa EcDev Analyst', category: 'analysis', description: 'Ottawa economic development data analysis — labour market, housing, CPI, vacancy, permits', enabled: true, avatar: '/avatars/ecdev-analyst.png' },
]

/** Quick lookup: slug → avatar path */
export const AVATAR_MAP: Record<string, string> = Object.fromEntries(
  ALL_ROLES.filter((r) => r.avatar).map((r) => [r.slug, r.avatar!]),
)

/** Find CategoryDef by value */
export function getCategoryDef(value: string): CategoryDef | undefined {
  return CATEGORIES.find((c) => c.value === value)
}
