"""
Unified Web Crawler CLI tool for ConsultRAG.

Usage:
  # === One-shot full crawl (BFS discover + PDF save) — run overnight ===
  uv run python scripts/crawler_cli.py crawl <url> <persona> [--depth 3] [--max-pages 100]

  # Multiple seed URLs in one run:
  uv run python scripts/crawler_cli.py crawl <url1> <url2> <url3> <persona>

  # === Individual phases (manual control) ===
  uv run python scripts/crawler_cli.py discover <url> <persona> [--depth N] [--max N]
  uv run python scripts/crawler_cli.py batch <manifest_json_path>
  uv run python scripts/crawler_cli.py single <url> <output_pdf_path>
"""
import argparse
import asyncio
import json
import sys
import time
from datetime import datetime
from pathlib import Path

import httpx

sys.path.insert(0, ".")
from engine_v2.settings import *  # noqa
from engine_v2.crawling.web_crawler_v2 import (
    discover_urls,
    save_pdfs_from_manifest,
    _save_single_pdf,
)

# ── Log file setup ───────────────────────────────────────────────────────────
LOG_DIR = Path("data/crawled_web")


def _log(msg: str, log_file: Path | None = None):
    """Print and optionally append to log file."""
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line)
    if log_file:
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(line + "\n")


# ╔══════════════════════════════════════════════════════════════════════════════╗
# ║  crawl — Full automated pipeline: BFS discover → PDF save (overnight OK)    ║
# ╚══════════════════════════════════════════════════════════════════════════════╝

async def run_crawl(args):
    """Full pipeline: discover URLs via BFS, then save each as PDF.

    Designed to run unattended overnight:
    - Multiple seed URLs supported (merged into one manifest)
    - Existing PDFs are auto-skipped (resume-safe)
    - Failed pages are logged but don't stop the crawl
    - Progress written to log file for morning review
    """
    persona = args.persona
    seed_urls = args.urls  # list of URLs
    depth = args.depth
    max_pages = args.max_pages
    delay = args.delay
    headless = not args.visible

    LOG_DIR.mkdir(parents=True, exist_ok=True)
    log_file = LOG_DIR / persona / "crawl.log"
    log_file.parent.mkdir(parents=True, exist_ok=True)

    _log("=" * 60, log_file)
    _log(f"FULL CRAWL: {persona}", log_file)
    _log(f"  Seeds:     {len(seed_urls)} URL(s)", log_file)
    for u in seed_urls:
        _log(f"             {u}", log_file)
    _log(f"  Depth:     {depth}", log_file)
    _log(f"  Max pages: {max_pages} (per seed)", log_file)
    _log(f"  Delay:     {delay}s between pages", log_file)
    _log("=" * 60, log_file)

    t0 = time.time()

    # ── Phase 1: BFS discovery for each seed URL ─────────────────────────
    for i, url in enumerate(seed_urls, 1):
        _log(f"\n[DISCOVER {i}/{len(seed_urls)}] {url}", log_file)
        try:
            manifest_path = await discover_urls(
                seed_url=url,
                persona_slug=persona,
                max_depth=depth,
                max_pages=max_pages,
                headless=headless,
            )
            # Read manifest to report count
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            total = manifest.get("total_urls", 0)
            _log(f"  [OK] Manifest: {total} URLs total", log_file)
        except Exception as e:
            _log(f"  [ERROR] Discovery failed: {e}", log_file)
            continue

    # ── Phase 2: Save all discovered URLs as PDFs ────────────────────────
    manifest_path = LOG_DIR / persona / "manifest.json"
    if not manifest_path.exists():
        _log("[ERROR] No manifest.json found, aborting", log_file)
        return

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    total_urls = len(manifest.get("pages", []))
    _log(f"\n[BATCH] Saving {total_urls} pages as PDF (delay={delay}s)", log_file)

    try:
        results = await save_pdfs_from_manifest(
            manifest_path=manifest_path,
            headless=headless,
            delay_between=delay,
        )
    except Exception as e:
        _log(f"[ERROR] Batch save crashed: {e}", log_file)
        results = []

    # ── Summary ──────────────────────────────────────────────────────────
    elapsed = time.time() - t0
    saved = [r for r in results if r.success]
    failed = [r for r in results if not r.success]
    total_mb = sum(r.file_size for r in saved) / (1024 * 1024) if saved else 0

    _log("\n" + "=" * 60, log_file)
    _log("CRAWL COMPLETE", log_file)
    _log(f"  Time:    {elapsed/60:.1f} min", log_file)
    _log(f"  Saved:   {len(saved)}/{len(results)} pages ({total_mb:.1f} MB)", log_file)
    _log(f"  Failed:  {len(failed)}", log_file)
    if failed:
        for r in failed:
            reason = (r.error or "unknown")[:80]
            _log(f"    ✗ {r.filename}: {reason}", log_file)
    _log("=" * 60, log_file)
    _log(f"Log saved: {log_file}", log_file)


# ╔══════════════════════════════════════════════════════════════════════════════╗
# ║  discover / batch / single — Individual phase commands                       ║
# ╚══════════════════════════════════════════════════════════════════════════════╝

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
    headless = not args.visible
    delay = args.delay
    print("=" * 60)
    print(f"Phase 2: Batch PDF Capture from Manifest")
    print(f"  Manifest: {args.manifest}")
    print(f"  Headless: {headless}, Delay: {delay}s")
    print("=" * 60)

    results = await save_pdfs_from_manifest(
        manifest_path=args.manifest,
        headless=headless,
        delay_between=delay,
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

    result = await _save_single_pdf(args.url, out_path, headless=not getattr(args, 'visible', False))

    if result.success:
        print(f"\n[OK] Saved: {result.file_size / 1024:.1f} KB to {out_path}")
    else:
        print(f"\n[FAILED] {result.error}")


# ╔══════════════════════════════════════════════════════════════════════════════╗
# ║  CLI argument parser                                                         ║
# ╚══════════════════════════════════════════════════════════════════════════════╝

def main():
    parser = argparse.ArgumentParser(
        description="Web Crawler CLI — BFS discover + PDF archival",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Full automated crawl (overnight-safe):
  uv run python scripts/crawler_cli.py crawl \\
    "https://www.canada.ca/en/.../study-canada.html" \\
    edu-school-planning --depth 3 --max-pages 100

  # Multiple seed URLs:
  uv run python scripts/crawler_cli.py crawl \\
    "https://...url1.html" "https://...url2.html" \\
    my-persona --depth 2

  # Just discover (no PDF saving):
  uv run python scripts/crawler_cli.py discover <url> <persona>

  # Just save PDFs from existing manifest:
  uv run python scripts/crawler_cli.py batch data/crawled_web/my-persona/manifest.json
        """,
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # ── crawl: Full pipeline (recommended) ───────────────────────────────
    parser_crawl = subparsers.add_parser(
        "crawl",
        help="Full pipeline: BFS discover + PDF save (overnight-safe)",
    )
    parser_crawl.add_argument(
        "urls", nargs="+",
        help="Seed URL(s) — last positional arg is persona slug",
    )
    parser_crawl.add_argument("--depth", type=int, default=3, help="BFS depth (default: 3)")
    parser_crawl.add_argument("--max-pages", type=int, default=100, help="Max pages per seed (default: 100)")
    parser_crawl.add_argument("--delay", type=float, default=2.0, help="Delay between PDF saves (default: 2s)")
    parser_crawl.add_argument("--visible", action="store_true", help="Show browser window (for debugging, default: headless)")

    # ── discover: Phase 1 only ───────────────────────────────────────────
    parser_discover = subparsers.add_parser("discover", help="Phase 1: Discover URLs using BFS")
    parser_discover.add_argument("url", help="Seed URL to start crawling")
    parser_discover.add_argument("persona", help="Persona slug (e.g., imm-pathways)")
    parser_discover.add_argument("--depth", type=int, default=2, help="Max depth")
    parser_discover.add_argument("--max-pages", type=int, default=50, help="Max pages to discover")

    # ── batch: Phase 2 only ──────────────────────────────────────────────
    parser_batch = subparsers.add_parser("batch", help="Phase 2: Save PDFs from a manifest file")
    parser_batch.add_argument("manifest", help="Path to manifest.json")
    parser_batch.add_argument("--delay", type=float, default=5.0, help="Delay between pages (default: 5s)")
    parser_batch.add_argument("--visible", action="store_true", help="Show browser window")

    # ── single: One page ─────────────────────────────────────────────────
    parser_single = subparsers.add_parser("single", help="Capture a single URL to PDF")
    parser_single.add_argument("url", help="Target URL")
    parser_single.add_argument("out", help="Output PDF file path")
    parser_single.add_argument("--visible", action="store_true", help="Show browser window")

    args = parser.parse_args()

    # For `crawl`, the last positional arg is the persona slug
    if args.command == "crawl":
        if len(args.urls) < 2:
            parser.error("crawl requires at least one URL and a persona slug as the last argument")
        args.persona = args.urls.pop()  # last arg = persona
        # Validate persona isn't a URL
        if args.persona.startswith("http"):
            parser.error(
                "Last argument must be the persona slug, not a URL. "
                "Usage: crawl <url1> [url2 ...] <persona>"
            )

    if args.command == "crawl":
        asyncio.run(run_crawl(args))
    elif args.command == "discover":
        asyncio.run(run_discover(args))
    elif args.command == "batch":
        asyncio.run(run_batch(args))
    elif args.command == "single":
        asyncio.run(run_single(args))


if __name__ == "__main__":
    main()
