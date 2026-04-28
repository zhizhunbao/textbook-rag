import type { CollectionConfig } from 'payload'
import { isAdmin } from '../access/isAdmin'

/**
 * Evaluations Collection — RAG quality evaluation results.
 *
 * Slug: evaluations
 * Aligned with engine-v2/evaluation/ module.
 */
export const Evaluations: CollectionConfig = {
  slug: 'evaluations',
  admin: {
    useAsTitle: 'query',
    defaultColumns: [
      'query', 'faithfulness', 'relevancy', 'contextRelevancy',
      'answerRelevancy', 'createdAt',
    ],
    group: 'Analytics',
  },
  access: {
    read: isAdmin,
    create: () => true,   // Engine writes eval results
    update: isAdmin,
    delete: isAdmin,
  },
  fields: [
    // ── Query reference ──
    {
      name: 'queryRef',
      type: 'relationship',
      relationTo: 'queries',
      admin: { description: 'Link to the original Queries record' },
    },

    // ── Question + answer ──
    {
      name: 'query',
      type: 'text',
      required: true,
      admin: { description: 'The question that was evaluated' },
    },
    {
      name: 'answer',
      type: 'textarea',
      admin: { description: 'The generated answer' },
    },
    {
      name: 'referenceAnswer',
      type: 'textarea',
      admin: { description: 'Ground-truth reference answer (if available)' },
    },

    // ── Scores (5-dimensional) ──
    {
      name: 'faithfulness',
      type: 'number',
      min: 0,
      max: 1,
      admin: { description: 'Is the answer grounded in the retrieved context? (0-1)' },
    },
    {
      name: 'relevancy',
      type: 'number',
      min: 0,
      max: 1,
      admin: { description: 'Is the retrieved context relevant to the query? (0-1)' },
    },
    {
      name: 'correctness',
      type: 'number',
      min: 0,
      max: 1,
      admin: { description: 'Is the answer factually correct? (0-1, requires reference)' },
    },
    {
      name: 'contextRelevancy',
      type: 'number',
      min: 0,
      max: 1,
      admin: { description: 'Quality of retrieved context for the query (0-1)' },
    },
    {
      name: 'answerRelevancy',
      type: 'number',
      min: 0,
      max: 1,
      admin: { description: 'How relevant is the answer to the query? (0-1)' },
    },

    // ── Question depth ──
    {
      name: 'questionDepth',
      type: 'text',
      admin: { description: 'Cognitive depth label: surface / understanding / synthesis' },
    },
    {
      name: 'questionDepthScore',
      type: 'number',
      min: 0,
      max: 1,
      admin: { description: 'Normalised question depth score (0-1, from 1-5 scale)' },
    },

    // ── Feedback ──
    {
      name: 'feedback',
      type: 'json',
      admin: { description: 'Evaluator feedback per dimension' },
    },

    // ── Four-category aggregate scores (EV2-T2-04) ──
    {
      name: 'ragScore',
      type: 'number',
      min: 0,
      max: 1,
      admin: { description: 'RAG aggregate: mean(context_relevancy, relevancy) (0-1)' },
    },
    {
      name: 'llmScore',
      type: 'number',
      min: 0,
      max: 1,
      admin: { description: 'LLM aggregate: faithfulness (0-1)' },
    },
    {
      name: 'answerScore',
      type: 'number',
      min: 0,
      max: 1,
      admin: { description: 'Answer aggregate: mean(correctness, answer_relevancy, completeness, clarity) (0-1)' },
    },
    {
      name: 'overallScore',
      type: 'number',
      min: 0,
      max: 1,
      admin: { description: 'Weighted overall: 0.3*RAG + 0.3*LLM + 0.4*Answer (0-1)' },
    },

    // ── Answer sub-dimensions (EV2-T2-04 / EI-T3) ──
    {
      name: 'completeness',
      type: 'number',
      min: 0,
      max: 1,
      admin: { description: 'Does the answer fully cover all question aspects? (0-1) [Deprecated]' },
    },
    {
      name: 'clarity',
      type: 'number',
      min: 0,
      max: 1,
      admin: { description: 'Is the answer clear, well-structured, readable? (0-1) [Deprecated]' },
    },
    {
      name: 'guidelinesPass',
      type: 'checkbox',
      admin: { description: 'Did the answer pass all QUALITY_GUIDELINES? (EI-T3-01)' },
    },
    {
      name: 'guidelinesFeedback',
      type: 'textarea',
      admin: { description: 'Specific feedback from the GuidelineEvaluator' },
    },

    // ── Retrieval strategy stats (EV2-T1 + T2-04) ──
    {
      name: 'retrievalMode',
      type: 'select',
      options: [
        { label: 'Hybrid', value: 'hybrid' },
        { label: 'Vector Only', value: 'vector_only' },
      ],
      admin: { description: 'Retrieval strategy used (hybrid BM25+Vector or vector-only)' },
    },
    {
      name: 'bm25Hits',
      type: 'number',
      min: 0,
      admin: { description: 'Number of sources from BM25 retriever' },
    },
    {
      name: 'vectorHits',
      type: 'number',
      min: 0,
      admin: { description: 'Number of sources from Vector retriever' },
    },
    {
      name: 'bothHits',
      type: 'number',
      min: 0,
      admin: { description: 'Number of sources matched by both BM25 and Vector' },
    },

    // ── IR Retrieval Metrics (EI-T2) ──
    {
      name: 'hitRate',
      type: 'number',
      min: 0,
      max: 1,
    },
    {
      name: 'mrr',
      type: 'number',
      min: 0,
      max: 1,
    },
    {
      name: 'precisionAtK',
      type: 'number',
      min: 0,
      max: 1,
    },
    {
      name: 'recallAtK',
      type: 'number',
      min: 0,
      max: 1,
    },
    {
      name: 'ndcg',
      type: 'number',
      min: 0,
      max: 1,
    },
    {
      name: 'irScore',
      type: 'number',
      min: 0,
      max: 1,
      admin: { description: 'Mean of IR retrieval metrics' },
    },
    {
      name: 'goldenMatchRef',
      type: 'relationship',
      relationTo: 'golden-dataset',
      admin: { description: 'Matched Golden Dataset record used for IR metrics' },
    },

    // ── Evaluation status (EV2-T2-04) ──
    {
      name: 'status',
      type: 'select',
      defaultValue: 'pending',
      options: [
        { label: 'Pass', value: 'pass' },
        { label: 'Fail', value: 'fail' },
        { label: 'Pending', value: 'pending' },
      ],
      admin: { description: 'Overall evaluation status' },
    },

    // ── Meta ──
    {
      name: 'model',
      type: 'text',
      admin: { description: 'LLM model used for the query' },
    },
    {
      name: 'sourceCount',
      type: 'number',
      admin: { description: 'Number of sources retrieved' },
    },
    {
      name: 'batchId',
      type: 'text',
      admin: { description: 'Batch evaluation run ID (for grouping)' },
    },

    // ── Evaluation metadata (EUX-T2) ──
    {
      name: 'judgeModel',
      type: 'text',
      admin: { description: 'LLM model used as evaluation judge (e.g. "azure/gpt-4o-mini")' },
    },
    {
      name: 'answerModel',
      type: 'text',
      admin: { description: 'LLM model that generated the answer (e.g. "llama3.2:3b")' },
    },
    {
      name: 'llmCalls',
      type: 'number',
      min: 0,
      admin: { description: 'Total LLM API calls made during this evaluation' },
    },

    // ── Improvement suggestions (EUX-T3) ──
    {
      name: 'suggestions',
      type: 'json',
      admin: { description: 'Array of improvement suggestions [{dimension, severity, message_en, message_zh}]' },
    },

    // ── AveragePrecision (EUX-T4, aligns with LlamaIndex METRIC_REGISTRY) ──
    {
      name: 'averagePrecision',
      type: 'number',
      min: 0,
      max: 1,
      admin: { description: 'Average Precision — aligns with LlamaIndex AP metric' },
    },
  ],
}

