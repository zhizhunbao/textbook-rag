"""
Batch regenerate & upload videos: TTS -> Remotion render -> WeChat upload.

Re-synthesizes narration and re-renders all videos that have storyline.md.
Skips EE/SP (immigration-focused) videos by default.

Usage:
    uv run scripts/batch_regen.py --dry-run            # Preview + compliance scan
    uv run scripts/batch_regen.py                       # Full: TTS + Render
    uv run scripts/batch_regen.py --render-only         # Skip TTS
    uv run scripts/batch_regen.py --filter bank         # Only matching slugs
    uv run scripts/batch_regen.py --include-all         # Include EE/SP videos too
    uv run scripts/batch_regen.py --upload              # TTS + Render + Upload
    uv run scripts/batch_regen.py --upload-only         # Upload existing videos
    uv run scripts/batch_regen.py --scan                # Compliance scan only
"""

# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///

import argparse
import re
import subprocess
import sys
import time
from pathlib import Path

# Fix Windows console encoding
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.stderr.reconfigure(encoding="utf-8", errors="replace")

PROJECT_ROOT = Path(__file__).parent.parent
VIDEO_DIR = PROJECT_ROOT / "data" / "short-videos"
WORKFLOW_DIR = PROJECT_ROOT / ".agent" / "workflows" / "short-video"
PUBLISH_SCRIPT = WORKFLOW_DIR / "scripts" / "publish_weixin.py"

# Immigration-focused prefixes to skip by default (platform compliance)
SKIP_PREFIXES = ("ee-", "sp-", "pnp")

# Hard-blocked words (should never appear in narration/title)
# immigration-consultant, immigration-agent, proxy-visa, proxy, DM-me, add-me
SENSITIVE_WORDS = [
    "\u79fb\u6c11\u987e\u95ee",  # immigration consultant
    "\u79fb\u6c11\u4e2d\u4ecb",  # immigration agent
    "\u4ee3\u529e\u7b7e\u8bc1",  # proxy visa
    "\u4ee3\u529e",              # proxy/agent
    "\u79c1\u4fe1",              # DM me
    "\u52a0\u6211",              # add me
]
# Soft warnings (OK in citations, risky in narration)
# immigration, visa, agent, IRCC, new-immigrant
WARN_WORDS = [
    "\u79fb\u6c11",    # immigration
    "\u7b7e\u8bc1",    # visa
    "\u4e2d\u4ecb",    # agent
    "IRCC",
    "\u65b0\u79fb\u6c11",  # new immigrant
]


def discover_videos(filter_str: str = "", include_all: bool = False) -> list[Path]:
    """Find all video dirs with storyline.md."""
    videos = []
    for d in sorted(VIDEO_DIR.iterdir()):
        if not d.is_dir():
            continue
        if not (d / "storyline.md").exists():
            continue
        if filter_str and filter_str not in d.name:
            continue
        if not include_all and d.name.startswith(SKIP_PREFIXES):
            continue
        videos.append(d)
    return videos


def scan_compliance(video_dir: Path) -> dict:
    """Scan storyline.md for compliance issues."""
    sl = video_dir / "storyline.md"
    text = sl.read_text(encoding="utf-8")

    issues = {"errors": [], "warnings": []}

    # Check author field
    author_match = re.search(r"\*\*作者\*\*:\s*(.+)", text)
    if author_match:
        author = author_match.group(1).strip()
        if author != "海外生活指南":
            issues["errors"].append(f"author='{author}', should be '海外生活指南'")

    # Extract narration lines only (not citation blocks)
    narration_blocks = re.findall(
        r"\*\*台词\*\*:\s*\n((?:(?!---|\*\*).+\n)*)", text, re.MULTILINE
    )
    narration_text = "\n".join(narration_blocks)

    # Extract titles
    titles = re.findall(r"^#{1,2}\s+.+$", text, re.MULTILINE)
    title_text = "\n".join(titles)

    check_text = narration_text + "\n" + title_text

    for w in SENSITIVE_WORDS:
        if w in check_text:
            issues["errors"].append(f"blocked word '{w}' in narration/title")

    for w in WARN_WORDS:
        count = check_text.count(w)
        if count > 0:
            issues["warnings"].append(f"'{w}' x{count} in narration/title")

    # Check for disclaimer slide
    if "[disclaimer]" not in text:
        issues["warnings"].append("no [disclaimer] slide")

    return issues


def run_tts(video_dir: Path, backend: str, voice: str) -> bool:
    """Run TTS synthesis."""
    cmd = [
        "uv", "run",
        str(WORKFLOW_DIR / "scripts" / "synthesize.py"),
        "--storyline", str(video_dir / "storyline.md"),
        "--output", str(video_dir / "narration") + "/",
        "--backend", backend,
        "--voice", voice,
        "--gap", "300",
        "--slide-gap", "800",
        "--fade", "80",
    ]
    print()
    result = subprocess.run(cmd, timeout=600)
    return result.returncode == 0


def run_render(video_dir: Path) -> bool:
    """Run Remotion render."""
    cmd = [
        "node",
        str(WORKFLOW_DIR / "remotion" / "render.mjs"),
        "--data", str(video_dir),
    ]
    print()
    result = subprocess.run(cmd, timeout=1200)
    return result.returncode == 0


def run_upload(video_dir: Path, dry_run: bool = False) -> bool:
    """Upload video to WeChat."""
    cmd = [
        "uv", "run", str(PUBLISH_SCRIPT),
        "--video", str(video_dir / "output" / "final.mp4"),
        "--storyline", str(video_dir / "storyline.md"),
        "--auto-close",
    ]
    if dry_run:
        cmd.append("--dry-run")
    print()
    result = subprocess.run(cmd, timeout=300)
    return result.returncode == 0


def main():
    parser = argparse.ArgumentParser(description="Batch regenerate & upload videos")
    parser.add_argument("--dry-run", action="store_true", help="Preview + compliance scan")
    parser.add_argument("--render-only", action="store_true", help="Skip TTS")
    parser.add_argument("--upload", action="store_true", help="Upload after render")
    parser.add_argument("--upload-only", action="store_true", help="Upload existing videos")
    parser.add_argument("--scan", action="store_true", help="Compliance scan only")
    parser.add_argument("--filter", default="", help="Only slugs containing this string")
    parser.add_argument("--include-all", action="store_true", help="Include EE/SP videos")
    parser.add_argument("--backend", default="edge", help="TTS backend")
    parser.add_argument("--voice", default="zh-CN-YunyangNeural", help="TTS voice")
    parser.add_argument(
        "--upload-interval", type=int, default=300,
        help="Seconds between uploads to avoid rate limiting (default: 300)",
    )
    args = parser.parse_args()

    videos = discover_videos(args.filter, args.include_all)

    if args.scan:
        mode = "COMPLIANCE SCAN"
    elif args.upload_only:
        mode = "UPLOAD ONLY"
    elif args.dry_run:
        mode = "DRY RUN + SCAN"
    elif args.render_only:
        mode = "RENDER ONLY"
    elif args.upload:
        mode = "FULL (TTS + Render + Upload)"
    else:
        mode = "FULL (TTS + Render)"

    print(f"\n{'='*60}")
    print(f"  Batch Video Regeneration")
    print(f"{'='*60}")
    print(f"  Videos: {len(videos)}")
    print(f"  Mode:   {mode}")
    if not args.scan:
        print(f"  TTS:    {args.backend} / {args.voice}")
    if not args.include_all:
        print(f"  Skip:   {SKIP_PREFIXES} (use --include-all to override)")
    print(f"{'='*60}\n")

    # ── Compliance Scan (always run for dry-run and scan modes) ──
    if args.scan or args.dry_run:
        has_errors = False
        for v in videos:
            slug = v.name
            issues = scan_compliance(v)
            errs = issues["errors"]
            warns = issues["warnings"]
            has_narr = "Y" if (v / "narration" / "narration.wav").exists() else "N"
            has_vid = "Y" if (v / "output" / "final.mp4").exists() else "N"

            if errs:
                label = "ERROR"
            elif warns:
                label = "WARN "
            else:
                label = "OK   "
            print(f"  [{label}] {slug:35s}  narr={has_narr}  vid={has_vid}")
            for e in errs:
                print(f"          ! {e}")
                has_errors = True
            for w in warns:
                print(f"          ~ {w}")

        if args.scan:
            print(f"\n  {'Fix errors before regenerating.' if has_errors else 'All clear.'}\n")
            return
        print(f"\n  --dry-run, exiting.\n")
        return

    # ── Main processing loop ──
    results = []
    total_start = time.time()

    for i, v in enumerate(videos, 1):
        slug = v.name
        print(f"\n[{i}/{len(videos)}] {slug}")
        print(f"{'-'*50}")

        step_start = time.time()
        status = "success"

        if args.upload_only:
            if not (v / "output" / "final.mp4").exists():
                print(f"  [SKIP] No final.mp4")
                results.append((slug, "no_video", 0))
                continue
            print(f"  Uploading...", end=" ", flush=True)
            if run_upload(v):
                print("OK")
            else:
                print("FAILED")
                status = "upload_failed"
            if i < len(videos):
                print(f"  Waiting {args.upload_interval}s before next upload...")
                time.sleep(args.upload_interval)
        else:
            # ── TTS ──
            if not args.render_only:
                print(f"  [1/2] TTS synthesizing...", end=" ", flush=True)
                if run_tts(v, args.backend, args.voice):
                    print("OK")
                else:
                    print("FAILED")
                    status = "tts_failed"
                    results.append((slug, status, 0))
                    continue
            else:
                if not (v / "narration" / "narration.wav").exists():
                    print(f"  [SKIP] No narration.wav")
                    results.append((slug, "no_narration", 0))
                    continue
                print(f"  [1/2] TTS skipped (render-only)")

            # ── Render ──
            print(f"  [2/2] Remotion rendering...", end=" ", flush=True)
            if run_render(v):
                print("OK")
            else:
                print("FAILED")
                status = "render_failed"

            # ── Upload (optional) ──
            if args.upload and status == "success":
                print(f"  [3/3] Uploading...", end=" ", flush=True)
                if run_upload(v):
                    print("OK")
                else:
                    print("FAILED")
                    status = "upload_failed"
                if i < len(videos):
                    print(f"  Waiting {args.upload_interval}s...")
                    time.sleep(args.upload_interval)

        elapsed = time.time() - step_start
        print(f"  Done in {elapsed:.0f}s")
        results.append((slug, status, round(elapsed)))

    # ── Summary ──
    total_elapsed = (time.time() - total_start) / 60
    success = sum(1 for _, s, _ in results if s == "success")
    failed = [(slug, s) for slug, s, _ in results if s != "success"]

    print(f"\n{'='*60}")
    print(f"  BATCH COMPLETE")
    print(f"{'='*60}")
    print(f"  Total time: {total_elapsed:.1f} min")
    print(f"  Success:    {success}/{len(results)}")
    if failed:
        print(f"  Failed:")
        for slug, s in failed:
            print(f"    - {slug}: {s}")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    main()
