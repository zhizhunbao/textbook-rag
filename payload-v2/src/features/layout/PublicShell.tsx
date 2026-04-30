'use client'

import Image from 'next/image'
import PublicNav from './PublicNav'

/**
 * PublicShell — shared background + nav wrapper for auth & landing pages.
 *
 * Renders the hero background image with a dark gradient overlay,
 * the PublicNav header, and the page content as children.
 */
export default function PublicShell({
  page = 'landing',
  children,
}: {
  page?: 'landing' | 'login' | 'register'
  children: React.ReactNode
}) {
  return (
    <main className="relative min-h-screen overflow-hidden bg-background text-foreground">
      {/* Shared hero background */}
      <Image
        src="/consultrag-hero.png"
        alt="ConsultRAG workspace background"
        fill
        priority
        sizes="100vw"
        className="object-cover"
      />
      <div className="absolute inset-0 bg-[linear-gradient(90deg,rgba(2,6,23,0.94)_0%,rgba(15,23,42,0.78)_48%,rgba(15,23,42,0.48)_100%)]" />

      {/* Shared nav */}
      <PublicNav page={page} />

      {/* Page content */}
      {children}
    </main>
  )
}
