#!/usr/bin/env python3
"""
brand_update.py — 批量更新各平台品牌信息（昵称/头像/Bio）
=========================================================

支持方式:
  - YouTube: 通过 YouTube Data API v3
  - B站: 通过 Bilibili API + cookie
  - TikTok: Playwright 自动化
  - 其他平台: 自动打开编辑页面，辅助手动操作
"""

from __future__ import annotations

import json
import logging
import sys
import webbrowser
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s",
                    datefmt="%H:%M:%S")
log = logging.getLogger(__name__)

# 项目路径
SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parents[3]  # textbook-rag/

# 品牌信息
BRAND = {
    "name_cn": "海外生活指南",
    "name_en": "Overseas Life Guide",
    "bio_cn": "🇨🇦 坐标加拿大\n📌 留学 | 移民 | 租房 | 生活实用干货\n💡 帮你少走弯路，快速适应加国生活",
    "bio_en": "🇨🇦 Canada newcomer guide\n📌 Study · Immigration · Housing · Daily life\n💡 Practical tips to settle in Canada faster",
    "avatar": str(SCRIPT_DIR / "assets" / "avatar.jpg"),
}

# Cookie 目录
COOKIES_DIR = PROJECT_ROOT / ".github" / "social-auto-upload" / "cookies"
CREDENTIALS_DIR = SCRIPT_DIR / "credentials"


# =====================================================================
# YouTube (API)
# =====================================================================
def update_youtube():
    """通过 YouTube Data API 更新频道名称和描述。"""
    log.info("🎬 更新 YouTube 频道信息...")
    
    token_file = CREDENTIALS_DIR / "youtube" / "youtube_token.json"
    if not token_file.exists():
        log.error("   ❌ YouTube token 不存在，请先登录")
        return False

    try:
        from google.oauth2.credentials import Credentials
        from google.auth.transport.requests import Request
        from googleapiclient.discovery import build
    except ImportError:
        log.error("   ❌ 需要: uv pip install google-auth google-api-python-client")
        return False

    token_data = json.loads(token_file.read_text(encoding="utf-8"))
    creds = Credentials(
        token=token_data["token"],
        refresh_token=token_data["refresh_token"],
        token_uri=token_data["token_uri"],
        client_id=token_data["client_id"],
        client_secret=token_data["client_secret"],
        scopes=token_data.get("scopes", []),
    )
    if creds.expired:
        creds.refresh(Request())

    # YouTube Data API 需要额外的 scope 来修改频道信息
    # youtube.upload scope 不够，需要 youtube scope
    # 这里先尝试，如果权限不足会提示
    try:
        yt = build("youtube", "v3", credentials=creds)
        
        # 获取当前频道
        channels = yt.channels().list(part="snippet,brandingSettings", mine=True).execute()
        if not channels.get("items"):
            log.error("   ❌ 找不到 YouTube 频道")
            return False

        channel = channels["items"][0]
        channel_id = channel["id"]
        log.info(f"   频道 ID: {channel_id}")
        log.info(f"   当前名称: {channel.get('snippet', {}).get('title', 'N/A')}")
        
        # 注意: 修改频道名称需要 youtube scope (不只是 youtube.upload)
        # 如果权限不足，我们打开浏览器让用户手动改
        log.info(f"   ⚠️ YouTube API 修改频道名需要完整 youtube scope")
        log.info(f"   🌐 打开 YouTube Studio 手动修改...")
        webbrowser.open("https://studio.youtube.com/channel/editing/details")
        log.info(f"   📝 请修改:")
        log.info(f"      名称: {BRAND['name_en']}")
        log.info(f"      描述: {BRAND['bio_en']}")
        return True
        
    except Exception as e:
        log.error(f"   ❌ YouTube API 错误: {e}")
        webbrowser.open("https://studio.youtube.com/channel/editing/details")
        return False


# =====================================================================
# Bilibili (API)
# =====================================================================
def update_bilibili():
    """通过 B站 API 更新个人信息。"""
    log.info("📺 更新 B站 个人信息...")
    
    cookie_file = COOKIES_DIR / "bilibili_creator.json"
    if not cookie_file.exists():
        log.error("   ❌ B站 cookie 不存在")
        return False

    try:
        import requests
    except ImportError:
        log.error("   ❌ 需要: uv pip install requests")
        return False

    # 读取 cookie
    cookie_data = json.loads(cookie_file.read_text(encoding="utf-8"))
    cookies = {}
    csrf = ""
    for item in cookie_data.get("cookie_info", {}).get("cookies", []):
        cookies[item["name"]] = item["value"]
        if item["name"] == "bili_jct":
            csrf = item["value"]

    if not csrf:
        log.warning("   ⚠️ 找不到 csrf token，打开浏览器手动修改")
        webbrowser.open("https://member.bilibili.com/platform/setting/nickname")
        return False

    # 更新昵称和签名
    url = "https://api.bilibili.com/x/member/web/update"
    data = {
        "uname": BRAND["name_cn"],
        "sign": BRAND["bio_cn"].replace("\n", " | "),
        "csrf": csrf,
    }
    
    try:
        resp = requests.post(url, data=data, cookies=cookies)
        result = resp.json()
        if result.get("code") == 0:
            log.info("   ✅ B站昵称和签名更新成功!")
        else:
            msg = result.get("message", "未知错误")
            log.warning(f"   ⚠️ B站 API: {msg}")
            log.info("   🌐 打开浏览器手动修改...")
            webbrowser.open("https://member.bilibili.com/platform/setting/nickname")
    except Exception as e:
        log.error(f"   ❌ B站 API 错误: {e}")
        webbrowser.open("https://member.bilibili.com/platform/setting/nickname")

    return True


# =====================================================================
# 其他平台 — 打开编辑页面辅助手动操作
# =====================================================================
MANUAL_URLS = {
    "xiaohongshu": {
        "name": "小红书",
        "emoji": "📕",
        "url": "https://creator.xiaohongshu.com/creator/home",
        "brand_name": BRAND["name_cn"],
        "bio": BRAND["bio_cn"],
    },
    "douyin": {
        "name": "抖音",
        "emoji": "🎵",
        "url": "https://creator.douyin.com/creator-micro/home",
        "brand_name": BRAND["name_cn"],
        "bio": BRAND["bio_cn"],
    },
    "kuaishou": {
        "name": "快手",
        "emoji": "⚡",
        "url": "https://cp.kuaishou.com/profile",
        "brand_name": BRAND["name_cn"],
        "bio": BRAND["bio_cn"],
    },
    "weixin": {
        "name": "视频号",
        "emoji": "💬",
        "url": "https://channels.weixin.qq.com/platform",
        "brand_name": BRAND["name_cn"],
        "bio": BRAND["bio_cn"],
    },
    "tiktok": {
        "name": "TikTok",
        "emoji": "🎵",
        "url": "https://www.tiktok.com/setting",
        "brand_name": BRAND["name_en"],
        "bio": BRAND["bio_en"],
    },
    "linkedin": {
        "name": "LinkedIn",
        "emoji": "💼",
        "url": "https://www.linkedin.com/in/me/edit/contact-info/",
        "brand_name": BRAND["name_en"],
        "bio": BRAND["bio_en"],
    },
    "instagram": {
        "name": "Instagram",
        "emoji": "📸",
        "url": "https://www.instagram.com/accounts/edit/",
        "brand_name": BRAND["name_en"],
        "bio": BRAND["bio_en"],
    },
}


def open_manual_platforms():
    """逐个打开需要手动修改的平台。"""
    log.info("\n" + "=" * 60)
    log.info("  以下平台需要手动修改（已打开编辑页面）")
    log.info("=" * 60)

    for key, info in MANUAL_URLS.items():
        log.info(f"\n{info['emoji']} {info['name']}:")
        log.info(f"   昵称: {info['brand_name']}")
        log.info(f"   Bio: {info['bio'].replace(chr(10), ' | ')}")
        log.info(f"   头像: 上传 {BRAND['avatar']}")

    input("\n按回车逐个打开编辑页面...")

    for key, info in MANUAL_URLS.items():
        log.info(f"\n🌐 打开 {info['name']} 编辑页面...")
        webbrowser.open(info["url"])
        input(f"   完成 {info['name']} 后按回车继续...")

    log.info("\n✅ 所有平台品牌更新完成!")


# =====================================================================
# Main
# =====================================================================
def main():
    log.info("=" * 60)
    log.info("  🎨 批量更新品牌信息")
    log.info("=" * 60)
    log.info(f"  中文名: {BRAND['name_cn']}")
    log.info(f"  英文名: {BRAND['name_en']}")
    log.info(f"  头像: {BRAND['avatar']}")
    log.info("")

    # API 自动更新
    update_youtube()
    update_bilibili()

    # 手动更新
    open_manual_platforms()


if __name__ == "__main__":
    main()
