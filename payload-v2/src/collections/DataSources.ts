import type { CollectionConfig } from 'payload'
import { isEditorOrAdmin } from '../access/isEditorOrAdmin'
import { isAdmin } from '../access/isAdmin'

/**
 * DataSources — Registry of external data sources for PDF discovery.
 *
 * Each record represents a web endpoint (e.g. ottawa.ca ED Updates, OREB)
 * that the system can crawl to discover new PDF documents for import.
 *
 * Categories align with project-brief.md Section 3:
 *   city, real_estate, tourism, commercial, research, news
 */
export const DataSources: CollectionConfig = {
  slug: 'data-sources',
  admin: {
    useAsTitle: 'name',
    defaultColumns: ['name', 'shortName', 'category', 'type', 'enabled', 'docsFound', 'docsIngested', 'lastSynced'],
    group: 'Content',
  },
  access: {
    read: () => true,
    create: isEditorOrAdmin,
    update: isEditorOrAdmin,
    delete: isAdmin,
  },
  fields: [
    {
      name: 'name',
      type: 'text',
      required: true,
      admin: { description: 'Full name of the data source organization' },
    },
    {
      name: 'shortName',
      type: 'text',
      required: true,
      admin: { description: 'Abbreviated name (e.g. OREB, CMHC)' },
    },
    {
      name: 'category',
      type: 'select',
      required: true,
      defaultValue: 'city',
      options: [
        { label: 'City of Ottawa', value: 'city' },
        { label: 'Real Estate & Housing', value: 'real_estate' },
        { label: 'Tourism & Creative', value: 'tourism' },
        { label: 'Commercial & Districts', value: 'commercial' },
        { label: 'Research & Statistics', value: 'research' },
        { label: 'News & Business', value: 'news' },
      ],
    },
    {
      name: 'discoveryUrl',
      type: 'text',
      required: true,
      admin: { description: 'URL to crawl for PDF discovery' },
    },
    {
      name: 'type',
      type: 'select',
      required: true,
      defaultValue: 'pdf_crawl',
      options: [
        { label: 'PDF Crawl', value: 'pdf_crawl' },
        { label: 'URL Pattern', value: 'url_pattern' },
        { label: 'API', value: 'api' },
        { label: 'Web Scrape', value: 'web_scrape' },
        { label: 'Manual', value: 'manual' },
      ],
    },
    {
      name: 'pdfPattern',
      type: 'text',
      admin: { description: 'Regex pattern to filter discovered PDF filenames (optional)' },
    },
    {
      name: 'schedule',
      type: 'select',
      defaultValue: 'manual',
      options: [
        { label: 'Manual', value: 'manual' },
        { label: 'Weekly', value: 'weekly' },
        { label: 'Monthly', value: 'monthly' },
        { label: 'Quarterly', value: 'quarterly' },
      ],
    },
    {
      name: 'icon',
      type: 'text',
      defaultValue: '📄',
      admin: { description: 'Emoji icon for display' },
    },
    {
      name: 'description',
      type: 'textarea',
      admin: { description: 'Brief description of this data source' },
    },
    {
      name: 'enabled',
      type: 'checkbox',
      defaultValue: true,
    },
    // ── Sync stats (auto-updated) ──
    {
      name: 'lastSynced',
      type: 'date',
      admin: { readOnly: true, description: 'Last discovery/sync timestamp' },
    },
    {
      name: 'docsFound',
      type: 'number',
      defaultValue: 0,
      admin: { readOnly: true, description: 'PDFs found in last discovery' },
    },
    {
      name: 'docsIngested',
      type: 'number',
      defaultValue: 0,
      admin: { readOnly: true, description: 'PDFs already imported' },
    },
  ],
}
