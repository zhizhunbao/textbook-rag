"""
TaxTips.ca site profile.
第三方加拿大税务信息网站 — 用于抓取各省税率表等静态数据。

Characteristics:
  - Domain: taxtips.ca / www.taxtips.ca
  - Static HTML site (no JS frameworks)
  - Tax rate tables are plain HTML tables (no dynamic rendering)
  - Simple structure, minimal noise
"""

from engine_v2.crawling import js_snippets as JS
from engine_v2.crawling.site_profile import SiteProfile, register

taxtips = SiteProfile(
    name="TaxTips.ca (Third Party)",
    domains=["taxtips.ca", "www.taxtips.ca"],

    # ── Discovery ──
    scope_strategy="first_segment",    # /taxrates/ scope
    language_filter=None,

    # ── Pre-PDF cleanup (ALL pages) ──
    pre_pdf_js=(
        f"({JS.STRIP_PRINT_MEDIA})();"
        """
        (() => {
            document.querySelectorAll(
                'footer, .site-footer, [role="contentinfo"]'
            ).forEach(el => el.remove());
        })();
        """
    ),
    # ── Non-first pages: also remove header/nav ──
    # Header/nav removal on non-first pages is handled by engine (REMOVE_HEADER_NAV)
    print_css=JS.PRINT_CSS_GENERIC,

    # ── Rate Limiting (polite — third party site) ──
    min_delay_between=8.0,
    retry_backoff_sec=15.0,

    # ── Skip patterns ──
    skip_path_patterns=[
        "/ads/",
        "/subscribe",
    ],
)

register(taxtips)
