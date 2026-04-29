import { buildConfig } from 'payload'
import { postgresAdapter } from '@payloadcms/db-postgres'
import { lexicalEditor } from '@payloadcms/richtext-lexical'
import { stripePlugin } from '@payloadcms/plugin-stripe'
import { seoPlugin } from '@payloadcms/plugin-seo'
import path from 'path'
import { fileURLToPath } from 'url'
import sharp from 'sharp'

import { Books } from './collections/Books'
import { Chapters } from './collections/Chapters'
import { Chunks } from './collections/Chunks'
import { DataSources } from './collections/DataSources'
import { Users } from './collections/Users'
import { IngestTasks } from './collections/IngestTasks'
import { Llms } from './collections/Llms'
import { Prompts } from './collections/Prompts'
import { Queries } from './collections/Queries'
import { Questions } from './collections/Questions'
import { QuestionSets } from './collections/QuestionSets'
import { Evaluations } from './collections/Evaluations'
import { GoldenDataset } from './collections/GoldenDataset'
import { ChatSessions } from './collections/ChatSessions'
import { ChatMessages } from './collections/ChatMessages'
import { Media } from './collections/Media'
import { PdfUploads } from './collections/PdfUploads'
import { Reports } from './collections/Reports'
import { ConsultingPersonas } from './collections/ConsultingPersonas'
import { ConsultingSessions } from './collections/ConsultingSessions'
import { UserDocuments } from './collections/UserDocuments'
import { UsageRecords } from './collections/UsageRecords'
import { homeMetricsEndpoint, seedEndpoint } from './collections/endpoints'

const filename = fileURLToPath(import.meta.url)
const dirname = path.dirname(filename)

export default buildConfig({
  admin: {
    user: Users.slug,
    importMap: {
      baseDir: path.resolve(dirname),
    },
  },
  collections: [
    Users,
    Media,
    PdfUploads,
    Books,
    Chapters,
    Chunks,
    DataSources,
    IngestTasks,
    Llms,
    Prompts,
    Queries,
    Questions,
    QuestionSets,
    Evaluations,
    GoldenDataset,
    ChatSessions,
    ChatMessages,
    Reports,
    ConsultingPersonas,
    ConsultingSessions,
    UserDocuments,
    UsageRecords,
  ],
  editor: lexicalEditor(),
  secret: process.env.PAYLOAD_SECRET || '',
  typescript: {
    outputFile: path.resolve(dirname, 'payload-types.ts'),
  },
  db: postgresAdapter({
    pool: {
      connectionString: process.env.DATABASE_URI || 'postgresql://payload:payload@127.0.0.1:5432/payload',
    },
  }),
  sharp,
  upload: {
    limits: {
      fileSize: 200_000_000, // 200 MB — for large PDFs
    },
  },
  endpoints: [seedEndpoint, homeMetricsEndpoint],
  plugins: [
    // GO-MON-07/08: Stripe payments — webhook handling + REST proxy
    stripePlugin({
      stripeSecretKey: process.env.STRIPE_SECRET_KEY || '',
      stripeWebhooksEndpointSecret: process.env.STRIPE_WEBHOOKS_ENDPOINT_SECRET,
      rest: false, // disable REST proxy in production (security risk)
      logs: process.env.NODE_ENV !== 'production',
      webhooks: {
        'customer.subscription.created': async ({ event, req }) => {
          const subscription = event.data.object as { customer: string }
          await _upgradeUserTier(req.payload, subscription.customer, 'pro')
        },
        'customer.subscription.deleted': async ({ event, req }) => {
          const subscription = event.data.object as { customer: string }
          await _upgradeUserTier(req.payload, subscription.customer, 'free')
        },
      },
    }),
    // GO-LAND-05: SEO meta management for landing/pricing pages
    seoPlugin({
      collections: [],  // no CMS collections need SEO yet
      generateTitle: ({ doc }) => `ConsultRAG — ${(doc as Record<string, string>)?.title || 'AI Consulting'}`,
      generateDescription: ({ doc }) => (doc as Record<string, string>)?.excerpt || 'AI-powered multi-role consulting with private document RAG',
    }),
  ],
})

/**
 * Helper: Update user tier when Stripe subscription changes.
 * Called by Stripe webhook handlers above.
 */
async function _upgradeUserTier(
  payload: any,
  stripeCustomerId: string,
  tier: 'free' | 'pro',
): Promise<void> {
  try {
    // Find user by stripeCustomerId
    const { docs } = await (payload as any).find({
      collection: 'users',
      where: { stripeCustomerId: { equals: stripeCustomerId } },
      limit: 1,
    })
    if (docs.length > 0) {
      await (payload as any).update({
        collection: 'users',
        id: docs[0].id,
        data: { tier },
      })
    }
  } catch (e) {
    console.error(`[Stripe Webhook] Failed to update tier: ${e}`)
  }
}
