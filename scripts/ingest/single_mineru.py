"""Run MinerU on a single PDF file.

Usage:
    uv run python scripts/ingest/single_mineru.py <pdf_path>
    uv run python scripts/ingest/single_mineru.py <pdf_path> --force   # reprocess even if output exists
    uv run python scripts/ingest/single_mineru.py <pdf_path> -o <output_dir>  # custom output dir

Examples:
    uv run python scripts/ingest/single_mineru.py data/crawled_web/telecom-luckymobile/index.pdf
    uv run python scripts/ingest/single_mineru.py data/crawled_web/telecom-luckymobile/index.pdf --force
"""
import subprocess
import sys
import time
from pathlib import Path


def main():
    if len(sys.argv) < 2 or sys.argv[1] in ("-h", "--help"):
        print(__doc__)
        sys.exit(0)

    pdf_path = Path(sys.argv[1]).resolve()
    if not pdf_path.exists():
        print(f"[ERROR] File not found: {pdf_path}")
        sys.exit(1)
    if not pdf_path.suffix.lower() == ".pdf":
        print(f"[ERROR] Not a PDF file: {pdf_path}")
        sys.exit(1)

    force = "--force" in sys.argv

    # Output dir: alongside the PDF by default, or custom via -o
    if "-o" in sys.argv:
        idx = sys.argv.index("-o")
        if idx + 1 < len(sys.argv):
            out_dir = Path(sys.argv[idx + 1]).resolve()
        else:
            print("[ERROR] -o requires a path argument")
            sys.exit(1)
    else:
        out_dir = pdf_path.parent / "mineru_output" / pdf_path.stem

    # Check if already processed
    if out_dir.exists() and not force:
        md_files = list(out_dir.rglob("*.md"))
        if md_files and sum(f.stat().st_size for f in md_files) > 50:
            print(f"[SKIP] Output already exists: {out_dir}")
            print(f"  Use --force to reprocess")
            # Show the markdown file
            for md in md_files:
                print(f"  -> {md} ({md.stat().st_size / 1024:.1f} KB)")
            sys.exit(0)

    size_mb = pdf_path.stat().st_size / (1024 * 1024)
    print(f"{'='*60}")
    print(f"MinerU Single File Processing")
    print(f"{'='*60}")
    print(f"  Input:  {pdf_path} ({size_mb:.1f} MB)")
    print(f"  Output: {out_dir}")
    print(f"{'='*60}")

    cmd = ["uv", "run", "mineru", "-p", str(pdf_path), "-o", str(out_dir), "-b", "pipeline"]

    start = time.time()
    try:
        result = subprocess.run(cmd, timeout=3600)
        elapsed = time.time() - start

        if result.returncode == 0:
            md_files = list(out_dir.rglob("*.md"))
            if md_files:
                print(f"\n[OK] Done in {elapsed:.0f}s ({elapsed/60:.1f} min)")
                for md in md_files:
                    print(f"  -> {md} ({md.stat().st_size / 1024:.1f} KB)")
            else:
                print(f"\n[WARN] MinerU completed but no .md files found in {out_dir}")
        else:
            print(f"\n[FAIL] MinerU exited with code {result.returncode}")
            sys.exit(1)

    except subprocess.TimeoutExpired:
        print(f"\n[FAIL] Timeout (>60 min)")
        sys.exit(1)
    except KeyboardInterrupt:
        print(f"\n[WARN] Interrupted by user after {time.time()-start:.0f}s")
        sys.exit(130)


if __name__ == "__main__":
    main()
