import type { CollectionConfig } from 'payload'
import { isEditorOrAdmin } from '../access/isEditorOrAdmin'
import { isAdmin } from '../access/isAdmin'

/**
 * DataSources — Registry of external data sources for PDF discovery.
 *
 * Each record represents a web endpoint (e.g. government sites, official portals)
 * that the system can crawl to discover new PDF documents for import.
 *
 * Refactored: bilingual naming (nameEn + nameZh), streamlined fields,
 * removed redundant shortName/icon/schedule in favour of syncInterval.
 */
export const DataSources: CollectionConfig = {
  slug: 'data-sources',
  admin: {
    useAsTitle: 'nameEn',
    defaultColumns: ['nameEn', 'nameZh', 'description', 'persona', 'type', 'enabled', 'syncInterval', 'docsFound', 'docsIngested', 'lastSynced'],
    group: 'Content',
  },
  access: {
    read: isAdmin,  // GO-MU-08: was () => true
    create: isEditorOrAdmin,
    update: isEditorOrAdmin,
    delete: isAdmin,
  },
  fields: [
    // ── Identity ──
    {
      name: 'nameEn',
      type: 'text',
      required: true,
      label: 'Name (EN)',
      admin: { description: 'English name of the data source' },
    },
    {
      name: 'nameZh',
      type: 'text',
      required: true,
      label: '名称 (ZH)',
      admin: { description: '数据源的中文名称' },
    },
    {
      name: 'description',
      type: 'textarea',
      required: true,
      admin: { description: 'Brief description of what this data source covers' },
    },
    // ── Source config ──
    {
      name: 'discoveryUrl',
      type: 'text',
      required: true,
      admin: { description: 'URL to crawl for content discovery' },
    },
    {
      name: 'type',
      type: 'select',
      required: true,
      defaultValue: 'web_scrape',
      options: [
        { label: 'Web Scrape', value: 'web_scrape' },
        { label: 'PDF Crawl', value: 'pdf_crawl' },
        { label: 'API', value: 'api' },
        { label: 'Manual', value: 'manual' },
      ],
    },
    {
      name: 'pdfPattern',
      type: 'text',
      admin: { description: 'Regex pattern to filter discovered PDF filenames (optional)' },
    },
    {
      name: 'enabled',
      type: 'checkbox',
      defaultValue: true,
    },
    // ── Persona association (G2-04) ──
    {
      name: 'persona',
      type: 'relationship',
      relationTo: 'consulting-personas',
      admin: {
        description: 'Link to a Consulting Persona — crawled content routes to ca_{slug} collection',
        position: 'sidebar',
      },
    },
    // ── Auto-sync config (G2-04) ──
    {
      name: 'autoSync',
      type: 'checkbox',
      defaultValue: false,
      admin: {
        description: 'Enable automatic scheduled sync for this data source',
        position: 'sidebar',
      },
    },
    {
      name: 'syncInterval',
      type: 'select',
      defaultValue: 'weekly',
      options: [
        { label: 'Daily', value: 'daily' },
        { label: 'Weekly', value: 'weekly' },
        { label: 'Monthly', value: 'monthly' },
      ],
      admin: {
        description: 'How often to auto-sync (only used when autoSync is enabled)',
        condition: (_, siblingData) => siblingData?.autoSync,
        position: 'sidebar',
      },
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
      admin: { readOnly: true, description: 'Documents found in last discovery' },
    },
    {
      name: 'docsIngested',
      type: 'number',
      defaultValue: 0,
      admin: { readOnly: true, description: 'Documents already imported' },
    },
  ],
}
