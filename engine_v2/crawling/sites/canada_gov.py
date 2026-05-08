"""
Canada.ca (Federal Government) site profile.
联邦政府网站 profile — IRCC 移民页面、GC Web Experience Toolkit。

Characteristics:
  - Uses /en/ language prefix (French at /fr/)
  - Department-level scope (e.g. /en/immigration-refugees-citizenship/)
  - Heavy use of <details> for collapsible content
  - GC Web Experience Toolkit (WET) CSS classes
  - Aggressive analytics/tracking (prevents networkidle)
  - Rate-limiting on rapid requests
"""

from engine_v2.crawling import js_snippets as JS
from engine_v2.crawling.site_profile import SiteProfile, register

canada_gov = SiteProfile(
    name="Canada.ca (Federal)",
    domains=["canada.ca", "www.canada.ca"],

    # ── Discovery ──
    scope_strategy="department",       # /en/immigration-refugees-citizenship/
    language_filter="/en/",            # English pages only

    # ── Algonquin-specific steps not needed here ──
    # Generic expansion (details, bootstrap, etc.) handled by engine defaults

    # ── Strip print media + Remove footer (DOM removal) ──
    # STRIP_PRINT_MEDIA removes @media print rules from GC WET stylesheets
    # so the PDF renders with the original screen layout (wider, cleaner).
    # REMOVE_GC_FOOTER deletes the site footer from DOM (identical on every page).
    pre_pdf_js=f"({JS.STRIP_PRINT_MEDIA})(); ({JS.REMOVE_GC_FOOTER})();",
    print_css=JS.PRINT_CSS_CANADA_GOV,

    # ── Rate Limiting (gov sites are aggressive) ──
    min_delay_between=8.0,
    retry_backoff_sec=15.0,
)

register(canada_gov)
