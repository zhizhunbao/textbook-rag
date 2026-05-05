"""Batch-update persona seed files with multiCollections."""
from __future__ import annotations

import re
from pathlib import Path

SEED_DIR = Path("payload-v2/src/seed/consulting-personas")

ALL_PROV = [
    "ca_prov_ontario", "ca_prov_bc", "ca_prov_alberta",
    "ca_prov_manitoba", "ca_prov_saskatchewan",
    "ca_prov_nova_scotia", "ca_prov_new_brunswick",
    "ca_prov_nwt", "ca_prov_quebec",
]

MAPPING: dict[str, list[str]] = {
    # ── Immigration ──
    "imm-family":        ["ca_federal"],
    "imm-pr-renewal":    ["ca_federal"],
    # ── Education ──
    "edu-school-planning": ["ca_federal", "ca_edu_algonquin"],
    "edu-visa-compliance": ["ca_federal"],
    "edu-work-permit":   ["ca_federal"],
    "edu-child-education": ["ca_federal"],
    "edu-academic-rules": ["ca_edu_algonquin"],
    # ── Settlement ──
    "life-rental":       ["ca_federal", "ca_real_estate"],
    "life-driving":      ["ca_federal"] + ALL_PROV,
    "life-utilities":    ["ca_federal"],
    "life-home-buying":  ["ca_federal", "ca_real_estate"],
    "life-car":          ["ca_federal"],
    # ── Healthcare ──
    "health-insurance":  ["ca_federal"] + ALL_PROV,
    "health-mental":     ["ca_federal"],
    "health-childcare":  ["ca_federal"],
    # ── Finance ──
    "fin-banking":       ["ca_federal"],
    "fin-tax":           ["ca_federal"],
    "fin-investment":    ["ca_federal"],
    "fin-cost-saving":   ["ca_federal", "ca_edu_algonquin"],
    # ── Career ──
    "career-resume":     ["ca_federal"],
    "career-internship": ["ca_federal", "ca_edu_algonquin"],
    "career-transition": ["ca_federal", "ca_edu_algonquin"],
    "career-volunteer":  ["ca_federal"],
    # ── Legal ──
    "legal-labor":       ["ca_federal"] + ALL_PROV,
    "legal-consumer":    ["ca_federal"],
    "legal-disputes":    ["ca_federal"],
    "legal-basics":      ["ca_federal"] + ALL_PROV,
    # ── Analysis ──
    "ecdev-analyst":     ["ca_ecdev", "ca_real_estate"],
}


def main() -> None:
    updated = 0
    for ts_file in sorted(SEED_DIR.rglob("*.ts")):
        if ts_file.name in ("types.ts", "index.ts"):
            continue
        text = ts_file.read_text(encoding="utf-8")

        m = re.search(r'slug: "([^"]+)"', text)
        if not m:
            continue
        slug = m.group(1)

        if slug not in MAPPING:
            continue

        colls = MAPPING[slug]

        if "multiCollections:" in text:
            print(f"  [SKIP] {slug} — already has multiCollections")
            continue

        # Format the array
        if len(colls) <= 3:
            arr = "[" + ", ".join(f'"{c}"' for c in colls) + "]"
            mc_line = f"  multiCollections: {arr},"
        else:
            items = "\n".join(f'    "{c}",' for c in colls)
            mc_line = f"  multiCollections: [\n{items}\n  ],"

        # Insert after chromaCollection line
        new_text = re.sub(
            r'(  chromaCollection: "[^"]+",)',
            r"\1\n" + mc_line,
            text,
            count=1,
        )

        if new_text != text:
            ts_file.write_text(new_text, encoding="utf-8")
            updated += 1
            print(f"  [OK] {slug} -> {len(colls)} collections")
        else:
            print(f"  [FAIL] {slug} — regex did not match")

    print(f"\nUpdated: {updated} files")


if __name__ == "__main__":
    main()
