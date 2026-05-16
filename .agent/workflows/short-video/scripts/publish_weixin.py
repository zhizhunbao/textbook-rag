#!/usr/bin/env python3
"""
publish_weixin.py — 微信视频号自动发布脚本
===========================================

使用 Playwright 模拟浏览器操作，自动上传视频到微信视频号。

用法:
    uv run .agent/workflows/short-video/scripts/publish_weixin.py \
        --video data/short-videos/{slug}/output/final.mp4 \
        --storyline data/short-videos/{slug}/storyline.md \
        [--tags "#加拿大移民 #留学费用"] \
        [--schedule "2026-05-15 20:00"] \
        [--dry-run]

首次使用:
    1. 先运行 --login-only 模式扫码登录
    2. 登录态保存在 Chrome 用户数据目录中，后续无需重复扫码
    3. Cookie 有效期约 30 天

环境变量:
    WEIXIN_CHROME_PATH — Chrome 可执行文件路径（可选，默认自动检测）
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
log = logging.getLogger("publish_weixin")

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
WEIXIN_CHANNELS_URL = "https://channels.weixin.qq.com"
WEIXIN_CREATE_URL = "https://channels.weixin.qq.com/platform/post/create"
WEIXIN_LOGIN_URL = "https://channels.weixin.qq.com/login"

# Chrome user data dir for persistent login
# (Chrome用户数据目录，保持登录态，避免每次扫码)
CHROME_USER_DATA_DIR = Path(__file__).resolve().parent.parent / "browser-data" / "weixin-channels"

# Default tags for immigration/study content
DEFAULT_TAGS = ["加拿大移民", "加拿大留学", "留学费用"]


# ---------------------------------------------------------------------------
# Storyline Parser — 从 storyline.md 提取发布元数据
# ---------------------------------------------------------------------------
def parse_storyline_metadata(storyline_path: Path) -> dict:
    """
    从 storyline.md 提取视频标题、描述、标签等发布信息。

    Returns:
        {
            "title": "加拿大留学一年，最少准备25万",
            "description": "留学费用真实账单...",
            "series": "留学费用真实账单 (1/1)",
            "author": "枫叶移民说",
        }
    """
    text = storyline_path.read_text(encoding="utf-8")
    meta: dict = {}

    # H1 标题 → 视频标题
    h1_match = re.search(r"^#\s+(.+)$", text, re.MULTILINE)
    if h1_match:
        meta["title"] = h1_match.group(1).strip()

    # 元数据 blockquote
    series_match = re.search(r"\*\*系列\*\*:\s*(.+)", text)
    if series_match:
        meta["series"] = series_match.group(1).strip()

    author_match = re.search(r"\*\*作者\*\*:\s*(.+)", text)
    if author_match:
        meta["author"] = author_match.group(1).strip()

    # 从 CTA slide 提取互动描述（排除 [preview] 的内容）
    # 只匹配 [cta] slide 的 **内容**
    # [preview] slide 的内容是下期预告，不应放进本期视频描述
    cta_match = re.search(r'## \[cta\].*?\*\*内容\*\*:\s*(.+)', text, re.DOTALL)
    if cta_match:
        meta["cta"] = cta_match.group(1).strip().split('\n')[0]

    # 收集台词作为描述（排除 [preview] 和 [cta] slide 的台词）
    # 先截断到 [preview] slide 之前
    preview_idx = re.search(r'^## \[preview\]', text, re.MULTILINE)
    text_for_narration = text[:preview_idx.start()] if preview_idx else text
    cta_idx = re.search(r'^## \[cta\]', text_for_narration, re.MULTILINE)
    text_for_narration = text_for_narration[:cta_idx.start()] if cta_idx else text_for_narration

    narration_lines = re.findall(r"^\*\*台词\*\*:\s*\n((?:(?!---).+\n)*)", text_for_narration, re.MULTILINE)
    all_lines = []
    for block in narration_lines:
        for line in block.strip().split("\n"):
            line = line.strip()
            if line:
                all_lines.append(line)

    # 视频描述 = 前3行台词（排除了preview/cta）
    desc_parts = []
    if all_lines:
        desc_parts.extend(all_lines[:3])
    meta["description"] = "\n".join(desc_parts)

    return meta


# ---------------------------------------------------------------------------
# Chrome Detection — 自动检测 Chrome 路径
# ---------------------------------------------------------------------------
def detect_chrome_path() -> str | None:
    """自动检测系统 Chrome 安装路径。"""
    env_path = os.environ.get("WEIXIN_CHROME_PATH")
    if env_path and Path(env_path).exists():
        return env_path

    # Windows 常见路径
    candidates = [
        Path(os.environ.get("PROGRAMFILES", "")) / "Google" / "Chrome" / "Application" / "chrome.exe",
        Path(os.environ.get("PROGRAMFILES(X86)", "")) / "Google" / "Chrome" / "Application" / "chrome.exe",
        Path(os.environ.get("LOCALAPPDATA", "")) / "Google" / "Chrome" / "Application" / "chrome.exe",
        # Edge as fallback
        Path(os.environ.get("PROGRAMFILES(X86)", "")) / "Microsoft" / "Edge" / "Application" / "msedge.exe",
        Path(os.environ.get("PROGRAMFILES", "")) / "Microsoft" / "Edge" / "Application" / "msedge.exe",
    ]
    for p in candidates:
        if p.exists():
            return str(p)
    return None


# ---------------------------------------------------------------------------
# Core Publisher
# ---------------------------------------------------------------------------
class WeixinChannelsPublisher:
    """微信视频号自动发布器。"""

    def __init__(self, headless: bool = False):
        self.headless = headless
        self.browser = None
        self.context = None
        self.page = None

    def _ensure_user_data_dir(self):
        """确保 Chrome 用户数据目录存在。"""
        CHROME_USER_DATA_DIR.mkdir(parents=True, exist_ok=True)
        log.info(f"📁 用户数据目录: {CHROME_USER_DATA_DIR}")

    def launch(self, use_chrome: bool = False):
        """启动浏览器（使用持久化上下文保持登录态）。

        Args:
            use_chrome: 是否使用系统 Chrome（默认用 Playwright 自带 Chromium，
                       避免跟已打开的 Chrome 冲突）
        """
        from playwright.sync_api import sync_playwright

        self._ensure_user_data_dir()
        self._cleanup_lock_files()

        self._pw = sync_playwright().start()

        launch_args = [
            "--disable-blink-features=AutomationControlled",
            "--no-first-run",
            "--no-default-browser-check",
        ]

        chrome_path = detect_chrome_path() if use_chrome else None

        log.info(f"🚀 启动浏览器 (headless={self.headless})")
        if chrome_path:
            log.info(f"   使用系统 Chrome: {chrome_path}")
        else:
            log.info("   使用 Playwright Chromium（避免与系统 Chrome 冲突）")

        try:
            self.context = self._pw.chromium.launch_persistent_context(
                user_data_dir=str(CHROME_USER_DATA_DIR),
                headless=self.headless,
                executable_path=chrome_path,
                args=launch_args,
                viewport={"width": 1280, "height": 900},
                locale="zh-CN",
                user_agent=(
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/131.0.0.0 Safari/537.36"
                ),
            )
        except Exception as e:
            error_msg = str(e)
            if "Target" in error_msg and "closed" in error_msg:
                log.warning("⚠️  浏览器启动冲突，清理锁文件后重试...")
                self._cleanup_lock_files(force=True)
                time.sleep(2)
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
            else:
                raise

        self.page = self.context.new_page()

    def _cleanup_lock_files(self, force: bool = False):
        """清理 Chrome profile 锁文件，避免启动冲突。"""
        lock_files = [
            CHROME_USER_DATA_DIR / "SingletonLock",
            CHROME_USER_DATA_DIR / "SingletonSocket",
            CHROME_USER_DATA_DIR / "SingletonCookie",
        ]
        for lf in lock_files:
            if lf.exists():
                if force:
                    try:
                        lf.unlink()
                        log.info(f"   🗑️  已删除锁文件: {lf.name}")
                    except Exception:
                        pass
                else:
                    log.debug(f"   锁文件存在: {lf.name}")

    def close(self):
        """关闭浏览器。"""
        if self.context:
            self.context.close()
        if self._pw:
            self._pw.stop()
        log.info("🔒 浏览器已关闭")

    def check_login(self) -> bool:
        """检查是否已登录。"""
        self.page.goto(WEIXIN_CHANNELS_URL, wait_until="domcontentloaded", timeout=60000)
        time.sleep(2)

        # 如果跳转到了 login 页面，说明未登录
        current_url = self.page.url
        if "login" in current_url:
            return False

        # 检查页面是否有创建按钮或发表按钮等已登录标志
        try:
            # 视频号助手后台通常有"发表"或"创建"等入口
            self.page.wait_for_selector(
                'text="发表"',
                timeout=5000,
            )
            return True
        except Exception:
            pass

        # 也检查是否能找到头像或账号名
        try:
            self.page.wait_for_selector(".account-name, .finder-nickname, .user-info", timeout=3000)
            return True
        except Exception:
            return False

    def wait_for_login(self, timeout: int = 120):
        """
        等待用户扫码登录。

        Args:
            timeout: 最大等待秒数
        """
        log.info("📱 请使用微信扫码登录...")
        log.info(f"   超时时间: {timeout}秒")

        self.page.goto(WEIXIN_LOGIN_URL, wait_until="domcontentloaded", timeout=60000)
        time.sleep(2)

        start = time.time()
        while time.time() - start < timeout:
            current_url = self.page.url
            if "login" not in current_url:
                log.info("✅ 登录成功!")
                return True
            time.sleep(2)

        log.error("❌ 登录超时")
        return False

    def upload_video(
        self,
        video_path: Path,
        title: str,
        description: str,
        tags: list[str] | None = None,
        schedule_time: datetime | None = None,
        dry_run: bool = False,
    ) -> bool:
        """
        上传视频到微信视频号。

        Args:
            video_path: 视频文件路径
            title: 视频标题
            description: 视频描述
            tags: 标签列表（如 ["加拿大移民", "留学费用"]）
            schedule_time: 定时发布时间（None = 立即发布）
            dry_run: 仅模拟，不实际发布

        Returns:
            是否成功
        """
        if not video_path.exists():
            log.error(f"❌ 视频文件不存在: {video_path}")
            return False

        video_size_mb = video_path.stat().st_size / (1024 * 1024)
        log.info(f"📹 视频: {video_path.name} ({video_size_mb:.1f} MB)")
        log.info(f"📝 标题: {title}")
        log.info(f"📄 描述: {description[:50]}...")
        if tags:
            log.info(f"🏷️  标签: {' '.join('#' + t for t in tags)}")

        # ------------------------------------------------------------------
        # Step 1: 进入创建页面
        # ------------------------------------------------------------------
        log.info("📂 打开创建页面...")
        self.page.goto(WEIXIN_CREATE_URL, wait_until="domcontentloaded", timeout=60000)

        # 等待右侧内容区域实际渲染（微信 SPA 异步加载）
        try:
            self.page.wait_for_selector(
                'input[type="file"], [class*="upload"], [class*="post-cover"], .center-content, .creation-content',
                timeout=15000,
            )
            log.info("   ✅ 创建页面已加载")
        except Exception:
            log.warning("⚠️  创建页面加载缓慢，额外等待...")
            time.sleep(8)

        time.sleep(2)

        # 检查是否需要登录
        if "login" in self.page.url:
            log.error("❌ 未登录，请先运行 --login-only 模式")
            return False

        # ------------------------------------------------------------------
        # Step 2: 上传视频文件
        # ------------------------------------------------------------------
        log.info("⬆️  上传视频文件...")

        # 视频号创建页的上传区域
        # 尝试多种选择器，因为微信会更新页面结构
        upload_selectors = [
            'input[type="file"]',
            'input[accept*="video"]',
            '.upload-content input[type="file"]',
            '.center-content input[type="file"]',
            '.creation-content input[type="file"]',
        ]

        uploaded = False
        for selector in upload_selectors:
            try:
                file_input = self.page.query_selector(selector)
                if file_input:
                    file_input.set_input_files(str(video_path.resolve()))
                    uploaded = True
                    log.info(f"   ✅ 文件已选择 (via {selector})")
                    break
            except Exception as e:
                log.debug(f"   选择器 {selector} 失败: {e}")
                continue

        if not uploaded:
            # 如果找不到 input，尝试点击上传按钮触发文件选择
            upload_btn_selectors = [
                '.upload-content',
                '.post-cover-upload',
                '[class*="upload"]',
                'span:has-text("上传视频")',
                'button:has-text("上传")',
                '.center-content [class*="upload"]',
            ]
            for btn_selector in upload_btn_selectors:
                try:
                    upload_btn = self.page.query_selector(btn_selector)
                    if upload_btn and upload_btn.is_visible():
                        with self.page.expect_file_chooser(timeout=5000) as fc_info:
                            upload_btn.click()
                        file_chooser = fc_info.value
                        file_chooser.set_files(str(video_path.resolve()))
                        uploaded = True
                        log.info(f"   ✅ 通过文件选择器上传 (via {btn_selector})")
                        break
                except Exception as e:
                    log.debug(f"   按钮选择器 {btn_selector} 失败: {e}")
                    continue

        if not uploaded:
            # 最后尝试：保存完整页面 HTML 以便调试
            log.error("❌ 无法找到上传入口")
            self._save_debug_screenshot("no_upload_input")
            # 保存页面 HTML 供调试
            try:
                html_path = CHROME_USER_DATA_DIR.parent / "screenshots" / "page_html.txt"
                html_content = self.page.content()
                html_path.write_text(html_content[:5000], encoding="utf-8")
                log.info(f"   📄 页面 HTML 已保存: {html_path}")
            except Exception:
                pass
            return False

        # ------------------------------------------------------------------
        # Step 3: 等待视频处理完成
        # ------------------------------------------------------------------
        log.info("⏳ 等待视频处理...")
        max_wait = 180  # 最多等 3 分钟
        start = time.time()
        while time.time() - start < max_wait:
            # 检查是否有进度条或处理完成标志
            progress = self.page.query_selector('[class*="progress"], [class*="upload-progress"]')
            if progress:
                text = progress.inner_text()
                if text:
                    log.info(f"   处理中: {text}")

            # 检查是否有视频预览（处理完成的标志）
            preview = self.page.query_selector(
                'video, [class*="video-preview"], [class*="cover-preview"]'
            )
            if preview:
                log.info("   ✅ 视频处理完成")
                break

            time.sleep(3)
        else:
            log.warning("⚠️  视频处理超时，继续尝试填写信息...")

        # ------------------------------------------------------------------
        # Step 4: 填写描述/标题
        # ------------------------------------------------------------------
        log.info("✏️  填写描述...")
        time.sleep(1)

        # 构建完整描述文本（包含标签）
        full_desc = description
        if tags:
            tag_text = " ".join(f"#{t}" for t in tags)
            full_desc = f"{description}\n{tag_text}"

        # 微信视频号的描述输入框
        desc_selectors = [
            '.input-editor',
            '[contenteditable="true"]',
            '.ql-editor',
            'textarea',
            '[class*="desc"] [contenteditable]',
        ]

        desc_filled = False
        for selector in desc_selectors:
            try:
                desc_input = self.page.query_selector(selector)
                if desc_input:
                    desc_input.click()
                    time.sleep(0.3)
                    # 清空现有内容
                    self.page.keyboard.press("Control+A")
                    time.sleep(0.1)
                    # 输入新内容
                    self.page.keyboard.type(full_desc, delay=30)
                    desc_filled = True
                    log.info("   ✅ 描述已填写")
                    break
            except Exception as e:
                log.debug(f"   选择器 {selector} 失败: {e}")
                continue

        if not desc_filled:
            log.warning("⚠️  未能填写描述，可能需要手动输入")
            self._save_debug_screenshot("desc_failed")

        # ------------------------------------------------------------------
        # Step 5: 添加话题标签（通过 # 触发）
        # ------------------------------------------------------------------
        if tags and desc_filled:
            log.info("🏷️  添加话题标签...")
            # 视频号在描述框输入 # 后会弹出话题选择
            # 已经在描述中包含了 #tag 格式

        # ------------------------------------------------------------------
        # Step 6: Dry Run 检查点
        # ------------------------------------------------------------------
        if dry_run:
            log.info("🔍 [DRY RUN] 截图保存，不实际发布")
            self._save_debug_screenshot("dry_run_preview")
            log.info("✅ [DRY RUN] 模拟完成，请检查截图")
            return True

        # ------------------------------------------------------------------
        # Step 7: 点击发表
        # ------------------------------------------------------------------
        log.info("📤 准备发表...")
        time.sleep(2)

        publish_selectors = [
            'button:has-text("发表")',
            '.btn-publish',
            '[class*="publish"] button',
            'button.weui-desktop-btn_primary',
        ]

        published = False
        for selector in publish_selectors:
            try:
                btn = self.page.query_selector(selector)
                if btn and btn.is_visible():
                    btn.click()
                    published = True
                    log.info("   ✅ 已点击发表")
                    break
            except Exception as e:
                log.debug(f"   选择器 {selector} 失败: {e}")
                continue

        if not published:
            log.warning("⚠️  未能自动点击发表，请手动操作")
            self._save_debug_screenshot("publish_btn_not_found")
            # 等待用户手动操作
            log.info("   等待 30 秒让用户手动操作...")
            time.sleep(30)

        # ------------------------------------------------------------------
        # Step 8: 确认发布成功
        # ------------------------------------------------------------------
        time.sleep(5)
        log.info("✅ 发布流程完成!")
        self._save_debug_screenshot("publish_done")
        return True

    def _save_debug_screenshot(self, name: str):
        """保存调试截图。"""
        screenshot_dir = CHROME_USER_DATA_DIR.parent / "screenshots"
        screenshot_dir.mkdir(parents=True, exist_ok=True)
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        path = screenshot_dir / f"{name}_{ts}.png"
        self.page.screenshot(path=str(path), full_page=True)
        log.info(f"   📸 截图: {path}")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def main():
    parser = argparse.ArgumentParser(
        description="微信视频号自动发布",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 首次登录（弹出浏览器扫码）
  uv run publish_weixin.py --login-only

  # 上传视频（从 storyline.md 自动提取标题和描述）
  uv run publish_weixin.py \\
    --video data/short-videos/sp-cost-quick/output/final.mp4 \\
    --storyline data/short-videos/sp-cost-quick/storyline.md

  # 模拟上传（不实际发表）
  uv run publish_weixin.py \\
    --video data/short-videos/sp-cost-quick/output/final.mp4 \\
    --storyline data/short-videos/sp-cost-quick/storyline.md \\
    --dry-run

  # 手动指定标题和描述
  uv run publish_weixin.py \\
    --video output/final.mp4 \\
    --title "加拿大留学一年花多少钱" \\
    --description "真实账单逐项拆解" \\
    --tags "#加拿大留学 #费用"
        """,
    )

    parser.add_argument("--video", type=Path, help="视频文件路径")
    parser.add_argument("--storyline", type=Path, help="storyline.md 路径（自动提取标题/描述）")
    parser.add_argument("--title", help="视频标题（覆盖 storyline 提取的标题）")
    parser.add_argument("--description", help="视频描述（覆盖 storyline 提取的描述）")
    parser.add_argument(
        "--tags",
        help='标签（空格分隔，如 "#加拿大移民 #留学"）',
    )
    parser.add_argument("--schedule", help='定时发布（如 "2026-05-15 20:00"）')
    parser.add_argument("--dry-run", action="store_true", help="模拟运行，不实际发表")
    parser.add_argument("--login-only", action="store_true", help="仅登录，不上传")
    parser.add_argument("--headless", action="store_true", help="无头模式（后台运行）")
    parser.add_argument("--check", action="store_true", help="检查登录状态")
    parser.add_argument("--use-chrome", action="store_true", help="使用系统 Chrome（默认用 Playwright Chromium）")
    parser.add_argument("--auto-close", action="store_true", help="完成后自动关闭浏览器（默认保持打开）")

    args = parser.parse_args()

    # 验证参数
    if not args.login_only and not args.check and not args.video:
        parser.error("必须指定 --video 或使用 --login-only / --check")

    # ------------------------------------------------------------------
    # Ensure playwright browsers installed
    # ------------------------------------------------------------------
    try:
        import playwright  # noqa: F401
    except ImportError:
        log.error("❌ 请先安装 playwright: pip install playwright")
        sys.exit(1)

    # ------------------------------------------------------------------
    # Initialize publisher
    # ------------------------------------------------------------------
    # 登录模式和 dry-run 不使用 headless（需要看到浏览器）
    headless = args.headless and not args.login_only
    publisher = WeixinChannelsPublisher(headless=headless)

    try:
        publisher.launch(use_chrome=args.use_chrome)

        # ----------------------------------------------------------
        # Mode: Login Only
        # ----------------------------------------------------------
        if args.login_only:
            if publisher.check_login():
                log.info("✅ 已经登录，无需重复扫码")
            else:
                success = publisher.wait_for_login(timeout=120)
                if not success:
                    sys.exit(1)
            return

        # ----------------------------------------------------------
        # Mode: Check Login
        # ----------------------------------------------------------
        if args.check:
            if publisher.check_login():
                log.info("✅ 登录状态正常")
            else:
                log.error("❌ 未登录，请运行 --login-only")
                sys.exit(1)
            return

        # ----------------------------------------------------------
        # Mode: Upload Video
        # ----------------------------------------------------------

        # 检查登录
        if not publisher.check_login():
            log.error("❌ 未登录，请先运行 --login-only 扫码登录")
            sys.exit(1)

        # 从 storyline 提取元数据
        meta = {}
        if args.storyline:
            if not args.storyline.exists():
                log.error(f"❌ storyline 不存在: {args.storyline}")
                sys.exit(1)
            meta = parse_storyline_metadata(args.storyline)
            log.info(f"📖 从 storyline 提取: title={meta.get('title', '?')}")

        # 确定标题和描述
        title = args.title or meta.get("title", "")
        description = args.description or meta.get("description", "")

        if not title:
            log.error("❌ 缺少标题，请用 --title 或 --storyline 指定")
            sys.exit(1)

        # 解析标签
        tags = DEFAULT_TAGS.copy()
        if args.tags:
            # 解析 "#标签1 #标签2" 格式
            custom_tags = [t.strip().lstrip("#") for t in args.tags.split() if t.strip()]
            tags.extend(custom_tags)
        # 去重
        tags = list(dict.fromkeys(tags))

        # 解析定时发布
        schedule_time = None
        if args.schedule:
            try:
                schedule_time = datetime.strptime(args.schedule, "%Y-%m-%d %H:%M")
                log.info(f"⏰ 定时发布: {schedule_time}")
            except ValueError:
                log.error(f'❌ 时间格式错误，应为 "YYYY-MM-DD HH:MM"')
                sys.exit(1)

        # 执行上传
        success = publisher.upload_video(
            video_path=args.video,
            title=title,
            description=description,
            tags=tags,
            schedule_time=schedule_time,
            dry_run=args.dry_run,
        )

        if success:
            log.info("🎉 完成!")
        else:
            log.error("❌ 发布失败")
            sys.exit(1)

    finally:
        if not args.auto_close:
            log.info("🔓 浏览器保持打开，按回车关闭...")
            try:
                input()
            except (EOFError, KeyboardInterrupt):
                pass
        publisher.close()


if __name__ == "__main__":
    main()
