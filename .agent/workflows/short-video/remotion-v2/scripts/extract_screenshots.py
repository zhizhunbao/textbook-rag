"""
extract_screenshots.py — 从 MinerU 输出中提取 PDF 页面截图 + bbox 元数据

坐标系统:
  - middle.json 的 bbox 已经是 PDF points, 和 PyMuPDF 1:1 对应, 无需换算
  - content_list.json 的 bbox 是 1000-canvas 归一化, 需要 /1000 * page_size 换算
  - 本脚本优先使用 middle.json (PDF points), 回退到 content_list.json

用法:
    python scripts/extract_screenshots.py \
        --storyline path/to/storyline.md \
        --mineru-root path/to/mineru_output \
        --output path/to/output/pages

功能:
    1. 解析 storyline.md 中的引用 (URL + 引用文本)
    2. 通过 URL → MinerU 输出目录映射
    3. 在 middle.json 中搜索引用文本 → 定位 bbox (PDF points) + page_idx
    4. 基于 section heading 做 section 级裁切 (而非单 bbox)
    5. 用 PyMuPDF 渲染裁切区域为高清 PNG (PyMuPDF 仅用于渲染)
    6. 将 bbox/pageSize 回写到 storyline.md (storyline 是唯一数据源)
"""
import argparse
import json
import re
import sys
from pathlib import Path
from difflib import SequenceMatcher
from urllib.parse import urlparse

try:
    import fitz  # PyMuPDF
except ImportError:
    print("ERROR: pymupdf required: pip install pymupdf")
    sys.exit(1)

# Windows console encoding fix
import io, os
if os.name == 'nt':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')


# ── MinerU source category mapping ──
DOMAIN_TO_CATEGORY = {
    "www.canada.ca": "federal-ircc",
    "canada.ca": "federal-ircc",
}

# ── Render params ──
DEFAULT_PADDING = 25.0   # PDF points
MIN_CROP_HEIGHT = 120.0  # PDF points


# ================================================================
# Storyline parsing
# ================================================================
def parse_storyline_citations(md_text: str) -> list[dict]:
    """Parse all slide citations from storyline.md.

    Returns: [{ slide_index, citation_index, text, url, slide_title }]
    """
    citations = []
    text = md_text.replace("\r\n", "\n").strip()

    # Truncate citation summary section
    summary_idx = text.find("## 📋")
    if summary_idx > -1:
        text = text[:summary_idx]

    # Split by slide separator
    pages = re.split(r"^---$", text, flags=re.MULTILINE)

    slide_index = -1
    for page in pages:
        page = page.strip()
        if not page:
            continue

        type_match = re.search(r"^## \[(\w+)\]\s*(.*)", page, re.MULTILINE)
        if not type_match:
            continue

        slide_index += 1
        slide_type = type_match.group(1)
        slide_title = type_match.group(2).strip()

        citation_pattern = re.compile(
            r'\*\*引用\s*(\d+)\*\*:\s*"([^"]+)"\s*\n\*\*来源\*\*:\s*(https?://\S+)(?:\s*\n\*\*本地\*\*:\s*(\S+))?',
            re.MULTILINE
        )

        for m in citation_pattern.finditer(page):
            # Extract existing screenshot filename from ![截图](pages/xxx.png)
            png_hint = None
            after_cite = page[m.end():]
            img_match = re.search(r'!\[截图\]\(pages/([^)]+\.png)\)', after_cite[:300])
            if img_match:
                png_hint = img_match.group(1)

            citations.append({
                "slide_index": slide_index,
                "citation_index": int(m.group(1)),
                "text": m.group(2).strip(),
                "url": m.group(3).strip(),
                "local_path": m.group(4).strip() if m.group(4) else None,
                "slide_title": slide_title,
                "slide_type": slide_type,
                "png_hint": png_hint,
            })

    return citations


# ================================================================
# MinerU directory resolution
# ================================================================
def url_to_mineru_dir(url: str, mineru_root: Path) -> Path | None:
    """Map citation URL to MinerU output directory."""
    parsed = urlparse(url)
    domain = parsed.hostname or ""

    category = None
    for d, cat in DOMAIN_TO_CATEGORY.items():
        if domain == d or domain.endswith("." + d):
            category = cat
            break

    if not category:
        return None

    path = parsed.path.strip("/")
    if path.endswith(".html"):
        path = path[:-5]

    candidate = mineru_root / category / path
    return candidate if candidate.exists() else None


def find_middle_json(mineru_dir: Path) -> Path | None:
    """Find middle.json in MinerU output directory (bbox = PDF points)."""
    dir_name = mineru_dir.name
    standard = mineru_dir / dir_name / "auto" / f"{dir_name}_middle.json"
    if standard.exists():
        return standard

    results = list(mineru_dir.rglob("*_middle.json"))
    return results[0] if results else None


def find_content_list(mineru_dir: Path) -> Path | None:
    """Find content_list.json in MinerU output directory (bbox = 1000-canvas)."""
    dir_name = mineru_dir.name
    standard = mineru_dir / dir_name / "auto" / f"{dir_name}_content_list.json"
    if standard.exists():
        return standard

    results = list(mineru_dir.rglob("*_content_list.json"))
    return results[0] if results else None


def find_origin_pdf(mineru_dir: Path) -> Path | None:
    """Find _origin.pdf in MinerU output directory."""
    dir_name = mineru_dir.name
    standard = mineru_dir / dir_name / "auto" / f"{dir_name}_origin.pdf"
    if standard.exists():
        return standard

    results = list(mineru_dir.rglob("*_origin.pdf"))
    return results[0] if results else None


# ================================================================
# MinerU layout analysis (middle.json — PDF points, no conversion)
# ================================================================
def load_page_blocks(middle_data: list | dict, page_idx: int) -> list[dict]:
    """Extract layout blocks for a page from middle.json.

    middle.json bbox is already in PDF points — maps 1:1 to PyMuPDF.

    Returns:
      [{"type": "title"|"text"|"table"|"image",
        "bbox": [x0, y0, x1, y1],  # PDF points
        "text": "...",
        "is_heading": bool}, ...]
    """
    pages = middle_data if isinstance(middle_data, list) else middle_data.get("pdf_info", middle_data)
    if not isinstance(pages, list) or page_idx >= len(pages):
        return []

    page_data = pages[page_idx]
    raw_blocks = page_data.get("preproc_blocks", page_data.get("para_blocks", []))

    blocks = []
    for rb in raw_blocks:
        btype = rb.get("type", "text")
        bbox = rb.get("bbox", [0, 0, 0, 0])

        if btype == "discarded":
            continue

        # Extract text from lines -> spans -> content
        text_parts = []
        for line in rb.get("lines", []):
            for span in line.get("spans", []):
                content = span.get("content", "")
                if content:
                    text_parts.append(content)
        text = " ".join(text_parts)

        blocks.append({
            "type": btype,
            "bbox": bbox,
            "text": text,
            "is_heading": btype == "title",
        })

    return blocks


def load_content_list_layout(content_list: list[dict], page_idx: int,
                              page_w: float, page_h: float) -> list[dict]:
    """Fallback: extract layout from content_list.json with /1000 conversion.

    content_list.json bbox is in 1000-canvas normalized coords:
        pdf_coord = content_list_coord / 1000 * page_size
    """
    blocks = []
    for item in content_list:
        if item.get("page_idx") != page_idx or item.get("type") == "discarded":
            continue

        raw_bbox = item.get("bbox", [0, 0, 0, 0])
        # Convert from 1000-canvas to PDF points
        bbox = [
            raw_bbox[0] / 1000 * page_w,
            raw_bbox[1] / 1000 * page_h,
            raw_bbox[2] / 1000 * page_w,
            raw_bbox[3] / 1000 * page_h,
        ]

        text = item.get("text", "")
        if not text and item.get("type") == "table":
            body = item.get("table_body", "")
            text = re.sub(r"<[^>]+>", " ", body).strip()

        blocks.append({
            "type": item.get("type", "text"),
            "bbox": bbox,
            "text": text,
            "is_heading": item.get("type") == "title" or bool(item.get("text_level")),
        })

    return blocks


# ================================================================
# Text matching
# ================================================================
def normalize_text(text: str) -> str:
    """Normalize text for fuzzy matching (quotes, dashes, LaTeX artifacts)."""
    text = text.lower()
    text = text.replace("\u2019", "'").replace("\u2018", "'").replace("`", "'")
    text = text.replace("\u201c", '"').replace("\u201d", '"')
    text = text.replace("\u2013", "-").replace("\u2014", "-")
    text = text.replace("\ufffd", "?")
    # Clean MinerU LaTeX artifacts
    text = text.replace("$", "")
    text = text.replace("\\%", "%").replace("\\_", "_")
    text = re.sub(r'(\d)\s+(\d)', r'\1\2', text)
    text = re.sub(r'(\d)\s*\.\s*(\d)', r'\1.\2', text)
    text = re.sub(r'(\d)\s+%', r'\1%', text)
    text = re.sub(r'\s+', ' ', text)
    return text.strip()


def extract_key_terms(cite_text: str) -> set:
    """Extract key terms (acronyms + number combos) from citation text.

    Used to validate that the matched page actually contains the
    referenced data (e.g., 'CLB7', 'TEER0', '134,980').
    """
    terms = set()
    # Acronym+number combos: CLB7, TEER0, NOC2021
    for m in re.findall(r'[A-Za-z]+\s*\d+', cite_text):
        terms.add(re.sub(r'\s+', '', m).lower())
    # Standalone acronyms: CLB, TEER, RCIP, AIP
    for w in re.findall(r'\b[A-Z]{2,}\b', cite_text):
        terms.add(w.lower())
    # Large numbers: 134,980 → 134980
    for n in re.findall(r'\d{1,3}(?:,\d{3})+', cite_text):
        terms.add(n.replace(',', ''))
    return {t for t in terms if len(t) >= 3}


def match_citation_in_blocks(blocks: list[dict], cite_text: str,
                              threshold: float = 0.35) -> list[dict]:
    """Match citation text against layout blocks.

    Returns matched blocks sorted by score (best first).
    """
    search_key = normalize_text(cite_text[:80])
    matches = []

    for block in blocks:
        block_text = normalize_text(block.get("text", ""))
        if not block_text:
            continue

        # Substring match (most reliable)
        is_sub = False
        if search_key[:40] in block_text:
            is_sub = True
        elif block_text in search_key and len(block_text) >= 35:
            is_sub = True

        if is_sub:
            matches.append({**block, "match_score": 0.95, "match_type": "substring"})
            continue

        # Fuzzy match
        ratio = SequenceMatcher(None, search_key[:80], block_text[:80]).ratio()
        if ratio >= threshold:
            matches.append({**block, "match_score": ratio, "match_type": "fuzzy"})

    matches.sort(key=lambda m: (
        m["match_score"],
        len(m.get("text", "")),
        m.get("type") == "table",
    ), reverse=True)

    return matches


# ================================================================
# Header / Nav detection (web page chrome removal)
# ================================================================
def detect_header_bottom(blocks: list, page_height: float) -> float:
    """Detect the bottom edge of web page header/nav/breadcrumb area.

    Returns the y-coordinate (in PDF points) below which real content
    starts.  Returns 0.0 if no header is detected (e.g. PDF documents).

    Detection targets canada.ca page chrome:
      - Source bar, Government of Canada logo, Search box
      - MENU nav bar, IRCC sign in
      - Breadcrumb (Canada.ca > Immigration and citizenship > ...)
    """
    NAV_KEYWORDS = {
        "menu", "search", "français", "sign in", "ircc",
        "canada.ca", "skip to main", "skip to",
    }
    header_bottom = 0.0
    found_any = False

    sorted_blocks = sorted(blocks, key=lambda b: b.get("bbox", [0, 0, 0, 0])[1])

    for b in sorted_blocks:
        text = b.get("text", "").lower().strip()
        bbox = b.get("bbox", [0, 0, 0, 0])
        bbox_top = bbox[1]

        # Only scan top 30% of page
        if bbox_top > page_height * 0.30:
            break

        is_nav = False
        # Nav keywords
        if any(kw in text for kw in NAV_KEYWORDS):
            is_nav = True
        # Breadcrumb (multiple > separators)
        if text.count(">") >= 2 or text.count("\u203a") >= 2:
            is_nav = True
        # Source/URL bar
        if text.startswith("source:") or text.startswith("http"):
            is_nav = True
        # Government of Canada header
        if "government" in text and "canada" in text:
            is_nav = True
        if "gouvernement" in text and "canada" in text:
            is_nav = True

        if is_nav:
            header_bottom = bbox[3]  # bottom of this block
            found_any = True
        elif found_any and b.get("is_heading"):
            # First real heading after nav → header ends
            break

    return header_bottom


# ================================================================
# Section bounds (section-level cropping)
# ================================================================
def find_section_bounds(
    blocks: list[dict],
    matched_blocks: list[dict],
    page_height: float = 792.0,
) -> tuple[float, float]:
    """Calculate section bounds around matched blocks (PDF points).

    Strategy:
    1. Union of matched block bboxes = citation area
    2. Expand UP to nearest title heading = section start
    3. Expand DOWN to next heading or large gap = section end
    """
    if not matched_blocks:
        if blocks:
            return (
                min(b["bbox"][1] for b in blocks),
                max(b["bbox"][3] for b in blocks),
            )
        return (0, page_height)

    cite_top = min(b["bbox"][1] for b in matched_blocks)
    cite_bottom = max(b["bbox"][3] for b in matched_blocks)

    # Expand UP: find nearest heading above
    section_top = cite_top
    headings_above = [
        b for b in blocks
        if b["is_heading"] and b["bbox"][3] <= cite_top
    ]
    if headings_above:
        nearest = max(headings_above, key=lambda x: x["bbox"][1])
        section_top = nearest["bbox"][1]

    # Expand DOWN: include continuation paragraphs until heading or gap
    section_bottom = cite_bottom
    below = sorted(
        [b for b in blocks if b["bbox"][1] >= cite_bottom],
        key=lambda x: x["bbox"][1]
    )
    for b in below:
        if b["is_heading"]:
            break
        gap = b["bbox"][1] - section_bottom
        if gap > 60:
            break
        section_bottom = b["bbox"][3]

    return (section_top, section_bottom)


# ================================================================
# Smart bbox expansion — use MinerU's block bboxes directly
# ================================================================
EXPAND_PADDING = 8.0   # breathing room around highlight (PDF points)
GAP_THRESHOLD = 40.0   # max vertical gap (pt) to still consider "same group"


def _union_blocks_bbox(block_list: list[dict]) -> list[float]:
    """Compute tight union bbox from a list of blocks' actual bboxes."""
    x1 = min(b["bbox"][0] for b in block_list)
    y1 = min(b["bbox"][1] for b in block_list)
    x2 = max(b["bbox"][2] for b in block_list)
    y2 = max(b["bbox"][3] for b in block_list)
    return [x1, y1, x2, y2]


def _pad_and_clamp(bbox: list[float], page_w: float, page_h: float,
                   padding: float = EXPAND_PADDING) -> list[float]:
    """Add padding to bbox and clamp to page boundaries."""
    return [
        max(0.0, bbox[0] - padding),
        max(0.0, bbox[1] - padding),
        min(page_w, bbox[2] + padding),
        min(page_h, bbox[3] + padding),
    ]


def expand_bbox_to_container(
    blocks: list[dict],
    matched_block: dict,
    page_w: float,
    page_h: float,
    min_area_ratio: float = 0.015,
) -> list[float]:
    """Expand a matched block's bbox using MinerU's own block segmentation.

    MinerU already segments the page into precise blocks (title, text,
    list, index, table, image …) with accurate bboxes.  Instead of
    re-detecting patterns, we simply:

    1. Find the matched block's position in the block list.
    2. Grow outward (up & down) to include adjacent blocks whose
       vertical gap to the current group is < GAP_THRESHOLD.
    3. Union all included blocks' actual bboxes + padding.

    This naturally covers tables (title + text + index rows), sections
    (heading + body paragraphs), and list groups.

    Returns: [x1, y1, x2, y2] in PDF points (with padding).
    """
    bbox = list(matched_block.get("bbox", [0, 0, 0, 0]))
    bx1, by1, bx2, by2 = bbox
    bbox_area = (bx2 - bx1) * (by2 - by1)
    page_area = page_w * page_h

    if page_area <= 0 or not blocks:
        return _pad_and_clamp(bbox, page_w, page_h)

    # ── Locate matched block in the ordered block list ──
    sorted_blocks = sorted(blocks, key=lambda b: b["bbox"][1])
    matched_idx = None
    for i, b in enumerate(sorted_blocks):
        if b["bbox"] == matched_block.get("bbox") and b.get("text") == matched_block.get("text"):
            matched_idx = i
            break
    if matched_idx is None:
        for i, b in enumerate(sorted_blocks):
            bb = b["bbox"]
            if (abs(bb[0] - bx1) < 5 and abs(bb[1] - by1) < 5
                    and abs(bb[2] - bx2) < 5 and abs(bb[3] - by2) < 5):
                matched_idx = i
                break
    if matched_idx is None:
        return _pad_and_clamp(bbox, page_w, page_h)

    # ── Strategy 1: Table-row detection ──
    # If multiple headings share the same left-x AND they have content
    # blocks beside them (same y, not below), they are row headers in a
    # table layout → include ALL rows as one group.
    title_blocks_idx = [i for i, b in enumerate(sorted_blocks) if b.get("is_heading")]
    if len(title_blocks_idx) >= 2:
        # Group titles by left-edge x alignment
        x_groups: dict[int, list[int]] = {}  # representative_x -> [indices]
        for ti in title_blocks_idx:
            tx = int(sorted_blocks[ti]["bbox"][0])
            placed = False
            for gx in x_groups:
                if abs(tx - gx) < 15:
                    x_groups[gx].append(ti)
                    placed = True
                    break
            if not placed:
                x_groups[tx] = [ti]

        # Find if matched block belongs to any aligned title group
        for gx, group_indices in x_groups.items():
            if len(group_indices) < 2:
                continue

            # ── Verify table layout: at least one title must have a
            # non-title block BESIDE it (y-overlap ≥ 50%), not below. ──
            is_table_layout = False
            for ti in group_indices:
                tb = sorted_blocks[ti]["bbox"]
                th = tb[3] - tb[1]
                for j, sb in enumerate(sorted_blocks):
                    if j == ti or sb.get("is_heading"):
                        continue
                    sb_bbox = sb["bbox"]
                    # y-overlap between title and candidate block
                    overlap_top = max(tb[1], sb_bbox[1])
                    overlap_bot = min(tb[3], sb_bbox[3])
                    overlap = max(0, overlap_bot - overlap_top)
                    if th > 0 and overlap / th >= 0.5:
                        is_table_layout = True
                        break
                if is_table_layout:
                    break

            if not is_table_layout:
                continue

            # Check if matched block is within the y-range of this title group
            group_top = min(sorted_blocks[gi]["bbox"][1] for gi in group_indices)
            group_bottom = max(sorted_blocks[gi]["bbox"][3] for gi in group_indices)
            if by1 >= group_top - 10 and by2 <= group_bottom + 400:
                # Table detected! Include all blocks from first row to after last row
                table_start = min(group_indices)
                table_end = max(group_indices)
                # Extend table_end to include content blocks after last title
                for i in range(table_end + 1, len(sorted_blocks)):
                    if sorted_blocks[i].get("is_heading"):
                        # Another heading not in our group → stop
                        if i not in group_indices:
                            break
                    table_end = i

                table_blocks = [sorted_blocks[i] for i in range(table_start, table_end + 1)]
                if table_blocks:
                    # Post-expansion: include trailing blocks close to table bottom
                    union_bottom = max(b["bbox"][3] for b in table_blocks)
                    for i in range(table_end + 1, len(sorted_blocks)):
                        blk = sorted_blocks[i]
                        gap = blk["bbox"][1] - union_bottom
                        if gap < GAP_THRESHOLD and not blk.get("is_heading"):
                            table_blocks.append(blk)
                            union_bottom = max(union_bottom, blk["bbox"][3])
                            table_end = i
                        elif gap >= GAP_THRESHOLD:
                            break

                    union = _union_blocks_bbox(table_blocks)
                    expanded = _pad_and_clamp(union, page_w, page_h)
                    expanded_area = (expanded[2] - expanded[0]) * (expanded[3] - expanded[1])
                    if expanded_area > bbox_area * 1.2:
                        print(f"   EXPAND [table]: "
                              f"[{bx1:.0f},{by1:.0f},{bx2:.0f},{by2:.0f}] -> "
                              f"[{expanded[0]:.0f},{expanded[1]:.0f},{expanded[2]:.0f},{expanded[3]:.0f}] "
                              f"({len(table_blocks)} MinerU blocks, {len(group_indices)} title rows)")
                        return expanded

    # ── Strategy 2: Section boundaries using headings as dividers ──
    # Section = from nearest heading above (inclusive) to nearest heading
    # below (exclusive).  This prevents expansion across sections.

    # Helper: check if heading A is a "parent" of heading B (immediately
    # above with a small gap, suggesting a title → subtitle relationship).
    def _is_parent_heading(parent_idx: int, child_idx: int) -> bool:
        if parent_idx < 0 or parent_idx >= len(sorted_blocks):
            return False
        parent = sorted_blocks[parent_idx]
        child = sorted_blocks[child_idx]
        if not parent.get("is_heading"):
            return False
        gap = child["bbox"][1] - parent["bbox"][3]
        return 0 <= gap < GAP_THRESHOLD

    if sorted_blocks[matched_idx].get("is_heading"):
        # ── Matched block IS a heading ──
        section_start = matched_idx

        # Look upward: if there's a parent heading immediately above
        # (e.g. "Overview of proposed changes" above "Simplifying…"),
        # include it so the red box covers the parent title too.
        for i in range(matched_idx - 1, -1, -1):
            if _is_parent_heading(i, section_start):
                section_start = i
            else:
                break  # stop at first non-parent

        # Look downward: include all content AND sub-headings until we
        # hit a heading that is NOT a sub-heading of our matched heading.
        # A sub-heading is one that follows with gap < GAP_THRESHOLD and
        # has no non-heading content separating it from the previous heading.
        section_end = len(sorted_blocks) - 1
        for i in range(matched_idx + 1, len(sorted_blocks)):
            if sorted_blocks[i].get("is_heading"):
                # Check if this heading is a sub-heading (close gap from
                # the previous block) or a sibling section heading
                prev_bottom = sorted_blocks[i - 1]["bbox"][3]
                gap = sorted_blocks[i]["bbox"][1] - prev_bottom
                if gap >= GAP_THRESHOLD:
                    section_end = i - 1
                    break
                # Sub-heading → continue including it
            # Non-heading content → continue
        # But if the last included block is a heading with content after it,
        # extend to include that trailing content
        if section_end < len(sorted_blocks) - 1:
            for i in range(section_end + 1, len(sorted_blocks)):
                if sorted_blocks[i].get("is_heading"):
                    break
                section_end = i
    else:
        # ── Matched block is NOT a heading ──
        # Upper bound: walk up to find nearest heading (section start)
        section_start = 0
        for i in range(matched_idx - 1, -1, -1):
            if sorted_blocks[i].get("is_heading"):
                section_start = i
                break

        # Also include parent heading above section_start if present
        for i in range(section_start - 1, -1, -1):
            if _is_parent_heading(i, section_start):
                section_start = i
            else:
                break

        # Lower bound: walk down to find nearest heading after matched (section end)
        section_end = len(sorted_blocks) - 1
        for i in range(matched_idx + 1, len(sorted_blocks)):
            if sorted_blocks[i].get("is_heading"):
                section_end = i - 1  # stop before next heading
                break

    # Collect all blocks in this section
    section_blocks = [sorted_blocks[i] for i in range(section_start, section_end + 1)]

    if len(section_blocks) <= 1:
        return _pad_and_clamp(bbox, page_w, page_h)

    # ── Post-processing: include side-panel blocks ──
    # Multi-column layouts (e.g., canada.ca) have side panels (Status,
    # Processing time) that float to the right of the main content.
    # These blocks are NOT in the y-sorted contiguous range because
    # other headings (like "Sections") may appear at a lower y between
    # the main column blocks and the right-side panel blocks.
    # Fix: find all non-heading blocks OUTSIDE the section range whose
    # y-range overlaps with the section's y-range, and include them.
    section_top_y = min(b["bbox"][1] for b in section_blocks)
    section_bot_y = max(b["bbox"][3] for b in section_blocks)
    section_indices = set(range(section_start, section_end + 1))
    side_panel_added = False

    for i, b in enumerate(sorted_blocks):
        if i in section_indices:
            continue  # already included
        if b.get("is_heading"):
            continue  # don't pull in other section headings

        bb = b["bbox"]
        # Check vertical overlap with section
        overlap_top = max(section_top_y, bb[1])
        overlap_bot = min(section_bot_y, bb[3])
        if overlap_bot - overlap_top > 0:
            # This block vertically overlaps with our section
            section_blocks.append(b)
            section_indices.add(i)
            side_panel_added = True

    # If side-panel blocks were added, also pull in blocks that are
    # vertically connected to them (e.g., Processing time below Status)
    if side_panel_added:
        expanded_bot = max(b["bbox"][3] for b in section_blocks)
        for i, b in enumerate(sorted_blocks):
            if i in section_indices or b.get("is_heading"):
                continue
            bb = b["bbox"]
            gap = bb[1] - expanded_bot
            if 0 <= gap < GAP_THRESHOLD:
                section_blocks.append(b)
                section_indices.add(i)
                expanded_bot = max(expanded_bot, bb[3])

    union = _union_blocks_bbox(section_blocks)
    expanded = _pad_and_clamp(union, page_w, page_h)
    expanded_area = (expanded[2] - expanded[0]) * (expanded[3] - expanded[1])

    if expanded_area > bbox_area * 1.2:
        print(f"   EXPAND [section]: "
              f"[{bx1:.0f},{by1:.0f},{bx2:.0f},{by2:.0f}] -> "
              f"[{expanded[0]:.0f},{expanded[1]:.0f},{expanded[2]:.0f},{expanded[3]:.0f}] "
              f"({len(section_blocks)} MinerU blocks, idx {section_start}-{section_end})")
        return expanded

    return _pad_and_clamp(bbox, page_w, page_h)



# ================================================================
# Content-aware crop (orphan removal + whitespace trim)
# ================================================================
def compute_content_crop(blocks: list[dict], page_h: float,
                          orphan_y_max: float = 70.0,
                          whitespace_min_ratio: float = 0.30,
                          padding: float = 15.0) -> tuple[float, float]:
    """Compute vertical crop to remove orphan cross-page fragments and bottom whitespace.

    Orphan: a table/image at the very top (y < orphan_y_max) followed by a heading
    or a large gap — likely a leftover from the previous page.

    Bottom whitespace: if the gap between last content block and page bottom
    exceeds whitespace_min_ratio of page height, crop it.

    Returns: (crop_y_top, crop_y_bottom) in PDF points.
             (0, page_h) means no crop needed.
    """
    if not blocks:
        return (0.0, page_h)

    sorted_blocks = sorted(blocks, key=lambda b: b["bbox"][1])

    # ── Detect orphan block at page top ──
    crop_y_top = 0.0
    first = sorted_blocks[0]
    if (first["type"] in ("table", "image") and
            first["bbox"][1] < orphan_y_max and
            len(sorted_blocks) > 1):
        second = sorted_blocks[1]
        # Next block is a heading or has a visible gap → orphan
        if second.get("is_heading") or second["bbox"][1] - first["bbox"][3] > 20:
            crop_y_top = max(0.0, second["bbox"][1] - padding)

    # ── Detect excessive bottom whitespace ──
    last = sorted_blocks[-1]
    content_bottom = last["bbox"][3]
    gap_ratio = (page_h - content_bottom) / page_h

    crop_y_bottom = page_h
    if gap_ratio > whitespace_min_ratio:
        crop_y_bottom = min(page_h, content_bottom + padding)

    return (crop_y_top, crop_y_bottom)


# ================================================================
# PyMuPDF rendering (only used for rendering, not layout analysis)
# ================================================================
def render_pdf_page(pdf_path: Path, page_idx: int, output_path: Path,
                    dpi: int = 250,
                    crop_y_top: float = 0.0,
                    crop_y_bottom: float = 0.0,
                    highlight_bbox: list[float] | None = None) -> tuple[int, int, float]:
    """Render PDF page as PNG with optional vertical content crop and highlight box.

    If highlight_bbox is provided as [x1, y1, x2, y2] in PDF points,
    a red rectangle is drawn on the page before rendering.

    Returns: (width, height, crop_y_offset)
      crop_y_offset = how much was cropped from the top (for coordinate adjustment).
    """
    doc = fitz.open(str(pdf_path))
    if page_idx >= len(doc):
        doc.close()
        return (0, 0, 0.0)

    page = doc[page_idx]
    p_w, p_h = float(page.rect.width), float(page.rect.height)

    if crop_y_bottom <= 0:
        crop_y_bottom = p_h

    needs_crop = crop_y_top > 0 or crop_y_bottom < p_h

    # Draw highlight rectangle if bbox provided
    if highlight_bbox:
        x1, y1, x2, y2 = highlight_bbox
        rect = fitz.Rect(x1, y1, x2, y2)
        # Draw red rectangle outline (no fill)
        shape = page.new_shape()
        shape.draw_rect(rect)
        shape.finish(color=(1, 0, 0), width=3.0, fill=None)
        shape.commit()

    zoom = dpi / 72.0
    mat = fitz.Matrix(zoom, zoom)

    if needs_crop:
        crop_rect = fitz.Rect(0, crop_y_top, p_w, crop_y_bottom)
        pix = page.get_pixmap(matrix=mat, clip=crop_rect)
    else:
        pix = page.get_pixmap(matrix=mat)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    pix.save(str(output_path))

    w, h = pix.width, pix.height
    doc.close()
    return (w, h, crop_y_top if needs_crop else 0.0)


def render_section_crop(pdf_path: Path, page_idx: int,
                         section_top: float, section_bottom: float,
                         output_path: Path, dpi: int = 300,
                         padding: float = DEFAULT_PADDING) -> tuple[int, int, list[float]]:
    """Render section region as PNG (section-level crop with heading).

    Uses section_top/section_bottom (PDF points) from find_section_bounds().
    Returns: (width, height, [crop_w_pts, crop_h_pts, crop_y_top, crop_y_bottom])
    """
    doc = fitz.open(str(pdf_path))
    if page_idx >= len(doc):
        doc.close()
        return (0, 0, [])

    page = doc[page_idx]
    p_w, p_h = float(page.rect.width), float(page.rect.height)

    # Add padding, clamp to page bounds
    crop_y1 = max(0.0, section_top - padding)
    crop_y2 = min(p_h, section_bottom + padding * 0.6)

    # Minimum height
    if crop_y2 - crop_y1 < MIN_CROP_HEIGHT:
        center = (crop_y1 + crop_y2) / 2
        crop_y1 = max(0.0, center - MIN_CROP_HEIGHT / 2)
        crop_y2 = min(p_h, center + MIN_CROP_HEIGHT / 2)

    # Full page width, section height
    crop_rect = fitz.Rect(0, crop_y1, p_w, crop_y2)

    zoom = dpi / 72.0
    mat = fitz.Matrix(zoom, zoom)
    pix = page.get_pixmap(matrix=mat, clip=crop_rect)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    pix.save(str(output_path))

    w, h = pix.width, pix.height
    doc.close()

    crop_w = p_w
    crop_h = crop_y2 - crop_y1
    return (w, h, [crop_w, crop_h, crop_y1, crop_y2])


def render_pdf_crop(pdf_path: Path, page_idx: int, bbox: list[float],
                     output_path: Path, dpi: int = 300,
                     padding: float = 25.0) -> tuple[int, int, list[float]]:
    """Render single bbox crop as PNG (legacy fallback).

    Returns: (width, height, [crop_w, crop_h, rel_x1, rel_y1, rel_x2, rel_y2])
    """
    doc = fitz.open(str(pdf_path))
    if page_idx >= len(doc):
        doc.close()
        return (0, 0, [])

    page = doc[page_idx]
    p_w, p_h = float(page.rect.width), float(page.rect.height)

    x1, y1, x2, y2 = bbox
    x1, x2 = sorted([float(x1), float(x2)])
    y1, y2 = sorted([float(y1), float(y2)])

    x1 = max(0.0, min(p_w, x1))
    x2 = max(0.0, min(p_w, x2))
    y1 = max(0.0, min(p_h, y1))
    y2 = max(0.0, min(p_h, y2))

    crop_x1 = max(0.0, x1 - padding)
    crop_y1 = max(0.0, y1 - padding)
    crop_x2 = min(p_w, x2 + padding)
    crop_y2 = min(p_h, y2 + padding)

    if crop_x1 >= crop_x2:
        crop_x1, crop_x2 = 0.0, p_w
    if crop_y1 >= crop_y2:
        crop_y1, crop_y2 = 0.0, p_h

    crop_rect = fitz.Rect(crop_x1, crop_y1, crop_x2, crop_y2)
    zoom = dpi / 72.0
    mat = fitz.Matrix(zoom, zoom)
    pix = page.get_pixmap(matrix=mat, clip=crop_rect)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    pix.save(str(output_path))

    w, h = pix.width, pix.height
    doc.close()

    crop_w = crop_x2 - crop_x1
    crop_h = crop_y2 - crop_y1
    rel_x1 = x1 - crop_x1
    rel_y1 = y1 - crop_y1
    rel_x2 = x2 - crop_x1
    rel_y2 = y2 - crop_y1

    return (w, h, [crop_w, crop_h, rel_x1, rel_y1, rel_x2, rel_y2])


def get_page_size_points(pdf_path: Path, page_idx: int) -> tuple[float, float]:
    """Get PDF page dimensions in points."""
    doc = fitz.open(str(pdf_path))
    if page_idx >= len(doc):
        doc.close()
        return (612, 792)
    page = doc[page_idx]
    rect = page.rect
    doc.close()
    return (rect.width, rect.height)


# ================================================================
# Storyline bbox writeback
# ================================================================
def update_storyline_bbox(storyline_path: Path, zoom_targets: list[dict]) -> None:
    """Write bbox/pageSize metadata back into storyline.md.

    For each zoom_target, finds the corresponding ![截图](xxx.png) line
    and inserts/updates **bbox** and **pageSize** fields right after it.

    This eliminates the need for document_map.json — storyline.md
    becomes the single source of truth for both content and layout data.
    """
    md_text = storyline_path.read_text(encoding="utf-8")
    lines = md_text.split("\n")

    # Build lookup: image_path → zoom_target data
    # zoom_targets are ordered by slide_index, so for duplicate images
    # (same screenshot used by multiple slides), we track by slide order.
    # Group targets by slide_index for ordered matching.
    targets_by_slide: dict[int, list[dict]] = {}
    for zt in zoom_targets:
        si = zt["slide_index"]
        if si not in targets_by_slide:
            targets_by_slide[si] = []
        targets_by_slide[si].append(zt)

    # Walk through storyline lines, tracking slide_index
    new_lines = []
    slide_index = -1
    cite_counter_per_slide: dict[int, int] = {}
    i = 0
    while i < len(lines):
        line = lines[i]

        # Detect slide boundary: ## [type] title
        if re.match(r"^## \[\w+\]\s+", line):
            slide_index += 1
            cite_counter_per_slide[slide_index] = 0

        # Detect ![截图](xxx.png) line
        img_match = re.match(r"^!\[截图\]\(([^)]+)\)", line)
        if img_match and slide_index >= 0:
            # Output the ![截图] line
            new_lines.append(line)
            i += 1

            # Skip any existing **bbox** / **pageSize** lines right after
            while i < len(lines) and re.match(
                r"^\*\*(bbox|pageSize)\*\*:", lines[i]
            ):
                i += 1  # skip old generated lines

            # Find the matching zoom_target for this citation
            cite_idx = cite_counter_per_slide.get(slide_index, 0)
            cite_counter_per_slide[slide_index] = cite_idx + 1

            targets = targets_by_slide.get(slide_index, [])
            if cite_idx < len(targets):
                zt = targets[cite_idx]
                bbox = zt.get("bbox", [0, 0, 0, 0])
                page_size = zt.get("page_size", [960, 792])
                # Format as clean integer lists
                bbox_str = f"[{bbox[0]:.0f}, {bbox[1]:.0f}, {bbox[2]:.0f}, {bbox[3]:.0f}]"
                ps_str = f"[{page_size[0]:.0f}, {page_size[1]:.0f}]"
                new_lines.append(f"**bbox**: {bbox_str}")
                new_lines.append(f"**pageSize**: {ps_str}")
            continue
        else:
            new_lines.append(line)
            i += 1

    # Write back
    result = "\n".join(new_lines)
    storyline_path.write_text(result, encoding="utf-8")
    print(f"\n📝 Storyline updated with bbox/pageSize: {storyline_path}")


# ================================================================
# Main
# ================================================================
def main():
    parser = argparse.ArgumentParser(
        description="MinerU middle.json layout + PyMuPDF rendering"
    )
    parser.add_argument("--storyline", required=True, help="storyline.md path")
    parser.add_argument("--mineru-root", required=True, help="MinerU output root directory")
    parser.add_argument("--output", required=True, help="Output directory (PNG files)")
    parser.add_argument("--dpi", type=int, default=250, help="PNG render DPI (default 250)")
    args = parser.parse_args()

    storyline_path = Path(args.storyline)
    mineru_root = Path(args.mineru_root)
    output_dir = Path(args.output)

    if not storyline_path.exists():
        print(f"ERROR: storyline not found: {storyline_path}")
        sys.exit(1)

    if not mineru_root.exists():
        print(f"ERROR: MinerU root not found: {mineru_root}")
        sys.exit(1)

    output_dir.mkdir(parents=True, exist_ok=True)

    # ── 1. Parse storyline citations ──
    print(f"Parsing storyline: {storyline_path}")
    md_text = storyline_path.read_text(encoding="utf-8")
    citations = parse_storyline_citations(md_text)
    print(f"   Found {len(citations)} citations")

    if not citations:
        print("WARNING: No citations found, skipping screenshot extraction")
        return

    # ── 2. Parse narration line counts per slide ──
    slide_narration_counts = {}
    pages_raw = re.split(r"^---$", md_text.replace("\r\n", "\n"), flags=re.MULTILINE)
    slide_idx = -1
    for page_raw in pages_raw:
        page_raw = page_raw.strip()
        if not page_raw:
            continue
        if not re.search(r"^## \[\w+\]", page_raw, re.MULTILINE):
            continue
        slide_idx += 1
        narr_match = re.search(
            r'\*\*(?:台词|Narration)\*\*:\s*\n([\s\S]*?)(?=\n\*\*|$)',
            page_raw
        )
        if narr_match:
            lines = [l.strip() for l in narr_match.group(1).split('\n') if l.strip()]
            slide_narration_counts[slide_idx] = len(lines)
        else:
            slide_narration_counts[slide_idx] = 0

    # ── 3. Process each citation ──
    pages_data = {}
    zoom_targets = []

    for cit in citations:
        url = cit["url"]
        slide_index = cit["slide_index"]
        cite_text = cit["text"]
        local_path = cit.get("local_path")

        print(f"\n--- Citation {cit['citation_index']} (slide {slide_index}): "
              f"{cite_text[:50]}...")
        print(f"   URL: {url}")

        # 3a. Resolve MinerU directory
        mineru_dir = None
        if local_path:
            candidate = mineru_root / local_path
            if candidate.exists():
                mineru_dir = candidate
            else:
                print(f"   WARN: local path not found: {candidate}, trying URL")

        if not mineru_dir:
            mineru_dir = url_to_mineru_dir(url, mineru_root)
            if not mineru_dir:
                print(f"   WARN: Cannot map to MinerU directory, skipping")
                continue

        # 3b. Find PDF
        pdf_path = find_origin_pdf(mineru_dir)
        if not pdf_path:
            print(f"   WARN: _origin.pdf not found, skipping")
            continue

        # 3c. Load layout: prefer middle.json (PDF points), fallback content_list
        middle_path = find_middle_json(mineru_dir)
        cl_path = find_content_list(mineru_dir)

        middle_data = None
        content_list = None
        layout_source = "none"

        if middle_path:
            middle_data = json.loads(middle_path.read_text("utf-8"))
            layout_source = "middle.json"
            print(f"   Layout: middle.json (PDF points, no conversion)")
        elif cl_path:
            content_list = json.loads(cl_path.read_text("utf-8"))
            layout_source = "content_list.json"
            print(f"   Layout: content_list.json (/1000 conversion)")
        else:
            print(f"   WARN: No layout file found, using full page")

        # 3d. Search citation in layout blocks
        page_w, page_h = get_page_size_points(pdf_path, 0)  # will update per page

        if middle_data:
            # middle.json: try all pages to find match
            pages_list = middle_data if isinstance(middle_data, list) else middle_data.get("pdf_info", middle_data)
            best_match = None
            best_page_idx = 0
            best_effective_score = 0.0
            key_terms = extract_key_terms(cite_text)

            for pidx in range(len(pages_list) if isinstance(pages_list, list) else 0):
                blocks = load_page_blocks(middle_data, pidx)
                matches = match_citation_in_blocks(blocks, cite_text)
                if matches:
                    # Keyword validation: penalise pages missing key terms
                    page_full_text = " ".join(
                        b.get("text", "") for b in blocks
                    ).lower()
                    if key_terms:
                        terms_found = sum(
                            1 for t in key_terms if t in page_full_text
                        )
                        coverage = terms_found / len(key_terms)
                    else:
                        coverage = 1.0

                    # Blend match score with keyword coverage
                    effective_score = matches[0]["match_score"] * (
                        0.5 + 0.5 * coverage
                    )

                    if effective_score > best_effective_score:
                        best_match = matches[0]
                        best_page_idx = pidx
                        best_effective_score = effective_score

            if best_match:
                page_idx = best_page_idx
                page_w, page_h = get_page_size_points(pdf_path, page_idx)
                blocks = load_page_blocks(middle_data, page_idx)
                matched_blocks = [best_match]
                section_top, section_bottom = find_section_bounds(blocks, matched_blocks, page_h)
                content_type = best_match.get("type", "text")
                bbox_raw = best_match.get("bbox", [0, 0, 0, 0])
                print(f"   MATCH: type={content_type}, page={page_idx}, "
                      f"score={best_match['match_score']:.2f} ({best_match['match_type']})")
                print(f"   Section: y={section_top:.0f}..{section_bottom:.0f} "
                      f"({section_bottom - section_top:.0f}pt)")

                # Smart bbox expansion: detect table/list/section containers
                bbox_raw = expand_bbox_to_container(
                    blocks, best_match, page_w, page_h
                )
            else:
                print(f"   WARN: No match in middle.json, skipping")
                continue

        elif content_list:
            # content_list.json fallback (with /1000 conversion)
            from difflib import SequenceMatcher as _SM
            search_clean = normalize_text(cite_text[:80])
            best_match = None
            best_page_idx = 0

            for entry in content_list:
                if entry.get("type") == "discarded":
                    continue
                entry_text = entry.get("text", "")
                if not entry_text and entry.get("type") == "table":
                    body = entry.get("table_body", "")
                    entry_text = re.sub(r"<[^>]+>", " ", body).strip()
                if not entry_text:
                    continue

                entry_clean = normalize_text(entry_text)
                if search_clean[:40] in entry_clean:
                    score = 0.95
                elif _SM(None, search_clean[:80], entry_clean[:80]).ratio() >= 0.35:
                    score = _SM(None, search_clean[:80], entry_clean[:80]).ratio()
                else:
                    continue

                if not best_match or score > best_match.get("_score", 0):
                    best_match = {**entry, "_score": score}
                    best_page_idx = entry.get("page_idx", 0)

            if best_match:
                page_idx = best_page_idx
                page_w, page_h = get_page_size_points(pdf_path, page_idx)
                # Convert bbox from 1000-canvas to PDF points
                raw_bbox = best_match.get("bbox", [0, 0, 0, 0])
                bbox_raw = [
                    raw_bbox[0] / 1000 * page_w,
                    raw_bbox[1] / 1000 * page_h,
                    raw_bbox[2] / 1000 * page_w,
                    raw_bbox[3] / 1000 * page_h,
                ]
                blocks = load_content_list_layout(content_list, page_idx, page_w, page_h)
                matched_blocks = match_citation_in_blocks(blocks, cite_text)
                section_top, section_bottom = find_section_bounds(
                    blocks, matched_blocks or [{"bbox": bbox_raw}], page_h
                )
                content_type = best_match.get("type", "text")
                print(f"   MATCH (content_list): type={content_type}, page={page_idx}")
                print(f"   Section: y={section_top:.0f}..{section_bottom:.0f}")
            else:
                print(f"   WARN: No match in content_list, skipping")
                continue
        else:
            # No layout at all
            print(f"   WARN: No layout data, skipping")
            continue

        # 3e. Render per-citation PNG with highlight box baked in
        parsed = urlparse(url)
        url_parts = parsed.path.strip("/").split("/")
        page_key = f"{'_'.join(url_parts[-2:])}_p{page_idx}"

        # Use storyline-specified filename if available (stable across runs),
        # otherwise generate one based on page_key + citation_index
        if cit.get("png_hint"):
            png_filename = cit["png_hint"]
            cite_key = png_filename.replace(".png", "")
        else:
            cite_key = f"{page_key}_c{cit['citation_index']}"
            png_filename = f"{cite_key}.png"

        png_path = output_dir / png_filename

        # Content-aware crop: remove orphan cross-page fragments + bottom whitespace
        crop_top, crop_bot = compute_content_crop(blocks, page_h)
        img_w, img_h, crop_offset = render_pdf_page(
            pdf_path, page_idx, png_path, dpi=args.dpi,
            crop_y_top=crop_top, crop_y_bottom=crop_bot,
            highlight_bbox=bbox_raw,
        )

        cropped_h = crop_bot - crop_top
        if crop_top > 0 or crop_bot < page_h:
            print(f"   CROP: y={crop_top:.0f}..{crop_bot:.0f} "
                  f"(removed {page_h - cropped_h:.0f}pt orphan/whitespace)")

        pages_data[cite_key] = {
            "image": f"pages/{png_filename}",
            "source_url": url,
            "source_label": _extract_source_label(url),
            "page_size_pts": [page_w, cropped_h],
            "image_size_px": [img_w, img_h],
            "crop_y_offset": crop_offset,
        }

        print(f"   Output: {png_filename} (with highlight)")

        # 3f. Calculate trigger_line
        total_lines = slide_narration_counts.get(slide_index, 1)
        slide_citations = [c for c in citations if c["slide_index"] == slide_index]
        cite_order = next(
            (i for i, c in enumerate(slide_citations) if c is cit), 0
        )
        total_cites = len(slide_citations)

        if total_cites == 1:
            trigger_line = 2
        else:
            trigger_line = max(1, 1 + int(cite_order * (total_lines - 1) / max(1, total_cites)))

        # Adjust coordinates for content-aware crop offset
        crop_y_off = pages_data.get(cite_key, {}).get("crop_y_offset", 0.0)
        adjusted_bbox = [
            bbox_raw[0], bbox_raw[1] - crop_y_off,
            bbox_raw[2], bbox_raw[3] - crop_y_off,
        ]
        adjusted_section = [
            section_top - crop_y_off,
            section_bottom - crop_y_off,
        ]
        adjusted_page_size = pages_data.get(cite_key, {}).get(
            "page_size_pts", [page_w, page_h]
        )

        zoom_targets.append({
            "slide_index": slide_index,
            "page_key": cite_key,
            "image": f"pages/{png_filename}",
            "bbox": adjusted_bbox,
            "section_bounds": adjusted_section,
            "page_size": adjusted_page_size,
            "label_zh": cit.get("slide_title", ""),
            "trigger_line": trigger_line,
            "citation_text": cite_text[:60],
            "content_type": content_type,
            "source_label": _extract_source_label(url),
            "layout_source": layout_source,
        })

    # ── 4. Write bbox/pageSize back into storyline.md ──
    update_storyline_bbox(storyline_path, zoom_targets)

    print(f"\n{'='*60}")
    print(f"Done:")
    print(f"   Page PNGs: {len(pages_data)}")
    print(f"   Zoom targets: {len(zoom_targets)}")
    print(f"   Storyline updated: {storyline_path}")
    print(f"{'='*60}")


def _extract_source_label(url: str) -> str:
    """Extract short source label from URL."""
    parsed = urlparse(url)
    path = parsed.path.strip("/")

    if "canada.ca" in (parsed.hostname or ""):
        if "immigration-refugees-citizenship" in path:
            return "IRCC"
        if "transparency" in path or "consultations" in path:
            return "IRCC Public Consultation"
        if "news" in path:
            return "Government of Canada News"
        return "Government of Canada"

    return parsed.hostname or "Source"


if __name__ == "__main__":
    main()
