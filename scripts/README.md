# scripts/

All operational scripts for the ConsultRAG data pipeline.

## Directory Structure

```
scripts/
├── crawl/                          # Step 1: Web crawling → PDF archival
│   ├── crawler_cli.py              # Main CLI: BFS discover + batch PDF save
│   ├── discover_ircc.py            # IRCC URL discovery (BFS + News pagination)
│   ├── crawl_provinces.py          # Batch PNP crawler for all provinces/territories
│   ├── crawl_algonquin.py          # Algonquin College program crawler
│   ├── clean_manifest.py           # Remove dead URLs (soft-404) from manifest.json
│   └── scrape_dli_list.py          # DLI full list: JSON download → PDF render
│
├── ingest/                         # Step 2 & 3: PDF → Markdown → ChromaDB
│   ├── batch_mineru.py             # Step 2: PDF → Markdown (via MinerU)
│   ├── batch_ingest_vectors.py     # Step 3: Markdown → ChromaDB (auto-scan delta)
│   └── fix_nested_dirs.py          # Fix double-nested MinerU output dirs
│
├── cms/                            # Step 4: Sync to Payload CMS
│   ├── sync_books.py               # Full pipeline: Engine→Payload→ChromaDB sync
│   ├── backfill_tasks.py           # Backfill ingest-task records from disk data
│   ├── update_persona_seeds.py     # Batch-update persona seeds with multiCollections
│   └── sync_file_sizes.py          # Sync PDF file sizes to Payload metadata
│
├── eval/                           # Evaluation & QA
│   ├── generate_questions.py       # Auto-generate benchmark Qs from crawled data
│   └── backfill_evaluations.py     # Re-evaluate pending/incomplete historical evals
│
├── live_qa/                        # Live broadcast Q&A testing
│   ├── benchmark.py                # 20-question stress test
│   ├── verify_knowledge.py         # Coverage verification
│   └── results/                    # Benchmark output files
│
├── acquire/                        # Data acquisition (textbooks, PDFs)
│   ├── download_ecdev_pdfs.py
│   ├── download_free_books.py
│   ├── explore_sources.py
│   └── search_github_books.py
│
├── db/                             # Database maintenance
│   └── rebuild_topic_index.py
│
├── vectors/                        # Vector store maintenance
│   └── patch_chroma_chapter_keys.py
│
├── diagnostics/                    # Debugging & analysis tools
│   ├── check_tasks.py              # Inspect Payload IngestTask records
│   └── analyze_coverage.py         # Topic coverage analysis for crawled pages
│
├── reports/                        # Course deliverable generators (docx/pptx)
│   ├── build_final_report.py
│   ├── fill_final_report.py
│   ├── gen_final_presentation.py
│   ├── generate_ppt.py
│   └── graphify_bert.py
│
├── deprecated/                     # One-off / obsolete scripts (kept for reference)
│   ├── ingest_edu_local.py         # Superseded by batch_ingest_vectors.py --category
│   ├── ingest_imm_pathways.py      # Superseded by sync_books.py
│   ├── ingest_imm_pathways_local.py # Superseded by batch_ingest_vectors.py
│   ├── batch_reingest_ecdev.py     # One-off LaTeX cleanup re-ingest (done)
│   ├── scrape_dli_probe.py
│   ├── fix_long_names.py
│   ├── check_failed.py
│   ├── shorten_web_filenames.py
│   ├── migrate_to_source_dirs.py
│   └── _inspect_tabs.py
│
├── _paths.py                       # Shared path constants
└── README.md                       # This file
```

## 4-Step Data Pipeline

```bash
# Step 1: Crawl web pages → PDF
uv run python scripts/crawl/crawler_cli.py crawl \
  "https://www.canada.ca/en/.../study-canada.html" \
  edu-school-planning --depth 3 --max-pages 200

# Step 1b: Discover + crawl all IRCC pages (BFS + news)
uv run python scripts/crawl/discover_ircc.py
uv run python scripts/crawl/crawler_cli.py batch data/crawled_web/federal-ircc/manifest.json

# Step 1c: Crawl provinces / Algonquin
uv run python scripts/crawl/crawl_provinces.py
uv run python scripts/crawl/crawl_algonquin.py

# Step 2: PDF → Markdown (MinerU)
uv run python scripts/ingest/batch_mineru.py --category federal-ircc

# Step 3: Markdown → ChromaDB (vectors)
uv run python scripts/ingest/batch_ingest_vectors.py --category federal-ircc

# Step 4: Sync to Payload CMS (books + metadata)
uv run python scripts/cms/sync_books.py
```

Each script auto-detects new/changed content and only processes the delta.

## Evaluation

```bash
# Auto-generate benchmark questions from crawled data
uv run python scripts/eval/generate_questions.py --persona federal-ircc
uv run python scripts/eval/generate_questions.py --persona federal-ircc --use-llm

# Re-evaluate pending evaluations
uv run python scripts/eval/backfill_evaluations.py --dry-run
```

## Utility Scripts

```bash
# Clean dead URLs from manifest
uv run python scripts/crawl/clean_manifest.py --dry-run

# Fix double-nested MinerU output dirs
uv run python scripts/ingest/fix_nested_dirs.py --dry-run

# Update persona seed files with multiCollections
uv run python scripts/cms/update_persona_seeds.py

# Sync PDF file sizes to Payload
uv run python scripts/cms/sync_file_sizes.py

# Backfill ingest tasks from real disk data
uv run python scripts/cms/backfill_tasks.py

# Analyze crawl coverage
uv run python scripts/diagnostics/analyze_coverage.py
```
