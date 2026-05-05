"""Download the DLI full list JSON from canada.ca → save raw JSON + render PDF.

Source: /content/dam/ircc/documents/json/dli/dli-full-list.json

Output:
    data/crawled_web/edu-school-planning/dli-full-list.json   (raw original)
    data/crawled_web/edu-school-planning/dli-full-list.pdf    (rendered for trust + MinerU pipeline)

Usage:
    uv run python scripts/scrape_dli_list.py
"""
import asyncio
import json
import sys
from pathlib import Path

import httpx

OUTPUT_DIR = Path("data/crawled_web/edu-school-planning")
DLI_JSON_URL = (
    "https://www.canada.ca/content/dam/ircc/documents/json/dli/dli-full-list.json"
)


def download_json() -> list[dict]:
    """Download and save raw JSON."""
    print("Downloading DLI JSON from canada.ca...")
    resp = httpx.get(DLI_JSON_URL, timeout=30, follow_redirects=True)
    resp.raise_for_status()

    raw = resp.json()
    data = raw.get("data", raw) if isinstance(raw, dict) else raw
    print(f"Downloaded {len(data)} records")

    # Save raw JSON (original data, untouched)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    raw_path = OUTPUT_DIR / "dli-full-list.json"
    raw_path.write_text(json.dumps(raw, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"[OK] Raw JSON saved: {raw_path} ({raw_path.stat().st_size / 1024:.1f} KB)")

    return data


def build_html(data: list[dict]) -> str:
    """Render DLI data as a clean HTML document for PDF conversion."""
    # Group by province
    by_province: dict[str, list[dict]] = {}
    for entry in data:
        prov = entry.get("Province", "Unknown")
        by_province.setdefault(prov, []).append(entry)

    html_parts = [
        "<!DOCTYPE html>",
        "<html lang='en'><head><meta charset='utf-8'>",
        "<title>Designated Learning Institutions (DLI) — Full List</title>",
        "<style>",
        "  body { font-family: Arial, sans-serif; margin: 20px; font-size: 11px; }",
        "  h1 { font-size: 18px; color: #26374a; }",
        "  h2 { font-size: 14px; color: #333; margin-top: 24px; page-break-after: avoid; }",
        "  .meta { color: #666; font-size: 10px; margin-bottom: 16px; }",
        "  table { width: 100%; border-collapse: collapse; margin-bottom: 16px; }",
        "  th { background: #26374a; color: white; text-align: left; padding: 4px 6px; font-size: 10px; }",
        "  td { border-bottom: 1px solid #ddd; padding: 3px 6px; font-size: 10px; }",
        "  tr:nth-child(even) { background: #f9f9f9; }",
        "  .summary { font-weight: bold; color: #26374a; }",
        "</style></head><body>",
        "<h1>Designated Learning Institutions (DLI) — Full List by Province</h1>",
        f"<p class='meta'>Source: Immigration, Refugees and Citizenship Canada (IRCC)<br>",
        f"Data URL: {DLI_JSON_URL}<br>",
        f"Total DLIs across Canada: {len(data)}</p>",
        "<p>A Designated Learning Institution (DLI) is a school approved by a "
        "provincial or territorial government to host international students. "
        "You need a letter of acceptance from a DLI before you can apply for "
        "a study permit. Each DLI has a unique DLI number (starts with 'O').</p>",
        "<p>PGWP Eligible: 'Yes' means graduates may be eligible for a "
        "Post-Graduation Work Permit. 'Details' means only certain programs qualify.</p>",
    ]

    for province in sorted(by_province.keys()):
        rows = by_province[province]
        html_parts.append(f"<h2>{province} ({len(rows)} institutions)</h2>")
        html_parts.append("<table><tr><th>Institution</th><th>DLI #</th>"
                          "<th>City</th><th>Campus</th><th>PGWP</th><th>Type</th></tr>")
        for r in sorted(rows, key=lambda x: x.get("Institution", "")):
            name = r.get("Institution", "")
            dli_num = r.get("DLI #", "")
            city = r.get("City", "")
            campus = r.get("Campus", "")
            pgwp = r.get("PGWP", "")
            pub_priv = r.get("Public/Private", "")
            html_parts.append(
                f"<tr><td>{name}</td><td>{dli_num}</td>"
                f"<td>{city}</td><td>{campus}</td>"
                f"<td>{pgwp}</td><td>{pub_priv}</td></tr>"
            )
        html_parts.append("</table>")

    html_parts.append(f"<p class='summary'>Total institutions: {len(data)}</p>")
    html_parts.append("</body></html>")
    return "\n".join(html_parts)


async def render_pdf(html: str) -> Path:
    """Render HTML string to PDF via Playwright."""
    from playwright.async_api import async_playwright

    pdf_path = OUTPUT_DIR / "dli-full-list.pdf"

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        await page.set_content(html, wait_until="networkidle")
        await page.pdf(
            path=str(pdf_path),
            format="Letter",
            print_background=True,
            margin={"top": "10mm", "bottom": "10mm", "left": "10mm", "right": "10mm"},
        )
        await browser.close()

    size_kb = pdf_path.stat().st_size / 1024
    print(f"[OK] PDF rendered: {pdf_path} ({size_kb:.1f} KB)")
    return pdf_path


def cleanup_old_md():
    """Remove the old .md file if it exists."""
    old_md = OUTPUT_DIR / "dli-full-list.md"
    if old_md.exists():
        old_md.unlink()
        print(f"[CLEAN] Removed old: {old_md}")


def main():
    data = download_json()
    html = build_html(data)
    asyncio.run(render_pdf(html))
    cleanup_old_md()
    print(f"\nDone! {len(data)} DLI records -> JSON (raw) + PDF (trust anchor)")


if __name__ == "__main__":
    main()
