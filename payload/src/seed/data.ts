/**
 * Seed data definitions — shared by CLI scripts and API route.
 *
 * Each collection has:
 *   - data array
 *   - slug (Payload collection slug)
 *   - uniqueField (field used for upsert dedup)
 */

// ─── LLM Models ──────────────────────────────────────────────────────────────

export const llmModelsData = [
  {
    name: 'qwen3.5:4b',
    displayName: 'Qwen 3.5 4B',
    provider: 'ollama',
    description:
      'Excellent multilingual model with strong Chinese and English support. Best balance of quality and speed for RAG tasks. Supports 128K context.',
    useCases: ['RAG Q&A', 'Summarization', 'Translation', 'General'],
    languages: 'en, zh, ja, ko, fr, de, es',
    parameterSize: '4B',
    contextWindow: 131072,
    maxOutputTokens: 8192,
    minRamGb: 6,
    quantization: 'Q4_K_M',
    isFree: true,
    costPer1kInput: 0,
    costPer1kOutput: 0,
    isDefault: true,
    isEnabled: true,
    sortOrder: 1,
  },
  {
    name: 'qwen2.5:14b',
    displayName: 'Qwen 2.5 14B',
    provider: 'ollama',
    description:
      'Larger Qwen model with improved reasoning and analytical capabilities. Better for complex questions requiring deep understanding.',
    useCases: ['Complex Analysis', 'RAG Q&A', 'Report Generation', 'Reasoning'],
    languages: 'en, zh, ja, ko, fr, de, es',
    parameterSize: '14B',
    contextWindow: 131072,
    maxOutputTokens: 8192,
    minRamGb: 10,
    quantization: 'Q4_K_M',
    isFree: true,
    costPer1kInput: 0,
    costPer1kOutput: 0,
    isDefault: false,
    isEnabled: true,
    sortOrder: 2,
  },
  {
    name: 'llama3.1:8b',
    displayName: 'Llama 3.1 8B',
    provider: 'ollama',
    description:
      "Meta's open-source model. Strong English performance, good for general Q&A. Fast inference speed.",
    useCases: ['General Q&A', 'English Content', 'Fast Processing'],
    languages: 'en, de, fr, it, pt, hi, es, th',
    parameterSize: '8B',
    contextWindow: 131072,
    maxOutputTokens: 4096,
    minRamGb: 6,
    quantization: 'Q4_K_M',
    isFree: true,
    costPer1kInput: 0,
    costPer1kOutput: 0,
    isDefault: false,
    isEnabled: true,
    sortOrder: 3,
  },
  {
    name: 'deepseek-r1:8b',
    displayName: 'DeepSeek R1 8B',
    provider: 'ollama',
    description:
      'Specialized in reasoning and step-by-step problem solving. Shows chain-of-thought process. Excellent for analysis mode.',
    useCases: ['Reasoning', 'Step-by-step Analysis', 'Math', 'Logic'],
    languages: 'en, zh',
    parameterSize: '8B',
    contextWindow: 65536,
    maxOutputTokens: 8192,
    minRamGb: 6,
    quantization: 'Q4_K_M',
    isFree: true,
    costPer1kInput: 0,
    costPer1kOutput: 0,
    isDefault: false,
    isEnabled: true,
    sortOrder: 4,
  },
  {
    name: 'gpt-4o',
    displayName: 'GPT-4o',
    provider: 'azure_openai',
    description:
      "OpenAI's flagship model. Top-tier quality across all tasks. Requires Azure OpenAI API key.",
    useCases: ['All Tasks', 'Complex Reasoning', 'High Quality Output'],
    languages: 'All major languages',
    parameterSize: 'Unknown',
    contextWindow: 128000,
    maxOutputTokens: 16384,
    minRamGb: 0,
    quantization: 'N/A (Cloud)',
    isFree: false,
    costPer1kInput: 0.0025,
    costPer1kOutput: 0.01,
    isDefault: false,
    isEnabled: false,
    sortOrder: 10,
  },
]

// ─── Prompt Modes ────────────────────────────────────────────────────────────

export const promptModesData = [
  {
    name: 'Default',
    slug: 'default',
    description: 'Balanced answers with source citations',
    systemPrompt:
      "You are a knowledgeable assistant. Answer the user's question based ONLY on the provided context. " +
      'Cite sources using [N] notation. If the context does not contain sufficient information, say so honestly.',
    icon: 'lightbulb',
    isDefault: true,
  },
  {
    name: 'Learning',
    slug: 'learning',
    description: 'Concept-focused explanations for studying',
    systemPrompt:
      'You are a patient tutor helping a student understand concepts from their textbook. ' +
      'Answer based ONLY on the provided context. Focus on explaining WHY and HOW, not just WHAT. ' +
      'Use analogies when helpful. Break complex ideas into steps. Cite sources as [N]. ' +
      'If the student seems confused, offer alternative explanations.',
    icon: 'book',
    isDefault: false,
  },
  {
    name: 'Analysis',
    slug: 'analysis',
    description: 'Structured reports with comparisons and tables',
    systemPrompt:
      'You are an analytical assistant. Answer based ONLY on the provided context. ' +
      'Structure your response with clear sections. Use tables or bullet lists to compare concepts. ' +
      'Highlight key differences, pros/cons, and trade-offs. Cite every claim with [N]. ' +
      'End with a brief summary of the main takeaways.',
    icon: 'chart',
    isDefault: false,
  },
  {
    name: 'Concise',
    slug: 'concise',
    description: 'Short, direct answers — maximum 3 sentences',
    systemPrompt:
      'You are a concise assistant. Give a short, direct answer using ONLY the provided context. ' +
      'Use [N] to cite sources. Maximum 3 sentences. No filler words.',
    icon: 'zap',
    isDefault: false,
  },
  {
    name: 'Detailed',
    slug: 'detailed',
    description: 'Comprehensive answers with examples and structure',
    systemPrompt:
      'You are a thorough assistant. Provide a comprehensive answer with examples where applicable, ' +
      'using ONLY the provided context. Cite every claim with [N] notation. Structure your response with clear paragraphs.',
    icon: 'align-left',
    isDefault: false,
  },
  {
    name: 'Academic',
    slug: 'academic',
    description: 'Formal academic style with objective tone',
    systemPrompt:
      'You are an academic writing assistant. Answer in formal academic style using ONLY the provided context. ' +
      'Cite sources as [N]. Avoid personal pronouns. Maintain a neutral, objective tone.',
    icon: 'graduation-cap',
    isDefault: false,
  },
  {
    name: 'Question Generation',
    slug: 'question-generation',
    description: 'Auto-generate study questions from textbook content (internal use)',
    systemPrompt:
      'You are a study assistant that generates questions STRICTLY based on the textbook excerpts provided below. ' +
      'RULES:\n' +
      '1. Every question MUST reference a specific concept, term, formula, method, or example that appears in the excerpts.\n' +
      '2. Do NOT generate generic questions like "What is the main topic?" or "What are the prerequisites?". ' +
      'Every question must be answerable ONLY from the given text.\n' +
      '3. NEVER reference page numbers, chapter numbers, section numbers, or figure numbers in your questions. ' +
      'Questions must be self-contained and answerable by searching for concepts, not by locating a specific page. ' +
      'BAD: "What is described on page 479?" GOOD: "What application of fast feature tracking involves interactive deformation?"\n' +
      '4. Include a mix: definition questions, comparison questions, "why" questions, and application questions.\n' +
      '5. The "topic_hint" should be a specific concept name from the excerpt (e.g., "BM25 Ranking", "Dependency Injection"), NOT generic labels.\n' +
      '\nGenerate exactly {count} questions. ' +
      'Return ONLY a JSON array. Each element must have: ' +
      '"question" (string), "book_title" (string, from the source), ' +
      '"topic_hint" (string, 2-4 word specific topic from the excerpt). ' +
      'Do NOT wrap in markdown code blocks.',
    icon: 'help-circle',
    isDefault: false,
  },
]

// ─── Query Templates ─────────────────────────────────────────────────────────

export const queryTemplatesData = [
  {
    name: 'Definition vs Comparison',
    category: 'disambiguation',
    triggerPatterns: ['what is', 'explain', 'tell me about', '什么是', '解释'],
    clarifyPrompt:
      'Are you looking for a definition or a comparison with related concepts?',
    clarifyPromptZh: '你想了解定义，还是与相关概念的对比？',
    suggestedQuestions: [
      'Give me the definition of {topic}',
      'Compare {topic} with related concepts',
      'Explain {topic} with examples',
    ],
    suggestedQuestionsZh: [
      '给我 {topic} 的定义',
      '将 {topic} 与相关概念进行对比',
      '用示例解释 {topic}',
    ],
    answerFormat:
      'Start with a clear definition, then provide context and examples.',
    answerFormatZh: '先给出清晰定义，然后提供上下文和示例。',
    isEnabled: true,
    sortOrder: 1,
  },
  {
    name: 'Broad Topic Narrowing',
    category: 'scope',
    triggerPatterns: ['how does', 'how to', 'everything about', '怎么', '如何', '关于'],
    clarifyPrompt:
      'This is a broad topic. Which aspect are you most interested in?',
    clarifyPromptZh: '这个话题比较宽泛，你最感兴趣哪个方面？',
    suggestedQuestions: [
      'How does {topic} work internally?',
      'What are the practical applications of {topic}?',
      'What are the advantages and disadvantages of {topic}?',
      'How is {topic} different from alternatives?',
    ],
    suggestedQuestionsZh: [
      '{topic} 的内部工作原理是什么？',
      '{topic} 有哪些实际应用？',
      '{topic} 的优缺点是什么？',
      '{topic} 与替代方案有何不同？',
    ],
    answerFormat:
      'Focus on the specific aspect requested. Use sections if covering multiple sub-topics.',
    answerFormatZh: '聚焦于所问的具体方面。如涉及多个子话题，请分节回答。',
    isEnabled: true,
    sortOrder: 2,
  },
  {
    name: 'Step-by-step vs Summary',
    category: 'format',
    triggerPatterns: ['how to implement', 'steps for', 'process of', '步骤', '实现', '流程'],
    clarifyPrompt:
      'Would you like a step-by-step walkthrough or a high-level summary?',
    clarifyPromptZh: '你想要逐步详解还是高层概述？',
    suggestedQuestions: [
      'Walk me through {topic} step by step',
      'Give me a high-level summary of {topic}',
      'What are the key steps in {topic}?',
    ],
    suggestedQuestionsZh: [
      '逐步讲解 {topic}',
      '给我 {topic} 的高层概述',
      '{topic} 的关键步骤是什么？',
    ],
    answerFormat:
      'Use numbered steps for walkthroughs. Use bullet points for summaries.',
    answerFormatZh: '详解用编号步骤，概述用要点列表。',
    isEnabled: true,
    sortOrder: 3,
  },
  {
    name: 'Deeper Understanding',
    category: 'followup',
    triggerPatterns: ['why', 'reason', 'cause', '为什么', '原因'],
    clarifyPrompt:
      'Do you want the theoretical reasoning or practical implications?',
    clarifyPromptZh: '你想了解理论原因还是实际影响？',
    suggestedQuestions: [
      'Why does {topic} work this way? (theory)',
      'What are the practical consequences of {topic}?',
      'What would happen if {topic} changed?',
    ],
    suggestedQuestionsZh: [
      '{topic} 为什么这样运作？（理论）',
      '{topic} 的实际后果是什么？',
      '如果 {topic} 改变了会怎样？',
    ],
    answerFormat:
      'Explain the underlying reasoning first, then discuss implications.',
    answerFormatZh: '先解释底层原因，再讨论影响。',
    isEnabled: true,
    sortOrder: 4,
  },
]

// ─── Seed config for the API route ───────────────────────────────────────────

export interface SeedCollection {
  label: string
  slug: string
  uniqueField: string
  data: Record<string, unknown>[]
}

export const seedCollections: SeedCollection[] = [
  { label: 'LLM Models', slug: 'llm-models', uniqueField: 'name', data: llmModelsData },
  { label: 'Prompt Modes', slug: 'prompt-modes', uniqueField: 'slug', data: promptModesData },
  { label: 'Query Templates', slug: 'query-templates', uniqueField: 'name', data: queryTemplatesData },
]
