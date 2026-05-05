# scripts/

All operational scripts for the ConsultRAG data pipeline.

## Directory Structure

```
scripts/
├── crawl/                  # Step 1: Web crawling → PDF archival
│   ├── crawler_cli.py      # Main CLI: BFS discover + batch PDF save (federal-ircc)
│   ├── crawl_provinces.py  # Batch PNP crawler for all provinces/territories
│   ├── crawl_algonquin.py  # Algonquin College program crawler
│   ├── clean_manifest.py   # Remove dead URLs (soft-404) from manifest.json
│   └── scrape_dli_list.py  # DLI full list: JSON download → PDF render
│
├── ingest/                 # Step 2 & 3: PDF → Markdown → ChromaDB
│   ├── batch_mineru.py     # Step 2: PDF → Markdown (via MinerU)
│   ├── batch_ingest.py     # Step 3: Markdown → ChromaDB (auto-scan delta)
│   ├── flatten_mineru.py   # Fix double-nested MinerU output dirs
│   ├── update_persona_collections.py  # Batch-update persona seeds with multiCollections
│   ├── ingest_edu_local.py         # One-off: edu-school-planning
│   ├── ingest_imm_pathways.py      # One-off: imm-pathways (via API)
│   └── ingest_imm_pathways_local.py # One-off: imm-pathways (local)
│
├── live_qa/                # Live broadcast Q&A testing
│   ├── benchmark.py        # 20-question stress test
│   ├── verify_knowledge.py # Coverage verification
│   └── results/            # Benchmark output files
│
├── acquire/                # Data acquisition (textbooks, PDFs)
│   ├── download_ecdev_pdfs.py
│   ├── download_free_books.py
│   ├── explore_sources.py
│   └── search_github_books.py
│
├── cms/                    # Payload CMS batch operations
│   ├── backfill_ingest_tasks.py
│   ├── batch_ingest_real_estate.py
│   ├── batch_reingest_ecdev.py
│   └── update_file_sizes.py
│
├── db/                     # Database maintenance
│   └── rebuild_topic_index.py
│
├── vectors/                # Vector store maintenance
│   └── patch_chroma_chapter_keys.py
│
├── diagnostics/            # Debugging & analysis tools
│   ├── check_tasks.py           # Inspect Payload IngestTask records
│   └── analyze_coverage.py      # Topic coverage analysis for crawled pages
│
├── eval/                   # Evaluation scripts
│   └── backfill_evaluations.py  # Re-evaluate pending/incomplete historical evals
│
├── reports/                # Course deliverable generators (docx/pptx)
│   ├── build_final_report.py      # Build Final Report docx from scratch
│   ├── fill_final_report.py       # Fill template docx with content
│   ├── gen_final_presentation.py  # Generate final project PPTX (v2)
│   ├── generate_ppt.py            # Generate demo PPTX (v1)
│   └── graphify_bert.py           # BERT knowledge graph builder (graphify)
│
├── deprecated/             # One-off / obsolete scripts (kept for reference)
│   ├── scrape_dli_probe.py         # DLI probe (superseded by scrape_dli_list)
│   ├── fix_long_names.py           # Fix long filenames (one-off)
│   ├── check_failed.py             # Check failed MinerU jobs (one-off)
│   ├── shorten_web_filenames.py    # Shorten crawled filenames (one-off)
│   ├── migrate_to_source_dirs.py   # Rename persona→source dirs (done)
│   └── _inspect_tabs.py            # Inspect Algonquin tab DOM (debug)
│
├── _paths.py               # Shared path constants (PROJECT_ROOT, DATA_DIR, etc.)
└── README.md               # This file
```

## 3-Step Data Pipeline

```bash
# Step 1a: Crawl federal → PDF
uv run python scripts/crawl/crawler_cli.py crawl \
  "https://www.canada.ca/en/.../study-canada.html" \
  edu-school-planning --depth 3 --max-pages 200

# Step 1b: Crawl all provinces → PDF
uv run python scripts/crawl/crawl_provinces.py

# Step 1c: Crawl Algonquin → PDF
uv run python scripts/crawl/crawl_algonquin.py

# Step 2: PDF → Markdown (MinerU)
uv run python scripts/ingest/batch_mineru.py --category federal-ircc

# Step 3: Markdown → ChromaDB
uv run python scripts/ingest/batch_ingest.py --category federal-ircc
```

Each script auto-detects new/changed content and only processes the delta.

## Utility Scripts

```bash
# Clean dead URLs from manifest
uv run python scripts/crawl/clean_manifest.py --dry-run

# Flatten double-nested MinerU output dirs
uv run python scripts/ingest/flatten_mineru.py --dry-run

# Update persona seed files with multiCollections
uv run python scripts/ingest/update_persona_collections.py

# Re-evaluate pending evaluations
uv run python scripts/eval/backfill_evaluations.py --dry-run

# Analyze crawl coverage
uv run python scripts/diagnostics/analyze_coverage.py
```
