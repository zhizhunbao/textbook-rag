/**
 * POST /api/sync-engine
 *
 * Syncs books from Engine SQLite → Payload CMS using Payload Local API.
 * No authentication needed since Local API bypasses access control.
 */

import { NextResponse } from 'next/server'
import { getPayload } from 'payload'
import config from '@payload-config'

const ENGINE = process.env.NEXT_PUBLIC_ENGINE_URL || 'http://localhost:8000'

export async function POST() {
  try {
    // 1. Fetch book list from Engine API
    const engineRes = await fetch(`${ENGINE}/engine/books`)
    if (!engineRes.ok) {
      return NextResponse.json(
        { success: false, error: `Engine /engine/books returned ${engineRes.status}` },
        { status: 502 },
      )
    }
    const engineBooks: Array<{
      id: number
      book_id: string
      title: string
      authors: string | null
      page_count: number | null
      chapter_count: number | null
      chunk_count: number | null
    }> = await engineRes.json()

    // 2. Use Payload Local API (bypasses access control)
    const payload = await getPayload({ config })

    const results = { created: 0, updated: 0, errors: [] as string[], total: engineBooks.length }

    for (const eb of engineBooks) {
      const bookData = {
        engineBookId: eb.book_id,
        title: eb.title,
        authors: eb.authors || '',
        category: inferCategory(eb.book_id),
        subcategory: inferSubcategory(eb.book_id),
        status: 'indexed' as const,
        chunkCount: eb.chunk_count || 0,
        pipeline: {
          chunked: 'done' as const,
          stored: 'done' as const,
          vector: 'done' as const,
          fts: 'done' as const,
          toc: 'done' as const,
        },
        metadata: {
          pageCount: eb.page_count || 0,
          chapterCount: eb.chapter_count || 0,
        },
      }

      try {
        // Check if exists
        const existing = await payload.find({
          collection: 'books',
          where: { engineBookId: { equals: eb.book_id } },
          limit: 1,
        })

        if (existing.docs.length > 0) {
          await payload.update({
            collection: 'books',
            id: existing.docs[0].id,
            data: bookData,
          })
          results.updated++
        } else {
          await payload.create({
            collection: 'books',
            data: bookData,
          })
          results.created++
        }
      } catch (err) {
        const msg = `${eb.book_id}: ${err instanceof Error ? err.message : String(err)}`
        results.errors.push(msg)
      }
    }

    return NextResponse.json({ success: true, ...results })
  } catch (err) {
    const message = err instanceof Error ? err.message : String(err)
    return NextResponse.json({ success: false, error: message }, { status: 500 })
  }
}

/** Infer book category from engine book_id */
function inferCategory(bookId: string): string {
  if (bookId.startsWith('ed_update') || bookId.startsWith('oreb_')) return 'ecdev'
  return 'textbook'
}

/** Infer subcategory from engine book_id for hierarchical filtering */
function inferSubcategory(bookId: string): string {
  // ── EC Development ──
  if (bookId.startsWith('ed_update')) return 'Quarterly Reports'
  if (bookId.startsWith('oreb_')) return 'Market Analysis'

  // ── Textbook subcategories by subject ──
  const SUBCATEGORY_MAP: Record<string, string> = {
    // Python
    ramalho_fluent_python: 'Python',
    percival_cosmic_python: 'Python',
    beazley_python_cookbook: 'Python',
    downey_think_python_2e: 'Python',
    downey_how_to_think_like_cs: 'Python',
    okken_python_testing_pytest: 'Python',
    seitz_black_hat_python: 'Python',
    lubanovic_fastapi_modern_web: 'Python',

    // JavaScript / TypeScript
    haverbeke_eloquent_javascript: 'JavaScript',
    flanagan_js_definitive_guide: 'JavaScript',
    simpson_ydkjs_async_performance: 'JavaScript',
    simpson_ydkjs_es6_beyond: 'JavaScript',
    simpson_ydkjs_scope_closures: 'JavaScript',
    simpson_ydkjs_types_grammar: 'JavaScript',
    simpson_ydkjs_up_going: 'JavaScript',
    simpson_ydkjs_this_object_prototypes: 'JavaScript',
    basarat_typescript_deep_dive: 'JavaScript',

    // ML & Statistics
    james_ISLR: 'Machine Learning',
    hastie_esl: 'Machine Learning',
    bishop_prml: 'Machine Learning',
    'shalev-shwartz_uml': 'Machine Learning',
    kelleher_ml_fundamentals: 'Machine Learning',
    murphy_pml1: 'Machine Learning',
    murphy_pml2: 'Machine Learning',
    barber_brml: 'Machine Learning',

    // Deep Learning
    goodfellow_deep_learning: 'Deep Learning',

    // NLP / IR
    eisenstein_nlp: 'NLP',
    jurafsky_slp3: 'NLP',
    manning_intro_to_ir: 'NLP',

    // Computer Vision
    szeliski_cv: 'Computer Vision',

    // Reinforcement Learning
    sutton_barto_rl_intro: 'Reinforcement Learning',
    hamilton_grl: 'Reinforcement Learning',

    // Math & Probability
    deisenroth_mml: 'Math',
    boyd_convex_optimization: 'Math',
    grinstead_snell_probability: 'Math',
    mackay_information_theory: 'Math',

    // Algorithms & Data Structures
    cormen_CLRS: 'Algorithms',

    // Software Engineering
    martin_clean_code: 'Software Engineering',
    martin_clean_architecture: 'Software Engineering',
    fowler_refactoring: 'Software Engineering',
    hunt_pragmatic_programmer: 'Software Engineering',
    gof_design_patterns: 'Software Engineering',
    google_swe: 'Software Engineering',
    chacon_pro_git: 'Software Engineering',

    // Systems & Infrastructure
    kleppmann_ddia: 'Systems',
    google_sre: 'Systems',
    nygard_release_it: 'Systems',
    ejsmont_web_scalability: 'Systems',
    kreibich_using_sqlite: 'Systems',

    // Networking & Web
    gourley_http_definitive_guide: 'Networking',
    barrett_ssh_definitive_guide: 'Networking',
    zalewski_tangled_web: 'Security',
    aumasson_serious_cryptography: 'Security',
    andriesse_practical_binary_analysis: 'Security',

    // Design & UX
    krug_dont_make_me_think: 'Design',
    norman_design_everyday_things: 'Design',

    // Data & Statistics
    downey_think_stats_2e: 'Statistics',
    fontaine_art_of_postgresql: 'Database',
  }

  return SUBCATEGORY_MAP[bookId] || ''
}
