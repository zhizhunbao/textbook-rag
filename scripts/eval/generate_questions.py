"""Generate benchmark questions by sending crawled directory tree to LLM.

Dynamically reads the crawled_web/<persona>/ directory structure,
builds a file tree, then asks the LLM to generate realistic
consulting questions that users would ask based on that content.

Usage:
    uv run python scripts/eval/generate_questions.py --persona federal-ircc
    uv run python scripts/eval/generate_questions.py --persona federal-ircc --model qwen3:8b
    uv run python scripts/eval/generate_questions.py --persona federal-ircc --dry-run
    uv run python scripts/eval/generate_questions.py --list-personas
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path

# ── Paths ──
PROJECT_ROOT = Path(__file__).resolve().parents[2]
CRAWLED_DIR = PROJECT_ROOT / "data" / "crawled_web"
OUTPUT_DIR = PROJECT_ROOT / "data" / "eval"

OLLAMA_URL = "http://localhost:11434"
DEFAULT_MODEL = "qwen3:4b"


# ── Build directory tree from disk ──

def build_dir_tree(root: Path, max_depth: int = 6) -> str:
    """Walk the crawled_web/<persona>/ directory and build an indented tree string.

    Only includes directories and PDF/HTML files, skipping noise files.
    Collapses deep branches to keep the tree within LLM context limits.
    """
    lines: list[str] = []
    skip_names = {"__pycache__", ".git", "node_modules", "auto", "images"}
    skip_exts = {".lock", ".json", ".log", ".png", ".jpg", ".jpeg", ".gif"}

    def _walk(dirpath: Path, prefix: str, depth: int) -> None:
        if depth > max_depth:
            lines.append(f"{prefix}... (truncated)")
            return

        try:
            entries = sorted(dirpath.iterdir())
        except PermissionError:
            return

        dirs = [e for e in entries if e.is_dir() and e.name not in skip_names]
        files = [
            e for e in entries
            if e.is_file() and e.suffix.lower() not in skip_exts
        ]

        for f in files:
            lines.append(f"{prefix}{f.name}")

        for i, d in enumerate(dirs):
            is_last = (i == len(dirs) - 1) and not files
            connector = "`-- " if is_last else "|-- "
            child_prefix = "    " if is_last else "|   "
            lines.append(f"{prefix}{connector}{d.name}/")
            _walk(d, prefix + child_prefix, depth + 1)

    lines.append(f"{root.name}/")
    _walk(root, "  ", 0)
    return "\n".join(lines)


def build_tree_from_manifest(manifest_path: Path, max_entries: int = 500) -> str:
    """Build a tree-like view from manifest.json filenames.

    This is more compact than walking disk — one line per crawled page.
    Groups by directory for readability.
    """
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    pages = manifest.get("pages", [])

    # Collect unique directory paths and their file counts
    dir_files: dict[str, list[str]] = {}
    for page in pages[:max_entries]:
        filename = page.get("filename", "")
        if not filename:
            continue
        parts = filename.replace("\\", "/").rsplit("/", 1)
        if len(parts) == 2:
            parent, name = parts
        else:
            parent, name = ".", parts[0]
        dir_files.setdefault(parent, []).append(name)

    # Build tree string
    lines = [f"Crawled pages ({len(pages)} total):"]
    for dirpath in sorted(dir_files.keys()):
        files = dir_files[dirpath]
        # Show directory with file count
        short_dir = dirpath
        # Strip common prefix for readability
        for prefix in ["en/immigration-refugees-citizenship/"]:
            if short_dir.startswith(prefix):
                short_dir = short_dir[len(prefix):]
                break
        lines.append(f"\n  {short_dir}/ ({len(files)} pages)")
        # Show first few filenames per directory
        for f in files[:8]:
            lines.append(f"    - {f}")
        if len(files) > 8:
            lines.append(f"    ... +{len(files) - 8} more")

    return "\n".join(lines)


# ── LLM interaction ──

LLM_PROMPT = """You are an expert at generating realistic benchmark questions for a Canadian immigration consulting RAG system.

Below is the directory tree of crawled government web pages. Each path represents an actual page that has been indexed into our knowledge base.

{tree}

Based on this content structure, generate {n} diverse, realistic questions that a real user (international student, immigrant, PR applicant) would ask. 

Requirements:
1. Questions should be specific and answerable from the crawled content
2. Mix of simple factual questions and complex scenario questions
3. Cover different topic areas proportionally to the content available
4. Include both English and Chinese questions (roughly 50/50)
5. Each question should be on its own line, prefixed with a number
6. Group questions by topic area with a header line starting with ##

Output format (strictly follow this):
## Study & Education
1. How do I apply for a study permit in Canada?
2. ...

## Immigration Pathways
3. ...

Do NOT include any other text, explanations, or formatting."""


def call_ollama(prompt: str, model: str = DEFAULT_MODEL) -> str:
    """Call Ollama API directly (no engine dependency)."""
    import httpx

    resp = httpx.post(
        f"{OLLAMA_URL}/api/generate",
        json={
            "model": model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": 0.7,
                "num_predict": 4096,
            },
        },
        timeout=300.0,
    )
    resp.raise_for_status()
    text = resp.json().get("response", "")
    # Strip <think> tags if present (qwen3 thinking mode)
    text = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL).strip()
    return text


def parse_llm_response(text: str) -> dict:
    """Parse the LLM response into structured questions grouped by category."""
    categories: dict[str, list[dict]] = {}
    current_category = "General"
    all_questions: list[dict] = []

    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue

        # Category header: ## Topic Name
        if line.startswith("##"):
            current_category = line.lstrip("#").strip()
            continue

        # Question line: 1. Question text  or  - Question text
        m = re.match(r"^(?:\d+[\.\)]\s*|[-*]\s+)(.+)", line)
        if m:
            question_text = m.group(1).strip()
            if len(question_text) < 8:
                continue
            q = {
                "question": question_text,
                "category": current_category,
                "source": "llm-generated",
            }
            categories.setdefault(current_category, []).append(q)
            all_questions.append(q)

    return {
        "categories": categories,
        "all_questions": all_questions,
        "total_questions": len(all_questions),
    }


# ── Main ──

def main():
    parser = argparse.ArgumentParser(
        description="Generate benchmark questions from crawled data via LLM",
    )
    parser.add_argument(
        "--persona", default="federal-ircc",
        help="Persona directory under crawled_web/",
    )
    parser.add_argument(
        "--model", default=DEFAULT_MODEL,
        help=f"Ollama model to use (default: {DEFAULT_MODEL})",
    )
    parser.add_argument(
        "--num-questions", "-n", type=int, default=60,
        help="Number of questions to generate",
    )
    parser.add_argument(
        "--use-manifest", action="store_true",
        help="Build tree from manifest.json instead of disk walk",
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Show the tree and prompt without calling LLM",
    )
    parser.add_argument(
        "--list-personas", action="store_true",
        help="List available personas and exit",
    )
    args = parser.parse_args()

    # List mode
    if args.list_personas:
        print("Available personas:")
        for d in sorted(CRAWLED_DIR.iterdir()):
            if d.is_dir():
                manifest = d / "manifest.json"
                count = ""
                if manifest.exists():
                    m = json.loads(manifest.read_text(encoding="utf-8"))
                    count = f" ({m.get('total_urls', '?')} URLs)"
                print(f"  {d.name}{count}")
        return

    persona_dir = CRAWLED_DIR / args.persona
    manifest_path = persona_dir / "manifest.json"

    if not persona_dir.exists():
        print(f"[ERROR] Persona directory not found: {persona_dir}")
        sys.exit(1)

    print(f"{'='*60}")
    print(f"Generate Questions: {args.persona}")
    print(f"Model: {args.model}")
    print(f"{'='*60}")

    # Step 1: Build directory tree
    print("\n[1/3] Building directory tree...")
    if args.use_manifest and manifest_path.exists():
        tree = build_tree_from_manifest(manifest_path)
        print(f"  Built from manifest ({manifest_path.name})")
    else:
        tree = build_dir_tree(persona_dir)
        print(f"  Built from disk walk ({persona_dir})")

    tree_lines = tree.count("\n") + 1
    tree_chars = len(tree)
    print(f"  Tree: {tree_lines} lines, {tree_chars:,} chars")

    # Truncate if too large for context window
    max_chars = 8000
    if tree_chars > max_chars:
        tree = tree[:max_chars] + f"\n... (truncated, {tree_chars - max_chars:,} chars omitted)"
        print(f"  Truncated to {max_chars:,} chars for LLM context")

    # Step 2: Build prompt
    prompt = LLM_PROMPT.format(tree=tree, n=args.num_questions)

    if args.dry_run:
        print(f"\n{'='*60}")
        print("TREE PREVIEW (first 80 lines):")
        print(f"{'='*60}")
        for line in tree.splitlines()[:80]:
            print(f"  {line}")
        print(f"\n[DRY RUN] Would send {len(prompt):,} char prompt to {args.model}")
        return

    # Step 3: Call LLM
    print(f"\n[2/3] Calling {args.model} ({len(prompt):,} chars)...")
    try:
        response_text = call_ollama(prompt, model=args.model)
    except Exception as e:
        print(f"[ERROR] LLM call failed: {e}")
        print("  Make sure Ollama is running: ollama serve")
        sys.exit(1)

    print(f"  Response: {len(response_text):,} chars")

    # Step 4: Parse and save
    print("\n[3/3] Parsing questions...")
    result = parse_llm_response(response_text)
    result["persona"] = args.persona
    result["model"] = args.model
    result["raw_response"] = response_text

    print(f"  Total questions: {result['total_questions']}")
    print(f"  Categories:")
    for cat, qs in result["categories"].items():
        print(f"    {cat}: {len(qs)}")

    # Preview
    print(f"\n{'-'*60}")
    print("Sample questions:")
    for q in result["all_questions"][:20]:
        print(f"  [{q['category'][:20]:<20}] {q['question']}")
    if result["total_questions"] > 20:
        print(f"  ... and {result['total_questions'] - 20} more")

    # Save
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    out_path = OUTPUT_DIR / f"{args.persona}_questions.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)
    print(f"\n[OK] Saved {result['total_questions']} questions to {out_path}")


if __name__ == "__main__":
    main()
