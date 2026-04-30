'use client'

import React from 'react'
import PublicNav from '@/features/layout/PublicNav'

export default function PrivacyPage() {
  return (
    <main className="min-h-screen bg-background font-sans text-foreground">
      <PublicNav page="privacy" />

      <div className="mx-auto max-w-3xl px-6 pb-20 pt-24">
        <h1 className="text-4xl font-extrabold mb-8">Privacy Policy</h1>
        
        <div className="space-y-8 text-muted-foreground leading-relaxed">
          <section>
            <h2 className="text-xl font-bold text-foreground mb-3">1. Information We Collect</h2>
            <p>
              We collect information you provide directly to us, such as when you create an account, upload documents, or communicate with us. This includes your email address, name, and the content of your queries.
            </p>
          </section>

          <section>
            <h2 className="text-xl font-bold text-foreground mb-3">2. Use of Information</h2>
            <p>
              We use the information we collect to provide, maintain, and improve our Service. This includes processing your documents to generate AI answers and managing your subscription.
            </p>
          </section>

          <section>
            <h2 className="text-xl font-bold text-foreground mb-3">3. Data Security</h2>
            <p>
              We take reasonable measures to protect your personal information and uploaded documents from loss, theft, and unauthorized access. Documents are stored securely and encrypted at rest.
            </p>
          </section>

          <section>
            <h2 className="text-xl font-bold text-foreground mb-3">4. Third-Party Services</h2>
            <p>
              We use third-party services like Stripe for payment processing and Azure/Ollama for AI inference. These services have their own privacy policies governing the use of your data.
            </p>
          </section>

          <section>
            <h2 className="text-xl font-bold text-foreground mb-3">5. Data Retention</h2>
            <p>
              We retain your personal information and uploaded documents as long as your account is active or as needed to provide you with the Service. You can delete your documents or account at any time.
            </p>
          </section>

          <section>
            <h2 className="text-xl font-bold text-foreground mb-3">6. Your Rights</h2>
            <p>
              You have the right to access, update, or delete your personal information. If you reside in the EEA or UK, you have additional rights under the GDPR.
            </p>
          </section>

          <section>
            <h2 className="text-xl font-bold text-foreground mb-3">7. Contact Us</h2>
            <p>
              If you have any questions about this Privacy Policy, please contact us at support@consultrag.com.
            </p>
          </section>

          <p className="pt-8 text-xs">Last updated: April 29, 2026</p>
        </div>
      </div>
    </main>
  )
}
