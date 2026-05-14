"""Build compact EE rounds summary files for better RAG retrieval.

Problem: 415 individual rounds produce 1619 nearly-identical chunks.
Vector search can't distinguish them, so queries only return a few.

Solution: Create yearly summary docs with compact tables.
Each year = 1 section → 1 chunk with ALL rounds for that year.
"""
import re
import sys
from pathlib import Path
from collections import defaultdict

sys.stdout.reconfigure(encoding="utf-8")

SRC = Path("data/mineru_output/federal-ircc/content/dam/ircc/documents/json")
OUT = Path("data/mineru_output/federal-ircc/ee-rounds-summary")

def extract_rounds(md_path: Path) -> list[dict]:
    """Extract round data from the MinerU-parsed markdown."""
    text = md_path.read_text(encoding="utf-8")
    pattern = r"Round #(\d+): (.+?)\n\nDate: (.+?)\n\n.*?\n\nInvitations: ([\d,]+) \| CRS: (\d+)"
    matches = re.findall(pattern, text)
    rounds = []
    for m in matches:
        rounds.append({
            "number": int(m[0]),
            "type": m[1].strip(),
            "date": m[2].strip(),
            "invitations": m[3].strip(),
            "crs": int(m[4]),
        })
    return rounds

def year_from_date(date_str: str) -> str:
    """Extract year from date string like 'April 29, 2026'."""
    parts = date_str.split(",")
    if len(parts) >= 2:
        return parts[-1].strip()
    return "Unknown"

def categorize_type(round_type: str) -> str:
    """Simplify round type for compact display."""
    t = round_type.lower()
    if "provincial nominee" in t:
        return "PNP"
    if "canadian experience" in t:
        return "CEC"
    if "french" in t:
        return "French"
    if "healthcare" in t:
        return "Healthcare"
    if "trade" in t:
        return "Trades"
    if "stem" in t or "science" in t or "technology" in t:
        return "STEM"
    if "transport" in t:
        return "Transport"
    if "agriculture" in t:
        return "Agriculture"
    if "physician" in t:
        return "Physicians"
    if "senior manager" in t:
        return "Senior Mgrs"
    if "no program specified" in t:
        return "General"
    if "education" in t:
        return "Education"
    return round_type[:30]

def main():
    # Collect all rounds from both files
    all_rounds = []
    for sub in ["ee_rounds_4_en", "ee_rounds_123_en"]:
        md_dir = SRC / sub / sub / "auto"
        md_file = md_dir / f"{sub}.md"
        if md_file.exists():
            rounds = extract_rounds(md_file)
            print(f"  {sub}: {len(rounds)} rounds extracted")
            all_rounds.extend(rounds)
    
    # Deduplicate by round number
    seen = set()
    unique = []
    for r in all_rounds:
        if r["number"] not in seen:
            seen.add(r["number"])
            unique.append(r)
    unique.sort(key=lambda r: r["number"], reverse=True)
    print(f"\n  Total unique rounds: {len(unique)}")
    
    # Group by year
    by_year = defaultdict(list)
    for r in unique:
        year = year_from_date(r["date"])
        by_year[year].append(r)
    
    # Create output directory structure
    OUT.mkdir(parents=True, exist_ok=True)
    auto_dir = OUT / "auto"
    auto_dir.mkdir(exist_ok=True)
    
    # Build the summary markdown
    lines = []
    lines.append("# Express Entry Rounds Summary — CRS Cutoff Scores\n")
    lines.append("Source: IRCC Ministerial Instructions (ee_rounds_4_en.json + ee_rounds_123_en.json)\n")
    lines.append(f"Total rounds: {len(unique)} (Round #1 to #{unique[0]['number']})\n")
    lines.append("This document provides a compact summary of all Express Entry rounds,")
    lines.append("grouped by year, for efficient retrieval of CRS cutoff scores,")
    lines.append("invitation counts, and round types.\n")
    
    for year in sorted(by_year.keys(), reverse=True):
        rounds = sorted(by_year[year], key=lambda r: r["number"], reverse=True)
        
        # Calculate year stats
        cec_rounds = [r for r in rounds if categorize_type(r["type"]) == "CEC"]
        general_rounds = [r for r in rounds if categorize_type(r["type"]) == "General"]
        pnp_rounds = [r for r in rounds if categorize_type(r["type"]) == "PNP"]
        cbs_rounds = [r for r in rounds if categorize_type(r["type"]) not in ("CEC", "General", "PNP")]
        
        non_pnp = [r for r in rounds if categorize_type(r["type"]) != "PNP"]
        if non_pnp:
            min_crs = min(r["crs"] for r in non_pnp)
            max_crs = max(r["crs"] for r in non_pnp)
        else:
            min_crs = max_crs = 0
        
        cec_crs = [r["crs"] for r in cec_rounds] if cec_rounds else []
        general_crs = [r["crs"] for r in general_rounds] if general_rounds else []
        
        lines.append(f"\n# Express Entry Rounds {year}\n")
        lines.append(f"Year {year}: {len(rounds)} rounds total")
        if cec_rounds:
            lines.append(f"  CEC rounds: {len(cec_rounds)}, CRS range {min(cec_crs)}-{max(cec_crs)}")
        if general_rounds:
            lines.append(f"  General rounds: {len(general_rounds)}, CRS range {min(general_crs)}-{max(general_crs)}")
        if pnp_rounds:
            lines.append(f"  PNP rounds: {len(pnp_rounds)}")
        if cbs_rounds:
            types = set(categorize_type(r["type"]) for r in cbs_rounds)
            lines.append(f"  Category-based (CBS): {len(cbs_rounds)} ({', '.join(sorted(types))})")
        lines.append("")
        
        lines.append("| # | Date | Type | Invited | CRS |")
        lines.append("|---|------|------|---------|-----|")
        for r in rounds:
            short_type = categorize_type(r["type"])
            lines.append(f"| {r['number']} | {r['date']} | {short_type} | {r['invitations']} | {r['crs']} |")
        lines.append("")
    
    # Write the summary
    content = "\n".join(lines)
    out_file = auto_dir / "ee-rounds-summary.md"
    out_file.write_text(content, encoding="utf-8")
    print(f"\n  Written: {out_file} ({len(content)} bytes)")
    print(f"  Sections: {len(by_year)} years")
    
    # Also create a minimal content_list.json for the MinerU reader
    content_list = []
    page_idx = 0
    for year in sorted(by_year.keys(), reverse=True):
        rounds = by_year[year]
        content_list.append({
            "page_idx": page_idx,
            "type": "text",
            "text": f"Express Entry Rounds {year} Summary"
        })
        page_idx += 1
    
    cl_file = auto_dir / "ee-rounds-summary_content_list.json"
    import json
    cl_file.write_text(json.dumps(content_list, indent=2), encoding="utf-8")
    print(f"  Written: {cl_file}")
    
    print("\nDone! Now run:")
    print(f"  python scripts/ingest/batch_ingest.py --category federal-ircc")
    print("  (or manually ingest just this book)")

if __name__ == "__main__":
    main()
