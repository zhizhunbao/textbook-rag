/**
 * i18n locale dictionaries — English / French bilingual messages
 *
 * Architecture:
 *   - Flat key structure kept for backward compatibility (`t.appName`)
 *   - Keys grouped by section via comments for maintainability
 *   - `tpl()` helper for safe string interpolation: `tpl(t.deleteConfirm, { count: 3 })`
 */

export type Locale = 'en' | 'fr'

// ────────────────────────────────────────
// Message shape — grouped by UI section
// ────────────────────────────────────────

export interface Messages {
  // ── Common ──
  appName: string
  appVersion: string
  signIn: string
  signOut: string
  startAsking: string
  settings: string
  collapse: string
  adminAccess: string
  goToAdminPanel: string

  // ── HomePage Hero ──
  heroTitle1: string
  heroTitleHighlight: string
  heroSubtitle: string

  // ── HomePage Stats ──
  statMultiTextbook: string
  statDeepTrace: string
  statPageCitations: string
  statMultiModels: string

  // ── HomePage Features ──
  featuresTitle: string
  featuresSubtitle: string
  featureQATitle: string
  featureQADesc: string
  featurePDFTitle: string
  featurePDFDesc: string
  featureTraceTitle: string
  featureTraceDesc: string

  // ── HomePage How It Works ──
  howTitle: string
  howSubtitle: string
  howStep1Title: string
  howStep1Desc: string
  howStep2Title: string
  howStep2Desc: string
  howStep3Title: string
  howStep3Desc: string

  // ── HomePage Pricing ──
  pricingTitle: string
  pricingSubtitle: string
  pricingGetStarted: string
  pricingUpgrade: string
  pricingPopular: string

  // ── HomePage CTA ──
  ctaTitle: string
  ctaSubtitle: string

  // ── LoginForm ──
  loginHeading: string
  loginSubheading: string
  emailLabel: string
  emailPlaceholder: string
  passwordLabel: string
  passwordPlaceholder: string
  signingIn: string
  loginErrorEmpty: string
  loginErrorFailed: string
  loginNoAccount: string
  loginGoToRegister: string

  // ── RegisterForm ──
  registerHeading: string
  registerSubheading: string
  registerDisplayNameLabel: string
  registerDisplayNamePlaceholder: string
  registerPasswordPlaceholder: string
  registerConfirmPasswordLabel: string
  registerConfirmPasswordPlaceholder: string
  registerSubmit: string
  registerCreating: string
  registerErrorEmpty: string
  registerErrorShortPassword: string
  registerErrorPasswordMismatch: string
  registerErrorEmailExists: string
  registerErrorFailed: string
  registerHasAccount: string
  registerGoToLogin: string

  // ── Sidebar Nav ──
  navNewChat: string
  navReaders: string
  navQuestionGen: string
  navGroupChat: string
  navGroupResources: string
  navGroupAdmin: string
  navGroupDataPipeline: string
  navGroupQueryPipeline: string
  navGroupQuality: string
  navAnalytics: string
  navEvaluation: string
  navFeedback: string
  navLlms: string
  navResponseSynthesizers: string
  navAcquisition: string
  navIngestion: string
  navRetrievers: string
  navQueryEngine: string
  navSeed: string
  navReports: string
  navConsulting: string
  navPersonas: string

  // ── Upload ──
  uploadPdf: string
  uploadDragDrop: string
  uploadClickBrowse: string
  uploadOr: string
  uploadDropRelease: string
  uploadProgress: string
  uploadSuccess: string
  uploadDismiss: string
  deleteConfirm: string       // uses {count}

  // ── Chat Panel ──
  chatWelcomeTitle: string
  chatWelcomeBody: string      // uses {count}
  chatWelcomeHint: string
  chatSearchAllDocs: string    // uses {count}
  chatPlaceholderSingle: string // uses {title}
  chatPlaceholderMulti: string
  chatInputHint: string
  chatSendTitle: string
  chatSearching: string
  chatJumpToLatest: string

  // ── Onboarding ──
  onboardingTitle: string
  onboardingSubtitle: string
  onboardingConfirm: string
  onboardingNoPersona: string
  onboardingSaving: string
  sidebarPersonaLabel: string
  sidebarNoPersona: string
}

// ────────────────────────────────────────
// String interpolation helper
// ────────────────────────────────────────

/**
 * Lightweight template interpolation.
 *
 * @example tpl("Delete {count} book(s)?", { count: 3 })
 *          // → "Delete 3 book(s)?"
 */
export function tpl(template: string, vars: Record<string, string | number>): string {
  return template.replace(/\{(\w+)\}/g, (_, key: string) =>
    key in vars ? String(vars[key]) : `{${key}}`,
  )
}

// ────────────────────────────────────────
// English
// ────────────────────────────────────────

const en: Messages = {
  // Common
  appName: 'EcDev Research',
  appVersion: 'v2.0',
  signIn: 'Sign In',
  signOut: 'Sign Out',
  startAsking: 'Start Asking',
  settings: 'Settings',
  collapse: 'Collapse',
  adminAccess: 'Admin access?',
  goToAdminPanel: 'Go to Admin Panel →',

  // Hero
  heroTitle1: 'AI-Powered',
  heroTitleHighlight: ' Research Assistant',
  heroSubtitle: 'Ask questions about City of Ottawa economic reports and get instant, accurate answers with deep source tracing and page-level citations.',

  // Stats
  statMultiTextbook: 'Documents',
  statDeepTrace: 'Conversations',
  statPageCitations: 'Questions Asked',
  statMultiModels: 'AI Models',

  // Features
  featuresTitle: 'Powerful Features',
  featuresSubtitle: 'Everything you need to analyze economic data smarter',
  featureQATitle: 'Intelligent Q&A',
  featureQADesc: 'Ask natural language questions and get accurate answers grounded in official City of Ottawa economic reports.',
  featurePDFTitle: 'PDF Viewer with Highlights',
  featurePDFDesc: 'View reports side-by-side with the chat. Source passages are highlighted directly on the PDF page.',
  featureTraceTitle: 'Full Trace & Analytics',
  featureTraceDesc: 'See exactly how the AI found its answer — retrieval scores, chunk rankings, and full query trace.',

  // How It Works
  howTitle: 'How It Works',
  howSubtitle: 'Three simple steps to get started',
  howStep1Title: 'Upload Reports',
  howStep1Desc: 'Admin uploads PDF reports. The system automatically ingests, chunks, and indexes the content.',
  howStep2Title: 'Ask Questions',
  howStep2Desc: 'Type a question in natural language. The AI searches across all indexed report content.',
  howStep3Title: 'Get Cited Answers',
  howStep3Desc: 'Receive accurate answers with page-level citations. Click sources to jump to the exact PDF page.',

  // Pricing
  pricingTitle: 'Simple, transparent pricing',
  pricingSubtitle: 'Start free. Upgrade when you need more.',
  pricingGetStarted: 'Get started',
  pricingUpgrade: 'Upgrade to Pro',
  pricingPopular: 'Recommended',

  // CTA
  ctaTitle: 'Ready to Explore the Data?',
  ctaSubtitle: 'Sign in and start asking questions about Ottawa economic reports today.',

  // Login
  loginHeading: 'EcDev Research',
  loginSubheading: 'Sign in to access the AI-powered research assistant',
  emailLabel: 'Email',
  emailPlaceholder: 'you@example.com',
  passwordLabel: 'Password',
  passwordPlaceholder: 'Enter your password',
  signingIn: 'Signing in...',
  loginErrorEmpty: 'Please enter both email and password',
  loginErrorFailed: 'Login failed. Please check your credentials.',
  loginNoAccount: 'Don\'t have an account?',
  loginGoToRegister: 'Register now →',

  // Register
  registerHeading: 'Create Account',
  registerSubheading: 'Register to access the AI-powered consulting assistant',
  registerDisplayNameLabel: 'Display Name (optional)',
  registerDisplayNamePlaceholder: 'Your name',
  registerPasswordPlaceholder: 'Minimum 6 characters',
  registerConfirmPasswordLabel: 'Confirm Password',
  registerConfirmPasswordPlaceholder: 'Re-enter your password',
  registerSubmit: 'Create Account',
  registerCreating: 'Creating account...',
  registerErrorEmpty: 'Please enter your email and password',
  registerErrorShortPassword: 'Password must be at least 6 characters',
  registerErrorPasswordMismatch: 'Passwords do not match',
  registerErrorEmailExists: 'This email is already registered. Try logging in instead.',
  registerErrorFailed: 'Registration failed. Please try again.',
  registerHasAccount: 'Already have an account?',
  registerGoToLogin: 'Sign in →',

  // Sidebar Nav
  navNewChat: 'New Chat',
  navReaders: 'Library',
  navQuestionGen: 'Question Gen',
  navGroupChat: 'Chat',
  navGroupResources: 'Resources',
  navGroupAdmin: 'Admin',
  navGroupDataPipeline: 'Data Pipeline',
  navGroupQueryPipeline: 'Query Pipeline',
  navGroupQuality: 'Quality',
  navAnalytics: 'Analytics',
  navEvaluation: 'Evaluation',
  navFeedback: 'Feedback',
  navLlms: 'LLMs',
  navResponseSynthesizers: 'Prompts',
  navAcquisition: 'Data Sources',
  navIngestion: 'Ingestion',
  navRetrievers: 'Retrievers',
  navQueryEngine: 'Query Engine',
  navSeed: 'Seed Database',
  navReports: 'Reports',
  navConsulting: 'Consulting',
  navPersonas: 'Personas',

  // Upload
  uploadPdf: 'Upload PDF',
  uploadDragDrop: 'Drag & drop a PDF here',
  uploadClickBrowse: 'click to browse',
  uploadOr: 'or',
  uploadDropRelease: 'Drop file to upload',
  uploadProgress: 'Uploading',
  uploadSuccess: 'Upload complete! Processing...',
  uploadDismiss: 'Dismiss',
  deleteConfirm: 'Delete {count} document(s)? This cannot be undone.',

  // Chat Panel
  chatWelcomeTitle: 'EcDev Research Assistant',
  chatWelcomeBody: 'Searching across {count} documents. Ask about employment, housing, inflation, or any economic indicator.',
  chatWelcomeHint: 'Browse suggested questions in the panel on the right →',
  chatSearchAllDocs: 'Searching all {count} documents',
  chatPlaceholderSingle: 'Ask about {title}...',
  chatPlaceholderMulti: 'Ask about Ottawa economic data...',
  chatInputHint: 'Enter to send · Shift+Enter for new line',
  chatSendTitle: 'Send message (Enter)',
  chatSearching: 'Searching the documents…',
  chatJumpToLatest: '↓ Jump to latest',

  // Onboarding
  onboardingTitle: 'Welcome! Choose Your Consulting Service',
  onboardingSubtitle: 'Select a role to get started with AI-powered consulting.',
  onboardingConfirm: 'Confirm Selection',
  onboardingNoPersona: 'Please select a role to continue',
  onboardingSaving: 'Saving...',
  sidebarPersonaLabel: 'Current Role',
  sidebarNoPersona: 'No role selected',
}

// ────────────────────────────────────────
// Français
// ────────────────────────────────────────

const fr: Messages = {
  // Common
  appName: 'EcDev Research',
  appVersion: 'v2.0',
  signIn: 'Se connecter',
  signOut: 'Se déconnecter',
  startAsking: 'Poser une question',
  settings: 'Paramètres',
  collapse: 'Réduire',
  adminAccess: 'Accès administrateur ?',
  goToAdminPanel: 'Accéder au panneau admin →',

  // Hero
  heroTitle1: 'Assistant de recherche',
  heroTitleHighlight: ' propulsé par l\'IA',
  heroSubtitle: 'Posez des questions sur les rapports économiques de la Ville d\'Ottawa et obtenez des réponses instantanées et précises avec traçabilité des sources et citations au niveau de la page.',

  // Stats
  statMultiTextbook: 'Documents',
  statDeepTrace: 'Conversations',
  statPageCitations: 'Questions posées',
  statMultiModels: 'Modèles IA',

  // Features
  featuresTitle: 'Fonctionnalités',
  featuresSubtitle: 'Tout ce dont vous avez besoin pour analyser les données économiques',
  featureQATitle: 'Questions-réponses intelligentes',
  featureQADesc: 'Posez des questions en langage naturel et obtenez des réponses précises basées sur les rapports économiques officiels de la Ville d\'Ottawa.',
  featurePDFTitle: 'Visionneuse PDF avec surbrillance',
  featurePDFDesc: 'Consultez les rapports côte à côte avec le chat. Les passages sources sont surlignés directement sur la page PDF.',
  featureTraceTitle: 'Traçabilité et analytique complètes',
  featureTraceDesc: 'Voyez exactement comment l\'IA a trouvé sa réponse — scores de recherche, classement des segments et trace complète de la requête.',

  // How It Works
  howTitle: 'Comment ça marche',
  howSubtitle: 'Trois étapes simples pour commencer',
  howStep1Title: 'Téléverser des rapports',
  howStep1Desc: 'L\'administrateur téléverse des rapports PDF. Le système ingère, segmente et indexe automatiquement le contenu.',
  howStep2Title: 'Poser des questions',
  howStep2Desc: 'Saisissez une question en langage naturel. L\'IA effectue une recherche dans tous les contenus indexés.',
  howStep3Title: 'Obtenir des réponses citées',
  howStep3Desc: 'Recevez des réponses précises avec des citations au niveau de la page. Cliquez sur une source pour accéder à la page PDF exacte.',

  // Pricing
  pricingTitle: 'Tarification simple et transparente',
  pricingSubtitle: 'Commencez gratuitement. Passez à la version supérieure quand vous en avez besoin.',
  pricingGetStarted: 'Commencer',
  pricingUpgrade: 'Passer à Pro',
  pricingPopular: 'Recommandé',

  // CTA
  ctaTitle: 'Prêt à explorer les données ?',
  ctaSubtitle: 'Connectez-vous et commencez à poser des questions sur les rapports économiques d\'Ottawa.',

  // Login
  loginHeading: 'EcDev Research',
  loginSubheading: 'Connectez-vous pour accéder à l\'assistant de recherche propulsé par l\'IA',
  emailLabel: 'Courriel',
  emailPlaceholder: 'vous@exemple.com',
  passwordLabel: 'Mot de passe',
  passwordPlaceholder: 'Entrez votre mot de passe',
  signingIn: 'Connexion en cours...',
  loginErrorEmpty: 'Veuillez saisir votre courriel et votre mot de passe',
  loginErrorFailed: 'Échec de la connexion. Veuillez vérifier vos identifiants.',
  loginNoAccount: 'Pas de compte ?',
  loginGoToRegister: 'Créer un compte →',

  // Register
  registerHeading: 'Créer un compte',
  registerSubheading: 'Inscrivez-vous pour accéder à l\'assistant de consultation propulsé par l\'IA',
  registerDisplayNameLabel: 'Nom d\'affichage (optionnel)',
  registerDisplayNamePlaceholder: 'Votre nom',
  registerPasswordPlaceholder: 'Minimum 6 caractères',
  registerConfirmPasswordLabel: 'Confirmer le mot de passe',
  registerConfirmPasswordPlaceholder: 'Saisissez à nouveau votre mot de passe',
  registerSubmit: 'Créer un compte',
  registerCreating: 'Création du compte...',
  registerErrorEmpty: 'Veuillez saisir votre courriel et votre mot de passe',
  registerErrorShortPassword: 'Le mot de passe doit comporter au moins 6 caractères',
  registerErrorPasswordMismatch: 'Les mots de passe ne correspondent pas',
  registerErrorEmailExists: 'Ce courriel est déjà enregistré. Essayez de vous connecter.',
  registerErrorFailed: 'Échec de l\'inscription. Veuillez réessayer.',
  registerHasAccount: 'Vous avez déjà un compte ?',
  registerGoToLogin: 'Se connecter →',

  // Sidebar Nav
  navNewChat: 'Nouvelle conversation',
  navReaders: 'Bibliothèque',
  navQuestionGen: 'Génération de questions',
  navGroupChat: 'Chat',
  navGroupResources: 'Ressources',
  navGroupAdmin: 'Administration',
  navGroupDataPipeline: 'Pipeline de données',
  navGroupQueryPipeline: 'Pipeline de requêtes',
  navGroupQuality: 'Qualité',
  navAnalytics: 'Analytique',
  navEvaluation: 'Évaluation',
  navFeedback: 'Rétroaction',
  navLlms: 'LLMs',
  navResponseSynthesizers: 'Prompts',
  navAcquisition: 'Sources de données',
  navIngestion: 'Ingestion',
  navRetrievers: 'Récupérateurs',
  navQueryEngine: 'Moteur de requêtes',
  navSeed: 'Base de données initiale',
  navReports: 'Rapports',
  navConsulting: 'Consultation',
  navPersonas: 'Personas',

  // Upload
  uploadPdf: 'Téléverser un PDF',
  uploadDragDrop: 'Glissez-déposez un PDF ici',
  uploadClickBrowse: 'cliquez pour parcourir',
  uploadOr: 'ou',
  uploadDropRelease: 'Relâchez pour téléverser',
  uploadProgress: 'Téléversement en cours',
  uploadSuccess: 'Téléversement terminé ! Traitement en cours...',
  uploadDismiss: 'Fermer',
  deleteConfirm: 'Supprimer {count} document(s) ? Cette action est irréversible.',

  // Chat Panel
  chatWelcomeTitle: 'Assistant de recherche EcDev',
  chatWelcomeBody: 'Recherche dans {count} documents. Posez des questions sur l\'emploi, le logement, l\'inflation ou tout indicateur économique.',
  chatWelcomeHint: 'Parcourez les questions suggérées dans le panneau de droite →',
  chatSearchAllDocs: 'Recherche dans les {count} documents',
  chatPlaceholderSingle: 'Poser une question sur {title}...',
  chatPlaceholderMulti: 'Poser une question sur les données économiques d\'Ottawa...',
  chatInputHint: 'Entrée pour envoyer · Maj+Entrée pour un saut de ligne',
  chatSendTitle: 'Envoyer le message (Entrée)',
  chatSearching: 'Recherche dans les documents…',
  chatJumpToLatest: '↓ Aller au plus récent',

  // Onboarding
  onboardingTitle: 'Bienvenue ! Choisissez votre service de consultation',
  onboardingSubtitle: 'Sélectionnez un rôle pour commencer la consultation assistée par IA.',
  onboardingConfirm: 'Confirmer la sélection',
  onboardingNoPersona: 'Veuillez sélectionner un rôle pour continuer',
  onboardingSaving: 'Enregistrement...',
  sidebarPersonaLabel: 'Rôle actuel',
  sidebarNoPersona: 'Aucun rôle sélectionné',
}

export const messages: Record<Locale, Messages> = { en, fr }
