"""
tiktok.py — TikTok 平台发布模块
================================

使用 Playwright 直接控制浏览器登录和上传（基于 SAU tk_uploader 逻辑）。
Cookie 存储在 .github/social-auto-upload/cookies/tiktok_{account}.json
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
from pathlib import Path

log = logging.getLogger(__name__)

TIKTOK_LOGIN_URL = "https://www.tiktok.com/login?lang=en"
TIKTOK_UPLOAD_URL = "https://www.tiktok.com/tiktokstudio/upload"


class TikTokPlatform:
    """TikTok 平台（Playwright 浏览器）。"""

    key = "tiktok"
    name = "TikTok"
    emoji = "🎵"

    def __init__(self, project_root: Path, publish_dir: Path,
                 account: str = "creator", **kwargs):
        self.project_root = project_root
        self.publish_dir = publish_dir
        self.account = account
        self.cookies_dir = project_root / ".github" / "social-auto-upload" / "cookies"
        self.cookie_file = self.cookies_dir / f"tiktok_{account}.json"

    # ------------------------------------------------------------------
    # Login
    # ------------------------------------------------------------------
    def login(self) -> bool:
        """打开持久化浏览器让用户登录 TikTok，保存 cookie。"""
        try:
            from playwright.sync_api import sync_playwright
        except ImportError:
            log.error("❌ 需要安装 playwright: pip install playwright")
            return False

        self.cookies_dir.mkdir(parents=True, exist_ok=True)

        # 持久化浏览器数据目录（避免自动化检测）
        browser_data = self.publish_dir / "credentials" / "tiktok" / "browser-data"
        browser_data.mkdir(parents=True, exist_ok=True)

        log.info("🌐 打开 TikTok 登录页面（持久化浏览器）...")
        log.info("   请用 Google 账号登录")
        log.info("   登录成功后按回车保存 cookie")

        with sync_playwright() as pw:
            # 使用 launch_persistent_context 避免被检测为自动化浏览器
            context = pw.chromium.launch_persistent_context(
                user_data_dir=str(browser_data),
                headless=False,
                channel="chrome",   # 使用系统 Chrome，不用 Playwright Chromium
                args=[
                    "--disable-blink-features=AutomationControlled",
                    "--no-sandbox",
                ],
                ignore_default_args=["--enable-automation"],
                locale="en-US",
                timezone_id="America/Toronto",
            )
            page = context.pages[0] if context.pages else context.new_page()
            page.goto(TIKTOK_LOGIN_URL)

            log.info("📱 等待登录... 登录完成后按回车键")
            try:
                input()
            except EOFError:
                import time
                start = time.time()
                while time.time() - start < 300:
                    url = page.url
                    if "tiktok.com" in url and "/login" not in url:
                        break
                    time.sleep(2)

            # 保存 storage state 为 cookie 文件
            context.storage_state(path=str(self.cookie_file))
            log.info(f"✅ Cookie 已保存: {self.cookie_file}")
            log.info(f"📁 浏览器数据: {browser_data}")
            context.close()
            return True

    # ------------------------------------------------------------------
    # Check
    # ------------------------------------------------------------------
    def check(self) -> bool:
        """检查 TikTok cookie 是否存在且有效。"""
        if not self.cookie_file.exists():
            return False

        try:
            data = json.loads(self.cookie_file.read_text(encoding="utf-8"))
            return bool(data)
        except Exception:
            return False

    # ------------------------------------------------------------------
    # Upload
    # ------------------------------------------------------------------
    def upload(self, video_path: str, title: str, tags: list[str] | None = None,
               description: str = "", **kwargs) -> bool:
        """上传视频到 TikTok（基于 SAU tk_uploader 逻辑）。"""
        if not self.cookie_file.exists():
            log.error("❌ 请先登录 TikTok")
            return False

        try:
            from playwright.async_api import async_playwright
        except ImportError:
            log.error("❌ 需要安装 playwright")
            return False

        tags = tags or []
        log.info(f"🎵 上传到 TikTok: {title}")

        async def _upload():
            async with async_playwright() as pw:
                browser = await pw.chromium.launch(
                    headless=False,
                    channel="chrome",
                    args=[
                        "--disable-blink-features=AutomationControlled",
                        "--no-sandbox",
                        "--lang=en-GB",
                    ],
                )
                context = await browser.new_context(
                    storage_state=str(self.cookie_file),
                )
                page = await context.new_page()

                try:
                    # 1. 切换语言到英文
                    await page.goto("https://www.tiktok.com")
                    await page.wait_for_load_state("domcontentloaded")
                    try:
                        await page.wait_for_selector('[data-e2e="nav-more-menu"]', timeout=10000)
                        more_text = await page.locator('[data-e2e="nav-more-menu"]').text_content()
                        if more_text and more_text.strip() != "More":
                            await page.locator('[data-e2e="nav-more-menu"]').click()
                            await page.locator('[data-e2e="language-select"]').click()
                            await page.locator('#creator-tools-selection-menu-header >> text=English (US)').click()
                            await page.wait_for_timeout(2000)
                    except Exception:
                        log.info("   跳过语言切换")

                    # 2. 进入上传页
                    await page.goto("https://www.tiktok.com/tiktokstudio/upload")
                    log.info(f"   📤 上传中: {title}")
                    await page.wait_for_url("https://www.tiktok.com/tiktokstudio/upload", timeout=15000)

                    try:
                        await page.wait_for_selector(
                            'iframe[data-tt="Upload_index_iframe"], div.upload-container',
                            timeout=15000
                        )
                    except Exception:
                        log.error("   上传页面加载超时")

                    # 3. 确定 base locator（iframe 或 body）
                    if await page.locator('iframe[data-tt="Upload_index_iframe"]').count():
                        locator_base = page.frame_locator('[data-tt="Upload_index_iframe"]')
                    else:
                        locator_base = page.locator("body")

                    # 4. 选择视频文件
                    upload_button = locator_base.locator('button:has-text("Select video"):visible')
                    await upload_button.wait_for(state="visible", timeout=15000)

                    async with page.expect_file_chooser() as fc_info:
                        await upload_button.click()
                    file_chooser = await fc_info.value
                    await file_chooser.set_files(video_path)
                    log.info("   📎 视频已选择")

                    # 4.5 关闭所有遮罩层（版权检查弹窗 + 新手引导）
                    await page.wait_for_timeout(3000)

                    # 方法1：尝试点击弹窗内的按钮
                    for _ in range(3):
                        # TUXModal — 尝试点击任何按钮
                        modal_btns = page.locator('[data-floating-ui-portal] button:visible')
                        if await modal_btns.count():
                            await modal_btns.first.click()
                            log.info("   ✅ 点击弹窗按钮")
                            await page.wait_for_timeout(1000)

                        # react-joyride 新手引导 — 点击跳过
                        joyride = page.locator('.react-joyride__overlay, [data-test-id="overlay"]')
                        if await joyride.count():
                            skip_btn = page.locator('button:has-text("Skip"), button:has-text("Close"), button:has-text("Got it")')
                            if await skip_btn.count():
                                await skip_btn.first.click()
                                log.info("   ✅ 关闭新手引导")
                            else:
                                await page.keyboard.press("Escape")
                            await page.wait_for_timeout(1000)

                    # 方法2：用 JS 强制移除所有遮罩层
                    await page.evaluate("""
                        // 移除 TUXModal overlay
                        document.querySelectorAll('[data-floating-ui-portal]').forEach(el => el.remove());
                        // 移除 react-joyride overlay
                        document.querySelectorAll('#react-joyride-portal').forEach(el => el.remove());
                        document.querySelectorAll('.react-joyride__overlay').forEach(el => el.remove());
                    """)
                    log.info("   🧹 已清理所有遮罩层")
                    await page.wait_for_timeout(500)

                    # 5. 填写标题和标签（force=True 绕过残留遮罩）
                    editor = locator_base.locator("div.public-DraftEditor-content")
                    await editor.click(force=True)
                    await page.keyboard.press("End")
                    await page.keyboard.press("Control+A")
                    await page.keyboard.press("Delete")
                    await page.keyboard.press("End")
                    await page.wait_for_timeout(1000)
                    await page.keyboard.insert_text(title)
                    await page.wait_for_timeout(1000)
                    await page.keyboard.press("End")
                    await page.keyboard.press("Enter")

                    for i, tag in enumerate(tags, 1):
                        log.info(f"   🏷️ 设置第 {i} 个标签: #{tag}")
                        await page.keyboard.press("End")
                        await page.wait_for_timeout(1000)
                        await page.keyboard.insert_text(f"#{tag} ")
                        await page.keyboard.press("Space")
                        await page.wait_for_timeout(1000)
                        await page.keyboard.press("Backspace")
                        await page.keyboard.press("End")

                    # 6. 等待上传完成
                    log.info("   ⏳ 等待视频上传...")
                    for _ in range(120):
                        try:
                            post_btn = locator_base.locator('div.button-group > button >> text=Post')
                            if await post_btn.get_attribute("disabled") is None:
                                log.info("   ✅ 视频上传完成")
                                break
                        except Exception:
                            pass
                        # 检查是否有上传错误需要重试
                        retry_btn = locator_base.locator('button[aria-label="Select file"]')
                        if await retry_btn.count():
                            log.info("   🔄 上传出错，重试...")
                            async with page.expect_file_chooser() as fc_info:
                                await retry_btn.click()
                            file_chooser = await fc_info.value
                            await file_chooser.set_files(video_path)
                        await page.wait_for_timeout(2000)

                    # 7. 点击发布
                    log.info("   🚀 点击发布...")
                    while True:
                        try:
                            publish_btn = locator_base.locator('div.button-group button').first
                            if await publish_btn.count():
                                await publish_btn.click()
                            await page.wait_for_url(
                                "https://www.tiktok.com/tiktokstudio/content",
                                timeout=5000
                            )
                            log.info("✅ TikTok 发布成功!")
                            break
                        except Exception:
                            log.info("   ⏳ 发布中...")
                            await page.wait_for_timeout(1000)

                    # 保存 cookie
                    await context.storage_state(path=str(self.cookie_file))
                    return True

                except Exception as e:
                    log.error(f"❌ TikTok 上传失败: {e}")
                    return False
                finally:
                    await context.close()
                    await browser.close()

        return asyncio.run(_upload())
