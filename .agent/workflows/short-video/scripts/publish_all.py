#!/usr/bin/env python3
"""
publish_all.py — 多平台一键发布脚本
=====================================

统一入口：读取 storyline.md 元数据，发布到多个平台。
底层调用 social-auto-upload (SAU) 的 CLI 完成实际上传。

用法:
    # 首次：逐平台扫码登录
    uv run .agent/workflows/short-video/scripts/publish_all.py --login xiaohongshu
    uv run .agent/workflows/short-video/scripts/publish_all.py --login douyin
    uv run .agent/workflows/short-video/scripts/publish_all.py --login bilibili

    # 检查所有平台登录状态
    uv run .agent/workflows/short-video/scripts/publish_all.py --check

    # 发布到所有已登录平台
    uv run .agent/workflows/short-video/scripts/publish_all.py \\
        --video data/short-videos/life-bank-choose/output/final.mp4 \\
        --storyline data/short-videos/life-bank-choose/storyline.md

    # 只发布到指定平台
    uv run .agent/workflows/short-video/scripts/publish_all.py \\
        --video data/short-videos/life-bank-choose/output/final.mp4 \\
        --storyline data/short-videos/life-bank-choose/storyline.md \\
        --platforms xiaohongshu,douyin

    # Dry run（不实际发布）
    uv run .agent/workflows/short-video/scripts/publish_all.py \\
        --video data/short-videos/life-bank-choose/output/final.mp4 \\
        --storyline data/short-videos/life-bank-choose/storyline.md \\
        --dry-run

Cookie 存储:
    小红书/抖音/快手:  .github/social-auto-upload/cookies/{platform}_{account}.json
    B站:               .github/social-auto-upload/cookies/bilibili_{account}.json
    视频号:            .agent/workflows/short-video/browser-data/weixin-channels/
"""

# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///

from __future__ import annotations

import argparse
import json
import logging
import os
import re
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("publish_all")

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
SCRIPT_DIR = Path(__file__).resolve().parent
WORKFLOW_DIR = SCRIPT_DIR.parent
PROJECT_ROOT = WORKFLOW_DIR.parent.parent.parent  # textbook-rag/
SAU_DIR = PROJECT_ROOT / ".github" / "social-auto-upload"
SAU_COOKIES_DIR = SAU_DIR / "cookies"

# Default account name（所有平台共用一个账号标识）
DEFAULT_ACCOUNT = "creator"

# ---------------------------------------------------------------------------
# Supported platforms
# ---------------------------------------------------------------------------
# 平台配置: 优先级从高到低
PLATFORMS = {
    "xiaohongshu": {
        "name": "小红书",
        "emoji": "📕",
        "sau": True,           # 走 SAU CLI
        "bilibili_tid": None,
    },
    "douyin": {
        "name": "抖音",
        "emoji": "🎵",
        "sau": True,
        "bilibili_tid": None,
    },
    "bilibili": {
        "name": "B站",
        "emoji": "📺",
        "sau": True,
        "bilibili_tid": 249,   # 生活 > 日常
    },
    "kuaishou": {
        "name": "快手",
        "emoji": "⚡",
        "sau": True,
        "bilibili_tid": None,
    },
    "weixin": {
        "name": "视频号",
        "emoji": "💬",
        "sau": False,          # 走独立 publish_weixin.py
        "bilibili_tid": None,
    },
}

# Base tags (always included) + keyword → topic tag mapping
_BASE_TAGS = ["加拿大生活", "海外生活攻略"]
_KEYWORD_TAG_MAP: list[tuple[list[str], str]] = [
    (["PR", "永居", "枫叶卡", "联邦", "通道", "EE", "PNP", "AIP"], "加拿大PR"),
    (["银行", "开户", "存款", "利率"], "加拿大银行"),
    (["工签", "工作", "LMIA"], "加拿大工作"),
    (["学签", "留学", "大学"], "留学生活"),
    (["租房", "买房", "住房"], "加拿大租房"),
    (["签证", "续签", "身份"], "加拿大签证"),
    (["报税", "税务", "退税"], "加拿大报税"),
    (["驾照", "买车", "保险"], "加拿大生活攻略"),
]


def _tags_from_title(title: str) -> str:
    """从 storyline 标题自动提取标签，回退到通用标签。"""
    tags = list(_BASE_TAGS)
    for keywords, tag in _KEYWORD_TAG_MAP:
        if any(kw in title for kw in keywords):
            if tag not in tags:
                tags.append(tag)
    # 至少 3 个标签
    if len(tags) < 3:
        tags.append("生活指南")
    return ",".join(tags[:5])  # 最多 5 个


# ---------------------------------------------------------------------------
# Storyline Parser — 复用 publish_weixin.py 的逻辑
# ---------------------------------------------------------------------------
def parse_storyline_metadata(storyline_path: Path) -> dict:
    """从 storyline.md 提取视频标题、描述等发布信息。"""
    text = storyline_path.read_text(encoding="utf-8")
    meta: dict = {}

    # H1 标题
    h1_match = re.search(r"^#\s+(.+)$", text, re.MULTILINE)
    if h1_match:
        meta["title"] = h1_match.group(1).strip()

    # 系列 / 作者
    series_match = re.search(r"\*\*系列\*\*:\s*(.+)", text)
    if series_match:
        meta["series"] = series_match.group(1).strip()

    author_match = re.search(r"\*\*作者\*\*:\s*(.+)", text)
    if author_match:
        meta["author"] = author_match.group(1).strip()

    # 从台词提取描述（排除 preview/cta/disclaimer/citation）
    preview_idx = re.search(r'^## \[(preview|cta|disclaimer|citation)\]', text, re.MULTILINE)
    text_for_narration = text[:preview_idx.start()] if preview_idx else text

    narration_lines = re.findall(
        r"^\*\*台词\*\*:\s*\n((?:(?!---).+\n)*)",
        text_for_narration,
        re.MULTILINE,
    )
    all_lines = []
    for block in narration_lines:
        for line in block.strip().split("\n"):
            line = line.strip()
            if line:
                all_lines.append(line)

    # 描述 = 前3行台词
    meta["description"] = "\n".join(all_lines[:3]) if all_lines else ""

    return meta


# ---------------------------------------------------------------------------
# SAU CLI Runner
# ---------------------------------------------------------------------------
def run_sau(args: list[str], timeout: int = 300) -> subprocess.CompletedProcess:
    """在 SAU 目录下运行 sau CLI 命令。"""
    cmd = ["uv", "run", "sau"] + args
    log.info(f"   $ {' '.join(cmd)}")
    result = subprocess.run(
        cmd,
        cwd=str(SAU_DIR),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=timeout,
    )
    if result.stdout.strip():
        log.info(f"   stdout: {result.stdout.strip()}")
    if result.stderr.strip():
        log.warning(f"   stderr: {result.stderr.strip()}")
    return result


def run_sau_interactive(args: list[str]) -> subprocess.CompletedProcess:
    """在 SAU 目录下运行交互式 sau CLI 命令（登录扫码用）。"""
    cmd = ["uv", "run", "sau"] + args
    log.info(f"   $ {' '.join(cmd)}")
    result = subprocess.run(
        cmd,
        cwd=str(SAU_DIR),
        timeout=300,
    )
    return result


# ---------------------------------------------------------------------------
# Login
# ---------------------------------------------------------------------------
def login_platform(platform: str, account: str) -> bool:
    """登录指定平台。"""
    cfg = PLATFORMS.get(platform)
    if not cfg:
        log.error(f"❌ 不支持的平台: {platform}")
        return False

    log.info(f"\n{'='*60}")
    log.info(f"{cfg['emoji']} 登录 {cfg['name']} (account={account})")
    log.info(f"{'='*60}")

    if platform == "weixin":
        # 视频号走独立脚本
        weixin_script = SCRIPT_DIR / "publish_weixin.py"
        cmd = ["uv", "run", str(weixin_script), "--login-only"]
        log.info(f"   $ {' '.join(cmd)}")
        result = subprocess.run(cmd, cwd=str(PROJECT_ROOT))
        return result.returncode == 0

    if platform == "bilibili":
        # B站需要交互式终端扫码
        result = run_sau_interactive([platform, "login", "--account", account])
        return result.returncode == 0

    # 小红书/抖音/快手 → headed 模式扫码
    result = run_sau_interactive([platform, "login", "--account", account, "--headed"])
    return result.returncode == 0


# ---------------------------------------------------------------------------
# Check Login Status
# ---------------------------------------------------------------------------
def check_platform(platform: str, account: str) -> bool:
    """检查平台登录状态。"""
    cfg = PLATFORMS.get(platform)
    if not cfg:
        return False

    if platform == "weixin":
        # 视频号检查浏览器数据目录是否存在
        weixin_data = WORKFLOW_DIR / "browser-data" / "weixin-channels"
        exists = weixin_data.exists() and any(weixin_data.iterdir())
        return exists

    if not cfg["sau"]:
        return False

    # 先检查 cookie 文件是否存在
    cookie_file = SAU_COOKIES_DIR / f"{platform}_{account}.json"
    if not cookie_file.exists():
        return False

    result = run_sau([platform, "check", "--account", account], timeout=30)
    return result.returncode == 0


def check_all(account: str):
    """检查所有平台登录状态。"""
    log.info("\n" + "=" * 60)
    log.info("  平台登录状态检查")
    log.info("=" * 60)

    results = {}
    for platform, cfg in PLATFORMS.items():
        ok = check_platform(platform, account)
        status = "✅ 已登录" if ok else "❌ 未登录"
        log.info(f"  {cfg['emoji']} {cfg['name']:6s}  {status}")
        results[platform] = ok

    logged_in = [p for p, ok in results.items() if ok]
    log.info(f"\n  已登录 {len(logged_in)}/{len(PLATFORMS)} 个平台")
    if logged_in:
        log.info(f"  可发布: {', '.join(logged_in)}")

    not_logged = [p for p, ok in results.items() if not ok]
    if not_logged:
        log.info(f"\n  未登录平台请运行:")
        for p in not_logged:
            log.info(f"    uv run .agent/workflows/short-video/scripts/publish_all.py --login {p}")

    return results


# ---------------------------------------------------------------------------
# Upload to Platform
# ---------------------------------------------------------------------------
def upload_to_platform(
    platform: str,
    account: str,
    video_path: Path,
    title: str,
    description: str,
    tags: str,
    dry_run: bool = False,
) -> bool:
    """上传视频到指定平台。"""
    cfg = PLATFORMS[platform]
    log.info(f"\n{cfg['emoji']} 发布到 {cfg['name']}...")

    if dry_run:
        log.info(f"   [DRY RUN] 跳过实际上传")
        log.info(f"   title: {title}")
        log.info(f"   desc:  {description[:60]}...")
        log.info(f"   tags:  {tags}")
        return True

    if platform == "weixin":
        # 视频号走独立脚本
        weixin_script = SCRIPT_DIR / "publish_weixin.py"
        cmd = [
            "uv", "run", str(weixin_script),
            "--video", str(video_path),
            "--title", title,
            "--description", description,
            "--auto-close",
        ]
        result = subprocess.run(cmd, cwd=str(PROJECT_ROOT), timeout=600)
        return result.returncode == 0

    if platform == "bilibili":
        # B站需要额外的 tid 参数
        tid = str(cfg.get("bilibili_tid", 249))
        result = run_sau_interactive([
            platform, "upload-video",
            "--account", account,
            "--file", str(video_path.resolve()),
            "--title", title,
            "--desc", description,
            "--tid", tid,
            "--tags", tags,
        ])
        return result.returncode == 0

    # 小红书/抖音/快手 — headed 模式防反爬
    result = run_sau_interactive([
        platform, "upload-video",
        "--account", account,
        "--file", str(video_path.resolve()),
        "--title", title,
        "--desc", description,
        "--tags", tags,
        "--headed",
    ])
    return result.returncode == 0


# ---------------------------------------------------------------------------
# Main: Publish to All Platforms
# ---------------------------------------------------------------------------
def publish_all(
    video_path: Path,
    storyline_path: Path,
    platforms: list[str] | None,
    account: str,
    dry_run: bool = False,
):
    """发布视频到所有指定平台。"""
    # 1. 解析 storyline
    meta = parse_storyline_metadata(storyline_path)
    title = meta.get("title", "")
    description = meta.get("description", "")

    if not title:
        log.error("❌ 无法从 storyline 提取标题")
        return False

    log.info("\n" + "=" * 60)
    log.info("  多平台发布")
    log.info("=" * 60)
    log.info(f"  📹 视频: {video_path.name}")
    log.info(f"  📝 标题: {title}")
    log.info(f"  📄 描述: {description[:60]}...")

    # 2. 确定目标平台
    if platforms:
        target_platforms = [p for p in platforms if p in PLATFORMS]
    else:
        # 默认：发布到所有已登录平台
        target_platforms = [
            p for p in PLATFORMS
            if check_platform(p, account)
        ]

    if not target_platforms:
        log.error("❌ 没有已登录的平台，请先运行 --login")
        return False

    log.info(f"  🎯 目标: {', '.join(target_platforms)}")

    if dry_run:
        log.info(f"  🔍 模式: DRY RUN（不实际发布）")

    # 3. 逐平台发布
    results = {}
    for platform in target_platforms:
        tags = _tags_from_title(title)
        try:
            ok = upload_to_platform(
                platform=platform,
                account=account,
                video_path=video_path,
                title=title,
                description=description,
                tags=tags,
                dry_run=dry_run,
            )
            results[platform] = ok
        except Exception as e:
            log.error(f"   ❌ {platform} 发布异常: {e}")
            results[platform] = False

        # 平台间间隔，避免触发风控
        if not dry_run and platform != target_platforms[-1]:
            log.info(f"   ⏳ 等待 10 秒后发布下一个平台...")
            time.sleep(10)

    # 4. 汇总
    log.info("\n" + "=" * 60)
    log.info("  发布结果")
    log.info("=" * 60)
    for platform, ok in results.items():
        cfg = PLATFORMS[platform]
        status = "✅ 成功" if ok else "❌ 失败"
        log.info(f"  {cfg['emoji']} {cfg['name']:6s}  {status}")

    success_count = sum(1 for ok in results.values() if ok)
    log.info(f"\n  成功 {success_count}/{len(results)}")

    return all(results.values())


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def main():
    parser = argparse.ArgumentParser(
        description="多平台视频一键发布",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 登录小红书
  uv run publish_all.py --login xiaohongshu

  # 检查所有平台登录状态
  uv run publish_all.py --check

  # 发布到所有已登录平台
  uv run publish_all.py \\
    --video data/short-videos/life-bank-choose/output/final.mp4 \\
    --storyline data/short-videos/life-bank-choose/storyline.md

  # 只发小红书和抖音
  uv run publish_all.py \\
    --video data/short-videos/life-bank-choose/output/final.mp4 \\
    --storyline data/short-videos/life-bank-choose/storyline.md \\
    --platforms xiaohongshu,douyin

  # Dry run
  uv run publish_all.py \\
    --video data/short-videos/life-bank-choose/output/final.mp4 \\
    --storyline data/short-videos/life-bank-choose/storyline.md \\
    --dry-run
        """,
    )

    parser.add_argument("--login", metavar="PLATFORM",
                        help="登录指定平台 (xiaohongshu/douyin/bilibili/kuaishou/weixin)")
    parser.add_argument("--check", action="store_true",
                        help="检查所有平台登录状态")
    parser.add_argument("--video", type=Path,
                        help="视频文件路径")
    parser.add_argument("--storyline", type=Path,
                        help="storyline.md 路径")
    parser.add_argument("--platforms",
                        help="目标平台（逗号分隔，如 xiaohongshu,douyin）")
    parser.add_argument("--account", default=DEFAULT_ACCOUNT,
                        help=f"账号名称（默认: {DEFAULT_ACCOUNT}）")
    parser.add_argument("--dry-run", action="store_true",
                        help="模拟运行，不实际发布")

    args = parser.parse_args()

    # Mode: Login
    if args.login:
        success = login_platform(args.login, args.account)
        sys.exit(0 if success else 1)

    # Mode: Check
    if args.check:
        check_all(args.account)
        sys.exit(0)

    # Mode: Publish
    if not args.video or not args.storyline:
        parser.error("发布模式需要 --video 和 --storyline 参数")

    if not args.video.exists():
        log.error(f"❌ 视频不存在: {args.video}")
        sys.exit(1)
    if not args.storyline.exists():
        log.error(f"❌ storyline 不存在: {args.storyline}")
        sys.exit(1)

    platforms = args.platforms.split(",") if args.platforms else None

    success = publish_all(
        video_path=args.video,
        storyline_path=args.storyline,
        platforms=platforms,
        account=args.account,
        dry_run=args.dry_run,
    )
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
