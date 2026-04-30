import type { Metadata } from 'next'

export const metadata: Metadata = {
  title: 'Privacy Policy | ConsultRAG',
  description: 'How we collect and protect your data at ConsultRAG.',
}

export default function PrivacyLayout({ children }: { children: React.ReactNode }) {
  return <>{children}</>
}
