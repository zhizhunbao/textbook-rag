"""Quick scan: count PDFs in crawled_web directories not yet in batch_mineru.py"""
from pathlib import Path

root = Path(__file__).parent.parent.parent / "data" / "crawled_web"
# directories already in SOURCE_DIRS
existing = {
    "federal-ircc", "federal-fcac",
    "prov-ontario", "prov-bc", "prov-alberta", "prov-manitoba",
    "prov-saskatchewan", "prov-nova-scotia", "prov-new-brunswick",
    "prov-nwt", "prov-quebec", "prov-yukon",
    "algonquin-programs",
    "bank-bmo", "bank-rbc", "bank-td", "bank-cibc", "bank-scotiabank",
}

for d in sorted(root.iterdir()):
    if not d.is_dir():
        continue
    pdfs = list(d.rglob("*.pdf"))
    count = len(pdfs)
    total_mb = sum(f.stat().st_size for f in pdfs) / (1024*1024) if pdfs else 0
    tag = "  [NEW]" if d.name not in existing else ""
    print(f"{d.name:30s} {count:4d} PDFs  {total_mb:8.1f} MB{tag}")
