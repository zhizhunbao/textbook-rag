"""
Unified Web Crawler CLI tool for ConsultRAG.
Consolidates previous test scripts into a single, structured command-line utility.

Usage:
  python scripts/crawler_cli.py discover <url> <persona> [--depth N] [--max N]
  python scripts/crawler_cli.py batch <manifest_json_path>
  python scripts/crawler_cli.py single <url> <output_pdf_path>
  python scripts/crawler_cli.py api-ingest <url> <persona>
"""
import argparse
import asyncio
import sys
from pathlib import Path
import httpx

sys.path.insert(0, ".")
from engine_v2.settings import *  # noqa
from engine_v2.crawling.web_crawler import (
    discover_urls,
    save_pdfs_from_manifest,
    _save_single_pdf_impl
)

async def run_discover(args):
    print("=" * 60)
    print(f"Phase 1: Discover URLs (BFS)")
    print(f"  Seed URL: {args.url}")
    print(f"  Persona:  {args.persona}")
    print(f"  Depth:    {args.depth}, Max Pages: {args.max_pages}")
    print("=" * 60)
    
    manifest_path = await discover_urls(
        seed_url=args.url,
        persona_slug=args.persona,
        max_depth=args.depth,
        max_pages=args.max_pages,
        headless=True
    )
    print(f"\n[OK] Manifest saved to: {manifest_path}")

async def run_batch(args):
    print("=" * 60)
    print(f"Phase 2: Batch PDF Capture from Manifest")
    print(f"  Manifest: {args.manifest}")
    print("=" * 60)
    
    results = await save_pdfs_from_manifest(
        manifest_path=args.manifest,
        headless=True,
        delay_between=2.0
    )
    
    saved = [r for r in results if r.success]
    skipped = [r for r in results if not r.success]
    
    print("\n" + "=" * 60)
    print("FINAL RESULTS:")
    for r in saved:
        print(f"  [OK] {r.filename} ({r.file_size/1024:.0f}KB)")
    for r in skipped:
        print(f"  [SKIP] {r.filename} ({r.error})")
    
    total_mb = sum(r.file_size for r in saved) / (1024*1024) if saved else 0
    print(f"\n{len(saved)}/{len(results)} saved ({total_mb:.1f} MB)")

async def run_single(args):
    print("=" * 60)
    print(f"Single Page Capture")
    print(f"  URL: {args.url}")
    print(f"  Out: {args.out}")
    print("=" * 60)
    
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    
    result = await _save_single_pdf_impl(args.url, out_path, headless=True)
    
    if result.success:
        print(f"\n[OK] Saved: {result.file_size / 1024:.1f} KB to {out_path}")
    else:
        print(f"\n[FAILED] {result.error}")

def run_api_ingest(args):
    print("=" * 60)
    print(f"Triggering Engine API Ingestion (/engine/crawl/ingest)")
    print(f"  URL: {args.url}")
    print(f"  Persona: {args.persona}")
    print("=" * 60)
    
    try:
        resp = httpx.post(
            "http://localhost:8001/engine/crawl/ingest",
            json={
                "url": args.url,
                "persona_slug": args.persona,
                "deep_crawl": True,
                "max_depth": args.depth,
                "max_pages": args.max_pages,
                "headless": False,  # Visible browser for debug
            },
            timeout=300.0,
        )
        
        print(f"Status: {resp.status_code}")
        data = resp.json()
        print(f"Success:       {data.get('success')}")
        print(f"Pages crawled: {data.get('pages_crawled')}")
        print(f"Chunks:        {data.get('chunk_count')}")
        print(f"Total words:   {data.get('total_words')}")
        print(f"Collection:    {data.get('collection')}")
    except Exception as e:
        print(f"[FAILED] API call error: {e}")

def main():
    parser = argparse.ArgumentParser(description="Web Crawler CLI Toolkit")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # Subcommand: discover
    parser_discover = subparsers.add_parser("discover", help="Phase 1: Discover URLs using BFS")
    parser_discover.add_argument("url", help="Seed URL to start crawling")
    parser_discover.add_argument("persona", help="Persona slug (e.g., imm-pathways)")
    parser_discover.add_argument("--depth", type=int, default=2, help="Max depth")
    parser_discover.add_argument("--max-pages", type=int, default=50, help="Max pages to discover")

    # Subcommand: batch
    parser_batch = subparsers.add_parser("batch", help="Phase 2: Save PDFs from a manifest file")
    parser_batch.add_argument("manifest", help="Path to manifest.json")

    # Subcommand: single
    parser_single = subparsers.add_parser("single", help="Test: Capture a single URL to PDF")
    parser_single.add_argument("url", help="Target URL")
    parser_single.add_argument("out", help="Output PDF file path")

    # Subcommand: api-ingest
    parser_api = subparsers.add_parser("api-ingest", help="Test: Trigger the REST API /engine/crawl/ingest endpoint")
    parser_api.add_argument("url", help="Seed URL")
    parser_api.add_argument("persona", help="Persona slug")
    parser_api.add_argument("--depth", type=int, default=2, help="Max depth")
    parser_api.add_argument("--max-pages", type=int, default=10, help="Max pages to ingest")

    args = parser.parse_args()

    if args.command == "discover":
        asyncio.run(run_discover(args))
    elif args.command == "batch":
        asyncio.run(run_batch(args))
    elif args.command == "single":
        asyncio.run(run_single(args))
    elif args.command == "api-ingest":
        run_api_ingest(args)

if __name__ == "__main__":
    main()
