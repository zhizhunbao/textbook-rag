"""Shared path constants for all scripts.

Every script can do:
    from _paths import PROJECT_ROOT, DATA_DIR, ...

This module resolves the project root by walking up from its own location
until it finds pyproject.toml, so it works regardless of how deep the
calling script is nested under scripts/.
"""

from pathlib import Path

def _find_project_root() -> Path:
    """Walk up from this file until we hit a directory with pyproject.toml."""
    current = Path(__file__).resolve().parent
    for _ in range(5):  # safety limit
        if (current / "pyproject.toml").exists():
            return current
        current = current.parent
    # Fallback: assume scripts/ is one level below project root
    return Path(__file__).resolve().parent.parent


PROJECT_ROOT = _find_project_root()
DATA_DIR = PROJECT_ROOT / "data"
CHROMA_DIR = DATA_DIR / "chroma_persist"
MINERU_DIR = DATA_DIR / "mineru_output"
RAW_PDFS_DIR = DATA_DIR / "raw_pdfs"
