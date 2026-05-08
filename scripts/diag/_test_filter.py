"""Test new section merger on PAL content_list."""
import sys, json
sys.path.insert(0, ".")
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from engine_v2.chunking.section_merger import merge_content_items

# Load PAL content_list
import glob
pal_pattern = "data/mineru_output/federal-ircc/**/provincial-attestation-letter/**/auto/*_content_list.json"
files = glob.glob(pal_pattern, recursive=True)
if not files:
    print("PAL content_list not found")
    sys.exit(1)

with open(files[0], "r", encoding="utf-8") as f:
    items = json.load(f)

print(f"Raw items: {len(items)}")
print()

merged = merge_content_items(items)

print(f"\nMerged chunks: {len(merged)}")
print()

for i, m in enumerate(merged):
    label = f"[{i+1}]"
    chars = len(m.text)
    pages = sorted(set(b.page_idx for b in m.bboxes)) if m.bboxes else ["?"]
    marker = ""
    if "PAL/TAL) is" in m.text:
        marker = " << DEFINITION"
    elif chars < 100:
        marker = " (short)"
    print(f"{label:5s} {chars:4d} chars  pages={pages}  type={m.content_type}")
    print(f"      {m.text[:150].replace(chr(10), ' ')}{marker}")
    print()
