"""Check failed MinerU PDFs."""
import fitz
from pathlib import Path

failed = [
    "actions-taken-to-strengthen-canadas-temporary-residence-programs-and-migration-pathways",
    "canada-to-stabilize-growth-and-decrease-number-of-new-international-student-permits-issued-to-approximately-360000-for-2024",
    "changes-to-international-student-program-aim-to-protect-students",
    "guide-5578-request-process-following-family-members-year-window-opportunity-provisions",
    "revised-requirements-to-better-protect-international-students",
    "speaking-notes-for-the-honourable-marc-miller-minister-of-immigration-refugees-and-citizenship-announcement-related-to-temporary-residents",
    "strengthening-temporary-residence-programs-for-sustainable-volumes",
    "updated-travel-information-for-mexican-citizens-coming-to-canada",
]

pdf_dir = Path("data/crawled_web/imm-pathways")
out_dir = Path("data/mineru_output/imm-pathways")

for name in failed:
    pdf_path = pdf_dir / f"{name}.pdf"
    if not pdf_path.exists():
        print(f"{name}: PDF NOT FOUND")
        continue
    doc = fitz.open(str(pdf_path))
    p0 = doc[0]
    text_len = sum(len(p.get_text()) for p in doc)
    print(f"{name}:")
    print(f"  pages={len(doc)}, page_size={p0.rect.width:.0f}x{p0.rect.height:.0f}, total_text={text_len} chars")
    
    # Check MinerU output
    mineru_dir = out_dir / name / name / "auto"
    md_files = list(mineru_dir.glob("*.md")) if mineru_dir.exists() else []
    print(f"  mineru_dir exists={mineru_dir.exists()}, md_files={len(md_files)}")
    if md_files:
        for f in md_files:
            print(f"    {f.name}: {f.stat().st_size} bytes")
    doc.close()
