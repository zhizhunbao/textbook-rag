#!/usr/bin/env python3
"""
discover.py — 竞品短视频搜索 + 筛选脚本
Competitor short-video discovery & filtering script.

Usage:
    uv run .agent/workflows/short-video/competitor-analysis/scripts/discover.py \
        --keyword "infographic shorts" \
        --platform youtube \
        --limit 30 \
        --min-likes 100 \
        --duration 15-180 \
        --output data/competitor-analysis/2026-05/
        [--debug]
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

# Fix Windows console encoding for emoji/CJK output
if sys.platform == "win32":
    os.environ.setdefault("PYTHONIOENCODING", "utf-8")
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def run_ytdlp(args: list[str]) -> str:
    """Run yt-dlp with given args and return stdout."""
    cmd = ["yt-dlp", *args]
    result = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8")
    if result.returncode != 0:
        print(f"[warn] yt-dlp stderr: {result.stderr.strip()}", file=sys.stderr)
    return result.stdout


def parse_duration_range(dur_str: str) -> tuple[int, int]:
    """Parse '30-120' -> (30, 120)."""
    lo, hi = dur_str.split("-")
    return int(lo), int(hi)


def search_videos(keyword: str, platform: str, limit: int) -> list[dict]:
    """
    Search for videos by keyword using yt-dlp.
    Returns list of raw JSON dicts from yt-dlp.
    """
    if platform != "youtube":
        print(f"[warn] Platform '{platform}' not fully supported, falling back to ytsearch.")

    search_query = f"ytsearch{limit}:{keyword}"

    raw = run_ytdlp([
        search_query,
        "--dump-json",
        "--no-download",
        "--no-playlist",
        "--ignore-errors",
        "--quiet",
    ])

    entries = []
    for line in raw.strip().split("\n"):
        line = line.strip()
        if not line:
            continue
        try:
            data = json.loads(line)
            entries.append(data)
        except json.JSONDecodeError:
            continue

    return entries


def extract_metadata(entry: dict) -> dict | None:
    """Extract relevant metadata from a yt-dlp JSON entry."""
    try:
        vid_id = entry.get("id", "")
        url = entry.get("webpage_url") or entry.get("url") or f"https://www.youtube.com/watch?v={vid_id}"
        title = entry.get("title", "unknown")
        duration = entry.get("duration")
        views = entry.get("view_count")
        likes = entry.get("like_count")           # may be None!
        comments = entry.get("comment_count")      # may be None!
        creator = entry.get("channel") or entry.get("uploader") or "unknown"
        upload_date = entry.get("upload_date", "")
        thumbnail = entry.get("thumbnail", "")

        # Mark whether stats are available
        has_stats = likes is not None

        # Safely default to 0 for calculations
        views_safe = views or 0
        likes_safe = likes or 0
        comments_safe = comments or 0

        # Calculate engagement rate: (likes + comments) / views
        engagement = 0.0
        if has_stats and views_safe > 0:
            engagement = (likes_safe + comments_safe) / views_safe * 100

        return {
            "id": vid_id,
            "url": url,
            "title": title,
            "creator": creator,
            "platform": "youtube",
            "duration_sec": int(duration) if duration else 0,
            "views": int(views_safe),
            "likes": int(likes_safe),
            "comments": int(comments_safe),
            "engagement_pct": round(engagement, 2),
            "has_stats": has_stats,
            "upload_date": upload_date,
            "thumbnail_url": thumbnail,
        }
    except Exception as e:
        print(f"[warn] Failed to extract metadata: {e}", file=sys.stderr)
        return None


def filter_candidates(
    candidates: list[dict],
    min_likes: int,
    dur_range: tuple[int, int],
) -> list[dict]:
    """
    Apply filtering rules:
      - duration within range
      - If stats available: likes >= min_likes AND engagement >= 1%
      - If stats NOT available: keep (will be sorted by views instead)
    """
    lo, hi = dur_range
    filtered = []
    skipped_duration = 0
    skipped_likes = 0
    skipped_engagement = 0

    for c in candidates:
        # Duration filter (always apply)
        if not (lo <= c["duration_sec"] <= hi):
            skipped_duration += 1
            continue

        # If we have stats, apply likes + engagement filters
        if c["has_stats"]:
            if c["likes"] < min_likes:
                skipped_likes += 1
                continue
            if c["engagement_pct"] < 1.0:
                skipped_engagement += 1
                continue

        # No stats = keep (can't filter what we don't have)
        filtered.append(c)

    print(f"   Filter breakdown: duration={skipped_duration}, "
          f"likes={skipped_likes}, engagement={skipped_engagement}")
    return filtered


def download_thumbnail(url: str, dest: Path) -> bool:
    """Download a single thumbnail image."""
    if not url:
        return False
    try:
        import urllib.request
        urllib.request.urlretrieve(url, str(dest))
        return True
    except Exception as e:
        print(f"[warn] Thumbnail download failed: {e}", file=sys.stderr)
        return False


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Competitor short-video discovery & filtering"
    )
    parser.add_argument("--keyword", required=True, help="Search keyword")
    parser.add_argument("--platform", default="youtube", help="Platform (default: youtube)")
    parser.add_argument("--limit", type=int, default=30, help="Max search results")
    parser.add_argument("--min-likes", type=int, default=100, help="Minimum likes to keep")
    parser.add_argument("--duration", default="15-180", help="Duration range in seconds, e.g. 15-180")
    parser.add_argument("--output", required=True, help="Output directory")
    parser.add_argument("--debug", action="store_true", help="Print raw entry fields for debugging")

    args = parser.parse_args()

    out_dir = Path(args.output)
    out_dir.mkdir(parents=True, exist_ok=True)
    thumb_dir = out_dir / "thumbnails"
    thumb_dir.mkdir(exist_ok=True)

    dur_range = parse_duration_range(args.duration)

    # --- Step 1: Search ---
    print(f"[search] keyword='{args.keyword}' platform={args.platform} limit={args.limit}")
    raw_entries = search_videos(args.keyword, args.platform, args.limit)
    print(f"   Found {len(raw_entries)} raw entries")

    # --- Debug: show raw fields ---
    if args.debug and raw_entries:
        print(f"\n   === DEBUG: first 3 raw entries ===")
        for i, entry in enumerate(raw_entries[:3]):
            print(f"   [{i}] id={entry.get('id')}")
            print(f"       title={entry.get('title', '')[:60]}")
            print(f"       duration={entry.get('duration')}")
            print(f"       view_count={entry.get('view_count')}")
            print(f"       like_count={entry.get('like_count')}")
            print(f"       comment_count={entry.get('comment_count')}")
            print(f"       channel={entry.get('channel')}")
        print(f"   === END DEBUG ===\n")

    # --- Step 2: Extract metadata ---
    candidates = []
    stats_count = 0
    for entry in raw_entries:
        meta = extract_metadata(entry)
        if meta:
            candidates.append(meta)
            if meta["has_stats"]:
                stats_count += 1

    print(f"   Extracted {len(candidates)} entries ({stats_count} with full stats, "
          f"{len(candidates) - stats_count} without likes/comments)")

    # --- Step 3: Filter ---
    filtered = filter_candidates(candidates, args.min_likes, dur_range)
    print(f"   After filtering: {len(filtered)} candidates")

    # --- Step 4: Sort ---
    # Entries with stats: sort by engagement
    # Entries without stats: sort by views (best proxy)
    with_stats = [c for c in filtered if c["has_stats"]]
    without_stats = [c for c in filtered if not c["has_stats"]]
    with_stats.sort(key=lambda x: x["engagement_pct"], reverse=True)
    without_stats.sort(key=lambda x: x["views"], reverse=True)
    sorted_all = with_stats + without_stats

    # Add rank
    for i, c in enumerate(sorted_all, 1):
        c["rank"] = i

    # --- Step 5: Download thumbnails ---
    print(f"   Downloading {len(sorted_all)} thumbnails...")
    for c in sorted_all:
        thumb_file = thumb_dir / f"{c['rank']:03d}_{c['id']}.jpg"
        if download_thumbnail(c["thumbnail_url"], thumb_file):
            c["thumbnail_local"] = str(thumb_file.relative_to(out_dir))

    # --- Step 6: Write candidates.json ---
    output_data = {
        "keyword": args.keyword,
        "platform": args.platform,
        "search_limit": args.limit,
        "filters": {
            "min_likes": args.min_likes,
            "duration_range": args.duration,
            "min_engagement_pct": 1.0,
        },
        "total_found": len(raw_entries),
        "with_stats": stats_count,
        "after_filter": len(sorted_all),
        "candidates": sorted_all,
    }

    candidates_path = out_dir / "candidates.json"
    candidates_path.write_text(
        json.dumps(output_data, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print(f"\n   Done! {len(sorted_all)} candidates -> {candidates_path}")
    if sorted_all:
        print(f"   Top 5:")
        for c in sorted_all[:5]:
            stat_info = f"eng={c['engagement_pct']:.1f}%" if c["has_stats"] else f"views={c['views']:,}"
            print(f"     #{c['rank']} [{stat_info}] {c['title'][:55]}")

    if len(sorted_all) < 20:
        print(f"\n   WARNING: Only {len(sorted_all)} candidates (target: >=20).")
        print(f"   Try: --min-likes 0, wider --duration, different --keyword")


if __name__ == "__main__":
    main()
