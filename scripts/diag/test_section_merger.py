"""Test section merger on the PAL document.

Validates that:
1. Small body-text items get merged into section-level chunks
2. Multi-page bboxes are preserved
3. Section titles are prepended for context
4. Tables remain standalone
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

import json
from engine_v2.chunking.section_merger import merge_content_items


PAL_DIR = ROOT / "data" / "mineru_output" / "federal-ircc" / (
    "en/immigration-refugees-citizenship/services/study-canada/"
    "study-permit/get-documents/provincial-attestation-letter/"
    "provincial-attestation-letter/auto"
)

CONTENT_LIST = PAL_DIR / "provincial-attestation-letter_content_list.json"


def main():
    with open(CONTENT_LIST, "r", encoding="utf-8") as f:
        items = json.load(f)

    print(f"Input: {len(items)} raw content items")
    print(f"  text items: {sum(1 for i in items if i.get('type') == 'text')}")
    print(f"  table items: {sum(1 for i in items if i.get('type') == 'table')}")
    print()

    merged = merge_content_items(items)

    print(f"\nOutput: {len(merged)} merged chunks")
    print("=" * 80)

    for i, m in enumerate(merged):
        pages = sorted(set(b.page_idx for b in m.bboxes)) if m.bboxes else [m.page_idx]
        page_str = ",".join(str(p) for p in pages)
        text_preview = m.text[:120].replace("\n", " | ")
        print(
            f"[{i:3d}] type={m.content_type:5s}  pages={page_str:>8s}  "
            f"len={len(m.text):5d}  bboxes={len(m.bboxes):2d}  "
            f"section={'Y' if m.section_title else '-'}"
        )
        print(f"      {text_preview}")
        print()

    # Size analysis
    sizes = [len(m.text) for m in merged if m.content_type == "text"]
    if sizes:
        print("=" * 80)
        print(f"Text chunk sizes:")
        print(f"  Min: {min(sizes)} chars")
        print(f"  Max: {max(sizes)} chars")
        print(f"  Mean: {sum(sizes)/len(sizes):.0f} chars")
        print(f"  < 50 chars: {sum(1 for s in sizes if s < 50)}")
        print(f"  < 120 chars: {sum(1 for s in sizes if s < 120)}")
        print(f"  >= 200 chars: {sum(1 for s in sizes if s >= 200)}")

    # Check for the PAL definition chunk
    print("\n" + "=" * 80)
    print("🔍 Looking for PAL definition chunk...")
    for i, m in enumerate(merged):
        if "PAL/TAL" in m.text and "letter from" in m.text.lower():
            print(f"  Found at chunk [{i}] ({len(m.text)} chars):")
            print(f"  {m.text[:300]}")
            break
    else:
        print("  ⚠️ PAL definition not found in merged output!")


if __name__ == "__main__":
    main()
