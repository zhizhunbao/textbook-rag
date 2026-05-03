/**
 * i18n locale dictionaries — English / Chinese bilingual messages
 *
 * Architecture:
 *   - Flat key structure kept for backward compatibility (`t.appName`)
 *   - Keys grouped by section via comments for maintainability
 *   - `tpl()` helper for safe string interpolation: `tpl(t.deleteConfirm, { count: 3 })`
 */

export type Locale = 'en' | 'zh'

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
  appName: 'ConsultRAG',
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
  loginHeading: 'ConsultRAG',
  loginSubheading: 'Sign in to access the AI-powered consulting assistant',
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
  chatWelcomeTitle: 'ConsultRAG Assistant',
  chatWelcomeBody: 'Ask your consulting questions. The AI will search across {count} knowledge base documents.',
  chatWelcomeHint: 'Browse suggested questions in the panel on the right →',
  chatSearchAllDocs: 'Searching all {count} documents',
  chatPlaceholderSingle: 'Ask about {title}...',
  chatPlaceholderMulti: 'Ask your question...',
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
// 中文 (Chinese)
// ────────────────────────────────────────

const zh: Messages = {
  // Common
  appName: 'ConsultRAG',
  appVersion: 'v2.0',
  signIn: '登录',
  signOut: '退出登录',
  startAsking: '开始提问',
  settings: '设置',
  collapse: '收起',
  adminAccess: '管理员入口',
  goToAdminPanel: '进入管理后台 →',

  // Hero
  heroTitle1: 'AI 智能',
  heroTitleHighlight: '顾问助手',
  heroSubtitle: '向 AI 专业顾问提问，获得即时、准确的回答，每条回答都附带来源追溯和页码引用。',

  // Stats
  statMultiTextbook: '知识文档',
  statDeepTrace: '对话次数',
  statPageCitations: '已回答问题',
  statMultiModels: 'AI 模型',

  // Features
  featuresTitle: '核心功能',
  featuresSubtitle: '帮助您高效获取专业咨询的全部工具',
  featureQATitle: '智能问答',
  featureQADesc: '用自然语言提问，AI 基于专业知识库文档为您提供精准回答。',
  featurePDFTitle: 'PDF 阅读与高亮',
  featurePDFDesc: '聊天界面与 PDF 并排显示，来源段落直接在 PDF 页面高亮标注。',
  featureTraceTitle: '完整追溯与分析',
  featureTraceDesc: '查看 AI 如何找到答案 — 检索评分、片段排名和完整查询追踪。',

  // How It Works
  howTitle: '如何使用',
  howSubtitle: '三步即可开始',
  howStep1Title: '上传文档',
  howStep1Desc: '管理员上传 PDF 文档，系统自动解析、分块并建立索引。',
  howStep2Title: '提出问题',
  howStep2Desc: '用自然语言输入问题，AI 将搜索所有已索引的文档内容。',
  howStep3Title: '获取引用回答',
  howStep3Desc: '获得精准回答并附带页码级引用。点击来源即可跳转到 PDF 对应页面。',

  // Pricing
  pricingTitle: '简单透明的定价',
  pricingSubtitle: '免费开始使用，按需升级。',
  pricingGetStarted: '立即开始',
  pricingUpgrade: '升级到专业版',
  pricingPopular: '推荐',

  // CTA
  ctaTitle: '准备好开始了吗？',
  ctaSubtitle: '登录并立即开始向 AI 顾问提问。',

  // Login
  loginHeading: 'ConsultRAG',
  loginSubheading: '登录以使用 AI 智能顾问助手',
  emailLabel: '邮箱',
  emailPlaceholder: 'you@example.com',
  passwordLabel: '密码',
  passwordPlaceholder: '请输入密码',
  signingIn: '登录中...',
  loginErrorEmpty: '请输入邮箱和密码',
  loginErrorFailed: '登录失败，请检查您的账号和密码。',
  loginNoAccount: '还没有账号？',
  loginGoToRegister: '立即注册 →',

  // Register
  registerHeading: '创建账号',
  registerSubheading: '注册以使用 AI 智能顾问助手',
  registerDisplayNameLabel: '显示名称（可选）',
  registerDisplayNamePlaceholder: '您的姓名',
  registerPasswordPlaceholder: '至少 6 个字符',
  registerConfirmPasswordLabel: '确认密码',
  registerConfirmPasswordPlaceholder: '再次输入密码',
  registerSubmit: '创建账号',
  registerCreating: '创建中...',
  registerErrorEmpty: '请输入邮箱和密码',
  registerErrorShortPassword: '密码至少需要 6 个字符',
  registerErrorPasswordMismatch: '两次输入的密码不一致',
  registerErrorEmailExists: '该邮箱已注册，请直接登录。',
  registerErrorFailed: '注册失败，请重试。',
  registerHasAccount: '已有账号？',
  registerGoToLogin: '去登录 →',

  // Sidebar Nav
  navNewChat: '新对话',
  navReaders: '文档库',
  navQuestionGen: '问题生成',
  navGroupChat: '对话',
  navGroupResources: '资源',
  navGroupAdmin: '管理',
  navGroupDataPipeline: '数据管线',
  navGroupQueryPipeline: '查询管线',
  navGroupQuality: '质量',
  navAnalytics: '分析',
  navEvaluation: '评估',
  navFeedback: '反馈',
  navLlms: '大模型',
  navResponseSynthesizers: '提示词',
  navAcquisition: '数据源',
  navIngestion: '数据摄入',
  navRetrievers: '检索器',
  navQueryEngine: '查询引擎',
  navSeed: '初始化数据',
  navReports: '报告',
  navConsulting: '顾问咨询',
  navPersonas: '角色管理',

  // Upload
  uploadPdf: '上传 PDF',
  uploadDragDrop: '拖拽 PDF 文件到此处',
  uploadClickBrowse: '点击浏览',
  uploadOr: '或',
  uploadDropRelease: '松开以上传',
  uploadProgress: '上传中',
  uploadSuccess: '上传完成！正在处理...',
  uploadDismiss: '关闭',
  deleteConfirm: '确定删除 {count} 个文档吗？此操作不可撤销。',

  // Chat Panel
  chatWelcomeTitle: 'ConsultRAG 智能顾问',
  chatWelcomeBody: '提出您的咨询问题，AI 将从 {count} 篇知识库文档中为您检索回答。',
  chatWelcomeHint: '在右侧面板浏览推荐问题 →',
  chatSearchAllDocs: '正在搜索 {count} 篇文档',
  chatPlaceholderSingle: '关于 {title} 提问...',
  chatPlaceholderMulti: '请输入您的问题...',
  chatInputHint: 'Enter 发送 · Shift+Enter 换行',
  chatSendTitle: '发送消息 (Enter)',
  chatSearching: '正在搜索文档…',
  chatJumpToLatest: '↓ 跳转到最新',

  // Onboarding
  onboardingTitle: '欢迎！选择您的咨询服务',
  onboardingSubtitle: '选择一个顾问角色，开始 AI 智能咨询。',
  onboardingConfirm: '确认选择',
  onboardingNoPersona: '请选择一个角色以继续',
  onboardingSaving: '保存中...',
  sidebarPersonaLabel: '当前角色',
  sidebarNoPersona: '未选择角色',
}

export const messages: Record<Locale, Messages> = { en, zh }
