#!/usr/bin/env python3
"""
login.py — 多平台统一登录脚本
==============================

逐平台扫码/登录，保存 cookie，后续发布免登录。

用法:
    # 登录单个平台
    uv run .agent/workflows/short-video/publish/login.py xiaohongshu

    # 登录所有平台
    uv run .agent/workflows/short-video/publish/login.py --all

    # 检查所有平台登录状态
    uv run .agent/workflows/short-video/publish/login.py --check

    # 指定账号
    uv run .agent/workflows/short-video/publish/login.py douyin --account myname

Cookie 存储位置:
    SAU 平台:  .github/social-auto-upload/cookies/{platform}_{account}.json
    视频号:    publish/credentials/weixin/browser-data/  (Playwright 持久化)
"""

# /// script
# requires-python = ">=3.11"
# dependencies = ["pyyaml>=6.0"]
# ///

from __future__ import annotations

import argparse
import json
import logging
import subprocess
import sys
import time
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
log = logging.getLogger("login")

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
PUBLISH_DIR = Path(__file__).resolve().parent
WORKFLOW_DIR = PUBLISH_DIR.parent
PROJECT_ROOT = WORKFLOW_DIR.parent.parent.parent
SAU_DIR = PROJECT_ROOT / ".github" / "social-auto-upload"
SAU_COOKIES_DIR = SAU_DIR / "cookies"
CONFIG_PATH = PUBLISH_DIR / "config.yaml"

# ---------------------------------------------------------------------------
# Platform Login Config
# ---------------------------------------------------------------------------
PLATFORM_LOGIN = {
    "xiaohongshu": {
        "name": "小红书",
        "emoji": "📕",
        "engine": "sau",
        "login_mode": "headed",      # headed = 弹出浏览器扫码
    },
    "douyin": {
        "name": "抖音",
        "emoji": "🎵",
        "engine": "sau",
        "login_mode": "headed",
    },
    "bilibili": {
        "name": "B站",
        "emoji": "📺",
        "engine": "sau",
        "login_mode": "terminal",    # bilibili 仅支持终端二维码
    },
    "kuaishou": {
        "name": "快手",
        "emoji": "⚡",
        "engine": "sau",
        "login_mode": "headed",
    },
    "weixin": {
        "name": "视频号",
        "emoji": "💬",
        "engine": "playwright",      # 独立 Playwright 脚本
        "login_mode": "browser",
    },
    "tiktok": {
        "name": "TikTok",
        "emoji": "🎵",
        "engine": "playwright",      # Playwright 浏览器登录
        "login_mode": "browser",
    },
    "youtube": {
        "name": "YouTube",
        "emoji": "🎬",
        "engine": "google_oauth",    # Google OAuth 2.0
        "login_mode": "oauth",
    },
}


# ---------------------------------------------------------------------------
# SAU Login
# ---------------------------------------------------------------------------
def sau_login(platform: str, account: str, mode: str) -> bool:
    """通过 SAU CLI 登录平台。"""
    if not SAU_DIR.exists():
        log.error(f"❌ SAU 目录不存在: {SAU_DIR}")
        log.info(f"   请先克隆: git clone https://github.com/... .github/social-auto-upload")
        return False

    SAU_COOKIES_DIR.mkdir(parents=True, exist_ok=True)

    cmd = ["uv", "run", "sau", platform, "login", "--account", account]
    if mode == "headed":
        cmd.append("--headed")

    log.info(f"   $ {' '.join(cmd)}")
    log.info(f"   Cookie 将保存到: {SAU_COOKIES_DIR / f'{platform}_{account}.json'}")

    result = subprocess.run(cmd, cwd=str(SAU_DIR))
    return result.returncode == 0


def sau_check(platform: str, account: str) -> bool:
    """检查 SAU 平台的 cookie 是否有效。"""
    cookie_file = SAU_COOKIES_DIR / f"{platform}_{account}.json"
    if not cookie_file.exists():
        return False

    # 验证 cookie 文件非空且是有效 JSON
    try:
        data = json.loads(cookie_file.read_text(encoding="utf-8"))
        if not data:
            return False
    except (json.JSONDecodeError, Exception):
        return False

    # 调用 SAU check 命令验证
    cmd = ["uv", "run", "sau", platform, "check", "--account", account]
    try:
        result = subprocess.run(
            cmd, cwd=str(SAU_DIR),
            capture_output=True, text=True, timeout=30,
        )
        return result.returncode == 0
    except (subprocess.TimeoutExpired, Exception):
        # check 命令超时，但 cookie 文件存在，先假定有效
        return cookie_file.exists()


# ---------------------------------------------------------------------------
# Weixin Login (Playwright)
# ---------------------------------------------------------------------------
def weixin_login(account: str) -> bool:
    """通过 Playwright 登录视频号。"""
    weixin_script = PUBLISH_DIR / "platforms" / "weixin.py"
    if not weixin_script.exists():
        weixin_script = WORKFLOW_DIR / "scripts" / "publish_weixin.py"

    if not weixin_script.exists():
        log.error(f"❌ 找不到视频号登录脚本")
        return False

    # 使用项目 .venv 的 python（已装好 playwright + 浏览器）
    # 避免 uv run 创建独立环境导致找不到 chromium
    venv_python = PROJECT_ROOT / ".venv" / "Scripts" / "python.exe"
    if venv_python.exists():
        cmd = [str(venv_python), str(weixin_script), "--login-only"]
    else:
        cmd = ["uv", "run", str(weixin_script), "--login-only"]

    log.info(f"   $ {' '.join(cmd)}")

    result = subprocess.run(cmd, cwd=str(PROJECT_ROOT))
    return result.returncode == 0


def weixin_check() -> bool:
    """检查视频号登录状态。"""
    # 检查新路径
    new_dir = PUBLISH_DIR / "credentials" / "weixin" / "browser-data"
    # 检查旧路径
    old_dir = WORKFLOW_DIR / "browser-data" / "weixin-channels"

    for d in [new_dir, old_dir]:
        if d.exists():
            try:
                if any(d.iterdir()):
                    return True
            except Exception:
                pass
    return False


# ---------------------------------------------------------------------------
# TikTok Login (Playwright)
# ---------------------------------------------------------------------------
def _tiktok_login(account: str) -> bool:
    """通过 Playwright 登录 TikTok。"""
    tiktok_script = PUBLISH_DIR / "platforms" / "tiktok.py"

    # 使用项目 .venv 的 python（已装好 playwright）
    venv_python = PROJECT_ROOT / ".venv" / "Scripts" / "python.exe"
    if venv_python.exists():
        cmd = [str(venv_python), "-c",
               f"import sys; sys.path.insert(0, r'{PUBLISH_DIR}'); "
               f"from platforms.tiktok import TikTokPlatform; "
               f"p = TikTokPlatform(project_root=__import__('pathlib').Path(r'{PROJECT_ROOT}'), "
               f"publish_dir=__import__('pathlib').Path(r'{PUBLISH_DIR}'), account='{account}'); "
               f"exit(0 if p.login() else 1)"]
    else:
        cmd = ["uv", "run", "--with", "playwright", str(tiktok_script), "--login"]

    log.info(f"   🌐 启动 TikTok 登录...")
    result = subprocess.run(cmd, cwd=str(PROJECT_ROOT))
    return result.returncode == 0


def _tiktok_check(account: str) -> bool:
    """检查 TikTok cookie 状态。"""
    cookie_file = SAU_COOKIES_DIR / f"tiktok_{account}.json"
    if cookie_file.exists():
        try:
            data = json.loads(cookie_file.read_text(encoding="utf-8"))
            return bool(data)
        except Exception:
            pass
    return False


# ---------------------------------------------------------------------------
# YouTube Login (Google OAuth)
# ---------------------------------------------------------------------------
def _youtube_login(account: str) -> bool:
    """通过 Google OAuth 授权 YouTube。"""
    # 使用项目 .venv 的 python（已装好 google-auth）
    venv_python = PROJECT_ROOT / ".venv" / "Scripts" / "python.exe"
    if venv_python.exists():
        cmd = [str(venv_python), "-c",
               f"import sys; sys.path.insert(0, r'{PUBLISH_DIR}'); "
               f"from platforms.youtube import YouTubePlatform; "
               f"p = YouTubePlatform(project_root=__import__('pathlib').Path(r'{PROJECT_ROOT}'), "
               f"publish_dir=__import__('pathlib').Path(r'{PUBLISH_DIR}'), account='{account}'); "
               f"exit(0 if p.login() else 1)"]
    else:
        log.error("❌ 找不到 .venv，请先运行 uv pip install google-auth-oauthlib google-api-python-client")
        return False

    log.info(f"   🌐 启动 YouTube OAuth 授权...")
    result = subprocess.run(cmd, cwd=str(PROJECT_ROOT))
    return result.returncode == 0


def _youtube_check() -> bool:
    """检查 YouTube token 状态。"""
    token_file = PUBLISH_DIR / "credentials" / "youtube" / "youtube_token.json"
    if token_file.exists():
        try:
            data = json.loads(token_file.read_text(encoding="utf-8"))
            return bool(data.get("refresh_token"))
        except Exception:
            pass
    return False


# ---------------------------------------------------------------------------
# Main Login Flow
# ---------------------------------------------------------------------------
def login_one(platform: str, account: str) -> bool:
    """登录单个平台。"""
    cfg = PLATFORM_LOGIN.get(platform)
    if not cfg:
        log.error(f"❌ 不支持的平台: {platform}")
        log.info(f"   支持的平台: {', '.join(PLATFORM_LOGIN.keys())}")
        return False

    log.info(f"\n{'='*60}")
    log.info(f"  {cfg['emoji']} 登录 {cfg['name']} (account={account})")
    log.info(f"{'='*60}")

    if platform == "weixin":
        return weixin_login(account)
    elif platform == "tiktok":
        return _tiktok_login(account)
    elif platform == "youtube":
        return _youtube_login(account)
    else:
        return sau_login(platform, account, cfg["login_mode"])


def check_one(platform: str, account: str) -> bool:
    """检查单个平台登录状态。"""
    cfg = PLATFORM_LOGIN.get(platform)
    if not cfg:
        return False

    if platform == "weixin":
        return weixin_check()
    elif platform == "tiktok":
        return _tiktok_check(account)
    elif platform == "youtube":
        return _youtube_check()
    else:
        return sau_check(platform, account)


def login_all(account: str):
    """逐个登录所有平台。"""
    log.info("\n" + "=" * 60)
    log.info("  多平台逐个登录")
    log.info("=" * 60)

    results = {}
    for platform, cfg in PLATFORM_LOGIN.items():
        # 先检查是否已登录
        already = check_one(platform, account)
        if already:
            log.info(f"\n  {cfg['emoji']} {cfg['name']}: ✅ 已登录，跳过")
            results[platform] = True
            continue

        log.info(f"\n  {cfg['emoji']} {cfg['name']}: ❌ 未登录，开始登录...")
        ok = login_one(platform, account)
        results[platform] = ok

        if ok:
            log.info(f"  {cfg['emoji']} {cfg['name']}: ✅ 登录成功")
        else:
            log.warning(f"  {cfg['emoji']} {cfg['name']}: ❌ 登录失败")

        # 平台间等 2 秒
        time.sleep(2)

    # 汇总
    _print_summary(results, account)
    return results


def check_all(account: str):
    """检查所有平台登录状态。"""
    log.info("\n" + "=" * 60)
    log.info("  平台登录状态检查")
    log.info("=" * 60)

    results = {}
    for platform, cfg in PLATFORM_LOGIN.items():
        ok = check_one(platform, account)
        results[platform] = ok

    _print_summary(results, account)
    return results


def _print_summary(results: dict, account: str):
    """打印登录状态汇总表。"""
    log.info("\n" + "=" * 60)
    log.info("  登录状态汇总")
    log.info("=" * 60)

    for platform, ok in results.items():
        cfg = PLATFORM_LOGIN[platform]
        status = "✅ 已登录" if ok else "❌ 未登录"

        # Cookie 位置
        if cfg["engine"] == "playwright":
            cookie_loc = "publish/credentials/weixin/browser-data/"
        else:
            cookie_file = SAU_COOKIES_DIR / f"{platform}_{account}.json"
            cookie_loc = str(cookie_file.relative_to(PROJECT_ROOT)) if PROJECT_ROOT in cookie_file.parents else str(cookie_file)

        log.info(f"  {cfg['emoji']} {cfg['name']:6s}  {status}  📁 {cookie_loc}")

    ok_count = sum(1 for v in results.values() if v)
    log.info(f"\n  已登录 {ok_count}/{len(results)} 个平台")

    failed = [p for p, ok in results.items() if not ok]
    if failed:
        log.info(f"\n  未登录平台请运行:")
        for p in failed:
            log.info(f"    uv run .agent/workflows/short-video/publish/login.py {p}")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def main():
    parser = argparse.ArgumentParser(
        description="多平台统一登录 — 扫码后保存 cookie，后续免登录",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
平台列表:
  xiaohongshu  📕 小红书 (浏览器扫码)
  douyin       🎵 抖音   (浏览器扫码)
  bilibili     📺 B站    (终端扫码)
  kuaishou     ⚡ 快手   (浏览器扫码)
  weixin       💬 视频号 (浏览器扫码)

示例:
  # 登录小红书
  uv run publish/login.py xiaohongshu

  # 登录所有平台（已登录的自动跳过）
  uv run publish/login.py --all

  # 检查哪些平台已登录
  uv run publish/login.py --check

  # 指定账号名
  uv run publish/login.py douyin --account work
        """,
    )

    parser.add_argument("platform", nargs="?",
                        help="平台名称 (xiaohongshu/douyin/bilibili/kuaishou/weixin)")
    parser.add_argument("--all", action="store_true",
                        help="逐个登录所有平台（已登录的自动跳过）")
    parser.add_argument("--check", action="store_true",
                        help="检查所有平台登录状态")
    parser.add_argument("--account", default="creator",
                        help="账号名称（默认: creator）")

    args = parser.parse_args()

    if args.check:
        check_all(args.account)
        sys.exit(0)

    if args.all:
        results = login_all(args.account)
        failed = sum(1 for ok in results.values() if not ok)
        sys.exit(1 if failed else 0)

    if args.platform:
        ok = login_one(args.platform, args.account)
        if ok:
            # 验证
            log.info("\n🔍 验证登录状态...")
            verified = check_one(args.platform, args.account)
            if verified:
                log.info("✅ Cookie 已保存，后续发布免登录!")
            else:
                log.warning("⚠️  登录可能成功，但验证未通过，建议重试")
        sys.exit(0 if ok else 1)

    parser.print_help()
    sys.exit(1)


if __name__ == "__main__":
    main()
