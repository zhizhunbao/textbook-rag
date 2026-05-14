"""
ACSIS Student Account Scraper
抓取 Algonquin College ACSIS 学生账户的学费明细。

使用方法：
  1. 先在浏览器登录 ACSIS: https://acsis.algonquincollege.com
  2. 运行本脚本（自动使用浏览器 cookies）:
     cd textbook-rag
     uv run python scripts/crawl/scrape_acsis.py

  # 指定 Chrome 用户数据目录（默认自动检测）:
     uv run python scripts/crawl/scrape_acsis.py --profile "C:/Users/40270/AppData/Local/Google/Chrome/User Data"

  # 指定输出目录:
     uv run python scripts/crawl/scrape_acsis.py --output data/crawled_web/acsis

输出：
  data/crawled_web/acsis/
    student_subledger.json   — 所有学期的费用明细（结构化 JSON）
    student_subledger.pdf    — 当前页面的 PDF 截图
"""
import argparse
import asyncio
import json
import os
import sys
from datetime import datetime
from pathlib import Path

# ── Default Chrome profile path (Windows) ────────────────────────────────────
DEFAULT_CHROME_PROFILE = os.path.expandvars(
    r"%LOCALAPPDATA%\Google\Chrome\User Data"
)

ACSIS_URL = "https://acsis.algonquincollege.com/wwwhome/student_subledger.aspx"
OUTPUT_DIR = Path("data/crawled_web/acsis")


async def scrape_acsis(
    chrome_profile: str = DEFAULT_CHROME_PROFILE,
    output_dir: Path = OUTPUT_DIR,
):
    """Login via Chrome cookies → scrape all terms from ACSIS subledger."""
    from playwright.async_api import async_playwright

    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"[ACSIS] Chrome profile: {chrome_profile}")
    print(f"[ACSIS] Target URL:     {ACSIS_URL}")
    print(f"[ACSIS] Output dir:     {output_dir}")
    print()

    async with async_playwright() as p:
        # ── Launch with user's Chrome profile to reuse login session ──
        # channel="chrome" uses system Chrome; user_data_dir reuses cookies
        context = await p.chromium.launch_persistent_context(
            user_data_dir=chrome_profile,
            channel="chrome",
            headless=False,   # ACSIS may need visible browser for auth
            args=["--disable-blink-features=AutomationControlled"],
        )

        page = context.pages[0] if context.pages else await context.new_page()

        # ── Navigate to ACSIS subledger ──────────────────────────────────
        print("[ACSIS] Navigating to student subledger...")
        await page.goto(ACSIS_URL, wait_until="networkidle", timeout=30000)
        await page.wait_for_timeout(2000)

        # Check if we're on the login page
        current_url = page.url.lower()
        if "login" in current_url or "adfs" in current_url or "microsoftonline" in current_url:
            print("[ACSIS] ⚠️  Login page detected. Please log in manually...")
            print("[ACSIS] Waiting up to 120 seconds for login...")

            # Wait for navigation back to ACSIS after login
            try:
                await page.wait_for_url(
                    "**/student_subledger*",
                    timeout=120000,
                )
                await page.wait_for_timeout(2000)
                print("[ACSIS] ✅ Login successful!")
            except Exception:
                print("[ACSIS] ❌ Login timeout. Please try again.")
                await context.close()
                return None

        # ── Find available terms from the dropdown ───────────────────────
        print("[ACSIS] Extracting available terms...")

        terms = await page.evaluate("""() => {
            const select = document.querySelector('select[id*="term"], select[name*="term"], select');
            if (!select) return [];
            return Array.from(select.options).map(o => ({
                value: o.value,
                text: o.textContent.trim(),
                selected: o.selected,
            }));
        }""")

        if not terms:
            print("[ACSIS] ⚠️  No term dropdown found. Trying to extract current page data...")
            terms = [{"value": "current", "text": "Current", "selected": True}]

        print(f"[ACSIS] Found {len(terms)} terms: {[t['text'] for t in terms]}")

        # ── Scrape data for each term ────────────────────────────────────
        all_data = {}

        for term in terms:
            term_label = term["text"]
            term_value = term["value"]

            if term_value and term_value != "current":
                # Select this term in dropdown
                print(f"\n[ACSIS] Switching to term: {term_label}...")
                await page.select_option(
                    'select[id*="term"], select[name*="term"], select',
                    value=term_value,
                )
                # ASP.NET postback — wait for page reload
                await page.wait_for_load_state("networkidle", timeout=15000)
                await page.wait_for_timeout(1500)

            # ── Extract table data ───────────────────────────────────────
            print(f"[ACSIS] Extracting data for {term_label}...")

            rows = await page.evaluate("""() => {
                const tables = document.querySelectorAll('table');
                const results = [];
                for (const table of tables) {
                    const trs = table.querySelectorAll('tr');
                    for (const tr of trs) {
                        const cells = tr.querySelectorAll('td, th');
                        if (cells.length >= 3) {
                            const row = Array.from(cells).map(c => c.textContent.trim());
                            if (row.some(c => c.length > 0)) {
                                results.push(row);
                            }
                        }
                    }
                }
                return results;
            }""")

            # Parse rows into structured data
            transactions = []
            for row in rows:
                # Skip header rows
                if any(h in row[0].lower() for h in ["transaction date", "date"]):
                    continue
                # Try to parse as transaction row
                if len(row) >= 4:
                    transactions.append({
                        "raw": row,
                    })

            # Also try to extract with specific column mapping
            structured = await page.evaluate("""() => {
                const rows = [];
                const trs = document.querySelectorAll('table tr');
                for (const tr of trs) {
                    const tds = tr.querySelectorAll('td');
                    if (tds.length >= 5) {
                        rows.push({
                            date: tds[0]?.textContent?.trim() || '',
                            code: tds[1]?.textContent?.trim() || '',
                            type: tds[2]?.textContent?.trim() || '',
                            amount: tds[3]?.textContent?.trim() || '',
                            detail: tds[4]?.textContent?.trim() || '',
                        });
                    }
                }
                return rows;
            }""")

            all_data[term_label] = {
                "term_value": term_value,
                "term_label": term_label,
                "transactions": structured if structured else transactions,
                "row_count": len(structured if structured else transactions),
                "scraped_at": datetime.now().isoformat(),
            }

            print(f"  → {len(structured or transactions)} rows extracted")

            # Save PDF for current term
            pdf_path = output_dir / f"subledger_{term_label}.pdf"
            await page.pdf(path=str(pdf_path), format="A4", print_background=True)
            print(f"  → PDF saved: {pdf_path}")

        # ── Save consolidated JSON ───────────────────────────────────────
        json_path = output_dir / "student_subledger.json"
        json_path.write_text(
            json.dumps(all_data, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        print(f"\n[ACSIS] ✅ Data saved: {json_path}")
        print(f"[ACSIS] Terms scraped: {list(all_data.keys())}")

        # Summary
        total_rows = sum(d["row_count"] for d in all_data.values())
        print(f"[ACSIS] Total transactions: {total_rows}")

        await context.close()
        return all_data


def main():
    parser = argparse.ArgumentParser(
        description="Scrape ACSIS student account subledger (tuition fees)",
    )
    parser.add_argument(
        "--profile",
        default=DEFAULT_CHROME_PROFILE,
        help=f"Chrome user data directory (default: {DEFAULT_CHROME_PROFILE})",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=OUTPUT_DIR,
        help=f"Output directory (default: {OUTPUT_DIR})",
    )
    args = parser.parse_args()

    result = asyncio.run(scrape_acsis(
        chrome_profile=args.profile,
        output_dir=args.output,
    ))

    if result:
        print("\n✅ Done!")
    else:
        print("\n❌ Failed. Make sure you're logged into ACSIS in Chrome first.")
        sys.exit(1)


if __name__ == "__main__":
    main()
