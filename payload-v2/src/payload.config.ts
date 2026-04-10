import { buildConfig } from 'payload'
import { postgresAdapter } from '@payloadcms/db-postgres'
import { lexicalEditor } from '@payloadcms/richtext-lexical'
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
import { Evaluations } from './collections/Evaluations'
import { ChatSessions } from './collections/ChatSessions'
import { ChatMessages } from './collections/ChatMessages'
import { Media } from './collections/Media'
import { PdfUploads } from './collections/PdfUploads'
import { seedEndpoint } from './collections/endpoints'

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
    Evaluations,
    ChatSessions,
    ChatMessages,
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
  endpoints: [seedEndpoint],
  plugins: [],
})
