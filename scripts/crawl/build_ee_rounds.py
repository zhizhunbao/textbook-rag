"""Build EE Rounds PDFs from raw JSON data.

Two independent PDFs are produced, one per JSON source:
  - ee_rounds_123_en.pdf  ← summary table + CRS distributions
  - ee_rounds_4_en.pdf    ← per-round Ministerial Instructions + NOC tables

Pipeline: JSON → HTML → PDF → MinerU → MD → ChromaDB

Usage:
    uv run python scripts/crawl/build_ee_rounds.py
    uv run python scripts/crawl/build_ee_rounds.py --dry-run
"""
import asyncio
import json
import re
import sys
from pathlib import Path

# ── Config ──
IRCC_DIR = Path(__file__).parent.parent.parent / "data" / "crawled_web" / "federal-ircc"
_JSON_DIR = IRCC_DIR / "content" / "dam" / "ircc" / "documents" / "json"

JSON_123_CANDIDATES = [
    _JSON_DIR / "ee_rounds_123_en.json",
    _JSON_DIR / "ee_rounds_123_en.json.json",  # legacy double-ext
]
JSON_4_CANDIDATES = [
    _JSON_DIR / "ee_rounds_4_en.json",
    _JSON_DIR / "ee_rounds_4_en.json.json",    # legacy double-ext
]

# 输出路径 = JSON 原始 URL 路径，book_id 拼出可访问的 JSON URL
_PATH_123 = "content/dam/ircc/documents/json/ee_rounds_123_en"
_PATH_4   = "content/dam/ircc/documents/json/ee_rounds_4_en"
OUTPUT_PDF_123 = IRCC_DIR / f"{_PATH_123}.pdf"
OUTPUT_PDF_4   = IRCC_DIR / f"{_PATH_4}.pdf"
SOURCE_URL_123 = "https://www.canada.ca/content/dam/ircc/documents/json/ee_rounds_123_en.json"
SOURCE_URL_4   = "https://www.canada.ca/content/dam/ircc/documents/json/ee_rounds_4_en.json"


def find_json(candidates: list[Path]) -> Path | None:
    for p in candidates:
        if p.exists():
            return p
    return None


def load_rounds_123(json_path: Path) -> list[dict]:
    """Load the summary rounds list from ee_rounds_123_en."""
    data = json.loads(json_path.read_text(encoding="utf-8"))
    if isinstance(data, dict) and "rounds" in data:
        return data["rounds"]
    return []


def load_rounds_4(json_path: Path) -> dict[str, dict]:
    """Load the detail rounds dict (keyed by drawNumber) from ee_rounds_4_en."""
    data = json.loads(json_path.read_text(encoding="utf-8"))
    if isinstance(data, dict) and "rounds" in data:
        result = {}
        for key, val in data["rounds"].items():
            num = val.get("drawNumber", key.lstrip("r"))
            result[num] = val
        return result
    return {}


def extract_noc_table(html_content: str) -> list[tuple[str, str]]:
    """Extract NOC (code, title) pairs from pageContent HTML."""
    rows = re.findall(
        r'<tr>\s*<td>\s*<p>(.*?)</p>\s*</td>\s*<td>\s*<p>(.*?)</p>\s*</td>\s*</tr>',
        html_content,
    )
    occupations = []
    for col1, col2 in rows:
        if re.match(r'^\d{4,5}$', col1.strip()):
            occupations.append((col1.strip(), col2.strip()))
        elif re.match(r'^\d{4,5}$', col2.strip()):
            occupations.append((col2.strip(), col1.strip()))
    return occupations


# ─── HTML builders ───────────────────────────────────────────────

def rounds_123_to_html(rounds: list[dict]) -> str:
    """JSON → HTML: summary table + CRS distribution (123_en only)."""
    h = []
    h.append(f"<h1>Express Entry: Rounds of Invitations — Summary Data</h1>")
    h.append(f"<p><strong>Source:</strong> {SOURCE_URL_123}</p>")
    h.append(f"<p><strong>Total rounds:</strong> {len(rounds)}</p>")
    h.append("<hr>")

    # Summary table
    h.append("<h2>Summary Table</h2><table><thead><tr>")
    for col in ["Round #", "Date", "Type", "Invitations", "CRS Score", "Tie-Breaking"]:
        h.append(f"<th>{col}</th>")
    h.append("</tr></thead><tbody>")
    for r in rounds:
        h.append(
            f"<tr><td>{r.get('drawNumber','')}</td>"
            f"<td>{r.get('drawDateFull', r.get('drawDate',''))}</td>"
            f"<td>{r.get('drawName','')}</td>"
            f"<td>{r.get('drawSize','')}</td>"
            f"<td>{r.get('drawCRS','')}</td>"
            f"<td>{r.get('drawCutOff','')}</td></tr>"
        )
    h.append("</tbody></table><hr>")

    # Detail sections (CRS distribution from 123 only, NO _4_en NOC data)
    h.append("<h2>Detailed Round Information</h2>")
    for r in rounds:
        num = r.get("drawNumber", "?")
        name = r.get("drawName", "")
        h.append(f"<h3>Round #{num}: {name}</h3><ul>")
        h.append(f"<li><strong>Date and time:</strong> {r.get('drawDateTime', '')}</li>")
        h.append(f"<li><strong>Programs:</strong> {r.get('drawText2', '')}</li>")
        h.append(f"<li><strong>Invitations issued:</strong> {r.get('drawSize', '')}</li>")
        h.append(f"<li><strong>CRS lowest score:</strong> {r.get('drawCRS', '')}</li>")
        h.append(f"<li><strong>Tie-breaking:</strong> {r.get('drawCutOff', '')}</li>")
        h.append("</ul>")

        if r.get("dd1"):
            h.append(f"<p><strong>CRS distribution:</strong> {r.get('drawDistributionAsOn', '')}</p>")
            h.append("<table><thead><tr><th>CRS Range</th><th>Candidates</th></tr></thead><tbody>")
            for label, key in [
                ("601-1200", "dd1"), ("501-600", "dd2"), ("451-500", "dd3"),
                ("401-450", "dd9"), ("351-400", "dd15"), ("301-350", "dd16"), ("0-300", "dd17"),
            ]:
                h.append(f"<tr><td>{label}</td><td>{r.get(key, '')}</td></tr>")
            h.append(f"<tr><td><strong>Total</strong></td><td><strong>{r.get('dd18','')}</strong></td></tr>")
            h.append("</tbody></table>")

    return "\n".join(h)


def rounds_4_to_html(detail_rounds: dict[str, dict]) -> str:
    """JSON → HTML: per-round Ministerial Instructions + NOC tables (4_en only)."""
    h = []
    h.append(f"<h1>Express Entry: Ministerial Instructions per Round</h1>")
    h.append(f"<p><strong>Source:</strong> {SOURCE_URL_4}</p>")
    h.append(f"<p><strong>Total rounds with detail:</strong> {len(detail_rounds)}</p>")
    h.append("<hr>")

    # Sort by round number descending
    sorted_items = sorted(
        detail_rounds.items(),
        key=lambda kv: int(kv[0]) if kv[0].isdigit() else 0,
        reverse=True,
    )

    for num, info in sorted_items:
        name = info.get("drawName", "")
        date = info.get("drawDateFull", "")
        h.append(f"<h2>Round #{num}: {name}</h2>")
        h.append(f"<p><strong>Date:</strong> {date}</p>")
        h.append(f"<p><strong>Programs:</strong> {info.get('drawText2', '')}</p>")
        h.append(f"<p><strong>Invitations:</strong> {info.get('drawSize', '')} | "
                 f"<strong>CRS:</strong> {info.get('drawCRS', '')}</p>")

        # fullText = the formal ministerial instrument preamble
        full_text = info.get("fullText", "")
        if full_text:
            # Strip HTML tags for cleaner rendering
            clean = re.sub(r'<[^>]+>', '', full_text)
            h.append(f"<p><em>{clean}</em></p>")

        # pageContent = the body of the Ministerial Instruction (definitions, category, NOC table, etc.)
        page_content = info.get("pageContent", "")
        if page_content:
            h.append(f"<div>{page_content}</div>")

        h.append("<hr>")

    return "\n".join(h)


async def html_to_pdf(html_body: str, pdf_path: Path, title: str = "Express Entry Rounds") -> None:
    """Render HTML body to PDF via Playwright."""
    from playwright.async_api import async_playwright

    html_page = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="utf-8">
    <title>{title}</title>
    <style>
        body {{ font-family: 'Segoe UI', Arial, sans-serif; margin: 40px; font-size: 11px; line-height: 1.4; }}
        h1 {{ color: #26374a; font-size: 20px; border-bottom: 3px solid #af3c43; padding-bottom: 8px; }}
        h2 {{ color: #26374a; font-size: 16px; margin-top: 24px; }}
        h3 {{ color: #333; font-size: 13px; margin-top: 16px; }}
        table {{ border-collapse: collapse; width: 100%; margin: 10px 0; page-break-inside: auto; }}
        tr {{ page-break-inside: avoid; }}
        th, td {{ border: 1px solid #ddd; padding: 4px 8px; text-align: left; font-size: 10px; }}
        th {{ background-color: #26374a; color: white; }}
        tr:nth-child(even) {{ background-color: #f9f9f9; }}
        hr {{ border: none; border-top: 1px solid #ccc; margin: 16px 0; }}
        ul {{ padding-left: 20px; }}
        li {{ margin: 2px 0; }}
        ol.lst-lwr-alph {{ list-style-type: lower-alpha; }}
        div.table-responsive {{ overflow-x: auto; }}
    </style>
</head>
<body>{html_body}</body>
</html>"""

    pdf_path.parent.mkdir(parents=True, exist_ok=True)
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        await page.set_content(html_page, wait_until="networkidle")
        await page.pdf(
            path=str(pdf_path),
            width="1280px",
            print_background=True,
            margin={"top": "10mm", "bottom": "10mm", "left": "10mm", "right": "10mm"},
        )
        await browser.close()

    print(f"  PDF saved: {pdf_path.name} ({pdf_path.stat().st_size/1024:.1f} KB)")


async def main():
    dry_run = "--dry-run" in sys.argv

    json_123 = find_json(JSON_123_CANDIDATES)
    json_4 = find_json(JSON_4_CANDIDATES)

    if not json_123 and not json_4:
        print("[ERROR] No EE rounds JSON files found.")
        sys.exit(1)

    print(f"{'='*60}")
    print("Build EE Rounds: JSON → HTML → PDF (separate files)")
    print(f"{'='*60}")

    # ── PDF 1: ee_rounds_123_en ──
    if json_123:
        print(f"\n  [123_en] Loading: {json_123.name}")
        rounds = load_rounds_123(json_123)
        print(f"    {len(rounds)} rounds loaded")

        if dry_run:
            print(f"    [DRY RUN] Would write: {OUTPUT_PDF_123}")
        else:
            html_body = rounds_123_to_html(rounds)
            await html_to_pdf(html_body, OUTPUT_PDF_123, title="EE Rounds Summary")
            print(f"    ✓ {OUTPUT_PDF_123.name} ({OUTPUT_PDF_123.stat().st_size/1024:.1f} KB)")
    else:
        print("  [123_en] Not found, skipping.")

    # ── PDF 2: ee_rounds_4_en ──
    if json_4:
        print(f"\n  [4_en]   Loading: {json_4.name}")
        detail_rounds = load_rounds_4(json_4)
        print(f"    {len(detail_rounds)} detail entries loaded")

        if dry_run:
            print(f"    [DRY RUN] Would write: {OUTPUT_PDF_4}")
        else:
            html_body = rounds_4_to_html(detail_rounds)
            await html_to_pdf(html_body, OUTPUT_PDF_4, title="EE Round Details")
            print(f"    ✓ {OUTPUT_PDF_4.name} ({OUTPUT_PDF_4.stat().st_size/1024:.1f} KB)")
    else:
        print("  [4_en]   Not found, skipping.")

    print(f"\n{'='*60}")
    print(f"DONE — each JSON has its own PDF")
    print(f"Next:  MinerU → ChromaDB")
    print(f"{'='*60}")


if __name__ == "__main__":
    asyncio.run(main())
