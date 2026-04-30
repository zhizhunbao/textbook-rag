'use client'

import React from 'react'
import PublicNav from '@/features/layout/PublicNav'

export default function TermsPage() {
  return (
    <main className="min-h-screen bg-background font-sans text-foreground">
      <PublicNav page="terms" />

      <div className="mx-auto max-w-3xl px-6 pb-20 pt-24">
        <h1 className="text-4xl font-extrabold mb-8">Terms of Service</h1>
        
        <div className="space-y-8 text-muted-foreground leading-relaxed">
          <section>
            <h2 className="text-xl font-bold text-foreground mb-3">1. Acceptance of Terms</h2>
            <p>
              By accessing or using ConsultRAG (&quot;the Service&quot;), you agree to be bound by these Terms of Service. If you do not agree to these terms, please do not use the Service.
            </p>
          </section>

          <section>
            <h2 className="text-xl font-bold text-foreground mb-3">2. Description of Service</h2>
            <p>
              ConsultRAG provides AI-powered consulting services using Retrieval-Augmented Generation (RAG). The service allows users to query specialized knowledge bases and upload personal documents for analysis.
            </p>
          </section>

          <section>
            <h2 className="text-xl font-bold text-foreground mb-3">3. User Accounts</h2>
            <p>
              You are responsible for maintaining the confidentiality of your account credentials and for all activities that occur under your account. You must notify us immediately of any unauthorized use of your account.
            </p>
          </section>

          <section>
            <h2 className="text-xl font-bold text-foreground mb-3">4. Subscription and Payments</h2>
            <p>
              Certain features of the Service require a paid subscription. Payments are processed through Stripe. By subscribing, you agree to the pricing and billing terms presented to you at the time of purchase.
            </p>
          </section>

          <section>
            <h2 className="text-xl font-bold text-foreground mb-3">5. Data Privacy and Content</h2>
            <p>
              Your use of the Service is also governed by our Privacy Policy. You retain all rights to the documents you upload, but you grant ConsultRAG a license to process these documents solely for the purpose of providing the Service to you.
            </p>
          </section>

          <section>
            <h2 className="text-xl font-bold text-foreground mb-3">6. Limitation of Liability</h2>
            <p>
              ConsultRAG is provided &quot;as is&quot; without warranties of any kind. AI-generated answers should be verified by professional consultants. We are not liable for any decisions made based on AI-generated content.
            </p>
          </section>

          <section>
            <h2 className="text-xl font-bold text-foreground mb-3">7. Changes to Terms</h2>
            <p>
              We reserve the right to modify these terms at any time. We will notify users of any significant changes by posting the new terms on this page.
            </p>
          </section>

          <p className="pt-8 text-xs">Last updated: April 29, 2026</p>
        </div>
      </div>
    </main>
  )
}
