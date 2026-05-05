"""Quick probe of DLI page structure."""
import asyncio
import sys
from playwright.async_api import async_playwright


async def probe():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        page = await browser.new_page()
        print("Navigating...")
        await page.goto(
            "https://www.canada.ca/en/immigration-refugees-citizenship/"
            "services/study-canada/study-permit/prepare/"
            "designated-learning-institutions-list.html",
            wait_until="domcontentloaded",
            timeout=60_000,
        )
        print("Page loaded, waiting 10s for JS...")
        await page.wait_for_timeout(10_000)

        # Dump page structure info
        info = await page.evaluate("""() => {
            const selects = document.querySelectorAll('select');
            const iframes = document.querySelectorAll('iframe');
            const tables = document.querySelectorAll('table');
            const details = [];
            selects.forEach((s, i) => {
                const opts = Array.from(s.options).slice(0, 5).map(o => o.text);
                details.push(`SELECT#${i}: id=${s.id}, name=${s.name}, opts=${JSON.stringify(opts)}`);
            });
            iframes.forEach((f, i) => {
                details.push(`IFRAME#${i}: src=${f.src?.substring(0, 100)}`);
            });
            tables.forEach((t, i) => {
                details.push(`TABLE#${i}: id=${t.id}, rows=${t.rows?.length}`);
            });
            // Also check for common DLI-specific elements
            const dliDiv = document.querySelector('#defined, #dli-list, [data-wb-tables]');
            if (dliDiv) details.push(`DLI_DIV: tag=${dliDiv.tagName}, id=${dliDiv.id}`);
            
            // Check wb-tables (WET framework dynamic tables)
            const wbTables = document.querySelectorAll('[class*="wb-tables"], .wb-tables');
            wbTables.forEach((t, i) => {
                details.push(`WB_TABLE#${i}: id=${t.id}, class=${t.className}`);
            });
            
            return {
                title: document.title,
                selectCount: selects.length,
                iframeCount: iframes.length,
                tableCount: tables.length,
                details: details,
                bodyText: document.body.innerText?.substring(0, 500)
            };
        }""")

        print(f"\nTitle: {info['title']}")
        print(f"Selects: {info['selectCount']}")
        print(f"Iframes: {info['iframeCount']}")
        print(f"Tables: {info['tableCount']}")
        print("\nDetails:")
        for d in info["details"]:
            print(f"  {d}")
        print(f"\nBody preview:\n{info['bodyText'][:300]}")

        await browser.close()


if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
asyncio.run(probe())
