"""
CDIC (Canada Deposit Insurance Corporation) site profile.
加拿大存款保险公司官网 — 用于抓取存款保险、机构历史等信息。

Characteristics:
  - Domain: cdic.ca / www.cdic.ca
  - WordPress-based site (uses cookies consent banner)
  - Relatively small site (~50 pages), mostly static content
  - No aggressive rate-limiting
"""

from engine_v2.crawling import js_snippets as JS
from engine_v2.crawling.site_profile import SiteProfile, register

federal_cdic = SiteProfile(
    name="CDIC (Federal Crown Corp)",
    domains=["cdic.ca", "www.cdic.ca"],

    # ── Discovery ──
    scope_strategy="root",             # Accept all paths on cdic.ca
    language_filter=None,              # No language prefix filtering

    # ── Pre-PDF cleanup (ALL pages) ──
    # Strip print media + remove footer/cookies (identical noise on every page)
    pre_pdf_js=(
        f"({JS.STRIP_PRINT_MEDIA})();"
        """
        (() => {
            // Remove footer (identical on every page)
            document.querySelectorAll(
                'footer, .site-footer, [role="contentinfo"]'
            ).forEach(el => el.remove());
            // Remove cookie consent banner
            document.querySelectorAll(
                '[class*="cookie"], [id*="cookie"]'
            ).forEach(el => el.remove());
        })();
        """
    ),
    # Header/nav removal on non-first pages is handled by engine (REMOVE_HEADER_NAV)
    print_css=JS.PRINT_CSS_GENERIC,

    # ── Rate Limiting (light — not a gov cluster) ──
    min_delay_between=5.0,
    retry_backoff_sec=10.0,

    # ── Skip patterns ──
    skip_path_patterns=[
        "/fr/",          # French pages
        "/sadc.",        # French domain redirect
        "/careers/",     # Job postings
    ],
)

register(federal_cdic)
