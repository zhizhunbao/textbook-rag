# scripts/

All operational scripts for the ConsultRAG data pipeline.

## Directory Structure

```
scripts/
├── crawl/                  # Step 1: Web crawling → PDF archival
│   ├── crawler_cli.py      # Main CLI: BFS discover + batch PDF save
│   └── scrape_dli_list.py  # DLI full list: JSON download → PDF render
│
├── ingest/                 # Step 2 & 3: PDF → Markdown → ChromaDB
│   ├── batch_mineru.py     # Step 2: PDF → Markdown (via MinerU)
│   ├── batch_ingest.py     # Step 3: Markdown → ChromaDB (auto-scan delta)
│   ├── ingest_edu_local.py         # One-off: edu-school-planning
│   ├── ingest_imm_pathways.py      # One-off: imm-pathways (via API)
│   └── ingest_imm_pathways_local.py # One-off: imm-pathways (local)
│
├── live_qa/                # Live broadcast Q&A testing
│   ├── benchmark.py        # 20-question stress test
│   └── verify_knowledge.py # Coverage verification
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
├── diagnostics/            # Debugging tools
│   └── check_tasks.py
│
├── eval/                   # Evaluation scripts
├── reports/                # Generated reports
│
├── deprecated/             # One-off scripts (kept for reference)
│   ├── scrape_dli_probe.py
│   ├── fix_long_names.py
│   ├── check_failed.py
│   └── shorten_web_filenames.py
│
├── _paths.py               # Shared path constants
└── README.md               # This file
```

## 3-Step Data Pipeline

```bash
# Step 1: Crawl → PDF
uv run python scripts/crawl/crawler_cli.py crawl \
  "https://www.canada.ca/en/.../study-canada.html" \
  edu-school-planning --depth 3 --max-pages 200

# Step 2: PDF → Markdown (MinerU)
uv run python scripts/ingest/batch_mineru.py --category edu-school-planning

# Step 3: Markdown → ChromaDB
uv run python scripts/ingest/batch_ingest.py --category edu-school-planning
```

Each script auto-detects new/changed content and only processes the delta.
