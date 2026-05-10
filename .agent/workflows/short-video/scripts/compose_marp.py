# /// script
# requires-python = ">=3.12"
# dependencies = [
#   "loguru",
# ]
# ///
"""
compose_marp.py — Marp slides.md → PNG 渲染器
===============================================
纯渲染工具：接收 AI 自由创作的 slides.md，调用 marp-cli 输出 PNG。
不包含任何模板、样式、布局逻辑——这些全部由 AI agent 在写 slides.md 时自行决定。

用法:
  uv run compose_marp.py --slides data/short-videos/{slug}/slides/slides.md

产出:
  slides/slides.001.png
  slides/slides.002.png
  ...
"""
from __future__ import annotations

import argparse
import subprocess
from pathlib import Path

from loguru import logger

import shutil
import sys

def render_marp(slides_md: Path):
    """调用 marp-cli 将 slides.md 渲染为 PNG 图片。"""
    if not slides_md.exists():
        logger.error(f"slides.md not found: {slides_md}")
        return

    output_dir = slides_md.parent
    logger.info(f"Rendering {slides_md.name} → PNG ...")

    # 不用 --output，让 Marp 在 slides.md 同目录下生成 slides.001.png 等
    cmd = [
        "npx", "-y", "@marp-team/marp-cli",
        str(slides_md),
        "--images", "png",
    ]

    r = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        timeout=120,
        shell=(sys.platform == "win32"),  # Windows 需要 shell 才能找到 npx.cmd
    )

    if r.returncode != 0:
        logger.error(f"marp-cli failed:\n{r.stderr[:500]}")
        return

    # ── 后处理：确保文件在 slides/ 目录且带 .png 后缀 ──
    # Marp 有时输出无后缀文件（如 slides.001），或输出到上级目录
    # 1) 检查上级目录是否有溢出文件
    parent_dir = output_dir.parent
    for f in sorted(parent_dir.glob("slides.[0-9]*")):
        if f.is_file() and not f.suffix:
            target = output_dir / (f.name + ".png")
            f.rename(target)
            logger.debug(f"Moved & renamed: {f.name} → {target.name}")
        elif f.is_file() and f.suffix == ".png":
            target = output_dir / f.name
            if not target.exists():
                f.rename(target)
                logger.debug(f"Moved: {f.name} → slides/{f.name}")

    # 2) 检查本目录无后缀文件
    for f in sorted(output_dir.glob("slides.[0-9]*")):
        if f.is_file() and not f.suffix:
            target = f.with_suffix(".png")
            f.rename(target)
            logger.debug(f"Renamed: {f.name} → {target.name}")

    pngs = sorted(output_dir.glob("slides.*.png"))
    if not pngs:
        pngs = sorted(output_dir.glob("*.png"))
    logger.success(f"Rendered {len(pngs)} PNG slides in {output_dir}")


def main():
    p = argparse.ArgumentParser(description="Marp slides.md → PNG 渲染器")
    p.add_argument("--slides", type=Path, required=True, help="slides.md 路径")
    args = p.parse_args()
    render_marp(args.slides)


if __name__ == "__main__":
    main()
