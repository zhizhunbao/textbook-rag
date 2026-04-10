"""MinerUReader — reads MinerU content_list.json into LlamaIndex Documents.

Aligns with llama_index.core.readers.base.BaseReader interface.
Each content item (text / table / image caption) becomes one Document
with rich metadata (page, bbox, content_type, chapter).
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Iterable

from llama_index.core.readers.base import BaseReader
from llama_index.core.schema import Document

from engine_v2.chunking import assign_chapter, build_chapter_ranges, extract_chapters

logger = logging.getLogger(__name__)


class MinerUReader(BaseReader):
    """Read MinerU auto-parsed output for one book into LlamaIndex Documents.

    Each item in content_list.json becomes a Document with metadata:
        - book_id, category, content_type, page_idx
        - bbox (normalised to PDF points)
        - chapter_key, reading_order
    """

    def __init__(self, mineru_dir: Path | str) -> None:
        self._mineru_dir = Path(mineru_dir)

    def lazy_load_data(  # type: ignore[override]
        self,
        book_dir_name: str,
        category: str = "textbook",
        **kwargs: Any,
    ) -> Iterable[Document]:
        """Yield one Document per content item.

        Args:
            book_dir_name: Directory name of the book under mineru_dir/category/
            category: textbook | ecdev | real_estate
        """
        auto_dir = (
            self._mineru_dir / category / book_dir_name / book_dir_name / "auto"
        )
        content_list_path = auto_dir / f"{book_dir_name}_content_list.json"
        middle_json_path = auto_dir / f"{book_dir_name}_middle.json"

        if not content_list_path.exists():
            logger.warning("content_list.json not found: %s", content_list_path)
            return

        with open(content_list_path, "r", encoding="utf-8") as f:
            content_list: list[dict] = json.load(f)

        page_sizes = self._load_page_sizes(middle_json_path)
        chapters = self._extract_chapters(content_list)
        chapter_ranges = self._build_chapter_ranges(content_list, chapters)

        reading_order = 0
        for item in content_list:
            item_type = item.get("type", "")
            if item_type == "discarded":
                continue

            text = self._extract_text(item, item_type)
            if not text:
                continue

            page_idx = item.get("page_idx", 0)
            bbox = self._normalise_bbox(
                item.get("bbox", [0, 0, 0, 0]),
                page_idx,
                page_sizes,
            )

            chapter_key = self._assign_chapter(page_idx, chapter_ranges)

            # Page dimensions for frontend bbox scaling (PDF points)
            pw, ph = page_sizes.get(page_idx, (0.0, 0.0))

            doc_id = f"{book_dir_name}_{reading_order:06d}"
            yield Document(
                doc_id=doc_id,
                text=text,
                metadata={
                    "book_id": book_dir_name,
                    "category": category,
                    "content_type": item_type,
                    "page_idx": page_idx,
                    "bbox": bbox,
                    "page_width": pw,
                    "page_height": ph,
                    "chapter_key": chapter_key,
                    "reading_order": reading_order,
                    "text_level": item.get("text_level"),
                },
                excluded_llm_metadata_keys=[
                    "bbox", "reading_order", "page_width", "page_height",
                ],
            )
            reading_order += 1

        logger.info(
            "MinerUReader: loaded %d documents from %s", reading_order, book_dir_name
        )

    # ------------------------------------------------------------------
    # Internal helpers — text extraction and bbox normalisation
    # ------------------------------------------------------------------

    @staticmethod
    def _clean_latex_artifacts(text: str) -> str:
        """Strip LaTeX math-mode artifacts from MinerU PDF text.

        MinerU wraps numbers/percentages/currency in LaTeX math delimiters:
            $4 . 1 \\%$   →  4.1%
            $\\$ 709,002$  →  $709,002
            $36 . 2 \\%$  →  36.2%
            $2 , 851$     →  2,851

        Also fixes:
            spaced decimals:  1 . 5  →  1.5
            spaced commas:    709 , 002  →  709,002
            dangling $:       leftover dollar signs from math mode
            \\% outside math: \\%  →  %
        """
        import re

        if "$" not in text and "\\%" not in text:
            return text  # fast path: nothing to clean

        # Step 1: Handle $\$ NNN$ pattern (currency)  →  $NNN
        # e.g. $\$ 709,002$  →  $709,002
        text = re.sub(
            r'\$\s*\\?\$\s*([0-9][0-9, .]*)\$',
            lambda m: "$" + m.group(1).replace(" ", ""),
            text,
        )

        # Step 2: Handle $N . N \%$ pattern (percentages)  →  N.N%
        # e.g. $4 . 1 \%$  →  4.1%
        text = re.sub(
            r'\$\s*([0-9][0-9 ,.]*)\\?%\s*\$',
            lambda m: m.group(1).replace(" ", "") + "%",
            text,
        )

        # Step 3: Handle remaining $number$ patterns (plain numbers in math mode)
        # e.g. $2 , 851$  →  2,851
        text = re.sub(
            r'\$\s*([0-9][0-9 ,.]*[0-9])\s*\$',
            lambda m: m.group(1).replace(" ", ""),
            text,
        )

        # Step 4: Fix spaced decimals outside math mode: 1 . 5 → 1.5
        text = re.sub(r'(\d)\s+\.\s+(\d)', r'\1.\2', text)

        # Step 5: Fix spaced commas in numbers: 709 , 002 → 709,002
        text = re.sub(r'(\d)\s+,\s+(\d)', r'\1,\2', text)

        # Step 6: Fix standalone \% → %
        text = text.replace("\\%", "%")

        # Step 7: Clean up any remaining single $ that aren't currency
        # (don't remove $ followed by a digit — that's likely currency like $633,000)
        # Remove isolated $ not adjacent to digits
        text = re.sub(r'\$(?!\d)', '', text)

        # Step 8: Fix smart quote / encoding artifacts
        text = text.replace("\u0092", "'").replace("\u0093", "\u201c").replace("\u0094", "\u201d")

        return text

    @staticmethod
    def _extract_text(item: dict, item_type: str) -> str:
        """Extract text content from a MinerU content item."""
        text = item.get("text", "").strip()
        if not text and item_type == "table":
            text = item.get("table_body", "")
        if not text and item_type == "image":
            captions = item.get("image_caption", [])
            text = " ".join(captions) if captions else ""
        text = text.strip()
        # Clean LaTeX artifacts from MinerU output
        if text:
            text = MinerUReader._clean_latex_artifacts(text)
        return text

    @staticmethod
    def _load_page_sizes(path: Path) -> dict[int, tuple[float, float]]:
        """Load page dimensions from middle.json."""
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except (json.JSONDecodeError, FileNotFoundError, OSError):
            return {}

        pages = data.get("pdf_info", data) if isinstance(data, dict) else data
        if not isinstance(pages, list):
            return {}

        result: dict[int, tuple[float, float]] = {}
        for page in pages:
            idx = page.get("page_idx")
            size = page.get("page_size")
            if idx is not None and size and len(size) == 2:
                result[idx] = (float(size[0]), float(size[1]))
        return result

    @staticmethod
    def _normalise_bbox(
        raw_bbox: list,
        page_idx: int,
        page_sizes: dict[int, tuple[float, float]],
    ) -> list[float]:
        """Convert normalised 1000x1000 canvas → PDF points."""
        if len(raw_bbox) < 4:
            return [0.0, 0.0, 0.0, 0.0]
        pw, ph = page_sizes.get(page_idx, (0.0, 0.0))
        if pw and ph:
            return [
                raw_bbox[0] / 1000 * pw,
                raw_bbox[1] / 1000 * ph,
                raw_bbox[2] / 1000 * pw,
                raw_bbox[3] / 1000 * ph,
            ]
        return [float(v) for v in raw_bbox[:4]]

    # ------------------------------------------------------------------
    # Chapter structure — delegates to chunking/ module
    # ------------------------------------------------------------------

    @staticmethod
    def _extract_chapters(content_list: list[dict]) -> list[dict]:
        """Extract chapter headings (delegates to chunking.extract_chapters)."""
        return extract_chapters(content_list)

    @staticmethod
    def _build_chapter_ranges(
        content_list: list[dict],
        chapters: list[dict],
    ) -> list[tuple[str, int, int]]:
        """Build chapter page ranges (delegates to chunking.build_chapter_ranges)."""
        return build_chapter_ranges(content_list, chapters)

    @staticmethod
    def _assign_chapter(
        page_idx: int,
        ranges: list[tuple[str, int, int]],
    ) -> str | None:
        """Assign chapter key to page (delegates to chunking.assign_chapter)."""
        return assign_chapter(page_idx, ranges)

