import type { CollectionConfig } from 'payload'

/**
 * QuestionSets — manages logical groupings of Questions for batch evaluation.
 *
 * A QuestionSet is a collection of Questions generated with a specific
 * sampling strategy, covering one or more books. Used by:
 *   - QD: Question Dataset pipeline (stratified sampling → batch generation)
 *   - EI: Golden Dataset evaluation (retrieval recall via sourceChunkId)
 *
 * Slug: question-sets
 * Aligned with engine_v2/question_gen/sampler.py (QD-04)
 */
export const QuestionSets: CollectionConfig = {
  slug: 'question-sets',
  admin: {
    useAsTitle: 'name',
    defaultColumns: ['name', 'purpose', 'questionCount', 'status', 'createdAt'],
    group: 'Content',
  },
  access: {
    read: () => true,
    create: () => true,     // Engine writes generated sets
    update: () => true,
    delete: () => true,     // open for now (local dev)
  },
  fields: [
    {
      name: 'name',
      type: 'text',
      required: true,
      admin: { description: 'Dataset name (e.g. "v1-retriever-eval", "all-books-benchmark")' },
    },
    {
      name: 'purpose',
      type: 'select',
      defaultValue: 'eval',
      options: [
        { label: 'Evaluation', value: 'eval' },
        { label: 'Benchmark', value: 'benchmark' },
        { label: 'Suggested Questions', value: 'suggested' },
        { label: 'Debug / Test', value: 'debug' },
      ],
      admin: { description: 'Purpose of this question set' },
    },
    {
      name: 'bookIds',
      type: 'json',
      admin: { description: 'Array of book IDs covered by this set' },
    },
    {
      name: 'generationConfig',
      type: 'json',
      admin: {
        description: 'Snapshot of generation parameters (strategy, k_per_book, etc.)',
      },
    },
    {
      name: 'questionCount',
      type: 'number',
      defaultValue: 0,
      admin: { description: 'Number of questions in this set' },
    },
    {
      name: 'status',
      type: 'select',
      defaultValue: 'generating',
      options: [
        { label: 'Generating', value: 'generating' },
        { label: 'Ready', value: 'ready' },
        { label: 'Archived', value: 'archived' },
      ],
      admin: { description: 'Current status of the question set' },
    },
  ],
}
