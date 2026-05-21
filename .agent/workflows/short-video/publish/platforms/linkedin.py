"""
linkedin.py — LinkedIn 平台发布模块
====================================

使用 Playwright Chromium + 独立持久化目录。
首次需要用邮箱+密码登录，之后 session 自动保持。

注意: Chrome 不允许用默认 User Data 做远程调试，
      所以必须使用独立的 browser-data 目录。
"""

from __future__ import annotations

import logging
from pathlib import Path

log = logging.getLogger(__name__)

LINKEDIN_LOGIN_URL = "https://www.linkedin.com/login"
LINKEDIN_FEED_URL = "https://www.linkedin.com/feed/"


class LinkedInPlatform:
    """LinkedIn 平台（Playwright Chromium 持久化浏览器）。"""

    key = "linkedin"
    name = "LinkedIn"
    emoji = "💼"

    def __init__(self, project_root: Path, publish_dir: Path,
                 account: str = "creator", **kwargs):
        self.project_root = project_root
        self.publish_dir = publish_dir
        self.account = account
        self.browser_data = publish_dir / "credentials" / "linkedin" / "browser-data"

    def _launch_context(self, pw):
        """启动 Playwright Chromium 持久化浏览器。"""
        self.browser_data.mkdir(parents=True, exist_ok=True)
        return pw.chromium.launch_persistent_context(
            user_data_dir=str(self.browser_data),
            headless=False,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
            ],
            ignore_default_args=["--enable-automation"],
            locale="en-US",
            timezone_id="America/Toronto",
            viewport={"width": 1280, "height": 900},
        )

    # ------------------------------------------------------------------
    # Login
    # ------------------------------------------------------------------
    def login(self) -> bool:
        """打开 LinkedIn 登录页，用户手动登录后 session 自动保持。"""
        try:
            from playwright.sync_api import sync_playwright
        except ImportError:
            log.error("❌ 需要安装 playwright: pip install playwright")
            return False

        log.info("🌐 打开 LinkedIn 登录页面...")
        log.info("   请用邮箱+密码登录（只需一次，session 会自动保持）")
        log.info("   登录成功看到 Feed 后按回车")

        with sync_playwright() as pw:
            context = self._launch_context(pw)
            page = context.pages[0] if context.pages else context.new_page()
            page.goto(LINKEDIN_LOGIN_URL, wait_until="domcontentloaded", timeout=30000)

            log.info("📱 等待登录... 登录完成后按回车键")
            input()

            log.info("✅ LinkedIn 登录完成，session 已保存")
            context.close()
            return True

    # ------------------------------------------------------------------
    # Check
    # ------------------------------------------------------------------
    def check(self) -> bool:
        """检查持久化浏览器数据是否存在。"""
        return self.browser_data.exists() and any(self.browser_data.iterdir())

    # ------------------------------------------------------------------
    # Upload
    # ------------------------------------------------------------------
    def upload(self, video_path: str, title: str, tags: list[str] | None = None,
               description: str = "", **kwargs) -> bool:
        """上传视频到 LinkedIn。"""
        try:
            from playwright.sync_api import sync_playwright
        except ImportError:
            log.error("❌ 需要安装 playwright")
            return False

        tags = tags or []
        log.info(f"💼 上传到 LinkedIn: {title}")

        with sync_playwright() as pw:
            context = self._launch_context(pw)

            try:
                page = context.pages[0] if context.pages else context.new_page()

                # 1. 进入 Feed
                log.info("   📄 正在打开 LinkedIn Feed...")
                page.goto(LINKEDIN_FEED_URL, wait_until="domcontentloaded", timeout=30000)
                page.wait_for_timeout(3000)

                # 检查登录状态
                if "/login" in page.url or "/uas/" in page.url:
                    log.error("❌ LinkedIn 未登录，请先运行 --login linkedin")
                    return False

                log.info("   📄 Feed 页面已加载")

                # 2. 点击 "Start a post" 输入框（它不是 button，是文本框）
                start_post = page.locator('text="Start a post"')
                if start_post.count() == 0:
                    start_post = page.locator('.share-box-feed-entry__top-bar')
                start_post.first.click(timeout=10000)
                page.wait_for_timeout(2000)
                log.info("   ✏️ 打开了 Post 编辑器")

                # 3. 直接找隐藏的 file input 并用 set_input_files 上传
                #    不点媒体按钮（会弹出系统文件选择框，Playwright 无法控制）
                file_input = page.locator('input[type="file"]')
                if file_input.count() == 0:
                    # file input 可能还没渲染，等一下
                    page.wait_for_selector('input[type="file"]', state="attached", timeout=15000)
                    file_input = page.locator('input[type="file"]')

                file_input.first.set_input_files(video_path)
                log.info(f"   📎 视频文件已上传: {Path(video_path).name}")

                # 5. 等待视频 Editor 出现，然后点 "Next"
                log.info("   ⏳ 等待视频 Editor 加载...")
                page.wait_for_timeout(5000)

                # LinkedIn 上传视频后会显示 Editor 页面，底部有 Back/Next 按钮
                for i in range(60):  # 最多等 2 分钟
                    next_btn = page.locator('button:has-text("Next")')
                    if next_btn.count() > 0:
                        try:
                            if next_btn.first.is_visible():
                                log.info("   ✅ 视频 Editor 已加载")
                                break
                        except Exception:
                            pass
                    if i % 10 == 0 and i > 0:
                        log.info(f"   ⏳ 仍在加载... ({i*2}s)")
                    page.wait_for_timeout(2000)

                # 点击 Next
                next_btn = page.locator('button:has-text("Next")')
                next_btn.first.click(timeout=10000)
                page.wait_for_timeout(3000)
                log.info("   ➡️ 点击了 Next")

                # 6. 现在应该回到 Post composer — 输入文字
                editor = page.locator('div[role="textbox"][contenteditable="true"]')
                if editor.count() == 0:
                    page.wait_for_selector('div[role="textbox"]', timeout=10000)
                    editor = page.locator('div[role="textbox"][contenteditable="true"]')
                
                editor.first.click()
                page.wait_for_timeout(500)

                post_text = title
                if description:
                    post_text += f"\n\n{description}"
                if tags:
                    hashtags = " ".join(f"#{tag}" for tag in tags)
                    post_text += f"\n\n{hashtags}"

                page.keyboard.type(post_text, delay=20)
                log.info("   📝 文字内容已输入")
                page.wait_for_timeout(1000)

                # 7. 点击 Post
                log.info("   🚀 点击发布...")
                post_btn = page.locator('button.share-actions__primary-action')
                if post_btn.count() == 0:
                    post_btn = page.locator('button:has-text("Post"):visible')
                post_btn.first.click(timeout=10000)

                # 等待视频上传+发布完成（最多 5 分钟）
                log.info("   ⏳ 等待视频上传完成（最多 5 分钟）...")
                for i in range(150):  # 150 * 2s = 5 min
                    # 检测发布完成：Post 编辑器消失
                    modal = page.locator('.share-box--is-open, .share-creation-state, div[role="dialog"]:has(button:has-text("Post"))')
                    if modal.count() == 0:
                        log.info("   ✅ Post 编辑器已关闭，发布完成")
                        break
                    # 检测成功提示 toast
                    toast = page.locator('text="Post successful"')
                    if toast.count() > 0:
                        log.info("   ✅ 检测到成功提示")
                        break
                    if i % 15 == 0 and i > 0:
                        log.info(f"   ⏳ 仍在上传... ({i*2}s)")
                    page.wait_for_timeout(2000)
                else:
                    log.warning("   ⚠️ 等待超时，视频可能仍在上传中")

                # 额外等待确保上传完成
                page.wait_for_timeout(5000)

                log.info("✅ LinkedIn 发布成功!")
                return True

            except Exception as e:
                log.error(f"❌ LinkedIn 上传失败: {e}")
                try:
                    cred_dir = self.publish_dir / "credentials" / "linkedin"
                    cred_dir.mkdir(parents=True, exist_ok=True)
                    page.screenshot(path=str(cred_dir / "error_screenshot.png"))
                    log.info("   📸 错误截图已保存")
                except Exception:
                    pass
                return False
            finally:
                context.close()
