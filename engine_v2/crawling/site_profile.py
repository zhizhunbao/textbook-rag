"""
SiteProfile — Declarative configuration for site-specific crawling behavior.
每个网站类型（政府、学校、通用）定义自己的 profile，引擎根据 URL 自动选择。

Usage:
    from engine_v2.crawling.site_profile import get_profile
    profile = get_profile("https://www.canada.ca/en/...")
    # profile.content_expansion_steps → list of (js_string, wait_ms) tuples
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable
from urllib.parse import urlparse


@dataclass
class SiteProfile:
    """Declarative configuration for a specific website's crawling behavior.

    Each website type (government, school, etc.) defines its own profile
    with site-specific selectors, JS snippets, and validation rules.
    The core engine is completely site-agnostic — all behavior differences
    are driven by profiles.
    """

    # ── Identity ──
    name: str                           # Human-readable name (e.g. "Canada.ca Federal")
    domains: list[str]                  # Matching domains (e.g. ["canada.ca", "www.canada.ca"])

    # ── Phase 1: URL Discovery ──
    # scope_strategy controls how scope_prefix is computed from the seed URL:
    #   "department"    → first 2 path segments (canada.ca: /en/immigration-refugees-citizenship/)
    #   "first_segment" → first path segment (default, e.g. /immigrate-to-b-c/)
    #   "root"          → "/" (accept all same-domain paths)
    scope_strategy: str = "first_segment"
    language_filter: str | None = None     # e.g. "/en/" — path must start with this

    # ── Phase 2: Page Rendering ──
    viewport_width: int = 1280
    viewport_height: int = 900
    wait_after_load_ms: int = 1500

    # ── Content Expansion Pipeline ──
    # Ordered list of (js_string, wait_after_ms) tuples.
    # The engine evaluates each JS snippet in order, waiting between steps.
    # Generic steps (cookie consent, lazy images, scroll, etc.) are prepended
    # automatically by the engine — profiles only add site-specific steps.
    extra_expansion_steps: list[tuple[str, int]] = field(default_factory=list)

    # ── Noise Removal ──
    # Additional JS to remove site-specific noise (chatbots, widgets, etc.)
    # Runs AFTER the generic popup/chatbot removal.
    extra_noise_removal_js: str | None = None

    # ── Pre-PDF Cleanup ──
    # JS to run just before PDF capture (remove interactive UI, etc.)
    pre_pdf_js: str | None = None

    # ── Print CSS ──
    print_css: str = ""                    # @media print overrides

    # ── Validation ──
    error_title_keywords: list[str] = field(default_factory=lambda: [
        "503", "403", "temporarily unavailable",
        "access denied", "forbidden", "just a moment",
    ])
    soft_404_keywords: list[str] = field(default_factory=lambda: [
        "not found", "page not found",
    ])
    # Per-site early skip rules: list of callables (page_info: dict, url: str) -> bool
    # Return True to SKIP this page.
    skip_rules: list[Callable[[dict[str, Any], str], bool]] = field(default_factory=list)

    # ── Source Banner ──
    inject_source_banner: bool = True
    banner_border_color: str = "#26374a"

    # ── Rate Limiting ──
    min_delay_between: float = 5.0       # Minimum seconds between pages
    retry_backoff_sec: float = 15.0      # Seconds to wait before retry on error

    # ── Discovery Mode ──
    # True → serial BFS (one page at a time), avoids WAF on bank/SPA sites.
    # False → crawl4ai's built-in concurrent BFS (default, fast for gov sites).
    serial_discovery: bool = False


# ══════════════════════════════════════════════════════════════════════════════
#  Profile Registry
# ══════════════════════════════════════════════════════════════════════════════

_PROFILES: dict[str, SiteProfile] = {}


def register(profile: SiteProfile) -> None:
    """Register a site profile for domain matching."""
    for domain in profile.domains:
        _PROFILES[domain.lower()] = profile


def get_profile(url: str) -> SiteProfile:
    """Look up the best matching SiteProfile for a URL.

    Matching order:
      1. Exact netloc match (e.g. "www.canada.ca")
      2. Without www. prefix (e.g. "canada.ca")
      3. Fallback to generic profile ("*")
    """
    netloc = urlparse(url).netloc.lower()

    # Exact match
    if netloc in _PROFILES:
        return _PROFILES[netloc]

    # Strip www. and try again
    bare = netloc.removeprefix("www.")
    if bare in _PROFILES:
        return _PROFILES[bare]

    # Fallback to generic
    return _PROFILES.get("*", SiteProfile(name="generic", domains=["*"]))


def compute_scope_prefix(seed_url: str, profile: SiteProfile) -> str:
    """Compute the URL scope prefix based on the profile's strategy.

    Used in Phase 1 (URL discovery) to filter discovered URLs.
    """
    parsed = urlparse(seed_url)
    path_parts = parsed.path.strip("/").split("/")

    if profile.scope_strategy == "department":
        # Canada.ca style: /en/immigration-refugees-citizenship/ → 2 segments
        return "/" + "/".join(path_parts[:2]) if len(path_parts) >= 2 else "/"
    elif profile.scope_strategy == "root":
        return "/"
    else:  # "first_segment" (default)
        return "/" + path_parts[0] if path_parts and path_parts[0] else "/"
