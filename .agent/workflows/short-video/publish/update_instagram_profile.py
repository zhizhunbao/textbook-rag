#!/usr/bin/env python3
"""更新 Instagram 昵称和 Bio — 使用已登录的持久化浏览器。"""

# /// script
# requires-python = ">=3.11"
# dependencies = ["playwright>=1.40"]
# ///

import asyncio
import logging
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s",
                    datefmt="%H:%M:%S")
log = logging.getLogger(__name__)

PUBLISH_DIR = Path(__file__).resolve().parent
BROWSER_DATA = PUBLISH_DIR / "credentials" / "instagram" / "browser-data"
EDIT_URL = "https://www.instagram.com/accounts/edit/"

# 品牌信息
NAME = "Overseas Life Guide"
BIO = "🇨🇦 Canada newcomer guide\n📌 Study · Immigration · Housing · Daily life\n💡 Practical tips to settle in Canada faster"


async def update_profile():
    from playwright.async_api import async_playwright

    async with async_playwright() as pw:
        context = await pw.chromium.launch_persistent_context(
            user_data_dir=str(BROWSER_DATA),
            headless=False,
            channel="chrome",
            args=["--disable-blink-features=AutomationControlled", "--no-sandbox"],
            ignore_default_args=["--enable-automation"],
            locale="en-US",
        )
        page = context.pages[0] if context.pages else await context.new_page()

        log.info("🌐 打开 Instagram 编辑页面...")
        await page.goto(EDIT_URL)
        await page.wait_for_load_state("domcontentloaded")
        await page.wait_for_timeout(4000)

        # 关闭可能的弹窗
        for txt in ["Not Now", "Not now"]:
            try:
                btn = page.locator(f'button:has-text("{txt}")').first
                if await btn.is_visible():
                    await btn.click()
                    await page.wait_for_timeout(1000)
            except Exception:
                pass

        # ── 修改 Bio ──
        log.info("✏️ 修改 Bio...")
        log.info(f"   目标: {BIO.replace(chr(10), ' | ')}")

        # 从截图看，Bio 区域在 "Bio" 标签下面，显示 "Rebuy Bro | Cars That Pay You Back"
        # 它有 34/150 字符计数，说明是可编辑的
        bio_edited = False

        # 策略 1: 直接点击 Bio 文本区域
        try:
            # 找到包含当前 bio 文本的区域（点击它使其可编辑）
            bio_area = page.locator('textarea, div[contenteditable="true"]')
            for i in range(await bio_area.count()):
                el = bio_area.nth(i)
                if await el.is_visible():
                    text = await el.text_content() or await el.input_value() if await el.evaluate("el => el.tagName") == "TEXTAREA" else ""
                    log.info(f"   🔍 找到可编辑区域 #{i}: {text[:50]}...")
                    await el.click()
                    await el.fill("")
                    await el.fill(BIO)
                    bio_edited = True
                    log.info("   ✅ Bio 已通过 fill() 设置")
                    break
        except Exception as e:
            log.info(f"   策略 1 失败: {e}")

        # 策略 2: 找到 "Bio" 标题后面的第一个可编辑元素，用键盘操作
        if not bio_edited:
            try:
                # 点击 Bio 标签旁的编辑区域
                bio_label = page.locator('text="Bio"').first
                if await bio_label.is_visible():
                    # Bio 输入框通常在标签的下一个兄弟/后续元素
                    # 点击 Bio 下方的文本区域
                    bio_box = page.locator('xpath=//span[text()="Bio"]/ancestor::div[1]/following-sibling::*//textarea | //span[text()="Bio"]/ancestor::div[1]/following-sibling::*//div[@contenteditable]').first
                    if await bio_box.is_visible():
                        await bio_box.click()
                        # 全选并删除
                        await page.keyboard.press("Control+A")
                        await page.keyboard.press("Delete")
                        await page.wait_for_timeout(500)
                        await page.keyboard.insert_text(BIO)
                        bio_edited = True
                        log.info("   ✅ Bio 已通过键盘设置")
            except Exception as e:
                log.info(f"   策略 2 失败: {e}")

        # 策略 3: 通过 JS 直接操作 — 找所有 textarea 并检查内容
        if not bio_edited:
            try:
                result = await page.evaluate("""() => {
                    // 找所有 textarea
                    const areas = document.querySelectorAll('textarea');
                    for (const ta of areas) {
                        return { found: true, value: ta.value, tag: 'textarea' };
                    }
                    // 找所有 contenteditable
                    const edits = document.querySelectorAll('[contenteditable="true"]');
                    for (const el of edits) {
                        return { found: true, value: el.textContent, tag: 'contenteditable' };
                    }
                    return { found: false };
                }""")
                log.info(f"   🔍 JS 扫描结果: {result}")

                if result.get("found"):
                    if result["tag"] == "textarea":
                        await page.evaluate(f"""() => {{
                            const ta = document.querySelector('textarea');
                            const nativeInputValueSetter = Object.getOwnPropertyDescriptor(
                                window.HTMLTextAreaElement.prototype, 'value'
                            ).set;
                            nativeInputValueSetter.call(ta, `{BIO}`);
                            ta.dispatchEvent(new Event('input', {{ bubbles: true }}));
                            ta.dispatchEvent(new Event('change', {{ bubbles: true }}));
                        }}""")
                        bio_edited = True
                        log.info("   ✅ Bio 已通过 JS 设置")
            except Exception as e:
                log.info(f"   策略 3 失败: {e}")

        if not bio_edited:
            log.warning("   ⚠️ 所有策略都失败，需要手动修改 Bio")

        await page.wait_for_timeout(1000)

        # ── 点击 Submit ──
        if bio_edited:
            log.info("💾 保存...")
            try:
                # Submit 按钮 — 可能是 disabled 直到有修改
                submit_btn = page.locator('div[role="button"]:has-text("Submit"), button:has-text("Submit")').first
                await submit_btn.wait_for(state="visible", timeout=5000)
                # 检查是否可点击
                is_disabled = await submit_btn.get_attribute("aria-disabled")
                if is_disabled == "true":
                    log.warning("   ⚠️ Submit 按钮仍然禁用，Bio 可能没有被 React 检测到变化")
                    # 尝试点击 bio 区域再手动输入触发 React state change
                    log.info("   🔄 尝试通过键盘输入触发变化...")
                    textarea = page.locator('textarea').first
                    if await textarea.is_visible():
                        await textarea.click()
                        await page.keyboard.press("Control+A")
                        await page.keyboard.press("Delete")
                        await page.wait_for_timeout(500)
                        # 逐字输入触发 React onChange
                        await page.keyboard.type(BIO, delay=20)
                        await page.wait_for_timeout(1000)
                        # 重新检查 Submit
                        is_disabled = await submit_btn.get_attribute("aria-disabled")

                if is_disabled != "true":
                    await submit_btn.click()
                    log.info("   ✅ 已提交保存!")
                    await page.wait_for_timeout(3000)
                else:
                    log.warning("   ⚠️ Submit 仍然禁用")
            except Exception as e:
                log.warning(f"   ⚠️ 保存失败: {e}")

        # ── 改 Name（需要去 Meta Accounts Center）──
        log.info("")
        log.info("📝 注意: Instagram 昵称需要在 Meta Accounts Center 修改")
        log.info("   🌐 打开 Personal details 页面...")
        await page.goto("https://accountscenter.instagram.com/personal_info/name/")
        await page.wait_for_load_state("domcontentloaded")
        await page.wait_for_timeout(3000)

        # 截图
        debug_path = PUBLISH_DIR / "credentials" / "instagram" / "debug_name_page.png"
        await page.screenshot(path=str(debug_path))
        log.info(f"📷 Name 编辑页截图: {debug_path}")
        log.info(f"   请手动将 Name 改为: {NAME}")
        log.info("   按回车关闭浏览器...")

        try:
            input()
        except EOFError:
            await page.wait_for_timeout(5000)

        # 最终截图
        final_path = PUBLISH_DIR / "credentials" / "instagram" / "debug_edit_final.png"
        await page.screenshot(path=str(final_path))

        await context.close()
        log.info("✅ 完成!")


if __name__ == "__main__":
    asyncio.run(update_profile())
