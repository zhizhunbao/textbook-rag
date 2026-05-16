#!/usr/bin/env python3
"""
organize_series.py — 微信视频号合集整理脚本
=============================================

使用 Playwright 登录视频号后台，自动创建合集并将已发布视频归档到对应系列。

用法:
    # 查看当前已发布视频列表
    uv run .agent/workflows/short-video/scripts/organize_series.py --list

    # 创建合集并归档（交互模式，需要确认）
    uv run .agent/workflows/short-video/scripts/organize_series.py --organize

    # 仅创建合集，不归档视频
    uv run .agent/workflows/short-video/scripts/organize_series.py --create-series

    # Dry run（截图但不操作）
    uv run .agent/workflows/short-video/scripts/organize_series.py --organize --dry-run

前置条件:
    已通过 publish_weixin.py --login-only 完成登录（共享浏览器数据目录）
"""

# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "playwright>=1.40",
# ]
# ///

from __future__ import annotations

import argparse
import json
import logging
import os
import re
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
log = logging.getLogger("organize_series")

# ---------------------------------------------------------------------------
# Constants — 复用 publish_weixin.py 的浏览器数据目录
# ---------------------------------------------------------------------------
CHROME_USER_DATA_DIR = Path(__file__).resolve().parent.parent / "browser-data" / "weixin-channels"
SCREENSHOT_DIR = CHROME_USER_DATA_DIR.parent / "screenshots"

# 微信视频号后台 URL
POST_LIST_URL = "https://channels.weixin.qq.com/platform/post/list"
COLLECTION_URL = "https://channels.weixin.qq.com/platform/post/collection"

# ---------------------------------------------------------------------------
# 系列定义 — 与 README.md Mini-Series 保持一致
# ---------------------------------------------------------------------------
SERIES_CONFIG = [
    {
        "name": "落地加拿大前7天",
        "description": "新移民/留学生到加拿大后，前7天必须搞定的事情。SIN号、银行开户、信用卡、手机号、医保……一天一件事，关注不迷路。",
        "slugs": [
            "life-sin-quick",      # #5 已发布
            "life-bank-quick",     # #6
            "life-credit-quick",   # #7
            "life-phone-quick",    # #8
            "life-healthcare-deep",# #9
        ],
        # 用于匹配已发布视频标题的关键词
        "title_keywords": ["SIN", "银行", "开户", "信用分", "信用卡", "手机", "套餐", "OHIP", "医保"],
    },
    {
        "name": "学签避坑指南",
        "description": "2026学签新政、PAL认证信、留学费用、打工规则、毕业工签……留学的坑我踩过，一个一个帮你避。",
        "slugs": [
            "sp-pal-quick",        # #3 已发布
            "sp-cost-quick",       # #2 已发布
            "sp-overview-quick",   # #10
            "sp-work-while-study-quick",  # #11
            "sp-pgwp-deep",        # #12
        ],
        "title_keywords": ["学签", "PAL", "留学一年", "花多少", "25万", "留学费用", "打工", "PGWP", "毕业工签"],
    },
    {
        "name": "EE快速通道从0到懂",
        "description": "Express Entry快速通道，用数据帮你拆解。CRS打分、邀请分数线、加分方法、定向抽签……每条只讲一个点。",
        "slugs": [
            "ee-crs-scoring",      # #1 已发布
            "ee-crs-cutoff-quick", # #4 已发布
            "ee-overview-quick",   # #13
            "ee-draws-2026-quick", # #14
            "ee-score-boost-deep", # #15
            "ee-pnp-boost-deep",   # #16
            "ee-category-quick",   # #17
        ],
        "title_keywords": ["EE", "CRS", "评分", "分数线", "507", "快速通道", "Express", "加分", "定向抽签"],
    },
    {
        "name": "省提名哪个省最容易",
        "description": "各省提名政策一个一个拆，安省、BC省、阿省……帮你找到最适合你的省份。",
        "slugs": [
            "pnp-overview-quick",
            "pnp-vs-ee-quick",
            "pnp-on-oinp-deep",
            "pnp-bc-bcpnp-deep",
            "pnp-ab-aaip-deep",
        ],
        "title_keywords": ["省提名", "PNP", "安省", "BC省", "阿省", "OINP", "BCPNP"],
    },
]


# ---------------------------------------------------------------------------
# Browser Helper — 复用 publish_weixin.py 的浏览器管理逻辑
# ---------------------------------------------------------------------------
class BrowserHelper:
    """轻量级浏览器管理器，复用已有登录态。"""

    def __init__(self, headless: bool = False):
        self.headless = headless
        self.context = None
        self.page = None
        self._pw = None

    def launch(self):
        from playwright.sync_api import sync_playwright

        CHROME_USER_DATA_DIR.mkdir(parents=True, exist_ok=True)

        # 清理锁文件
        for lf_name in ["SingletonLock", "SingletonSocket", "SingletonCookie"]:
            lf = CHROME_USER_DATA_DIR / lf_name
            if lf.exists():
                try:
                    lf.unlink()
                except Exception:
                    pass

        self._pw = sync_playwright().start()

        launch_args = [
            "--disable-blink-features=AutomationControlled",
            "--no-first-run",
            "--no-default-browser-check",
        ]

        log.info(f"🚀 启动浏览器 (headless={self.headless})")

        self.context = self._pw.chromium.launch_persistent_context(
            user_data_dir=str(CHROME_USER_DATA_DIR),
            headless=self.headless,
            args=launch_args,
            viewport={"width": 1280, "height": 900},
            locale="zh-CN",
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/131.0.0.0 Safari/537.36"
            ),
        )
        self.page = self.context.new_page()

    def close(self):
        if self.context:
            self.context.close()
        if self._pw:
            self._pw.stop()
        log.info("🔒 浏览器已关闭")

    def screenshot(self, name: str):
        SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        path = SCREENSHOT_DIR / f"{name}_{ts}.png"
        self.page.screenshot(path=str(path), full_page=True)
        log.info(f"📸 截图: {path}")
        return path

    def check_login(self) -> bool:
        """检查是否已登录。"""
        self.page.goto(POST_LIST_URL, wait_until="domcontentloaded", timeout=60000)
        time.sleep(3)

        if "login" in self.page.url:
            return False

        # 检查页面是否加载了内容列表
        try:
            self.page.wait_for_selector(
                '[class*="post-feed"], [class*="post-list"], .post-item, table',
                timeout=8000,
            )
            return True
        except Exception:
            # 再试一次：是否有"发表"按钮（登录态标志）
            try:
                self.page.wait_for_selector('text="发表"', timeout=3000)
                return True
            except Exception:
                return False


# ---------------------------------------------------------------------------
# Core: 获取已发布视频列表
# ---------------------------------------------------------------------------
def fetch_published_videos(browser: BrowserHelper) -> list[dict]:
    """
    从视频号后台获取已发布视频列表。

    DOM 结构 (2026-05 verified):
        .post-feed-item           — 每个视频卡片
          .post-title             — 标题+描述文本
          .post-time span         — 发布时间
          .data-item .count       — 数据指标（播放/点赞/评论/转发/在看）
          .bandage "仅自己可见"    — 私密视频标记

    Returns:
        [{"title": "...", "date": "...", "views": ..., ...}, ...]
    """
    log.info("📋 获取已发布视频列表...")
    browser.page.goto(POST_LIST_URL, wait_until="domcontentloaded", timeout=60000)
    time.sleep(3)

    # 等待微前端内容加载 — 找到包含 .post-feed-item 的 frame
    log.info("  ⏳ 等待内容加载...")
    target = browser.page  # 默认主页面

    # 检查所有 frame（微前端可能在 iframe 里）
    for frame in browser.page.frames:
        try:
            el = frame.query_selector(".post-feed-item")
            if el:
                target = frame
                log.info(f"  🎯 内容在 frame: {frame.url[:60]}")
                break
        except Exception:
            continue

    # 如果主页面和 frame 都没有，等 spinner 消失后重试
    if target == browser.page and not browser.page.query_selector(".post-feed-item"):
        max_wait = 25
        start = time.time()
        while time.time() - start < max_wait:
            time.sleep(2)
            # 再检查所有 frame
            for frame in browser.page.frames:
                try:
                    el = frame.query_selector(".post-feed-item")
                    if el:
                        target = frame
                        log.info(f"  🎯 内容在 frame: {frame.url[:60]}")
                        break
                except Exception:
                    continue
            if target != browser.page:
                break
            # 也检查主页面
            if browser.page.query_selector(".post-feed-item"):
                break
        else:
            log.warning("  ⚠️ 未能找到 .post-feed-item，截图调试...")
            browser.screenshot("post_list_no_items")

    # 截图记录
    browser.screenshot("post_list")

    # 提取视频卡片
    items = target.query_selector_all(".post-feed-item")
    log.info(f"  找到 {len(items)} 个视频卡片")

    videos = []
    for item in items:
        try:
            video = {}

            # 标题（.post-title 包含标题+描述+标签）
            # text_content() 保留原始换行，inner_text() 会把换行变空格
            title_el = item.query_selector(".post-title")
            if title_el:
                full_text = title_el.text_content().strip()
                lines = [l.strip() for l in full_text.split("\n") if l.strip()]
                video["title"] = lines[0] if lines else "(无标题)"
                video["full_desc"] = full_text
            else:
                video["title"] = "(无标题)"
                video["full_desc"] = ""

            # 发布时间
            time_el = item.query_selector(".post-time span")
            if time_el:
                video["date"] = time_el.inner_text().strip()
            else:
                video["date"] = ""

            # 是否私密
            badge = item.query_selector(".bandage")
            video["private"] = bool(badge)

            # 数据指标（5个: 播放/点赞/评论/转发/在看）
            counts = item.query_selector_all(".data-item .count")
            count_values = []
            for c in counts:
                try:
                    count_values.append(int(c.inner_text().strip()))
                except (ValueError, Exception):
                    count_values.append(0)

            if len(count_values) >= 5:
                video["views"] = count_values[0]
                video["likes"] = count_values[1]
                video["comments"] = count_values[2]
                video["shares"] = count_values[3]
                video["thumbs"] = count_values[4]

            videos.append(video)
            status = "🔒" if video["private"] else "✅"
            log.info(f"  {status} {video['title'][:30]} | {video.get('date','')} | 👁{video.get('views',0)}")

        except Exception as e:
            log.debug(f"  提取失败: {e}")
            continue

    log.info(f"  📊 共提取 {len(videos)} 条视频")
    return videos


# ---------------------------------------------------------------------------
# Core: 匹配视频到系列
# ---------------------------------------------------------------------------
def match_videos_to_series(videos: list[dict]) -> dict[str, list[dict]]:
    """
    将视频按标题关键词匹配到系列。

    匹配范围：标题+描述正文，用 regex 去掉 #hashtags 避免交叉匹配。
    每个视频只归属一个系列（首次匹配优先）。
    """
    result = {s["name"]: [] for s in SERIES_CONFIG}
    matched_titles = set()

    for video in videos:
        if video.get("private"):
            continue
        title = video.get("title", "")
        if title in matched_titles or title == "(无标题)":
            continue

        # 提取匹配文本：完整描述去掉 #hashtag 词
        full = video.get("full_desc", "")
        # 去掉 #hashtag（中英文），避免共享标签导致误匹配
        clean = re.sub(r'#\S+', '', full)
        # 只取前 200 字（描述正文，不含尾部垃圾）
        search_text = clean[:200]

        for series in SERIES_CONFIG:
            found = False
            for keyword in series["title_keywords"]:
                if keyword.lower() in search_text.lower():
                    result[series["name"]].append(video)
                    matched_titles.add(title)
                    found = True
                    break
            if found:
                break  # 每个视频只归一个系列

    return result


def print_organize_plan(videos: list[dict], matches: dict[str, list[dict]]):
    """打印视频整理计划。"""
    public = [v for v in videos if not v.get("private")]
    private = [v for v in videos if v.get("private")]

    print("\n" + "=" * 70)
    print("📋 视频号合集整理计划")
    print("=" * 70)

    print(f"\n已发布视频: {len(public)} 条公开 + {len(private)} 条私密")

    if public:
        print("\n--- 公开视频 ---")
        for v in public:
            views = v.get("views", 0)
            shares = v.get("shares", 0)
            print(f"  ✅ {v['title'][:40]:40} | {v.get('date',''):20} | 👁{views:>4} ↗{shares}")

    for series_name, matched_videos in matches.items():
        series_conf = next(s for s in SERIES_CONFIG if s["name"] == series_name)
        print(f"\n📂 系列「{series_name}」")

        if matched_videos:
            for v in matched_videos:
                print(f"   ✅ {v['title'][:50]}")
        else:
            print("   (暂无已发布视频匹配)")

    # 未归类的公开视频
    all_matched_titles = set()
    for mv in matches.values():
        for v in mv:
            all_matched_titles.add(v["title"])

    unmatched = [v for v in public if v["title"] not in all_matched_titles]
    if unmatched:
        print(f"\n❓ 未归类视频 ({len(unmatched)} 条):")
        for v in unmatched:
            print(f"   - {v['title'][:50]}")

    print("\n" + "=" * 70)


# ---------------------------------------------------------------------------
# Core: 在视频号后台创建合集
# ---------------------------------------------------------------------------
def create_collection(browser: BrowserHelper, name: str, description: str, dry_run: bool = False) -> bool:
    """
    在视频号后台创建合集。

    实际 UI (2026-05 verified):
        URL: /platform/post/list?tab=collection
        点击「创建合集」按钮 → 弹出对话框
        对话框：标题输入框（0/20字）+ 取消/创建 按钮
    """
    log.info(f"📂 创建合集: {name}")

    # 导航到合集 tab
    collection_url = "https://channels.weixin.qq.com/platform/post/list?tab=collection"
    browser.page.goto(collection_url, wait_until="domcontentloaded", timeout=60000)
    time.sleep(5)

    # 找到正确的 frame（微前端）
    target = browser.page
    max_retries = 3
    for attempt in range(max_retries):
        for frame in browser.page.frames:
            try:
                el = frame.query_selector('text="创建合集"')
                if el:
                    target = frame
                    break
            except Exception:
                continue
        if target != browser.page:
            break
        log.info(f"  ⏳ 等待页面加载... (第{attempt+1}次)")
        time.sleep(5)

    # 检查合集是否已存在
    try:
        page_text = target.inner_text("body") if target != browser.page else browser.page.inner_text("body")
        if name in page_text:
            log.info(f"  ⏩ 合集「{name}」已存在，跳过")
            return True
    except Exception:
        pass

    browser.screenshot(f"collection_tab_{name[:6]}")

    if dry_run:
        log.info(f"  [DRY RUN] 跳过实际创建: {name}")
        return True

    # Step 1: 点击「创建合集」按钮
    try:
        create_btn = target.query_selector('text="创建合集"')
        if not create_btn:
            create_btn = target.query_selector('button:has-text("创建合集")')
        if not create_btn:
            create_btn = target.query_selector('[class*="create"]')

        if create_btn:
            create_btn.click()
            log.info("  ✅ 点击了「创建合集」按钮")
            time.sleep(3)
        else:
            log.warning("  ⚠️ 未找到「创建合集」按钮")
            browser.screenshot(f"no_create_btn_{name[:6]}")
            return False
    except Exception as e:
        log.warning(f"  ⚠️ 点击创建按钮失败: {e}")
        return False

    # Step 2: 在弹出的对话框中填写标题（20字以内）
    try:
        time.sleep(1)
        # 对话框中的输入框
        dialog_input = browser.page.query_selector(
            'input[placeholder*="合集"], input[placeholder*="粉丝"]'
        )
        if not dialog_input:
            dialog_input = browser.page.query_selector('.weui-desktop-dialog input[type="text"]')
        if not dialog_input:
            dialog_input = browser.page.query_selector('input[type="text"]')

        if dialog_input:
            dialog_input.click()
            time.sleep(0.3)
            browser.page.keyboard.press("Control+a")
            browser.page.keyboard.type(name[:20], delay=50)
            log.info(f"  ✅ 填写标题: {name[:20]}")
            time.sleep(1)
        else:
            log.warning("  ⚠️ 未找到标题输入框")
            browser.screenshot(f"no_input_{name[:6]}")
            return False
    except Exception as e:
        log.warning(f"  ⚠️ 填写标题失败: {e}")
        return False

    # Step 3: 点击「创建」确认按钮
    try:
        confirm_btn = None
        dialog_btns = browser.page.query_selector_all('.weui-desktop-dialog button')
        for btn in dialog_btns:
            btn_text = btn.inner_text().strip()
            if btn_text == "创建":
                confirm_btn = btn
                break

        if not confirm_btn:
            all_btns = browser.page.query_selector_all('button')
            for btn in all_btns:
                try:
                    if btn.inner_text().strip() == "创建":
                        confirm_btn = btn
                        break
                except Exception:
                    continue

        if confirm_btn:
            confirm_btn.click()
            log.info("  ✅ 点击了「创建」确认")
            time.sleep(5)  # 创建后等久一点
            browser.screenshot(f"created_{name[:6]}")
            return True
        else:
            log.warning("  ⚠️ 未找到「创建」确认按钮")
            browser.screenshot(f"no_confirm_{name[:6]}")
            return False
    except Exception as e:
        log.warning(f"  ⚠️ 确认创建失败: {e}")
        return False


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def main():
    parser = argparse.ArgumentParser(
        description="微信视频号合集整理",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 查看已发布视频和整理计划
  uv run organize_series.py --list

  # 创建合集并整理（需确认）
  uv run organize_series.py --organize

  # Dry run
  uv run organize_series.py --organize --dry-run

  # 仅创建合集
  uv run organize_series.py --create-series
        """,
    )

    parser.add_argument("--list", action="store_true", help="列出已发布视频和整理计划")
    parser.add_argument("--organize", action="store_true", help="创建合集并整理视频")
    parser.add_argument("--create-series", action="store_true", help="仅创建合集")
    parser.add_argument("--dry-run", action="store_true", help="模拟运行，不实际操作")
    parser.add_argument("--headless", action="store_true", help="无头模式")
    parser.add_argument("--auto-close", action="store_true", help="完成后自动关闭浏览器")

    args = parser.parse_args()

    if not any([args.list, args.organize, args.create_series]):
        parser.error("请指定 --list、--organize 或 --create-series")

    # 启动浏览器
    browser = BrowserHelper(headless=args.headless)

    try:
        browser.launch()

        # 检查登录
        if not browser.check_login():
            log.error("❌ 未登录，请先运行: uv run publish_weixin.py --login-only")
            sys.exit(1)

        log.info("✅ 登录状态正常")

        # ----------------------------------------------------------
        # Mode: List — 查看视频和整理计划
        # ----------------------------------------------------------
        if args.list or args.organize:
            videos = fetch_published_videos(browser)

            if not videos:
                log.warning("⚠️ 未能自动提取视频列表，请查看截图确认页面结构")
                log.info("💡 截图已保存，可手动查看后台页面结构")
                # 仍然打印系列计划（无匹配数据）
                print_organize_plan([], {s["name"]: [] for s in SERIES_CONFIG})
            else:
                matches = match_videos_to_series(videos)
                print_organize_plan(videos, matches)

        # ----------------------------------------------------------
        # Mode: Create Series — 创建合集
        # ----------------------------------------------------------
        if args.create_series or args.organize:
            log.info("\n📂 开始创建合集...")
            for series in SERIES_CONFIG:
                success = create_collection(
                    browser,
                    name=series["name"],
                    description=series["description"],
                    dry_run=args.dry_run,
                )
                if success:
                    log.info(f"  ✅ 合集「{series['name']}」创建完成")
                else:
                    log.warning(f"  ⚠️ 合集「{series['name']}」创建失败，可能需要手动")
                time.sleep(2)

        # ----------------------------------------------------------
        # Mode: Organize — 整理视频到合集
        # ----------------------------------------------------------
        if args.organize and not args.dry_run:
            log.info("\n📎 视频归档到合集...")
            log.info("⚠️ 微信视频号目前需要在每条视频的编辑页面手动添加到合集")
            log.info("💡 建议操作流程：")
            log.info("   1. 在后台 → 内容管理 → 找到视频")
            log.info("   2. 点击编辑 → 找到「加入合集」选项")
            log.info("   3. 选择对应合集 → 保存")
            log.info("")
            log.info("已为你创建好合集，请手动将视频添加进去。")

        log.info("\n🎉 完成!")

    finally:
        if not args.auto_close:
            log.info("🔓 浏览器保持打开，可手动操作。按回车关闭...")
            try:
                input()
            except (EOFError, KeyboardInterrupt):
                pass
        browser.close()


if __name__ == "__main__":
    main()
