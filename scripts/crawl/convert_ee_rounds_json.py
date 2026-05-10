"""Convert Express Entry rounds JSON files to Markdown + PDF for RAG ingestion.

The rounds-invitations page dynamically loads data from JSON via wb-jsonmanager.
PDF captures show blank fields. This script converts the raw JSON into structured
Markdown tables, then renders to PDF via Playwright so it can flow through the
standard MinerU → ChromaDB pipeline.

Usage:
    uv run python scripts/crawl/convert_ee_rounds_json.py
    uv run python scripts/crawl/convert_ee_rounds_json.py --dry-run
"""
import asyncio
import json
import re
import sys
from pathlib import Path

# ── Config ──
IRCC_DIR = Path(__file__).parent.parent.parent / "data" / "crawled_web" / "federal-ircc"
JSON_FILES = [
    IRCC_DIR / "content" / "dam" / "ircc" / "documents" / "json" / "ee_rounds_123_en.json.json",
    IRCC_DIR / "content" / "dam" / "ircc" / "documents" / "json" / "ee_rounds_123_en.json",
]
JSON_4_FILES = [
    IRCC_DIR / "content" / "dam" / "ircc" / "documents" / "json" / "ee_rounds_4_en.json.json",
    IRCC_DIR / "content" / "dam" / "ircc" / "documents" / "json" / "ee_rounds_4_en.json",
]
OUTPUT_MD = IRCC_DIR / "ee-rounds-invitations-data.md"
OUTPUT_PDF = IRCC_DIR / "ee-rounds-invitations-data.pdf"
SOURCE_URL = "https://www.canada.ca/en/immigration-refugees-citizenship/services/immigrate-canada/express-entry/rounds-invitations.html"


def find_json(candidates: list[Path]) -> Path | None:
    """Find the first existing JSON file from candidates."""
    for p in candidates:
        if p.exists():
            return p
    return None


def load_rounds(json_path: Path) -> list[dict]:
    """Load rounds array from JSON file."""
    data = json.loads(json_path.read_text(encoding="utf-8"))
    if isinstance(data, dict) and "rounds" in data:
        return data["rounds"]
    return []


def load_detail_rounds(json_path: Path) -> dict[str, dict]:
    """Load detail rounds from ee_rounds_4 (keyed by round number)."""
    data = json.loads(json_path.read_text(encoding="utf-8"))
    if isinstance(data, dict) and "rounds" in data:
        detail = data["rounds"]
        # detail is {"r414": {...}, "r413": {...}, ...}
        result = {}
        for key, val in detail.items():
            num = val.get("drawNumber", key.lstrip("r"))
            result[num] = val
        return result
    return {}


def extract_noc_table(html_content: str) -> list[tuple[str, str]]:
    """Extract NOC occupation code+title pairs from pageContent HTML."""
    # Find all <tr><td><p>CODE</p></td><td><p>TITLE</p></td></tr> patterns
    # Some rows have code first, some have title first
    rows = re.findall(r'<tr>\s*<td>\s*<p>(.*?)</p>\s*</td>\s*<td>\s*<p>(.*?)</p>\s*</td>\s*</tr>', html_content)
    occupations = []
    for col1, col2 in rows:
        # Determine which column is the code (numeric) and which is the title
        if re.match(r'^\d{4,5}$', col1.strip()):
            occupations.append((col1.strip(), col2.strip()))
        elif re.match(r'^\d{4,5}$', col2.strip()):
            occupations.append((col2.strip(), col1.strip()))
    return occupations


def rounds_to_markdown(rounds: list[dict], detail_rounds: dict[str, dict] | None = None) -> str:
    """Convert rounds data to structured Markdown."""
    lines = [
        f"# Express Entry: Rounds of Invitations — Complete Data",
        f"",
        f"**Source:** {SOURCE_URL}",
        f"**Data extracted from:** ee_rounds_123_en.json, ee_rounds_4_en.json",
        f"**Total rounds:** {len(rounds)}",
        f"",
        f"---",
        f"",
        f"## Summary Table: All Rounds of Invitations",
        f"",
        f"| Round # | Date | Type | Invitations Issued | CRS Score | Tie-Breaking Date |",
        f"|---------|------|------|-------------------|-----------|-------------------|",
    ]

    for r in rounds:
        num = r.get("drawNumber", "")
        date = r.get("drawDateFull", r.get("drawDate", ""))
        name = r.get("drawName", "")
        size = r.get("drawSize", "")
        crs = r.get("drawCRS", "")
        cutoff = r.get("drawCutOff", "")
        lines.append(f"| {num} | {date} | {name} | {size} | {crs} | {cutoff} |")

    lines.append("")
    lines.append("---")
    lines.append("")

    # Detailed sections for ALL rounds with detail data
    lines.append("## Detailed Round Information (All Rounds)")
    lines.append("")

    for r in rounds:
        num = r.get("drawNumber", "?")
        date = r.get("drawDateFull", r.get("drawDate", ""))
        name = r.get("drawName", "")
        size = r.get("drawSize", "")
        crs = r.get("drawCRS", "")
        cutoff = r.get("drawCutOff", "")
        dt = r.get("drawDateTime", "")
        programs = r.get("drawText2", "")
        dist_date = r.get("drawDistributionAsOn", "")

        lines.append(f"### Round #{num}: {name}")
        lines.append("")
        lines.append(f"- **Date and time:** {dt}")
        lines.append(f"- **Round type:** {name}")
        lines.append(f"- **Programs:** {programs}")
        lines.append(f"- **Number of invitations issued:** {size}")
        lines.append(f"- **CRS score of lowest-ranked candidate invited:** {crs}")
        lines.append(f"- **Tie-breaking rule:** {cutoff}")

        # CRS distribution if available
        if r.get("dd1"):
            lines.append(f"- **CRS distribution as of:** {dist_date}")
            lines.append("")
            lines.append("| CRS Range | Candidates |")
            lines.append("|-----------|-----------|")
            lines.append(f"| 601-1200 | {r.get('dd1', '')} |")
            lines.append(f"| 501-600 | {r.get('dd2', '')} |")
            lines.append(f"| 451-500 | {r.get('dd3', '')} |")
            lines.append(f"| 401-450 | {r.get('dd9', '')} |")
            lines.append(f"| 351-400 | {r.get('dd15', '')} |")
            lines.append(f"| 301-350 | {r.get('dd16', '')} |")
            lines.append(f"| 0-300 | {r.get('dd17', '')} |")
            lines.append(f"| **Total** | **{r.get('dd18', '')}** |")

        # NOC occupation table from detail data (category-based rounds)
        if detail_rounds and num in detail_rounds:
            detail = detail_rounds[num]
            page_html = detail.get("pageContent", "")
            occupations = extract_noc_table(page_html)
            if occupations:
                lines.append("")
                lines.append(f"**Eligible NOC Occupations ({len(occupations)} occupations):**")
                lines.append("")
                lines.append("| NOC Code | Occupation Title |")
                lines.append("|----------|-----------------|")
                for code, title in occupations:
                    lines.append(f"| {code} | {title} |")

        lines.append("")

    return "\n".join(lines)


async def md_to_pdf(md_path: Path, pdf_path: Path) -> None:
    """Render Markdown to PDF via Playwright (HTML intermediate)."""
    from playwright.async_api import async_playwright

    md_content = md_path.read_text(encoding="utf-8")

    # Simple MD → HTML (tables + basic formatting)
    html_content = md_to_html(md_content)

    html_page = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="utf-8">
    <title>Express Entry Rounds of Invitations</title>
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
        strong {{ color: #333; }}
    </style>
</head>
<body>{html_content}</body>
</html>"""

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

    size = pdf_path.stat().st_size
    print(f"  PDF saved: {pdf_path.name} ({size/1024:.1f} KB)")


def md_to_html(md_text: str) -> str:
    """Minimal Markdown → HTML converter for tables, headings, lists, bold."""
    import re
    lines = md_text.split("\n")
    html_lines = []
    in_table = False
    in_list = False
    header_done = False

    for line in lines:
        stripped = line.strip()

        # Headings
        if stripped.startswith("### "):
            if in_table: html_lines.append("</table>"); in_table = False
            if in_list: html_lines.append("</ul>"); in_list = False
            html_lines.append(f"<h3>{_inline(stripped[4:])}</h3>")
            continue
        if stripped.startswith("## "):
            if in_table: html_lines.append("</table>"); in_table = False
            if in_list: html_lines.append("</ul>"); in_list = False
            html_lines.append(f"<h2>{_inline(stripped[3:])}</h2>")
            continue
        if stripped.startswith("# "):
            if in_table: html_lines.append("</table>"); in_table = False
            if in_list: html_lines.append("</ul>"); in_list = False
            html_lines.append(f"<h1>{_inline(stripped[2:])}</h1>")
            continue

        # HR
        if stripped == "---":
            if in_table: html_lines.append("</table>"); in_table = False
            if in_list: html_lines.append("</ul>"); in_list = False
            html_lines.append("<hr>")
            continue

        # Table
        if stripped.startswith("|"):
            # Skip separator rows
            if re.match(r"^\|[\s\-:|]+\|$", stripped):
                header_done = True
                continue
            cells = [c.strip() for c in stripped.split("|")[1:-1]]
            if not in_table:
                html_lines.append("<table><thead>")
                in_table = True
                header_done = False
            if not header_done:
                html_lines.append("<tr>" + "".join(f"<th>{_inline(c)}</th>" for c in cells) + "</tr>")
                html_lines.append("</thead><tbody>")
                header_done = True
            else:
                html_lines.append("<tr>" + "".join(f"<td>{_inline(c)}</td>" for c in cells) + "</tr>")
            continue

        if in_table:
            html_lines.append("</tbody></table>")
            in_table = False
            header_done = False

        # List
        if stripped.startswith("- "):
            if not in_list:
                html_lines.append("<ul>")
                in_list = True
            html_lines.append(f"<li>{_inline(stripped[2:])}</li>")
            continue

        if in_list:
            html_lines.append("</ul>")
            in_list = False

        # Paragraph
        if stripped:
            html_lines.append(f"<p>{_inline(stripped)}</p>")

    if in_table: html_lines.append("</tbody></table>")
    if in_list: html_lines.append("</ul>")

    return "\n".join(html_lines)


def _inline(text: str) -> str:
    """Handle inline markdown: **bold**."""
    import re
    text = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", text)
    return text


async def main():
    dry_run = "--dry-run" in sys.argv

    # Find JSON files
    json_123 = find_json(JSON_FILES)
    json_4 = find_json(JSON_4_FILES)

    if not json_123 and not json_4:
        print("[ERROR] No EE rounds JSON files found. Run crawler first:")
        print("  uv run python scripts/crawl/crawler_cli.py batch data/crawled_web/federal-ircc/manifest.json")
        sys.exit(1)

    print(f"{'='*60}")
    print("Convert EE Rounds JSON → Markdown → PDF")
    print(f"{'='*60}")

    # Load rounds
    rounds = []
    if json_123:
        print(f"  Loading: {json_123.name}")
        rounds = load_rounds(json_123)
        print(f"    {len(rounds)} rounds loaded")
    detail_rounds = {}
    if json_4:
        print(f"  Loading: {json_4.name}")
        detail_rounds = load_detail_rounds(json_4)
        print(f"    {len(detail_rounds)} detail entries loaded")

    if not rounds:
        print("[ERROR] No rounds data found in JSON files")
        sys.exit(1)

    # Convert to Markdown
    md_content = rounds_to_markdown(rounds, detail_rounds=detail_rounds)
    # Count how many rounds have NOC tables
    noc_count = sum(1 for r in rounds if r.get('drawNumber') in detail_rounds
                    and extract_noc_table(detail_rounds[r['drawNumber']].get('pageContent', '')))
    print(f"\n  Generated Markdown: {len(md_content)} chars, {len(rounds)} rounds, {noc_count} with NOC tables")

    if dry_run:
        print(f"\n  [DRY RUN] Would write:")
        print(f"    {OUTPUT_MD}")
        print(f"    {OUTPUT_PDF}")
        print(f"\n  First 500 chars of MD:")
        print(md_content[:500])
        return

    # Save Markdown
    OUTPUT_MD.write_text(md_content, encoding="utf-8")
    print(f"  Markdown saved: {OUTPUT_MD.name}")

    # Render to PDF
    print(f"  Rendering PDF...")
    await md_to_pdf(OUTPUT_MD, OUTPUT_PDF)

    print(f"\n{'='*60}")
    print("DONE — Next steps:")
    print(f"  1. Run MinerU:  uv run python scripts/ingest/batch_mineru.py --category federal-ircc")
    print(f"  2. Run ingest:  uv run python scripts/ingest/batch_ingest.py --category federal-ircc")
    print(f"{'='*60}")


if __name__ == "__main__":
    asyncio.run(main())
