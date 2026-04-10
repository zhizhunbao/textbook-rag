"""Test _clean_latex_artifacts on actual OREB data."""
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
import json
from engine_v2.readers.mineru_reader import MinerUReader

# Test with known problematic strings
tests = [
    ('$4 . 1 \\%$ higher', '4.1% higher'),
    ('$\\$ 709,002$', '$709,002'),
    ('$36 . 2 \\%$ from Q4', '36.2% from Q4'),
    ('$2 , 851$ units', '2,851 units'),
    ('was $\\$ 633,000$ in August', 'was $633,000 in August'),
    ('a modest $1 . 5 \\%$ increase', 'a modest 1.5% increase'),
    ('$25 . 4 \\%$ decrease', '25.4% decrease'),
]

print("Unit tests:")
all_pass = True
for raw, expected in tests:
    result = MinerUReader._clean_latex_artifacts(raw)
    status = "✓" if result == expected else "✗"
    if result != expected:
        all_pass = False
    print(f"  {status} '{raw}' → '{result}'")
    if result != expected:
        print(f"    EXPECTED: '{expected}'")

# Test on real content_list.json data
print("\n" + "=" * 60)
print("Real data samples (before → after):")
print("=" * 60)

cl_path = "data/mineru_output/real_estate/oreb_marketupdate_hlp_august25/oreb_marketupdate_hlp_august25/auto/oreb_marketupdate_hlp_august25_content_list.json"
with open(cl_path, "r", encoding="utf-8") as f:
    content_list = json.load(f)

for item in content_list:
    raw = item.get("text", "").strip()
    if "$" in raw or "\\%" in raw:
        cleaned = MinerUReader._clean_latex_artifacts(raw)
        print(f"\n  BEFORE: {raw[:200]}")
        print(f"  AFTER:  {cleaned[:200]}")
