"""
instagram.py — Instagram Reels 平台发布模块
=============================================

使用 Playwright 直接控制浏览器登录和上传 Reels。
Cookie 存储在 .github/social-auto-upload/cookies/instagram_{account}.json
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
from pathlib import Path

log = logging.getLogger(__name__)

INSTAGRAM_LOGIN_URL = "https://www.instagram.com/accounts/login/"
INSTAGRAM_HOME_URL = "https://www.instagram.com/"


class InstagramPlatform:
    """Instagram Reels 平台（Playwright 浏览器）。"""

    key = "instagram"
    name = "Instagram"
    emoji = "📸"

    def __init__(self, project_root: Path, publish_dir: Path,
                 account: str = "creator", **kwargs):
        self.project_root = project_root
        self.publish_dir = publish_dir
        self.account = account
        self.cookies_dir = project_root / ".github" / "social-auto-upload" / "cookies"
        self.cookie_file = self.cookies_dir / f"instagram_{account}.json"

    # ------------------------------------------------------------------
    # Login
    # ------------------------------------------------------------------
    def login(self) -> bool:
        """打开持久化浏览器让用户登录 Instagram，保存 cookie。"""
        try:
            from playwright.sync_api import sync_playwright
        except ImportError:
            log.error("❌ 需要安装 playwright: pip install playwright")
            return False

        self.cookies_dir.mkdir(parents=True, exist_ok=True)

        # 持久化浏览器数据目录（避免自动化检测）
        browser_data = self.publish_dir / "credentials" / "instagram" / "browser-data"
        browser_data.mkdir(parents=True, exist_ok=True)

        log.info("🌐 打开 Instagram 登录页面（持久化浏览器）...")
        log.info("   请用账号密码登录（或已保存的 session）")
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
            page.goto(INSTAGRAM_LOGIN_URL)

            log.info("📱 等待登录... 登录完成后按回车键")
            try:
                input()
            except EOFError:
                import time
                start = time.time()
                while time.time() - start < 300:
                    url = page.url
                    if "instagram.com" in url and "/login" not in url:
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
        """检查 Instagram cookie 是否存在且有效。"""
        if not self.cookie_file.exists():
            return False

        try:
            data = json.loads(self.cookie_file.read_text(encoding="utf-8"))
            return bool(data)
        except Exception:
            return False

    # ------------------------------------------------------------------
    # Upload (Reels)
    # ------------------------------------------------------------------
    def upload(self, video_path: str, title: str, tags: list[str] | None = None,
               description: str = "", **kwargs) -> bool:
        """上传视频到 Instagram Reels。"""
        if not self.cookie_file.exists():
            log.error("❌ 请先登录 Instagram")
            return False

        try:
            from playwright.async_api import async_playwright
        except ImportError:
            log.error("❌ 需要安装 playwright")
            return False

        tags = tags or []
        log.info(f"📸 上传到 Instagram Reels: {title}")

        async def _upload():
            async with async_playwright() as pw:
                # 使用持久化 context 保持登录态
                browser_data = self.publish_dir / "credentials" / "instagram" / "browser-data"
                browser_data.mkdir(parents=True, exist_ok=True)

                context = await pw.chromium.launch_persistent_context(
                    user_data_dir=str(browser_data),
                    headless=False,
                    channel="chrome",
                    args=[
                        "--disable-blink-features=AutomationControlled",
                        "--no-sandbox",
                    ],
                    ignore_default_args=["--enable-automation"],
                    locale="en-US",
                    timezone_id="America/Toronto",
                )
                page = context.pages[0] if context.pages else await context.new_page()

                try:
                    # 1. 进入 Instagram 首页
                    await page.goto(INSTAGRAM_HOME_URL)
                    await page.wait_for_load_state("domcontentloaded")
                    await page.wait_for_timeout(5000)

                    # 关闭可能的弹窗（通知、cookie consent 等）
                    for dismiss_text in ["Not Now", "Not now", "Decline optional cookies", "Allow essential and optional cookies"]:
                        try:
                            btn = page.locator(f'button:has-text("{dismiss_text}")').first
                            if await btn.is_visible():
                                await btn.click()
                                await page.wait_for_timeout(1000)
                        except Exception:
                            pass

                    # 2. 点击侧边栏 "Create" 按钮（"+" 图标）
                    log.info("   📤 打开创建界面...")
                    create_clicked = False

                    # 从截图看侧边栏是纯图标，Create 是 "+" 号
                    create_selectors = [
                        'svg[aria-label="New post"]',                    # SVG 图标 aria-label
                        'a:has(svg[aria-label="New post"])',             # 包裹 SVG 的链接
                        'div[role="button"]:has(svg[aria-label="New post"])',
                        'span:text("Create")',                           # 宽屏时有文字
                        'a:has(span:text("Create"))',                    # 宽屏侧边栏
                        'div[role="button"]:has(span:text("Create"))',
                        '[aria-label="New post"]',                       # 任意元素
                        '[aria-label="Create"]',                         # 备选 aria-label
                    ]
                    for sel in create_selectors:
                        try:
                            btn = page.locator(sel).first
                            if await btn.is_visible():
                                await btn.click()
                                create_clicked = True
                                log.info(f"   ✅ Create 按钮已点击 (selector: {sel})")
                                break
                        except Exception:
                            continue

                    if not create_clicked:
                        log.error("   ❌ 找不到 Create 按钮")
                        debug_path = self.publish_dir / "credentials" / "instagram" / "debug_create.png"
                        await page.screenshot(path=str(debug_path))
                        log.error(f"   📷 截图已保存: {debug_path}")
                        return False

                    await page.wait_for_timeout(1500)

                    # 2.5 Create 点击后弹出下拉菜单（Post / AI），点击 "Post"
                    log.info("   📤 选择 Post...")
                    post_clicked = False
                    post_selectors = [
                        'span:text("Post")',
                        'div[role="button"]:has-text("Post")',
                        'a:has-text("Post")',
                        'button:has-text("Post")',
                    ]
                    for sel in post_selectors:
                        try:
                            btn = page.locator(sel).first
                            if await btn.is_visible():
                                await btn.click()
                                post_clicked = True
                                log.info(f"   ✅ Post 已点击 (selector: {sel})")
                                break
                        except Exception:
                            continue

                    if not post_clicked:
                        log.warning("   ⚠️ 未找到 Post 菜单项，可能直接进入了创建界面")

                    await page.wait_for_timeout(2000)
                    log.info("   📎 选择视频文件...")

                    # 等待创建 modal 出现
                    try:
                        await page.wait_for_selector(
                            'div[role="dialog"], div[class*="Modal"], div[class*="modal"]',
                            timeout=10000,
                        )
                        log.info("   ✅ 创建对话框已打开")
                    except Exception:
                        log.warning("   ⚠️ 未检测到 dialog，继续尝试...")

                    # 尝试多种 "Select from computer" 按钮选择器
                    select_selectors = [
                        'button:text("Select from computer")',
                        'button:text("Select From Computer")',
                        'button:has-text("Select from")',
                        'button:has-text("Select From")',
                        'div[role="dialog"] button:not([aria-label])',  # dialog 内无 aria-label 的按钮
                        'button._acan',                                 # Instagram 内部类名
                        'button[class*="select"]',
                    ]

                    file_selected = False
                    for sel in select_selectors:
                        try:
                            btn = page.locator(sel).first
                            if await btn.is_visible():
                                log.info(f"   🔍 找到文件选择按钮 (selector: {sel})")
                                async with page.expect_file_chooser(timeout=5000) as fc_info:
                                    await btn.click()
                                file_chooser = await fc_info.value
                                await file_chooser.set_files(video_path)
                                file_selected = True
                                log.info("   ✅ 视频已选择")
                                break
                        except Exception:
                            continue

                    # 备选：直接通过 input[type=file] 设置文件（绕过按钮点击）
                    if not file_selected:
                        log.info("   🔄 尝试直接设置 input[type=file]...")
                        try:
                            file_input = page.locator('input[type="file"]').first
                            await file_input.set_input_files(video_path)
                            file_selected = True
                            log.info("   ✅ 视频已通过 input[type=file] 选择")
                        except Exception as e:
                            log.error(f"   ❌ input[type=file] 也失败: {e}")

                    if not file_selected:
                        debug_path = self.publish_dir / "credentials" / "instagram" / "debug_select.png"
                        await page.screenshot(path=str(debug_path))
                        log.error(f"   ❌ 选择视频失败，截图: {debug_path}")
                        return False

                    await page.wait_for_timeout(5000)

                    # 3.5 关闭 "Video posts are now shared as reels" 提示弹窗
                    log.info("   🔄 检查 Reels 提示弹窗...")
                    for ok_text in ["OK", "Ok", "Got it", "Got It"]:
                        try:
                            ok_btn = page.locator(f'button:has-text("{ok_text}")').first
                            if await ok_btn.is_visible():
                                await ok_btn.click()
                                log.info(f"   ✅ Reels 提示已关闭 (clicked: {ok_text})")
                                await page.wait_for_timeout(1500)
                                break
                        except Exception:
                            continue

                    # 4. 裁剪/调整页面 → 点 Next（可能需要多次）
                    # HTML: <div role="button" tabindex="0">Next</div>
                    log.info("   ⏭️ 跳过裁剪和滤镜...")
                    for step in range(4):
                        try:
                            next_btn = page.get_by_role("button", name="Next")
                            if await next_btn.count() > 0 and await next_btn.first.is_visible():
                                await next_btn.first.click()
                                log.info(f"   ⏭️ Next (step {step + 1})")
                                await page.wait_for_timeout(3000)
                            else:
                                log.info(f"   ℹ️ Next 不可见，可能已经到最后一步")
                                break
                        except Exception as e:
                            log.info(f"   ℹ️ Next 点击异常: {e}")
                            break

                    # 截图看当前状态
                    debug_path = self.publish_dir / "credentials" / "instagram" / "debug_after_next.png"
                    await page.screenshot(path=str(debug_path))
                    log.info(f"   📷 Next 之后截图: {debug_path}")

                    # 5. 填写描述 + 标签
                    log.info("   ✏️ 填写描述和标签...")
                    caption_written = False

                    # 构建完整文案
                    caption_text = title
                    if description:
                        caption_text += f"\n\n{description}"
                    if tags:
                        hashtags = " ".join(f"#{tag}" for tag in tags)
                        caption_text += f"\n\n{hashtags}"

                    # 策略 1: 通过 aria-label 找
                    caption_selectors = [
                        'div[aria-label="Write a caption..."]',
                        'textarea[aria-label="Write a caption..."]',
                        'div[aria-label="Caption"]',
                        'textarea[aria-label="Caption"]',
                        'div[contenteditable="true"]',
                        'textarea',
                    ]
                    for sel in caption_selectors:
                        try:
                            el = page.locator(sel).first
                            if await el.is_visible():
                                await el.click()
                                await page.keyboard.press("Control+A")
                                await page.keyboard.press("Delete")
                                await page.wait_for_timeout(300)
                                await page.keyboard.type(caption_text, delay=10)
                                caption_written = True
                                log.info(f"   ✅ 描述已填写 (selector: {sel})")
                                break
                        except Exception:
                            continue

                    if not caption_written:
                        log.warning("   ⚠️ 未能填写描述，继续发布...")

                    await page.wait_for_timeout(1000)

                    # 6. 点击 Share
                    # HTML 结构类似 Next: <div role="button">Share</div>
                    log.info("   🚀 点击发布...")
                    shared = False
                    try:
                        share_btn = page.get_by_role("button", name="Share")
                        if await share_btn.count() > 0 and await share_btn.first.is_visible():
                            await share_btn.first.click()
                            shared = True
                            log.info("   ✅ Share 已点击")
                    except Exception as e:
                        log.info(f"   ⚠️ get_by_role Share 失败: {e}")

                    # 备选选择器
                    if not shared:
                        for sel in ['div[role="button"]:text("Share")', 'button:has-text("Share")']:
                            try:
                                btn = page.locator(sel).first
                                if await btn.is_visible():
                                    await btn.click()
                                    shared = True
                                    log.info(f"   ✅ Share 已点击 (selector: {sel})")
                                    break
                            except Exception:
                                continue

                    if not shared:
                        debug_path = self.publish_dir / "credentials" / "instagram" / "debug_share.png"
                        await page.screenshot(path=str(debug_path))
                        log.error(f"   ❌ 找不到 Share 按钮，截图: {debug_path}")
                        return False

                    # 7. 等待发布完成
                    log.info("   ⏳ 等待发布完成（最长 5 分钟）...")

                    # 点击 Share 后立即截图确认
                    await page.wait_for_timeout(3000)
                    debug_path = self.publish_dir / "credentials" / "instagram" / "debug_after_share.png"
                    await page.screenshot(path=str(debug_path))
                    log.info(f"   📷 Share 之后截图: {debug_path}")

                    try:
                        # 等待确认文本或 URL 变化（5 分钟超时）
                        await page.wait_for_selector(
                            'text=/shared|Reel shared|Post shared|Your .* has been shared/i',
                            timeout=300000,
                        )
                        log.info("✅ Instagram Reels 发布成功!")
                    except Exception:
                        # 超时后再截图检查最终状态
                        final_path = self.publish_dir / "credentials" / "instagram" / "debug_final.png"
                        await page.screenshot(path=str(final_path))
                        log.info(f"   📷 最终状态截图: {final_path}")
                        # 检查 URL 是否已经变了（成功发布后可能跳转）
                        current_url = page.url
                        log.info(f"   🔗 当前 URL: {current_url}")
                        log.info("✅ Instagram 发布操作完成（请手动确认是否成功）")

                    return True

                except Exception as e:
                    log.error(f"❌ Instagram 上传失败: {e}")
                    debug_path = self.publish_dir / "credentials" / "instagram" / "debug_error.png"
                    try:
                        await page.screenshot(path=str(debug_path))
                        log.error(f"   📷 截图: {debug_path}")
                    except Exception:
                        pass
                    return False
                finally:
                    # 保存更新后的 cookie
                    await context.storage_state(path=str(self.cookie_file))
                    await context.close()

        return asyncio.run(_upload())
