/**
 * collections/endpoints/sync-engine.ts
 * Payload Custom Endpoint: POST /api/books/sync-engine
 *
 * Syncs books from Engine v2 API → Payload CMS Books collection.
 * Engine v2 discovers books by scanning the filesystem (data/mineru_output/),
 * so no database is involved on the engine side.
 *
 * Registered on the Books collection via `endpoints` field.
 */

import type { Endpoint } from 'payload'

const ENGINE = process.env.NEXT_PUBLIC_ENGINE_URL || 'http://localhost:8001'

export const syncEngineEndpoint: Endpoint = {
  handler: async (req) => {
    try {
      const { payload } = req

      // 1. Fetch book list from Engine v2 API (filesystem scan)
      const engineRes = await fetch(`${ENGINE}/engine/books`)
      if (!engineRes.ok) {
        return Response.json(
          { success: false, error: `Engine /engine/books returned ${engineRes.status}` },
          { status: 502 },
        )
      }

      const engineBooks: Array<{
        book_id: string
        title: string
        category: string
        page_count: number
        chunk_count: number
        pdf_size_bytes: number
      }> = await engineRes.json()

      const results = { created: 0, updated: 0, errors: [] as string[], total: engineBooks.length }

      for (const eb of engineBooks) {
        const meta = BOOK_METADATA[eb.book_id]

        const bookData: Record<string, unknown> = {
          engineBookId: eb.book_id,
          title: meta?.title ?? eb.title,
          authors: meta?.authors ?? null,
          category: eb.category || inferCategory(eb.book_id),
          subcategory: inferSubcategory(eb.book_id),
          status: 'indexed' as const,
          chunkCount: eb.chunk_count || 0,
          pipeline: {
            chunked: 'done' as const,
            toc: 'done' as const,
            vector: 'done' as const,
          },
          metadata: {
            pageCount: eb.page_count || 0,
            fileSize: eb.pdf_size_bytes || 0,
          },
        }

        try {
          const existing = await payload.find({
            collection: 'books',
            where: { engineBookId: { equals: eb.book_id } },
            limit: 1,
          })

          let bookDoc: { id: number; coverImage?: unknown }

          if (existing.docs.length > 0) {
            bookDoc = await payload.update({
              collection: 'books',
              id: existing.docs[0].id,
              data: bookData,
            }) as { id: number; coverImage?: unknown }
            results.updated++
          } else {
            bookDoc = await payload.create({
              collection: 'books',
              data: bookData,
            }) as { id: number; coverImage?: unknown }
            results.created++
          }

          // Auto-extract cover if book doesn't have one yet
          if (!bookDoc.coverImage) {
            try {
              const coverRes = await fetch(`${ENGINE}/engine/books/${eb.book_id}/cover`)
              if (coverRes.ok) {
                const coverBuffer = Buffer.from(await coverRes.arrayBuffer())
                const mediaDoc = await payload.create({
                  collection: 'media',
                  data: { alt: `${meta?.title ?? eb.title} cover` },
                  file: {
                    data: coverBuffer,
                    mimetype: 'image/png',
                    name: `${eb.book_id}_cover.png`,
                    size: coverBuffer.length,
                  },
                })
                // Link cover to book
                await payload.update({
                  collection: 'books',
                  id: bookDoc.id,
                  data: { coverImage: mediaDoc.id },
                })
              }
            } catch {
              // Cover extraction is best-effort — don't fail the sync
            }
          }
        } catch (err) {
          const msg = `${eb.book_id}: ${err instanceof Error ? err.message : String(err)}`
          results.errors.push(msg)
        }
      }

      return Response.json({ success: true, ...results })
    } catch (err) {
      const message = err instanceof Error ? err.message : String(err)
      return Response.json({ success: false, error: message }, { status: 500 })
    }
  },
  method: 'post',
  path: '/sync-engine',
}

// ── Helper functions ────────────────────────────────────────────────────────

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
    ramalho_fluent_python: 'Python',
    percival_cosmic_python: 'Python',
    beazley_python_cookbook: 'Python',
    downey_think_python_2e: 'Python',
    downey_how_to_think_like_cs: 'Python',
    okken_python_testing_pytest: 'Python',
    seitz_black_hat_python: 'Python',
    lubanovic_fastapi_modern_web: 'Python',
    haverbeke_eloquent_javascript: 'JavaScript',
    flanagan_js_definitive_guide: 'JavaScript',
    simpson_ydkjs_async_performance: 'JavaScript',
    simpson_ydkjs_es6_beyond: 'JavaScript',
    simpson_ydkjs_scope_closures: 'JavaScript',
    simpson_ydkjs_types_grammar: 'JavaScript',
    simpson_ydkjs_up_going: 'JavaScript',
    simpson_ydkjs_this_object_prototypes: 'JavaScript',
    basarat_typescript_deep_dive: 'JavaScript',
    james_ISLR: 'Machine Learning',
    hastie_esl: 'Machine Learning',
    bishop_prml: 'Machine Learning',
    'shalev-shwartz_uml': 'Machine Learning',
    kelleher_ml_fundamentals: 'Machine Learning',
    murphy_pml1: 'Machine Learning',
    murphy_pml2: 'Machine Learning',
    barber_brml: 'Machine Learning',
    goodfellow_deep_learning: 'Deep Learning',
    'Deep-Learning-with-PyTorch': 'Deep Learning',
    eisenstein_nlp: 'NLP',
    jurafsky_slp3: 'NLP',
    jurafsky_slp3_jan2026: 'NLP',
    manning_intro_to_ir: 'NLP',
    szeliski_cv: 'Computer Vision',
    sutton_barto_rl_intro: 'Reinforcement Learning',
    hamilton_grl: 'Reinforcement Learning',
    deisenroth_mml: 'Math',
    boyd_convex_optimization: 'Math',
    grinstead_snell_probability: 'Math',
    mackay_information_theory: 'Math',
    downey_think_stats_2e: 'Math',
    cormen_CLRS: 'Algorithms',
    martin_clean_code: 'Software Engineering',
    martin_clean_code_excerpt: 'Software Engineering',
    martin_clean_architecture: 'Software Engineering',
    fowler_refactoring: 'Software Engineering',
    hunt_pragmatic_programmer: 'Software Engineering',
    gof_design_patterns: 'Software Engineering',
    google_swe: 'Software Engineering',
    kleppmann_ddia: 'Systems',
    google_sre: 'Systems',
    nygard_release_it: 'Systems',
    ejsmont_web_scalability: 'Systems',
    kreibich_using_sqlite: 'Systems',
    gourley_http_definitive_guide: 'Networking',
    barrett_ssh_definitive_guide: 'Networking',
    zalewski_tangled_web: 'Security',
    aumasson_serious_cryptography: 'Security',
    andriesse_practical_binary_analysis: 'Security',
    chacon_pro_git: 'DevOps',
    krug_dont_make_me_think: 'Design',
    norman_design_everyday_things: 'Design',
    fontaine_art_of_postgresql: 'Database',
  }

  return SUBCATEGORY_MAP[bookId] || ''
}

// ── Book metadata registry (title + authors) ────────────────────────────────
// Engine v2 derives title from book_id via _humanize_title(), which is lossy.
// This registry provides accurate titles and author names for known books.

interface BookMeta { title: string; authors: string }

const BOOK_METADATA: Record<string, BookMeta> = {
  // ── Python ──
  ramalho_fluent_python:       { title: 'Fluent Python', authors: 'Luciano Ramalho' },
  beazley_python_cookbook:      { title: 'Python Cookbook', authors: 'David Beazley, Brian K. Jones' },
  downey_think_python_2e:      { title: 'Think Python (2e)', authors: 'Allen B. Downey' },
  downey_how_to_think_like_cs: { title: 'How to Think Like a Computer Scientist', authors: 'Allen B. Downey' },
  okken_python_testing_pytest: { title: 'Python Testing with pytest', authors: 'Brian Okken' },
  percival_cosmic_python:      { title: 'Architecture Patterns with Python', authors: 'Harry Percival, Bob Gregory' },
  seitz_black_hat_python:      { title: 'Black Hat Python (2e)', authors: 'Justin Seitz, Tim Arnold' },
  lubanovic_fastapi_modern_web:{ title: 'FastAPI: Modern Python Web Development', authors: 'Bill Lubanovic' },

  // ── JavaScript / TypeScript ──
  flanagan_js_definitive_guide:         { title: 'JavaScript: The Definitive Guide (7e)', authors: 'David Flanagan' },
  haverbeke_eloquent_javascript:        { title: 'Eloquent JavaScript (3e)', authors: 'Marijn Haverbeke' },
  simpson_ydkjs_up_going:               { title: "You Don't Know JS: Up & Going", authors: 'Kyle Simpson' },
  simpson_ydkjs_scope_closures:         { title: "You Don't Know JS: Scope & Closures", authors: 'Kyle Simpson' },
  simpson_ydkjs_this_object_prototypes: { title: "You Don't Know JS: this & Object Prototypes", authors: 'Kyle Simpson' },
  simpson_ydkjs_types_grammar:          { title: "You Don't Know JS: Types & Grammar", authors: 'Kyle Simpson' },
  simpson_ydkjs_async_performance:      { title: "You Don't Know JS: Async & Performance", authors: 'Kyle Simpson' },
  simpson_ydkjs_es6_beyond:             { title: "You Don't Know JS: ES6 & Beyond", authors: 'Kyle Simpson' },
  basarat_typescript_deep_dive:         { title: 'TypeScript Deep Dive', authors: 'Basarat Ali Syed' },

  // ── Algorithms ──
  cormen_CLRS: { title: 'Introduction to Algorithms (CLRS)', authors: 'Thomas H. Cormen, Charles E. Leiserson, Ronald L. Rivest, Clifford Stein' },

  // ── Machine Learning ──
  goodfellow_deep_learning:    { title: 'Deep Learning', authors: 'Ian Goodfellow, Yoshua Bengio, Aaron Courville' },
  'Deep-Learning-with-PyTorch':{ title: 'Deep Learning with PyTorch', authors: 'Eli Stevens, Luca Antiga, Thomas Viehmann' },
  bishop_prml:                 { title: 'Pattern Recognition and Machine Learning', authors: 'Christopher M. Bishop' },
  hastie_esl:                  { title: 'The Elements of Statistical Learning', authors: 'Trevor Hastie, Robert Tibshirani, Jerome Friedman' },
  james_ISLR:                  { title: 'An Introduction to Statistical Learning', authors: 'Gareth James, Daniela Witten, Trevor Hastie, Robert Tibshirani' },
  kelleher_ml_fundamentals:    { title: 'Fundamentals of Machine Learning', authors: 'John D. Kelleher, Brian Mac Namee, Aoife D\'Arcy' },
  murphy_pml1:                 { title: 'Probabilistic Machine Learning: An Introduction', authors: 'Kevin P. Murphy' },
  murphy_pml2:                 { title: 'Probabilistic Machine Learning: Advanced Topics', authors: 'Kevin P. Murphy' },
  barber_brml:                 { title: 'Bayesian Reasoning and Machine Learning', authors: 'David Barber' },
  'shalev-shwartz_uml':       { title: 'Understanding Machine Learning', authors: 'Shai Shalev-Shwartz, Shai Ben-David' },

  // ── Mathematics ──
  deisenroth_mml:              { title: 'Mathematics for Machine Learning', authors: 'Marc Peter Deisenroth, A. Aldo Faisal, Cheng Soon Ong' },
  boyd_convex_optimization:    { title: 'Convex Optimization', authors: 'Stephen Boyd, Lieven Vandenberghe' },
  grinstead_snell_probability: { title: 'Introduction to Probability', authors: 'Charles M. Grinstead, J. Laurie Snell' },
  downey_think_stats_2e:       { title: 'Think Stats (2e)', authors: 'Allen B. Downey' },
  mackay_information_theory:   { title: 'Information Theory, Inference and Learning Algorithms', authors: 'David J.C. MacKay' },

  // ── NLP / IR ──
  jurafsky_slp3:        { title: 'Speech and Language Processing (3e)', authors: 'Dan Jurafsky, James H. Martin' },
  jurafsky_slp3_jan2026:{ title: 'Speech and Language Processing (3e, Jan 2026)', authors: 'Dan Jurafsky, James H. Martin' },
  eisenstein_nlp:       { title: 'Introduction to Natural Language Processing', authors: 'Jacob Eisenstein' },
  manning_intro_to_ir:  { title: 'Introduction to Information Retrieval', authors: 'Christopher D. Manning, Prabhakar Raghavan, Hinrich Schütze' },

  // ── Computer Vision ──
  szeliski_cv: { title: 'Computer Vision: Algorithms and Applications (2e)', authors: 'Richard Szeliski' },

  // ── Reinforcement Learning ──
  sutton_barto_rl_intro: { title: 'Reinforcement Learning: An Introduction (2e)', authors: 'Richard S. Sutton, Andrew G. Barto' },

  // ── Graph Learning ──
  hamilton_grl: { title: 'Graph Representation Learning', authors: 'William L. Hamilton' },

  // ── Software Engineering ──
  martin_clean_code:          { title: 'Clean Code', authors: 'Robert C. Martin' },
  martin_clean_code_excerpt:  { title: 'Clean Code (Excerpt)', authors: 'Robert C. Martin' },
  martin_clean_architecture:  { title: 'Clean Architecture', authors: 'Robert C. Martin' },
  gof_design_patterns:        { title: 'Design Patterns', authors: 'Erich Gamma, Richard Helm, Ralph Johnson, John Vlissides' },
  kleppmann_ddia:             { title: 'Designing Data-Intensive Applications', authors: 'Martin Kleppmann' },
  hunt_pragmatic_programmer:  { title: 'The Pragmatic Programmer (20th Anniversary)', authors: 'David Thomas, Andrew Hunt' },
  fowler_refactoring:         { title: 'Refactoring (2e)', authors: 'Martin Fowler' },
  ejsmont_web_scalability:    { title: 'Web Scalability for Startup Engineers', authors: 'Artur Ejsmont' },
  google_swe:                 { title: 'Software Engineering at Google', authors: 'Titus Winters, Tom Manshreck, Hyrum Wright' },

  // ── DevOps / SRE ──
  chacon_pro_git:    { title: 'Pro Git (2e)', authors: 'Scott Chacon, Ben Straub' },
  google_sre:        { title: 'Site Reliability Engineering', authors: 'Betsy Beyer, Chris Jones, Jennifer Petoff, Niall Richard Murphy' },
  nygard_release_it: { title: 'Release It! (2e)', authors: 'Michael T. Nygard' },

  // ── Security ──
  aumasson_serious_cryptography:       { title: 'Serious Cryptography', authors: 'Jean-Philippe Aumasson' },
  andriesse_practical_binary_analysis: { title: 'Practical Binary Analysis', authors: 'Dennis Andriesse' },
  zalewski_tangled_web:                { title: 'The Tangled Web', authors: 'Michal Zalewski' },

  // ── Networking ──
  gourley_http_definitive_guide: { title: 'HTTP: The Definitive Guide', authors: 'David Gourley, Brian Totty' },
  barrett_ssh_definitive_guide:  { title: 'SSH: The Definitive Guide (2e)', authors: 'Daniel J. Barrett, Richard E. Silverman, Robert G. Byrnes' },

  // ── Database ──
  kreibich_using_sqlite:      { title: 'Using SQLite', authors: 'Jay A. Kreibich' },
  fontaine_art_of_postgresql: { title: 'The Art of PostgreSQL', authors: 'Dimitri Fontaine' },

  // ── UX / Design ──
  krug_dont_make_me_think:            { title: "Don't Make Me Think (Revisited)", authors: 'Steve Krug' },
  norman_design_everyday_things:      { title: 'The Design of Everyday Things', authors: 'Don Norman' },
  williams_non_designers_design_book: { title: "The Non-Designer's Design Book", authors: 'Robin Williams' },

  // ── Educational Design ──
  mayer_multimedia_learning:        { title: 'Multimedia Learning (3e)', authors: 'Richard E. Mayer' },
  clark_mayer_elearning:            { title: 'e-Learning and the Science of Instruction', authors: 'Ruth Colvin Clark, Richard E. Mayer' },
  knaflic_storytelling_with_data:   { title: 'Storytelling with Data', authors: 'Cole Nussbaumer Knaflic' },
  williams_animators_survival_kit:  { title: "The Animator's Survival Kit", authors: 'Richard Williams' },
  heath_made_to_stick:              { title: 'Made to Stick', authors: 'Chip Heath, Dan Heath' },
  mckee_story:                      { title: 'Story', authors: 'Robert McKee' },
  snyder_save_the_cat:              { title: 'Save the Cat!', authors: 'Blake Snyder' },
}
