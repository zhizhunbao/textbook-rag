import { withPayload } from '@payloadcms/next/withPayload'
import createNextIntlPlugin from 'next-intl/plugin'
import type { NextConfig } from 'next'

const withNextIntl = createNextIntlPlugin()

const nextConfig: NextConfig = {
  devIndicators: false,
  webpack: (config) => {
    // Required for react-pdf / pdfjs-dist in Next.js webpack
    config.resolve.alias.canvas = false
    config.resolve.alias.encoding = false

    // pdfjs-dist v4 ships .mjs files that need 'javascript/auto'
    // to prevent "Object.defineProperty called on non-object" webpack error
    config.module.rules.push({
      test: /pdf\.mjs$/,
      include: /node_modules[/\\]pdfjs-dist/,
      type: 'javascript/auto',
    })

    return config
  },
}

// Compose: next-intl → Payload
export default withPayload(withNextIntl(nextConfig))
