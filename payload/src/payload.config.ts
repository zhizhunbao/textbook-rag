import { buildConfig } from 'payload'
import { sqliteAdapter } from '@payloadcms/db-sqlite'
import { lexicalEditor } from '@payloadcms/richtext-lexical'
import path from 'path'
import { fileURLToPath } from 'url'
import sharp from 'sharp'

import { Books } from './collections/Books'
import { Chapters } from './collections/Chapters'
import { Chunks } from './collections/Chunks'
import { Users } from './collections/Users'
import { PipelineTasks } from './collections/PipelineTasks'
import { QueryLogs } from './collections/QueryLogs'

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
    Books,
    Chapters,
    Chunks,
    PipelineTasks,
    QueryLogs,
  ],
  editor: lexicalEditor(),
  secret: process.env.PAYLOAD_SECRET || '',
  typescript: {
    outputFile: path.resolve(dirname, 'payload-types.ts'),
  },
  db: sqliteAdapter({
    client: {
      url: process.env.DATABASE_URI || 'file:../data/payload.db',
    },
  }),
  sharp,
  upload: {
    limits: {
      fileSize: 50_000_000, // 50 MB — for PDFs
    },
  },
  plugins: [],
})

