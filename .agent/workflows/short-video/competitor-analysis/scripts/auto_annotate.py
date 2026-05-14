#!/usr/bin/env python3
"""
auto_annotate.py — 自动抽帧 + 场景检测 + 生成标注框架
Auto keyframe extraction + scene detection + annotation scaffold generation.

Requires: ffmpeg in PATH

Usage:
    uv run .agent/workflows/short-video/competitor-analysis/scripts/auto_annotate.py \
        --input data/competitor-analysis/2026-05/ \
        --videos data/competitor-analysis/2026-05/videos/ \
        --output data/competitor-analysis/2026-05/analyses/
"""

from __future__ import annotations

import argparse
import json
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


def extract_keyframes(video_path: Path, output_dir: Path, interval_sec: int = 3) -> list[str]:
    """
    Extract keyframes every N seconds using ffmpeg.
    Returns list of output image paths.
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    stem = video_path.stem
    pattern = str(output_dir / f"{stem}_%03d.jpg")

    cmd = [
        "ffmpeg", "-i", str(video_path),
        "-vf", f"fps=1/{interval_sec}",
        "-q:v", "3",  # JPEG quality (2=best, 31=worst)
        "-y",  # Overwrite
        pattern,
    ]

    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True,
            encoding="utf-8", timeout=120
        )
        if result.returncode != 0:
            print(f"   [warn] ffmpeg error for {video_path.name}: {result.stderr[:200]}", file=sys.stderr)
            return []
    except subprocess.TimeoutExpired:
        print(f"   [warn] ffmpeg timed out for {video_path.name}", file=sys.stderr)
        return []

    # Collect output frames
    frames = sorted(output_dir.glob(f"{stem}_*.jpg"))
    return [str(f) for f in frames]


def detect_scene_changes(video_path: Path, threshold: float = 0.3) -> list[float]:
    """
    Detect scene changes using ffmpeg's scene detection filter.
    Returns list of timestamps where scenes change.
    """
    cmd = [
        "ffmpeg", "-i", str(video_path),
        "-vf", f"select='gt(scene,{threshold})',showinfo",
        "-f", "null", "-",
    ]

    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True,
            encoding="utf-8", timeout=120
        )
        # Parse timestamps from showinfo output
        timestamps = []
        for line in result.stderr.split("\n"):
            if "pts_time:" in line:
                try:
                    pts_part = line.split("pts_time:")[1].split()[0]
                    timestamps.append(float(pts_part))
                except (IndexError, ValueError):
                    continue
        return timestamps
    except Exception:
        return []


def get_video_duration(video_path: Path) -> float:
    """Get video duration in seconds using ffprobe."""
    cmd = [
        "ffprobe", "-v", "error",
        "-show_entries", "format=duration",
        "-of", "csv=p=0",
        str(video_path),
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", timeout=30)
        return float(result.stdout.strip())
    except Exception:
        return 0.0


def extract_dominant_colors(frame_path: Path) -> list[str]:
    """
    Extract dominant colors from a frame using ffmpeg's palettegen.
    Returns hex color strings.
    """
    palette_path = frame_path.parent / f"{frame_path.stem}_palette.png"
    cmd = [
        "ffmpeg", "-i", str(frame_path),
        "-vf", "palettegen=max_colors=5:stats_mode=single",
        "-y", str(palette_path),
    ]
    try:
        subprocess.run(cmd, capture_output=True, timeout=30)
        # We'll just note that palette was generated;
        # actual color reading would need PIL or manual inspection
        if palette_path.exists():
            palette_path.unlink()  # Clean up
            return ["(see keyframes for colors)"]
    except Exception:
        pass
    return []


def generate_analysis_md(
    candidate: dict,
    video_path: Path | None,
    frames: list[str],
    scene_changes: list[float],
    duration: float,
    rank: int,
    output_dir: Path,
) -> Path:
    """Generate analysis markdown file for a single video."""

    num_scenes = len(scene_changes) + 1  # +1 for initial scene
    avg_scene_dur = duration / num_scenes if num_scenes > 0 else duration

    # Build frame reference section
    frame_refs = ""
    if frames:
        frame_refs = "\n#### 关键帧参考\n\n"
        for i, f in enumerate(frames):
            ts = i * 3  # every 3 seconds
            frame_refs += f"- `{ts}s`: `{Path(f).name}`\n"

    # Build scene change section
    scene_str = ", ".join([f"{t:.1f}s" for t in scene_changes[:20]]) if scene_changes else "未检测到"

    md = f"""## 视频分析: {candidate.get('title', 'unknown')}

### 基本信息
- URL: {candidate.get('url', '')}
- 创作者: {candidate.get('creator', 'unknown')}
- 平台: {candidate.get('platform', 'youtube')}
- 时长: {duration:.0f}s
- 播放/赞/评: {candidate.get('views', 0):,} / {candidate.get('likes', 0):,} / {candidate.get('comments', 0):,}
- 互动率: {candidate.get('engagement_pct', 0):.2f}%
- 来源关键词: {candidate.get('source_keyword', '')}
- Composite Score: {candidate.get('composite_score', 0)}

---

### 🎬 场景检测 (自动)

- 检测到 **{num_scenes}** 个场景
- 平均每场景: **{avg_scene_dur:.1f}s**
- 切换时间点: {scene_str}
{frame_refs}

---

### 🎯 结构模式

#### 钩子 (前 3 秒)
- 类型: [待分析 - 查看第1帧]
- 描述: ""

#### Slide 编排
| # | 时间段 | 类型 | 内容概要 | 停留秒数 |
|---|--------|------|---------|---------|\n"""

    # Auto-fill slide table from scene changes
    prev_t = 0.0
    for i, t in enumerate(scene_changes[:15], 1):
        dur_s = t - prev_t
        md += f"| {i} | {prev_t:.0f}-{t:.0f}s | 待分析 | 查看帧 {Path(frames[int(t//3)]).name if frames and int(t//3) < len(frames) else '?'} | {dur_s:.1f}s |\n"
        prev_t = t
    # Last scene
    if duration > prev_t:
        md += f"| {len(scene_changes)+1} | {prev_t:.0f}-{duration:.0f}s | 待分析 | 最后一帧 | {duration-prev_t:.1f}s |\n"

    md += f"""
#### 节奏
- 总场景数: {num_scenes}
- 平均每场景: {avg_scene_dur:.1f}s
- 信息密度: [待分析]

---

### 🎨 布局模式
- 文字对齐: [待分析 - 查看帧]
- 表格: [待分析]
- 数字高亮: [待分析]
- 留白比例: [待分析]
- 字幕区位置: [待分析]

---

### 🌈 视觉风格
- 整体色调: [待分析 - 查看帧]
- 主色: [待分析]
- 强调色: [待分析]
- 字体风格: [待分析]
- 装饰元素: [待分析]

---

### 💬 字幕风格
- 位置: [待分析]
- 高亮方式: [待分析]
- 字号: [待分析]

---

### 💡 学到什么
- 可复用的模式: [待分析]
- 我们缺的: [待分析]
"""

    # Write file
    output_file = output_dir / f"{rank:03d}.md"
    output_file.write_text(md, encoding="utf-8")
    return output_file


def main():
    parser = argparse.ArgumentParser(description="Auto keyframe extraction + annotation scaffold")
    parser.add_argument("--input", required=True, help="Base dir with merged_candidates.json")
    parser.add_argument("--videos", required=True, help="Directory with downloaded videos")
    parser.add_argument("--output", required=True, help="Output directory for analyses")
    parser.add_argument("--interval", type=int, default=3, help="Keyframe interval in seconds")
    parser.add_argument("--scene-threshold", type=float, default=0.3, help="Scene change threshold")

    args = parser.parse_args()

    base_dir = Path(args.input)
    videos_dir = Path(args.videos)
    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)
    frames_dir = output_dir / "frames"
    frames_dir.mkdir(exist_ok=True)

    # Load merged candidates
    merged_path = base_dir / "merged_candidates.json"
    if not merged_path.exists():
        print(f"ERROR: {merged_path} not found. Run batch_download.py first.")
        return

    data = json.loads(merged_path.read_text(encoding="utf-8"))
    candidates = data.get("candidates", [])

    # Find downloaded videos
    video_files = list(videos_dir.glob("*.mp4"))
    print(f"[annotate] Found {len(video_files)} videos in {videos_dir}")

    if not video_files:
        print("   No videos to analyze. Run batch_download.py first.")
        return

    # Match videos to candidates by ID
    vid_map = {}
    for vf in video_files:
        for c in candidates:
            if c["id"] in vf.name:
                vid_map[c["id"]] = (c, vf)
                break

    print(f"   Matched {len(vid_map)} videos to candidates")

    # Process each video
    results = []
    for i, (vid_id, (candidate, video_path)) in enumerate(vid_map.items(), 1):
        print(f"\n[{i}/{len(vid_map)}] Processing: {candidate['title'][:50]}...")

        # Get duration
        duration = get_video_duration(video_path)
        print(f"   Duration: {duration:.0f}s")

        # Extract keyframes
        vid_frames_dir = frames_dir / f"{i:03d}_{vid_id}"
        print(f"   Extracting keyframes (every {args.interval}s)...")
        frames = extract_keyframes(video_path, vid_frames_dir, args.interval)
        print(f"   Got {len(frames)} keyframes")

        # Detect scene changes
        print(f"   Detecting scene changes (threshold={args.scene_threshold})...")
        scenes = detect_scene_changes(video_path, args.scene_threshold)
        print(f"   Found {len(scenes)} scene changes")

        # Generate analysis markdown
        analysis_path = generate_analysis_md(
            candidate, video_path, frames, scenes, duration, i, output_dir
        )
        print(f"   Analysis scaffold -> {analysis_path.name}")

        results.append({
            "rank": i,
            "id": vid_id,
            "title": candidate["title"],
            "frames_count": len(frames),
            "scenes_count": len(scenes) + 1,
            "avg_scene_duration": round(duration / (len(scenes) + 1), 1) if scenes else duration,
            "frames_dir": str(vid_frames_dir),
            "analysis_file": str(analysis_path),
        })

    # Save summary
    summary_path = output_dir / "annotation_summary.json"
    summary_path.write_text(
        json.dumps({"processed": len(results), "results": results},
                   ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print(f"\n{'='*60}")
    print(f"Done! {len(results)} videos analyzed")
    print(f"   Analyses: {output_dir}")
    print(f"   Keyframes: {frames_dir}")
    print(f"   Summary: {summary_path}")
    print(f"\nNext: Agent can view keyframes to fill in [待分析] fields")


if __name__ == "__main__":
    main()
