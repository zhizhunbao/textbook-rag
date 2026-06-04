"""
Provincial government site profiles.
各省政府网站 profile — 省提名 PNP 页面。

Covers: ontario.ca, quebec.ca, welcomebc.ca, alberta.ca,
        immigratemanitoba.com, liveinnovascotia.com, gnb.ca,
        gov.nl.ca, princeedwardisland.ca, saskatchewan.ca,
        yukon.ca, immigratenwt.ca

Most provincial sites use standard Bootstrap/WordPress patterns.
The generic expansion pipeline handles them well.
Site-specific overrides only where needed.
"""

from engine_v2.crawling import js_snippets as JS
from engine_v2.crawling.site_profile import SiteProfile, register

# ── Ontario (Radware WAF, aggressive rate-limiting) ──
_ONTARIO_REMOVE_BOILERPLATE = """() => {
    // Remove site footer (identical on every page — pollutes RAG)
    // NOTE: do NOT use [role="contentinfo"] — on ontario.ca it wraps
    // the Updated/Published dates and final content paragraphs too.
    document.querySelectorAll(
        'footer.footer, .footer--expanded, .footer__expanded-top-section, ' +
        '.footer__expanded-bottom-section, .footer__copyright'
    ).forEach(el => el.remove());
}"""

_ONTARIO_PRE_PDF = """() => {
    // Force all content containers to show full content (no clipping).
    // Ontario.ca CSS clips overflow in print mode, truncating bottom content.
    document.querySelectorAll(
        'main, article, .main-content, .body-field, ' +
        '.grid__inner-wrap, .grid__outer-wrap, .book__off-canvas--wrapper, ' +
        '.row, .columns, .small-12, [id="toc-end"]'
    ).forEach(el => {
        el.style.overflow = 'visible';
        el.style.maxHeight = 'none';
        el.style.height = 'auto';
    });
    // Ensure body/html don't clip either
    document.documentElement.style.overflow = 'visible';
    document.documentElement.style.height = 'auto';
    document.body.style.overflow = 'visible';
    document.body.style.height = 'auto';
}"""

ontario_gov = SiteProfile(
    name="Ontario.ca",
    domains=["ontario.ca", "www.ontario.ca"],
    scope_strategy="first_segment",
    print_css=JS.PRINT_CSS_GENERIC,
    min_delay_between=15.0,    # Radware WAF blocks after ~14 reqs at 8s
    retry_backoff_sec=30.0,
    extra_noise_removal_js=_ONTARIO_REMOVE_BOILERPLATE,
    pre_pdf_js=_ONTARIO_PRE_PDF,
)
register(ontario_gov)

# ── Quebec ──
quebec_gov = SiteProfile(
    name="Quebec.ca",
    domains=["quebec.ca", "www.quebec.ca"],
    scope_strategy="first_segment",
    language_filter="/en/",    # English pages (/en/immigration/)
    print_css=JS.PRINT_CSS_GENERIC,
    min_delay_between=5.0,
)
register(quebec_gov)

# ── British Columbia ──
bc_welcomebc = SiteProfile(
    name="WelcomeBC",
    domains=["welcomebc.ca", "www.welcomebc.ca"],
    scope_strategy="first_segment",
    print_css=JS.PRINT_CSS_GENERIC,
    min_delay_between=5.0,
)
register(bc_welcomebc)

# ── Alberta ──
alberta_gov = SiteProfile(
    name="Alberta.ca",
    domains=["alberta.ca", "www.alberta.ca"],
    scope_strategy="root",     # Flat URL patterns: /aaip-*, /immigration, etc.
    print_css=JS.PRINT_CSS_GENERIC,
    min_delay_between=5.0,
)
register(alberta_gov)

# ── Manitoba ──
manitoba_immigrate = SiteProfile(
    name="Immigrate Manitoba",
    domains=["immigratemanitoba.com", "www.immigratemanitoba.com"],
    scope_strategy="first_segment",
    print_css=JS.PRINT_CSS_GENERIC,
)
register(manitoba_immigrate)

# ── Nova Scotia ──
nova_scotia = SiteProfile(
    name="Live in Nova Scotia",
    domains=["liveinnovascotia.com", "www.liveinnovascotia.com"],
    scope_strategy="first_segment",
    print_css=JS.PRINT_CSS_GENERIC,
)
register(nova_scotia)

# ── New Brunswick ──
new_brunswick = SiteProfile(
    name="GNB.ca",
    domains=["gnb.ca", "www2.gnb.ca"],
    scope_strategy="first_segment",
    print_css=JS.PRINT_CSS_GENERIC,
)
register(new_brunswick)

# ── Newfoundland & Labrador ──
newfoundland = SiteProfile(
    name="Gov.nl.ca",
    domains=["gov.nl.ca", "www.gov.nl.ca"],
    scope_strategy="first_segment",
    print_css=JS.PRINT_CSS_GENERIC,
)
register(newfoundland)

# ── PEI ──
pei = SiteProfile(
    name="PEI.ca",
    domains=["princeedwardisland.ca", "www.princeedwardisland.ca"],
    scope_strategy="first_segment",
    print_css=JS.PRINT_CSS_GENERIC,
)
register(pei)

# ── Saskatchewan ──
saskatchewan = SiteProfile(
    name="Saskatchewan.ca",
    domains=["saskatchewan.ca", "www.saskatchewan.ca"],
    scope_strategy="first_segment",
    print_css=JS.PRINT_CSS_GENERIC,
)
register(saskatchewan)

# ── Yukon ──
yukon = SiteProfile(
    name="Yukon.ca",
    domains=["yukon.ca", "www.yukon.ca"],
    scope_strategy="first_segment",
    language_filter="/en/",
    print_css=JS.PRINT_CSS_GENERIC,
)
register(yukon)

# ── Northwest Territories ──
nwt = SiteProfile(
    name="ImmigrateNWT",
    domains=["immigratenwt.ca", "www.immigratenwt.ca"],
    scope_strategy="first_segment",
    print_css=JS.PRINT_CSS_GENERIC,
)
register(nwt)
