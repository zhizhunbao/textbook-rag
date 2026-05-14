#!/usr/bin/env python3
"""
batch_download.py — 合并多目录候选 + 下载 Top N 视频
Merge candidates from multiple keyword directories, rank, and download top N.

Usage:
    uv run .agent/workflows/short-video/competitor-analysis/scripts/batch_download.py \
        --input data/competitor-analysis/2026-05/ \
        --top 10 \
        --output data/competitor-analysis/2026-05/videos/
"""

from __future__ import annotations

import argparse
import json
import math
import os
import subprocess
import sys
from pathlib import Path

# Fix Windows console encoding
if sys.platform == "win32":
    os.environ.setdefault("PYTHONIOENCODING", "utf-8")
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")


def load_all_candidates(base_dir: Path) -> list[dict]:
    """Load and merge candidates from all subdirectories."""
    all_candidates = []
    seen_ids = set()

    for candidates_file in base_dir.rglob("candidates.json"):
        # Skip merged output
        if candidates_file.parent == base_dir and candidates_file.name == "merged_candidates.json":
            continue

        try:
            data = json.loads(candidates_file.read_text(encoding="utf-8"))
            keyword = data.get("keyword", "unknown")
            for c in data.get("candidates", []):
                vid_id = c.get("id", "")
                if vid_id and vid_id not in seen_ids:
                    seen_ids.add(vid_id)
                    c["source_keyword"] = keyword
                    c["source_dir"] = str(candidates_file.parent.relative_to(base_dir))
                    all_candidates.append(c)
        except Exception as e:
            print(f"[warn] Failed to load {candidates_file}: {e}", file=sys.stderr)

    return all_candidates


def composite_score(c: dict) -> float:
    """
    Composite ranking score: sqrt(views) * min(engagement, 15%).
    - sqrt(views) ensures reach matters heavily (37 views = 6, 170K = 413)
    - Cap engagement at 15% to prevent tiny channels gaming the rank
    """
    views = max(c.get("views", 0), 1)
    eng = min(c.get("engagement_pct", 0), 15.0)  # Cap at 15%
    if not c.get("has_stats", False):
        return math.sqrt(views) * 0.01
    return math.sqrt(views) * eng


def download_video(url: str, output_path: Path, cookies_browser: str = "") -> bool:
    """Download a single video using yt-dlp."""
    cmd = [
        "yt-dlp",
        "-f", "bestvideo[height<=720]+bestaudio/best[height<=720]",
        "--merge-output-format", "mp4",
        "-o", str(output_path),
        "--no-playlist",
        "--quiet",
        "--no-warnings",
    ]
    if cookies_browser:
        cmd.extend(["--cookies-from-browser", cookies_browser])
    cmd.append(url)

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", timeout=300)
        return result.returncode == 0
    except subprocess.TimeoutExpired:
        print(f"[warn] Download timed out: {url}", file=sys.stderr)
        return False
    except Exception as e:
        print(f"[warn] Download failed: {e}", file=sys.stderr)
        return False


def main():
    parser = argparse.ArgumentParser(description="Merge candidates + download top N videos")
    parser.add_argument("--input", required=True, help="Base directory with keyword subdirs")
    parser.add_argument("--top", type=int, default=10, help="Number of top videos to download")
    parser.add_argument("--output", required=True, help="Output directory for videos")
    parser.add_argument("--min-views", type=int, default=1000, help="Minimum views to consider")
    parser.add_argument("--cookies", default="", help="Browser for cookies (e.g. chrome)")
    parser.add_argument("--dry-run", action="store_true", help="Show ranking without downloading")

    args = parser.parse_args()

    base_dir = Path(args.input)
    out_dir = Path(args.output)
    out_dir.mkdir(parents=True, exist_ok=True)

    # --- Step 1: Merge ---
    print(f"[merge] Scanning {base_dir} for candidates.json files...")
    all_candidates = load_all_candidates(base_dir)
    print(f"   Found {len(all_candidates)} unique candidates")

    if not all_candidates:
        print("   ERROR: No candidates found.")
        return

    # --- Step 1.5: Filter by min views ---
    before = len(all_candidates)
    all_candidates = [c for c in all_candidates if c.get("views", 0) >= args.min_views]
    print(f"   After min-views filter ({args.min_views}): {len(all_candidates)} (filtered {before - len(all_candidates)})")

    if not all_candidates:
        print("   ERROR: No candidates passed min-views filter. Try lowering --min-views.")
        return

    # --- Step 2: Score and rank ---
    for c in all_candidates:
        c["composite_score"] = round(composite_score(c), 2)

    all_candidates.sort(key=lambda x: x["composite_score"], reverse=True)

    for i, c in enumerate(all_candidates, 1):
        c["global_rank"] = i

    # --- Step 3: Show top N ---
    top_n = all_candidates[:args.top]

    print(f"\n   Top {args.top} by composite score (log10(views) x engagement%):")
    print(f"   {'#':>3} {'Score':>7} {'Views':>10} {'Eng%':>6} {'Dur':>5} {'Keyword':<25} {'Title':<50}")
    print(f"   {'---':>3} {'-------':>7} {'----------':>10} {'------':>6} {'-----':>5} {'-'*25:<25} {'-'*50:<50}")
    for c in top_n:
        stat = f"{c['engagement_pct']:.1f}%" if c.get("has_stats") else "n/a"
        print(f"   {c['global_rank']:>3} {c['composite_score']:>7.1f} {c['views']:>10,} {stat:>6} "
              f"{c['duration_sec']:>4}s {c.get('source_keyword', ''):<25} {c['title'][:50]}")

    # Save merged ranking
    merged_path = base_dir / "merged_candidates.json"
    merged_data = {
        "total_unique": len(all_candidates),
        "top_n": args.top,
        "candidates": all_candidates[:50],
    }
    merged_path.write_text(json.dumps(merged_data, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n   Merged ranking -> {merged_path}")

    if args.dry_run:
        print("\n   --dry-run: skipping downloads.")
        return

    # --- Step 4: Download ---
    print(f"\n[download] Downloading {len(top_n)} videos...")
    success = 0
    for c in top_n:
        rank = c["global_rank"]
        vid_id = c["id"]
        safe_title = "".join(ch if ch.isalnum() or ch in "-_ " else "" for ch in c["title"][:30]).strip()
        filename = f"{rank:03d}_{safe_title}_{vid_id}.mp4"
        output_path = out_dir / filename

        if output_path.exists():
            print(f"   #{rank} already exists, skipping")
            c["local_video"] = str(output_path)
            success += 1
            continue

        print(f"   #{rank} downloading: {c['title'][:50]}...")
        if download_video(c["url"], output_path, args.cookies):
            print(f"   #{rank} -> {filename}")
            c["local_video"] = str(output_path)
            success += 1
        else:
            print(f"   #{rank} FAILED")

    print(f"\n   Done! {success}/{len(top_n)} downloaded to {out_dir}")

    # Update merged file with download paths
    merged_path.write_text(json.dumps(merged_data, ensure_ascii=False, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
