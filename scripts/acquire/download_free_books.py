"""
Download free & open-access textbooks that have direct PDF links.
For books only available as HTML/GitHub repos, print instructions.

Usage:
    uv run python scripts/download_free_books.py
"""

import os
import sys
import urllib.request
import urllib.error
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "raw_pdfs" / "textbooks"

# Books with direct PDF download links
DIRECT_PDF_BOOKS = [
    {
        "name": "Pro Git (2nd ed)",
        "author": "Scott Chacon & Ben Straub",
        "filename": "chacon_pro_git.pdf",
        "dest_dir": BASE_DIR / "devops" / "_sources",
        "url": "https://github.com/progit/progit2/releases/download/2.1.436/progit.pdf",
    },
]

# Books available online but not as direct PDF
ONLINE_ONLY_BOOKS = [
    {
        "name": "TypeScript Deep Dive",
        "author": "Basarat Ali Syed",
        "filename": "basarat_typescript_deep_dive.pdf",
        "dest_dir": BASE_DIR / "webdev" / "_sources",
        "instructions": [
            "GitHub repo: https://github.com/basarat/typescript-book",
            "Go to Actions tab -> latest build -> download 'artifacts' (PDF/EPUB)",
            "Or read online: https://basarat.gitbook.io/typescript/",
        ],
    },
    {
        "name": "Software Engineering at Google",
        "author": "Winters, Manshreck, Wright",
        "filename": "google_swe.pdf",
        "dest_dir": BASE_DIR / "se" / "_sources",
        "instructions": [
            "Free HTML: https://abseil.io/resources/swe-book",
            "PDF generator: https://github.com/aspect-build/swe-book-pdf",
            "Clone that repo and run it to generate PDF locally",
        ],
    },
    {
        "name": "Architecture Patterns with Python",
        "author": "Harry Percival & Bob Gregory",
        "filename": "percival_cosmic_python.pdf",
        "dest_dir": BASE_DIR / "se" / "_sources",
        "instructions": [
            "Free online: https://www.cosmicpython.com/",
            "Source: https://github.com/cosmicpython/book",
            "O'Reilly also offers free access with registration",
        ],
    },
    {
        "name": "Site Reliability Engineering",
        "author": "Google",
        "filename": "google_sre.pdf",
        "dest_dir": BASE_DIR / "devops" / "_sources",
        "instructions": [
            "Free online: https://sre.google/sre-book/table-of-contents/",
            "PDF generator: https://github.com/captn3m0/google-sre-ebook",
            "Clone that repo and run it to generate EPUB/PDF",
        ],
    },
]


def download_pdf(url: str, dest: Path) -> bool:
    """Download a PDF file with progress indication."""
    dest.parent.mkdir(parents=True, exist_ok=True)

    if dest.exists():
        size_mb = round(dest.stat().st_size / (1024 * 1024), 1)
        print(f"  Already exists: {dest.name} ({size_mb} MB)")
        return True

    print(f"  Downloading from: {url}")
    print(f"  Saving to: {dest}")

    try:
        req = urllib.request.Request(url, headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
        })
        with urllib.request.urlopen(req, timeout=120) as resp:
            total = resp.headers.get("Content-Length")
            total = int(total) if total else None
            data = bytearray()
            block_size = 65536
            downloaded = 0

            while True:
                chunk = resp.read(block_size)
                if not chunk:
                    break
                data.extend(chunk)
                downloaded += len(chunk)
                if total:
                    pct = round(downloaded / total * 100)
                    mb = round(downloaded / (1024 * 1024), 1)
                    total_mb = round(total / (1024 * 1024), 1)
                    sys.stdout.write(
                        f"\r  Progress: {mb}/{total_mb} MB ({pct}%)"
                    )
                    sys.stdout.flush()

            print()  # newline after progress

            # Validate PDF
            if len(data) < 10000:
                print(f"  ERROR: File too small ({len(data)} bytes)")
                return False
            if data[:4] != b"%PDF":
                print("  ERROR: Not a valid PDF file")
                return False

            with open(dest, "wb") as f:
                f.write(data)

            size_mb = round(len(data) / (1024 * 1024), 1)
            print(f"  OK: {dest.name} ({size_mb} MB)")
            return True

    except urllib.error.HTTPError as e:
        print(f"  ERROR: HTTP {e.code} - {e.reason}")
        return False
    except Exception as e:
        print(f"  ERROR: {e}")
        return False


def main():
    print("=" * 60)
    print("  Free Textbook Downloader")
    print("=" * 60)

    # Ensure directories
    for book in DIRECT_PDF_BOOKS + ONLINE_ONLY_BOOKS:
        book["dest_dir"].mkdir(parents=True, exist_ok=True)

    # Download direct PDFs
    success = 0
    failed = 0

    print("\n--- Direct PDF Downloads ---\n")
    for book in DIRECT_PDF_BOOKS:
        dest = book["dest_dir"] / book["filename"]
        print(f"[DOWNLOAD] {book['name']} ({book['author']})")
        if download_pdf(book["url"], dest):
            success += 1
        else:
            failed += 1
        print()

    # Print instructions for online-only books
    print("\n--- Online-Only Books (manual steps needed) ---\n")
    for book in ONLINE_ONLY_BOOKS:
        dest = book["dest_dir"] / book["filename"]
        if dest.exists():
            size_mb = round(dest.stat().st_size / (1024 * 1024), 1)
            print(f"[EXISTS] {book['name']} ({size_mb} MB)")
        else:
            print(f"[MANUAL] {book['name']} ({book['author']})")
            print(f"  Save as: {dest}")
            for instr in book["instructions"]:
                print(f"    -> {instr}")
        print()

    # Summary
    print("=" * 60)
    print(f"  Downloaded: {success}")
    print(f"  Failed: {failed}")
    print(f"  Manual: {len(ONLINE_ONLY_BOOKS)}")
    total_existing = sum(
        1 for b in DIRECT_PDF_BOOKS + ONLINE_ONLY_BOOKS
        if (b["dest_dir"] / b["filename"]).exists()
    )
    print(f"  Total available locally: {total_existing}/{len(DIRECT_PDF_BOOKS) + len(ONLINE_ONLY_BOOKS)}")
    print("=" * 60)


if __name__ == "__main__":
    main()
