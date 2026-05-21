#!/usr/bin/env python3
"""
publish_all.py — 多平台一键发布脚本 (v2)
==========================================

统一入口：读取 config.yaml 平台配置 + storyline.md 元数据，发布到多个平台。
底层调用 social-auto-upload (SAU) CLI 或 Playwright 完成实际上传。

用法:
    # 首次：逐平台扫码登录
    uv run .agent/workflows/short-video/publish/publish_all.py --login xiaohongshu

    # 检查所有平台登录状态
    uv run .agent/workflows/short-video/publish/publish_all.py --check

    # 发布到所有已登录平台
    uv run .agent/workflows/short-video/publish/publish_all.py \\
        --video data/short-videos/life-bank-choose/output/final.mp4 \\
        --storyline data/short-videos/life-bank-choose/storyline.md

    # 只发布到指定平台
    uv run .agent/workflows/short-video/publish/publish_all.py \\
        --video data/short-videos/life-bank-choose/output/final.mp4 \\
        --storyline data/short-videos/life-bank-choose/storyline.md \\
        --platforms xiaohongshu,douyin

    # Dry run（不实际发布）
    uv run .agent/workflows/short-video/publish/publish_all.py \\
        --video data/short-videos/life-bank-choose/output/final.mp4 \\
        --storyline data/short-videos/life-bank-choose/storyline.md \\
        --dry-run
"""

# /// script
# requires-python = ">=3.11"
# dependencies = ["pyyaml>=6.0", "google-auth-oauthlib>=1.0", "google-api-python-client>=2.0", "playwright>=1.40"]
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

import yaml

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
PUBLISH_DIR = Path(__file__).resolve().parent
WORKFLOW_DIR = PUBLISH_DIR.parent
PROJECT_ROOT = WORKFLOW_DIR.parent.parent.parent  # textbook-rag/

# Ensure platforms/ subpackage is importable
if str(PUBLISH_DIR) not in sys.path:
    sys.path.insert(0, str(PUBLISH_DIR))

CONFIG_PATH = PUBLISH_DIR / "config.yaml"

# ---------------------------------------------------------------------------
# Config Loader
# ---------------------------------------------------------------------------
def load_config() -> dict:
    """加载 config.yaml 并解析路径模板。"""
    if not CONFIG_PATH.exists():
        log.error(f"❌ 找不到配置文件: {CONFIG_PATH}")
        sys.exit(1)

    with open(CONFIG_PATH, encoding="utf-8") as f:
        cfg = yaml.safe_load(f)

    # 解析路径模板
    creds = cfg.get("credentials", {})
    for key, val in creds.items():
        if isinstance(val, str):
            creds[key] = val.format(
                project_root=str(PROJECT_ROOT),
                publish_dir=str(PUBLISH_DIR),
            )

    return cfg


def get_sau_dir() -> Path:
    """SAU 工具目录。"""
    return PROJECT_ROOT / ".github" / "social-auto-upload"


def get_sau_cookies_dir(cfg: dict) -> Path:
    """SAU cookie 目录 (从 config.yaml 读取)。"""
    creds = cfg.get("credentials", {})
    path = creds.get("sau_cookies_dir", "")
    if path:
        return Path(path)
    return get_sau_dir() / "cookies"


def get_weixin_browser_data(cfg: dict) -> Path:
    """视频号浏览器数据目录 (从 config.yaml 读取)。"""
    creds = cfg.get("credentials", {})
    path = creds.get("weixin_browser_data", "")
    if path:
        return Path(path)
    return PUBLISH_DIR / "credentials" / "weixin" / "browser-data"


# ---------------------------------------------------------------------------
# Storyline Parser
# ---------------------------------------------------------------------------
def parse_storyline_metadata(storyline_path: Path) -> dict:
    """从 storyline.md 提取视频标题、描述等发布信息。"""
    text = storyline_path.read_text(encoding="utf-8")
    meta: dict = {}

    # H1 标题
    h1_match = re.search(r"^#\s+(.+)$", text, re.MULTILINE)
    if h1_match:
        meta["title"] = h1_match.group(1).strip()

    # 系列 / 作者 (中英双语)
    series_match = re.search(r"\*\*(?:系列|Series)\*\*:\s*(.+)", text)
    if series_match:
        meta["series"] = series_match.group(1).strip()

    author_match = re.search(r"\*\*(?:作者|Author)\*\*:\s*(.+)", text)
    if author_match:
        meta["author"] = author_match.group(1).strip()

    # 从台词提取描述（排除 preview/cta/disclaimer/citation）
    preview_idx = re.search(r'^## \[(preview|cta|disclaimer|citation)\]', text, re.MULTILINE)
    text_for_narration = text[:preview_idx.start()] if preview_idx else text

    narration_lines = re.findall(
        r"^\*\*(?:台词|Narration)\*\*:\s*\n((?:(?!---).+\n)*)",
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
def run_sau(cfg: dict, args: list[str], timeout: int = 300) -> subprocess.CompletedProcess:
    """在 SAU 目录下运行 sau CLI 命令。"""
    sau_dir = get_sau_dir()
    cmd = ["uv", "run", "sau"] + args
    log.info(f"   $ {' '.join(cmd)}")
    result = subprocess.run(
        cmd,
        cwd=str(sau_dir),
        capture_output=True,
        text=True,
        timeout=timeout,
    )
    if result.stdout.strip():
        log.info(f"   stdout: {result.stdout.strip()}")
    if result.stderr.strip():
        log.warning(f"   stderr: {result.stderr.strip()}")
    return result


def run_sau_interactive(cfg: dict, args: list[str]) -> subprocess.CompletedProcess:
    """在 SAU 目录下运行交互式 sau CLI 命令（登录扫码用）。"""
    sau_dir = get_sau_dir()
    cmd = ["uv", "run", "sau"] + args
    log.info(f"   $ {' '.join(cmd)}")
    result = subprocess.run(
        cmd,
        cwd=str(sau_dir),
        timeout=300,
    )
    return result


# ---------------------------------------------------------------------------
# Login
# ---------------------------------------------------------------------------
def _get_youtube_platform(cfg: dict, account: str):
    """创建 YouTubePlatform 实例。"""
    from platforms.youtube import YouTubePlatform
    return YouTubePlatform(
        project_root=PROJECT_ROOT,
        publish_dir=PUBLISH_DIR,
        account=account,
        category_id=cfg.get("platforms", {}).get("youtube", {}).get("category_id", "22"),
    )


def _get_tiktok_platform(cfg: dict, account: str):
    """创建 TikTokPlatform 实例。"""
    from platforms.tiktok import TikTokPlatform
    return TikTokPlatform(
        project_root=PROJECT_ROOT,
        publish_dir=PUBLISH_DIR,
        account=account,
    )


def _get_linkedin_platform(cfg: dict, account: str):
    """创建 LinkedInPlatform 实例。"""
    from platforms.linkedin import LinkedInPlatform
    return LinkedInPlatform(
        project_root=PROJECT_ROOT,
        publish_dir=PUBLISH_DIR,
        account=account,
    )


def _get_instagram_platform(cfg: dict, account: str):
    """创建 InstagramPlatform 实例。"""
    from platforms.instagram import InstagramPlatform
    return InstagramPlatform(
        project_root=PROJECT_ROOT,
        publish_dir=PUBLISH_DIR,
        account=account,
    )


def login_platform(cfg: dict, platform: str, account: str) -> bool:
    """登录指定平台。"""
    platforms = cfg.get("platforms", {})
    pcfg = platforms.get(platform)
    if not pcfg:
        log.error(f"❌ 不支持的平台: {platform}")
        return False

    log.info(f"\n{'='*60}")
    log.info(f"{pcfg['emoji']} 登录 {pcfg['name']} (account={account})")
    log.info(f"{'='*60}")

    engine = pcfg.get("engine", "sau")

    if engine == "google_oauth":
        # YouTube → Google OAuth 2.0
        yt = _get_youtube_platform(cfg, account)
        return yt.login()

    if platform == "tiktok":
        # TikTok → Playwright 浏览器登录
        tk = _get_tiktok_platform(cfg, account)
        return tk.login()

    if platform == "linkedin":
        # LinkedIn → Playwright 持久化浏览器登录
        li = _get_linkedin_platform(cfg, account)
        return li.login()

    if platform == "instagram":
        # Instagram → Playwright 持久化浏览器登录
        ig = _get_instagram_platform(cfg, account)
        return ig.login()

    if platform == "weixin":
        # 视频号走独立脚本
        weixin_script = PUBLISH_DIR / "platforms" / "weixin.py"
        if not weixin_script.exists():
            # 回退到旧路径
            weixin_script = WORKFLOW_DIR / "scripts" / "publish_weixin.py"
        cmd = ["uv", "run", str(weixin_script), "--login-only"]
        log.info(f"   $ {' '.join(cmd)}")
        result = subprocess.run(cmd, cwd=str(PROJECT_ROOT))
        return result.returncode == 0

    if platform == "bilibili":
        result = run_sau_interactive(cfg, [platform, "login", "--account", account])
        return result.returncode == 0

    # 小红书/抖音/快手 → headed 模式扫码
    result = run_sau_interactive(cfg, [platform, "login", "--account", account, "--headed"])
    return result.returncode == 0


# ---------------------------------------------------------------------------
# Check Login Status
# ---------------------------------------------------------------------------
def check_platform(cfg: dict, platform: str, account: str) -> bool:
    """检查平台登录状态。"""
    platforms = cfg.get("platforms", {})
    pcfg = platforms.get(platform)
    if not pcfg:
        return False

    engine = pcfg.get("engine", "sau")

    if engine == "google_oauth":
        # YouTube → 检查 token 文件
        try:
            yt = _get_youtube_platform(cfg, account)
            return yt.check()
        except Exception:
            return False

    if platform == "tiktok":
        # TikTok → 检查 cookie 文件
        try:
            tk = _get_tiktok_platform(cfg, account)
            return tk.check()
        except Exception:
            return False

    if platform == "linkedin":
        # LinkedIn → 检查 cookie/browser-data
        try:
            li = _get_linkedin_platform(cfg, account)
            return li.check()
        except Exception:
            return False

    if platform == "instagram":
        # Instagram → 检查 cookie 文件
        try:
            ig = _get_instagram_platform(cfg, account)
            return ig.check()
        except Exception:
            return False

    if platform == "weixin":
        weixin_data = Path(get_weixin_browser_data(cfg))
        # 也检查旧路径
        if not weixin_data.exists():
            weixin_data = WORKFLOW_DIR / "browser-data" / "weixin-channels"
        exists = weixin_data.exists() and any(weixin_data.iterdir())
        return exists

    if engine != "sau":
        return False

    # 先检查 cookie 文件是否存在
    cookies_dir = get_sau_cookies_dir(cfg)
    cookie_file = Path(cookies_dir) / f"{platform}_{account}.json"
    if not cookie_file.exists():
        return False

    result = run_sau(cfg, [platform, "check", "--account", account], timeout=30)
    return result.returncode == 0


def check_all(cfg: dict, account: str):
    """检查所有平台登录状态。"""
    platforms = cfg.get("platforms", {})

    log.info("\n" + "=" * 60)
    log.info("  平台登录状态检查")
    log.info("=" * 60)

    results = {}
    for platform, pcfg in platforms.items():
        if not pcfg.get("enabled", True):
            status = "⏭️  已禁用"
            ok = False
        else:
            ok = check_platform(cfg, platform, account)
            status = "✅ 已登录" if ok else "❌ 未登录"
        log.info(f"  {pcfg['emoji']} {pcfg['name']:6s}  {status}")
        results[platform] = ok

    logged_in = [p for p, ok in results.items() if ok]
    log.info(f"\n  已登录 {len(logged_in)}/{len(platforms)} 个平台")
    if logged_in:
        log.info(f"  可发布: {', '.join(logged_in)}")

    not_logged = [p for p, ok in results.items()
                  if not ok and platforms[p].get("enabled", True)]
    if not_logged:
        log.info(f"\n  未登录平台请运行:")
        for p in not_logged:
            log.info(f"    uv run .agent/workflows/short-video/publish/publish_all.py --login {p}")

    return results


# ---------------------------------------------------------------------------
# Upload to Platform
# ---------------------------------------------------------------------------
def upload_to_platform(
    cfg: dict,
    platform: str,
    account: str,
    video_path: Path,
    title: str,
    description: str,
    tags: str,
    dry_run: bool = False,
) -> bool:
    """上传视频到指定平台。"""
    platforms = cfg.get("platforms", {})
    pcfg = platforms[platform]
    engine = pcfg.get("engine", "sau")
    log.info(f"\n{pcfg['emoji']} 发布到 {pcfg['name']}...")

    if dry_run:
        log.info(f"   [DRY RUN] 跳过实际上传")
        log.info(f"   title: {title}")
        log.info(f"   desc:  {description[:60]}...")
        log.info(f"   tags:  {tags}")
        return True

    # --- YouTube (Google OAuth API) ---
    if engine == "google_oauth":
        yt = _get_youtube_platform(cfg, account)
        tag_list = [t.strip() for t in tags.split(",") if t.strip()] if tags else []
        return yt.upload(
            video_path=str(video_path.resolve()),
            title=title,
            tags=tag_list,
            description=description,
        )

    # --- TikTok (Playwright) ---
    if platform == "tiktok":
        tk = _get_tiktok_platform(cfg, account)
        tag_list = [t.strip() for t in tags.split(",") if t.strip()] if tags else []
        return tk.upload(
            video_path=str(video_path.resolve()),
            title=title,
            tags=tag_list,
            description=description,
        )

    # --- LinkedIn (Playwright) ---
    if platform == "linkedin":
        li = _get_linkedin_platform(cfg, account)
        tag_list = [t.strip() for t in tags.split(",") if t.strip()] if tags else []
        return li.upload(
            video_path=str(video_path.resolve()),
            title=title,
            tags=tag_list,
            description=description,
        )

    # --- Instagram Reels (Playwright) ---
    if platform == "instagram":
        ig = _get_instagram_platform(cfg, account)
        tag_list = [t.strip() for t in tags.split(",") if t.strip()] if tags else []
        return ig.upload(
            video_path=str(video_path.resolve()),
            title=title,
            tags=tag_list,
            description=description,
        )

    # --- 视频号 (Playwright) ---
    if platform == "weixin":
        weixin_script = PUBLISH_DIR / "platforms" / "weixin.py"
        if not weixin_script.exists():
            weixin_script = WORKFLOW_DIR / "scripts" / "publish_weixin.py"
        cmd = [
            "uv", "run", str(weixin_script),
            "--video", str(video_path),
            "--title", title,
            "--description", description,
            "--auto-close",
        ]
        result = subprocess.run(cmd, cwd=str(PROJECT_ROOT), timeout=600)
        return result.returncode == 0

    # --- B站 (SAU + tid) ---
    if platform == "bilibili":
        tid = str(pcfg.get("bilibili_tid", 249))
        result = run_sau_interactive(cfg, [
            platform, "upload-video",
            "--account", account,
            "--file", str(video_path.resolve()),
            "--title", title,
            "--desc", description,
            "--tid", tid,
            "--tags", tags,
        ])
        return result.returncode == 0

    # --- 小红书/抖音/快手 (SAU) — headed 模式防反爬 ---
    result = run_sau_interactive(cfg, [
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
    cfg: dict,
    video_path: Path,
    storyline_path: Path,
    platforms_filter: list[str] | None,
    account: str,
    dry_run: bool = False,
):
    """发布视频到所有指定平台。"""
    platforms = cfg.get("platforms", {})

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
    if platforms_filter:
        target_platforms = [p for p in platforms_filter if p in platforms]
    else:
        # 默认：发布到所有已启用且已登录的平台
        target_platforms = [
            p for p, pcfg in platforms.items()
            if pcfg.get("enabled", True) and check_platform(cfg, p, account)
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
        pcfg = platforms[platform]
        tags = pcfg.get("default_tags", "")
        try:
            ok = upload_to_platform(
                cfg=cfg,
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
        pcfg = platforms[platform]
        status = "✅ 成功" if ok else "❌ 失败"
        log.info(f"  {pcfg['emoji']} {pcfg['name']:6s}  {status}")

    success_count = sum(1 for ok in results.values() if ok)
    log.info(f"\n  成功 {success_count}/{len(results)}")

    return all(results.values())


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def main():
    parser = argparse.ArgumentParser(
        description="多平台视频一键发布 (v2 — config.yaml 驱动)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 登录小红书
  uv run publish/publish_all.py --login xiaohongshu

  # 检查所有平台登录状态
  uv run publish/publish_all.py --check

  # 发布到所有已登录平台
  uv run publish/publish_all.py \\
    --video data/short-videos/life-bank-choose/output/final.mp4 \\
    --storyline data/short-videos/life-bank-choose/storyline.md

  # 只发小红书和抖音
  uv run publish/publish_all.py \\
    --video data/short-videos/life-bank-choose/output/final.mp4 \\
    --storyline data/short-videos/life-bank-choose/storyline.md \\
    --platforms xiaohongshu,douyin

  # Dry run
  uv run publish/publish_all.py \\
    --video data/short-videos/life-bank-choose/output/final.mp4 \\
    --storyline data/short-videos/life-bank-choose/storyline.md \\
    --dry-run
        """,
    )

    parser.add_argument("--login", metavar="PLATFORM",
                        help="登录指定平台 (xiaohongshu/douyin/bilibili/kuaishou/weixin/youtube/tiktok/linkedin/instagram)")
    parser.add_argument("--check", action="store_true",
                        help="检查所有平台登录状态")
    parser.add_argument("--video", type=Path,
                        help="视频文件路径")
    parser.add_argument("--storyline", type=Path,
                        help="storyline.md 路径")
    parser.add_argument("--platforms",
                        help="目标平台（逗号分隔，如 xiaohongshu,douyin）")
    parser.add_argument("--account",
                        help="账号名称（默认读 config.yaml）")
    parser.add_argument("--dry-run", action="store_true",
                        help="模拟运行，不实际发布")

    args = parser.parse_args()

    # 加载配置
    cfg = load_config()
    account = args.account or cfg.get("default_account", "creator")

    # Mode: Login
    if args.login:
        success = login_platform(cfg, args.login, account)
        sys.exit(0 if success else 1)

    # Mode: Check
    if args.check:
        check_all(cfg, account)
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

    platforms_filter = args.platforms.split(",") if args.platforms else None

    success = publish_all(
        cfg=cfg,
        video_path=args.video,
        storyline_path=args.storyline,
        platforms_filter=platforms_filter,
        account=account,
        dry_run=args.dry_run,
    )
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
