"""Test: verify hybrid prefilter with vector-first merge."""
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.path.insert(0, ".")

from engine_v2.retrievers.book_filter import prefilter_book_ids

COLLECTION = "ca_federal"
EXPECTED = "crs-criteria"

queries = [
    ("Express Entry latest round minimum CRS score", "EE latest round"),
    ("CRS comprehensive ranking system factors maximum points", "CRS factors max"),
    ("CRS age points table CLB language points", "age+CLB points"),
    ("provincial nominee program 600 additional CRS points", "PNP 600 points"),
    ("CRS CLB level points first official language", "CLB level points"),
    ("CRS removing job offer points March 2025", "job offer removal"),
]

print("=" * 60)
print("Vector-first hybrid prefilter test")
print("=" * 60)

all_pass = True
for query, label in queries:
    result = prefilter_book_ids(query, COLLECTION, max_books=15)
    
    if result is None:
        print(f"\n  [{label}] -> None (FAIL)")
        all_pass = False
        continue
    
    crs_found = any(EXPECTED in bid for bid in result)
    status = "OK" if crs_found else "MISS"
    if not crs_found:
        all_pass = False
    
    print(f"\n  [{label}] {len(result)} books, crs-criteria: {status}")
    for i, bid in enumerate(result[:10]):
        parts = bid.split("/")
        short = "/".join(parts[-2:]) if len(parts) > 2 else bid
        flag = " <<<" if EXPECTED in bid else ""
        print(f"    [{i+1:2d}] .../{short}{flag}")
    if len(result) > 10:
        print(f"    ... +{len(result)-10} more")

print(f"\n{'='*60}")
print(f"Result: {'ALL PASS' if all_pass else 'SOME MISS'}")
print(f"{'='*60}")
