"""
Nuke and rebuild the SQLite database from MinerU output.

Steps:
  1. Delete data/textbook_rag.sqlite3.
  2. Create schema (books, book_assets, chapters, pages, chunks,
     source_locators, chunk_fts).
  3. Ingest every book from data/mineru_output/{category}/{book}/
     (content_list.json + middle.json for page sizes).
  4. Populate the FTS5 virtual table via INSERT trigger.

For vector embeddings, run build_vectors.py separately (GPU-accelerated).

Usage:
    uv run python scripts/rebuild_db.py
    uv run python scripts/rebuild_db.py --book ed_update_q1_2022  # one book
"""

from __future__ import annotations

import argparse
import json
import re
import sqlite3
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "data" / "textbook_rag.sqlite3"
MINERU_DIR = BASE_DIR / "data" / "mineru_output"

# Category → raw PDF source directory
SOURCE_DIRS: dict[str, Path] = {
    "textbooks":   BASE_DIR / "data" / "raw_pdfs" / "textbooks",
    "ecdev":       BASE_DIR / "data" / "raw_pdfs" / "ecdev",
    "real_estate": BASE_DIR / "data" / "raw_pdfs" / "real_estate",
}

# ── Book metadata registry (same as rebuild_topic_index.py) ──────────────────
BOOK_REGISTRY: dict[str, dict] = {
    "ramalho_fluent_python": {"title": "Fluent Python", "authors": "Luciano Ramalho"},
    "beazley_python_cookbook": {"title": "Python Cookbook", "authors": "David Beazley, Brian K. Jones"},
    "downey_think_python_2e": {"title": "Think Python", "authors": "Allen B. Downey"},
    "downey_how_to_think_like_cs": {"title": "How to Think Like a Computer Scientist", "authors": "Allen B. Downey"},
    "okken_python_testing_pytest": {"title": "Python Testing with pytest", "authors": "Brian Okken"},
    "percival_cosmic_python": {"title": "Architecture Patterns with Python", "authors": "Harry Percival, Bob Gregory"},
    "flanagan_js_definitive_guide": {"title": "JavaScript: The Definitive Guide", "authors": "David Flanagan"},
    "haverbeke_eloquent_javascript": {"title": "Eloquent JavaScript", "authors": "Marijn Haverbeke"},
    "simpson_ydkjs_up_going": {"title": "YDKJS: Up & Going", "authors": "Kyle Simpson"},
    "simpson_ydkjs_scope_closures": {"title": "YDKJS: Scope & Closures", "authors": "Kyle Simpson"},
    "simpson_ydkjs_this_object_prototypes": {"title": "YDKJS: this & Object Prototypes", "authors": "Kyle Simpson"},
    "simpson_ydkjs_types_grammar": {"title": "YDKJS: Types & Grammar", "authors": "Kyle Simpson"},
    "simpson_ydkjs_async_performance": {"title": "YDKJS: Async & Performance", "authors": "Kyle Simpson"},
    "simpson_ydkjs_es6_beyond": {"title": "YDKJS: ES6 & Beyond", "authors": "Kyle Simpson"},
    "basarat_typescript_deep_dive": {"title": "TypeScript Deep Dive", "authors": "Basarat Ali Syed"},
    "cormen_CLRS": {"title": "Introduction to Algorithms", "authors": "Cormen, Leiserson, Rivest, Stein"},
    "goodfellow_deep_learning": {"title": "Deep Learning", "authors": "Goodfellow, Bengio, Courville"},
    "bishop_prml": {"title": "Pattern Recognition and Machine Learning", "authors": "Christopher Bishop"},
    "hastie_esl": {"title": "The Elements of Statistical Learning", "authors": "Hastie, Tibshirani, Friedman"},
    "james_ISLR": {"title": "An Introduction to Statistical Learning", "authors": "James, Witten, Hastie, Tibshirani"},
    "kelleher_ml_fundamentals": {"title": "Fundamentals of Machine Learning", "authors": "John D. Kelleher"},
    "murphy_pml1": {"title": "Probabilistic Machine Learning: An Introduction", "authors": "Kevin P. Murphy"},
    "murphy_pml2": {"title": "Probabilistic Machine Learning: Advanced Topics", "authors": "Kevin P. Murphy"},
    "barber_brml": {"title": "Bayesian Reasoning and Machine Learning", "authors": "David Barber"},
    "shalev-shwartz_uml": {"title": "Understanding Machine Learning", "authors": "Shalev-Shwartz, Ben-David"},
    "deisenroth_mml": {"title": "Mathematics for Machine Learning", "authors": "Deisenroth, Faisal, Ong"},
    "boyd_convex_optimization": {"title": "Convex Optimization", "authors": "Stephen Boyd, Lieven Vandenberghe"},
    "grinstead_snell_probability": {"title": "Introduction to Probability", "authors": "Grinstead, Snell"},
    "downey_think_stats_2e": {"title": "Think Stats", "authors": "Allen B. Downey"},
    "mackay_information_theory": {"title": "Information Theory, Inference, and Learning Algorithms", "authors": "David J.C. MacKay"},
    "jurafsky_slp3": {"title": "Speech and Language Processing", "authors": "Dan Jurafsky, James H. Martin"},
    "eisenstein_nlp": {"title": "Introduction to Natural Language Processing", "authors": "Jacob Eisenstein"},
    "manning_intro_to_ir": {"title": "Introduction to Information Retrieval", "authors": "Manning, Raghavan, Schütze"},
    "szeliski_cv": {"title": "Computer Vision: Algorithms and Applications", "authors": "Richard Szeliski"},
    "sutton_barto_rl_intro": {"title": "Reinforcement Learning: An Introduction", "authors": "Richard Sutton, Andrew Barto"},
    "hamilton_grl": {"title": "Graph Representation Learning", "authors": "William L. Hamilton"},
    "krug_dont_make_me_think": {"title": "Don't Make Me Think", "authors": "Steve Krug"},
    "norman_design_everyday_things": {"title": "The Design of Everyday Things", "authors": "Don Norman"},
    "martin_clean_code": {"title": "Clean Code", "authors": "Robert C. Martin"},
    "martin_clean_architecture": {"title": "Clean Architecture", "authors": "Robert C. Martin"},
    "gof_design_patterns": {"title": "Design Patterns", "authors": "Gamma, Helm, Johnson, Vlissides"},
    "kleppmann_ddia": {"title": "Designing Data-Intensive Applications", "authors": "Martin Kleppmann"},
    "hunt_pragmatic_programmer": {"title": "The Pragmatic Programmer", "authors": "David Thomas, Andrew Hunt"},
    "fowler_refactoring": {"title": "Refactoring", "authors": "Martin Fowler"},
    "ejsmont_web_scalability": {"title": "Web Scalability for Startup Engineers", "authors": "Artur Ejsmont"},
    "fontaine_art_of_postgresql": {"title": "The Art of PostgreSQL", "authors": "Dimitri Fontaine"},
    "google_swe": {"title": "Software Engineering at Google", "authors": "Winters, Manshreck, Wright"},
    "chacon_pro_git": {"title": "Pro Git", "authors": "Scott Chacon, Ben Straub"},
    "google_sre": {"title": "Site Reliability Engineering", "authors": "Beyer, Jones, Petoff, Murphy"},
    "nygard_release_it": {"title": "Release It!", "authors": "Michael T. Nygard"},
    "seitz_black_hat_python": {"title": "Black Hat Python", "authors": "Justin Seitz, Tim Arnold"},
    "aumasson_serious_cryptography": {"title": "Serious Cryptography", "authors": "Jean-Philippe Aumasson"},
    "andriesse_practical_binary_analysis": {"title": "Practical Binary Analysis", "authors": "Dennis Andriesse"},
    "zalewski_tangled_web": {"title": "The Tangled Web", "authors": "Michal Zalewski"},
    "gourley_http_definitive_guide": {"title": "HTTP: The Definitive Guide", "authors": "Gourley, Totty"},
    "barrett_ssh_definitive_guide": {"title": "SSH, The Secure Shell: The Definitive Guide", "authors": "Barrett, Silverman, Byrnes"},
    "lubanovic_fastapi_modern_web": {"title": "FastAPI: Modern Python Web Development", "authors": "Bill Lubanovic"},
    "kreibich_using_sqlite": {"title": "Using SQLite", "authors": "Jay A. Kreibich"},
}

MAX_CHAPTERS_PER_BOOK = 80

# ── Schema DDL ───────────────────────────────────────────────────────────────

SCHEMA_SQL = """
PRAGMA journal_mode = WAL;
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS books (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    book_id         TEXT    NOT NULL UNIQUE,
    title           TEXT    NOT NULL,
    authors         TEXT    NOT NULL DEFAULT '',
    page_count      INTEGER NOT NULL DEFAULT 0,
    chapter_count   INTEGER NOT NULL DEFAULT 0,
    chunk_count     INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS book_assets (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    book_id         INTEGER NOT NULL REFERENCES books(id),
    asset_kind      TEXT    NOT NULL,
    path            TEXT    NOT NULL,
    url             TEXT,
    created_at      TEXT    NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS chapters (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    book_id         INTEGER NOT NULL REFERENCES books(id),
    chapter_key     TEXT    NOT NULL,
    title           TEXT    NOT NULL,
    content_type    TEXT    NOT NULL DEFAULT 'text'
);

CREATE TABLE IF NOT EXISTS pages (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    book_id         INTEGER NOT NULL REFERENCES books(id),
    page_number     INTEGER NOT NULL,
    width           REAL    NOT NULL DEFAULT 0,
    height          REAL    NOT NULL DEFAULT 0,
    created_at      TEXT    NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS chunks (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    chunk_id            TEXT    NOT NULL UNIQUE,
    book_id             INTEGER NOT NULL REFERENCES books(id),
    chapter_id          INTEGER REFERENCES chapters(id),
    primary_page_id     INTEGER REFERENCES pages(id),
    content_type        TEXT    NOT NULL DEFAULT 'text',
    text                TEXT    NOT NULL DEFAULT '',
    reading_order       INTEGER NOT NULL DEFAULT 0,
    chroma_document_id  TEXT
);

CREATE TABLE IF NOT EXISTS source_locators (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    chunk_id        INTEGER NOT NULL REFERENCES chunks(id),
    page_id         INTEGER NOT NULL REFERENCES pages(id),
    locator_kind    TEXT    NOT NULL DEFAULT 'bbox',
    x0              REAL    NOT NULL DEFAULT 0,
    y0              REAL    NOT NULL DEFAULT 0,
    x1              REAL    NOT NULL DEFAULT 0,
    y1              REAL    NOT NULL DEFAULT 0
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_chunks_book_id ON chunks(book_id);
CREATE INDEX IF NOT EXISTS idx_chunks_chapter_id ON chunks(chapter_id);
CREATE INDEX IF NOT EXISTS idx_chunks_primary_page ON chunks(primary_page_id);
CREATE INDEX IF NOT EXISTS idx_pages_book_page ON pages(book_id, page_number);
CREATE INDEX IF NOT EXISTS idx_chapters_book ON chapters(book_id);
CREATE INDEX IF NOT EXISTS idx_source_locators_chunk ON source_locators(chunk_id);
CREATE INDEX IF NOT EXISTS idx_source_locators_page ON source_locators(page_id);
CREATE INDEX IF NOT EXISTS idx_book_assets_book ON book_assets(book_id);

-- FTS5 virtual table
CREATE VIRTUAL TABLE IF NOT EXISTS chunk_fts USING fts5(
    text,
    content='chunks',
    content_rowid='id'
);

-- TOC entries extracted from source PDF bookmarks (populated by rebuild_toc.py)
CREATE TABLE IF NOT EXISTS toc_entries (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    book_id     INTEGER NOT NULL REFERENCES books(id),
    level       INTEGER NOT NULL DEFAULT 1,
    number      TEXT    NOT NULL DEFAULT '',
    title       TEXT    NOT NULL,
    pdf_page    INTEGER NOT NULL,
    sort_order  INTEGER NOT NULL DEFAULT 0
);

CREATE INDEX IF NOT EXISTS idx_toc_entries_book ON toc_entries(book_id);
CREATE INDEX IF NOT EXISTS idx_toc_entries_page ON toc_entries(book_id, pdf_page);

-- Triggers to keep FTS in sync
CREATE TRIGGER IF NOT EXISTS chunks_ai AFTER INSERT ON chunks BEGIN
    INSERT INTO chunk_fts(rowid, text) VALUES (new.id, new.text);
END;

CREATE TRIGGER IF NOT EXISTS chunks_ad AFTER DELETE ON chunks BEGIN
    INSERT INTO chunk_fts(chunk_fts, rowid, text) VALUES('delete', old.id, old.text);
END;

CREATE TRIGGER IF NOT EXISTS chunks_au AFTER UPDATE ON chunks BEGIN
    INSERT INTO chunk_fts(chunk_fts, rowid, text) VALUES('delete', old.id, old.text);
    INSERT INTO chunk_fts(rowid, text) VALUES (new.id, new.text);
END;
"""


# ── Chapter extraction (adapted from rebuild_topic_index.py) ─────────────────

def extract_chapters(content_list_path: Path) -> list[dict]:
    """Extract chapter headings from content_list.json."""
    try:
        with open(content_list_path, "r", encoding="utf-8") as f:
            content = json.load(f)
    except (json.JSONDecodeError, FileNotFoundError):
        return []

    chapters: list[dict] = []
    seen: set[str] = set()

    # Strategy 1: text_level=1 items that look like chapter headings
    for item in content:
        if item.get("type") != "text" or item.get("text_level") != 1:
            continue
        text = item.get("text", "").strip()
        if len(text) < 3 or len(text) > 300:
            continue

        ch_match = re.match(
            r"(?:chapter\s+)?(\d+)[\.:\s]+(.{3,120})",
            text, re.IGNORECASE,
        )
        if ch_match:
            ch_key = f"ch{ch_match.group(1).zfill(2)}"
            if ch_key not in seen:
                seen.add(ch_key)
                chapters.append({
                    "chapter_key": ch_key,
                    "title": ch_match.group(2).strip().rstrip(".,: "),
                })
            continue

        app_match = re.match(
            r"appendix\s+([A-Z])[\.:\s]*(.{3,120})",
            text, re.IGNORECASE,
        )
        if app_match:
            app_key = f"app{app_match.group(1)}"
            if app_key not in seen:
                seen.add(app_key)
                chapters.append({
                    "chapter_key": app_key,
                    "title": app_match.group(2).strip().rstrip(".,: "),
                })

    # Strategy 2: ToC blocks (fallback if strategy 1 yields few)
    if len(chapters) < 3:
        toc_chapters = _extract_from_toc(content)
        if len(toc_chapters) > len(chapters):
            chapters = toc_chapters

    return chapters[:MAX_CHAPTERS_PER_BOOK]


def _extract_from_toc(content: list[dict]) -> list[dict]:
    chapters: list[dict] = []
    seen: set[str] = set()
    for item in content:
        if item.get("type") != "text":
            continue
        text = item.get("text", "")
        if text.count("\n") < 3:
            continue
        for match in re.finditer(
            r"(?:chapter\s+)?(\d+)[\.:\s]+([^\n]{3,80}?)(?:\s*\.{2,}\s*\d+|\s*\d+\s*$|\s*$)",
            text, re.IGNORECASE | re.MULTILINE,
        ):
            ch_key = f"ch{match.group(1).zfill(2)}"
            title = match.group(2).strip().rstrip(".,: ")
            if ch_key not in seen and len(title) > 2:
                seen.add(ch_key)
                chapters.append({"chapter_key": ch_key, "title": title})
    return chapters[:MAX_CHAPTERS_PER_BOOK]


# ── Page sizes from middle.json ──────────────────────────────────────────────

def load_page_sizes(middle_json_path: Path) -> dict[int, tuple[float, float]]:
    """Return {page_idx: (width, height)} from *_middle.json."""
    try:
        with open(middle_json_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (json.JSONDecodeError, FileNotFoundError, OSError):
        return {}

    page_sizes: dict[int, tuple[float, float]] = {}

    if isinstance(data, dict) and "pdf_info" in data:
        pages = data["pdf_info"]
    elif isinstance(data, list):
        pages = data
    else:
        return {}

    for page in pages:
        idx = page.get("page_idx")
        size = page.get("page_size")
        if idx is not None and size and len(size) == 2:
            page_sizes[idx] = (float(size[0]), float(size[1]))

    return page_sizes


# ── Content ingestion ────────────────────────────────────────────────────────

def assign_chapter(page_idx: int, chapter_ranges: list[tuple[int, int]]) -> int | None:
    """Given a page index, return the chapter list-index it belongs to."""
    for i, (start, end) in enumerate(chapter_ranges):
        if start <= page_idx < end:
            return i
    return None


def _auto_registry_entry(book_dir_name: str, category: str) -> dict:
    """Generate a minimal registry entry for books not in BOOK_REGISTRY.

    Used for ecdev / real_estate where titles are derived from the filename.
    """
    title = book_dir_name.replace("_", " ").title()
    # Prettify common patterns: ed_update_q1_2022 → "Ed Update Q1 2022"
    return {"title": title, "authors": category, "category": category}


def ingest_book(
    conn: sqlite3.Connection,
    book_dir_name: str,
    category: str,
    chroma_docs: list[dict] | None,
) -> dict:
    """Ingest one book. Returns stats dict."""
    meta = BOOK_REGISTRY.get(book_dir_name) or _auto_registry_entry(book_dir_name, category)
    title = meta.get("title", book_dir_name.replace("_", " ").title())
    authors = meta.get("authors", "")

    auto_dir = MINERU_DIR / category / book_dir_name / book_dir_name / "auto"
    content_list_path = auto_dir / f"{book_dir_name}_content_list.json"
    middle_json_path = auto_dir / f"{book_dir_name}_middle.json"

    if not content_list_path.exists():
        return {"status": "skipped", "reason": "no content_list.json"}

    # Load content list
    with open(content_list_path, "r", encoding="utf-8") as f:
        content_list = json.load(f)

    # Load page sizes
    page_sizes = load_page_sizes(middle_json_path)

    # Determine total pages
    max_page_idx = max(
        (item.get("page_idx", 0) for item in content_list),
        default=0,
    )
    total_pages = max_page_idx + 1

    # Extract chapters
    chapters = extract_chapters(content_list_path)

    # Insert book
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO books (book_id, title, authors, page_count, chapter_count) "
        "VALUES (?, ?, ?, ?, ?)",
        (book_dir_name, title, authors, total_pages, len(chapters)),
    )
    book_pk = cur.lastrowid

    # Insert book assets (PDFs)
    _insert_book_assets(cur, book_pk, book_dir_name, category, auto_dir)

    # Insert pages
    page_pk_map: dict[int, int] = {}  # page_idx -> pages.id
    for pg_idx in range(total_pages):
        w, h = page_sizes.get(pg_idx, (0.0, 0.0))
        cur.execute(
            "INSERT INTO pages (book_id, page_number, width, height) VALUES (?, ?, ?, ?)",
            (book_pk, pg_idx, w, h),
        )
        page_pk_map[pg_idx] = cur.lastrowid

    # Insert chapters
    chapter_pk_map: dict[int, int] = {}  # list-index -> chapters.id
    for i, ch in enumerate(chapters):
        cur.execute(
            "INSERT INTO chapters (book_id, chapter_key, title) VALUES (?, ?, ?)",
            (book_pk, ch["chapter_key"], ch["title"]),
        )
        chapter_pk_map[i] = cur.lastrowid

    # Build chapter page ranges for assignment
    # For each chapter heading, find its first page_idx in content_list
    chapter_first_pages: list[int] = []
    for ch in chapters:
        ch_key = ch["chapter_key"]
        ch_num_match = re.match(r"ch(\d+)", ch_key)
        if ch_num_match:
            ch_num = ch_num_match.group(1)
            pattern = re.compile(
                rf"(?:chapter\s+)?{re.escape(ch_num)}\b",
                re.IGNORECASE,
            )
            for item in content_list:
                if (
                    item.get("type") == "text"
                    and item.get("text_level") == 1
                    and pattern.search(item.get("text", ""))
                ):
                    chapter_first_pages.append(item.get("page_idx", 0))
                    break
            else:
                chapter_first_pages.append(0)
        else:
            # appendix — search for it
            for item in content_list:
                if (
                    item.get("type") == "text"
                    and item.get("text_level") == 1
                    and ch["title"].lower() in item.get("text", "").lower()
                ):
                    chapter_first_pages.append(item.get("page_idx", 0))
                    break
            else:
                chapter_first_pages.append(0)

    # Create ranges: each chapter runs until the next chapter starts
    chapter_ranges: list[tuple[int, int]] = []
    for i, start in enumerate(chapter_first_pages):
        end = chapter_first_pages[i + 1] if i + 1 < len(chapter_first_pages) else total_pages
        chapter_ranges.append((start, end))

    # Insert chunks + source_locators
    chunk_count = 0
    reading_order = 0

    for item in content_list:
        item_type = item.get("type", "")
        if item_type == "discarded":
            continue

        text = item.get("text", "").strip()
        if not text and item_type not in ("image", "table"):
            continue

        # For tables, use table_body if no text
        if item_type == "table" and not text:
            text = item.get("table_body", "")
        # For images, use caption
        if item_type == "image" and not text:
            captions = item.get("image_caption", [])
            text = " ".join(captions) if captions else ""
        if not text:
            continue

        page_idx = item.get("page_idx", 0)
        bbox = item.get("bbox", [0, 0, 0, 0])
        if len(bbox) < 4:
            bbox = [0, 0, 0, 0]

        # content_list.json bbox uses a normalised 1000x1000 canvas.
        # Convert to PDF-point coordinates so they match pages.width/height.
        pw, ph = page_sizes.get(page_idx, (0.0, 0.0))
        if pw and ph:
            bbox = [bbox[0] / 1000 * pw, bbox[1] / 1000 * ph,
                    bbox[2] / 1000 * pw, bbox[3] / 1000 * ph]

        # Map content type
        content_type = item_type  # text, equation, table, image

        # Determine chapter
        ch_list_idx = assign_chapter(page_idx, chapter_ranges)
        chapter_pk = chapter_pk_map.get(ch_list_idx) if ch_list_idx is not None else None

        # Page PK
        page_pk = page_pk_map.get(page_idx)

        chunk_id = f"{book_dir_name}_{chunk_count:06d}"

        cur.execute(
            "INSERT INTO chunks "
            "(chunk_id, book_id, chapter_id, primary_page_id, content_type, text, reading_order) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (chunk_id, book_pk, chapter_pk, page_pk, content_type, text, reading_order),
        )
        chunk_pk = cur.lastrowid

        # Source locator
        if page_pk is not None:
            cur.execute(
                "INSERT INTO source_locators "
                "(chunk_id, page_id, locator_kind, x0, y0, x1, y1) "
                "VALUES (?, ?, ?, ?, ?, ?, ?)",
                (chunk_pk, page_pk, "bbox", bbox[0], bbox[1], bbox[2], bbox[3]),
            )

        reading_order += 1
        chunk_count += 1

    # Update book chunk_count
    cur.execute("UPDATE books SET chunk_count = ? WHERE id = ?", (chunk_count, book_pk))

    conn.commit()
    return {
        "status": "ok",
        "pages": total_pages,
        "chapters": len(chapters),
        "chunks": chunk_count,
        "category": category,
    }


def _insert_book_assets(
    cur: sqlite3.Cursor, book_pk: int, book_dir_name: str, category: str, auto_dir: Path
):
    """Register PDF and other assets in book_assets table."""
    # Source PDF — look in the category-specific raw PDF directory
    src_dir = SOURCE_DIRS.get(category, SOURCE_DIRS["textbooks"])
    src_pdf = src_dir / f"{book_dir_name}.pdf"
    if src_pdf.exists():
        cur.execute(
            "INSERT INTO book_assets (book_id, asset_kind, path) VALUES (?, ?, ?)",
            (book_pk, "source_pdf", str(src_pdf.relative_to(BASE_DIR))),
        )

    # Origin PDF from MinerU output
    origin_pdf = auto_dir / f"{book_dir_name}_origin.pdf"
    if origin_pdf.exists():
        cur.execute(
            "INSERT INTO book_assets (book_id, asset_kind, path) VALUES (?, ?, ?)",
            (book_pk, "origin_pdf", str(origin_pdf.relative_to(BASE_DIR))),
        )

    # Markdown
    md_file = auto_dir / f"{book_dir_name}.md"
    if md_file.exists():
        cur.execute(
            "INSERT INTO book_assets (book_id, asset_kind, path) VALUES (?, ?, ?)",
            (book_pk, "markdown", str(md_file.relative_to(BASE_DIR))),
        )

    # Content list JSON
    cl_file = auto_dir / f"{book_dir_name}_content_list.json"
    if cl_file.exists():
        cur.execute(
            "INSERT INTO book_assets (book_id, asset_kind, path) VALUES (?, ?, ?)",
            (book_pk, "content_list", str(cl_file.relative_to(BASE_DIR))),
        )



# ── Main ─────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Nuke & rebuild textbook_rag SQLite DB")
    parser.add_argument("--book", type=str, default=None,
                        help="Only process a specific book directory")
    args = parser.parse_args()

    # ── Step 1: Nuke ──
    print("💣 Nuking existing SQLite DB...")
    if DB_PATH.exists():
        DB_PATH.unlink()
        print(f"  Deleted {DB_PATH}")
    for suffix in ("-wal", "-shm"):
        p = DB_PATH.parent / (DB_PATH.name + suffix)
        if p.exists():
            p.unlink()

    # ── Step 2: Create schema ──
    print("\n📐 Creating schema...")
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    conn.executescript(SCHEMA_SQL)
    conn.commit()
    print("  ✅ Schema created")

    # ── Step 3: Ingest books — scan all category subdirectories ──
    print("\n📚 Ingesting books...")

    categories = ["textbooks", "ecdev", "real_estate"]
    total_stats = {"books": 0, "pages": 0, "chapters": 0, "chunks": 0}

    for category in categories:
        cat_dir = MINERU_DIR / category
        if not cat_dir.is_dir():
            continue

        for book_dir in sorted(cat_dir.iterdir()):
            if not book_dir.is_dir():
                continue
            dir_name = book_dir.name
            if dir_name.endswith(".processing"):
                continue
            if args.book and dir_name != args.book:
                continue

            result = ingest_book(conn, dir_name, category, None)
            if result["status"] == "ok":
                total_stats["books"] += 1
                total_stats["pages"] += result["pages"]
                total_stats["chapters"] += result["chapters"]
                total_stats["chunks"] += result["chunks"]
                print(f"  \u2713 [{category}] {dir_name}: {result['pages']} pg, "
                      f"{result['chapters']} ch, {result['chunks']} chunks")
            else:
                print(f"  \u2717 [{category}] {dir_name}: {result.get('reason', 'unknown')}")

    conn.close()

    # ── Summary ──
    size_kb = DB_PATH.stat().st_size / 1024 if DB_PATH.exists() else 0
    print(f"\n{'='*60}")
    print(f"✅ Rebuild complete! Run build_vectors.py next for semantic search.")
    print(f"   📖 {total_stats['books']} books")
    print(f"   📄 {total_stats['pages']} pages")
    print(f"   📑 {total_stats['chapters']} chapters")
    print(f"   🧩 {total_stats['chunks']} chunks")
    print(f"   💾 SQLite: {size_kb:.0f} KB ({DB_PATH})")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
