"""
Telecom carrier site profile — configuration for Canadian telecom websites.
电信运营商 profile，针对 SPA + Cloudflare 反爬优化。

Design philosophy (参考 canada_gov.py):
  - Keep it simple — minimal JS manipulation, preserve original page layout.
  - Use STRIP_PRINT_MEDIA to prevent @media print from breaking layout.
  - Use wider viewport (1440px) to avoid triggering mobile breakpoints.
  - Only remove genuine noise (cookies, chat widgets, skip links).
  - Do NOT force-expand accordions via CSS — click-based expansion is enough.
"""

from engine_v2.crawling import js_snippets as JS
from engine_v2.crawling.site_profile import SiteProfile, register

# ── Telecom pre-PDF cleanup (lightweight — follows canada_gov.py pattern) ──
TELECOM_PRE_PDF_JS = f"""(async () => {{
    // 1. Strip @media print rules (reuse shared snippet)
    ({JS.STRIP_PRINT_MEDIA})();

    // 2. Hide <style> tags inside <body> (CSS text leak fix)
    const s = document.createElement('style');
    s.textContent = 'body style {{ display: none !important; }}';
    document.head.appendChild(s);

    // 3. Remove genuine noise (cookie banners, chat widgets, skip links)
    document.querySelectorAll(
        '[class*="cookie"], [class*="Cookie"], [id*="cookie"], ' +
        '[class*="chat-widget"], [class*="ChatWidget"], ' +
        '[class*="onetrust"], [id*="onetrust"]'
    ).forEach(el => el.remove());

    document.querySelectorAll('script, noscript').forEach(el => el.remove());

    document.querySelectorAll(
        'a[href="#main"], a[href="#content"], a[href="#main-content"], ' +
        '.skip-link, .skip-nav, [class*="skip-to-main"], [class*="SkipTo"]'
    ).forEach(el => el.remove());
    document.querySelectorAll('a').forEach(a => {{
        if (/skip to (main|content)/i.test(a.textContent)) a.remove();
    }});

    // 4. Close open dropdown menus (province selectors, etc.)
    document.querySelectorAll(
        '[class*="dropdown-menu"][class*="show"], ' +
        '[class*="dropdown"][class*="open"], ' +
        '[data-radix-popper-content-wrapper], ' +
        '[data-state="open"][role="menu"]'
    ).forEach(el => el.remove());

    // 5. Text-based fallback: remove floating province selectors
    const provinces = ['alberta', 'british columbia', 'manitoba', 'new brunswick',
        'newfoundland', 'nova scotia', 'ontario', 'prince edward', 'quebec', 'saskatchewan'];
    document.querySelectorAll('div, ul, section').forEach(el => {{
        const pos = getComputedStyle(el).position;
        if (pos !== 'absolute' && pos !== 'fixed') return;
        const text = (el.innerText || '').toLowerCase();
        if (provinces.filter(p => text.includes(p)).length >= 4) el.remove();
    }});
}})();"""

# ── Telecom accordion expansion (click-based only, no CSS force) ──
EXPAND_TELECOM_ACCORDIONS = """
(async () => {
    const delay = ms => new Promise(r => setTimeout(r, ms));

    // 1. Click accordion triggers by ATTRIBUTE (safe — won't trigger navigation)
    document.querySelectorAll(
        '[class*="accordion"] > button, [class*="Accordion"] > button, ' +
        '[class*="accordion"] > [role="button"], ' +
        '[data-toggle="collapse"], [data-bs-toggle="collapse"], ' +
        '[class*="expandable"] > button, [class*="Expandable"] > button, ' +
        '.faq-question, .plan-details-toggle, ' +
        '[class*="accordion-trigger"], [class*="AccordionTrigger"]'
    ).forEach(btn => {
        try { btn.click(); } catch(e) {}
    });
    await delay(500);

    // 2. Click [aria-expanded="false"] ONLY inside main content
    const main = document.querySelector('main') || document.body;
    main.querySelectorAll('[aria-expanded="false"]').forEach(el => {
        if (el.closest('nav, header, footer, [role="navigation"], [role="banner"]')) return;
        if (el.closest('[class*="dropdown"], [class*="Dropdown"], [class*="select"], [class*="Select"]')) return;
        if (el.getAttribute('aria-haspopup') === 'listbox' || el.getAttribute('aria-haspopup') === 'true') return;
        if (el.getAttribute('role') === 'combobox' || el.getAttribute('role') === 'listbox') return;
        const text = (el.textContent || '').trim().toLowerCase();
        if (['menu', 'sign in', 'log in', 'my account', 'search', 'shop',
             'plans', 'devices', 'phones', 'ontario', 'quebec', 'alberta',
             'british columbia', 'select province', 'select a province'].includes(text)) return;
        try { el.click(); } catch(e) {}
    });
    await delay(500);

    // 3. Open all <details> elements
    document.querySelectorAll('details').forEach(d => { d.open = true; });
})();
"""

# ── Print CSS (follows canada_gov.py pattern — neutralize fixed/sticky, keep layout) ──
TELECOM_PRINT_CSS = """
@media print {
    * {
        color-adjust: exact !important;
        -webkit-print-color-adjust: exact !important;
        print-color-adjust: exact !important;
    }
    /* Neutralize fixed/sticky → relative (keeps them in flow, no overlap) */
    [style*="position: fixed"], [style*="position: sticky"],
    header, nav,
    [role="banner"], [role="navigation"] {
        position: relative !important;
        top: auto !important;
        z-index: auto !important;
    }
    /* Hide body style tags (CSS text leak fix) */
    body style { display: none !important; }
    .noprint { display: none !important; }
}
"""

# ── Shared telecom profile config ──
_TELECOM_PROFILE_DEFAULTS = dict(
    scope_strategy="root",
    min_delay_between=8.0,        # 8s between pages — Cloudflare sensitive
    retry_backoff_sec=30.0,       # 30s backoff on Cloudflare block
    wait_after_load_ms=5000,      # 5s wait — SPA needs time to render
    viewport_width=1440,          # Wider viewport to avoid mobile breakpoints
    serial_discovery=True,        # Serial BFS — one page at a time, avoids WAF
    skip_path_patterns=[
        # Phone/device product pages (hardware catalogs, not useful for plan info)
        "/phones/", "/devices/", "/shop/phones", "/shop/devices",
        "/accessories", "/shop/accessories",
        # French locale duplicates
        "/fr/", "/fr-CA/",
        # Province-specific duplicates (Public Mobile pattern: /en/qc/, /en/bc/, etc.)
        "/en/qc/", "/en/bc/", "/en/ab/", "/en/sk/", "/en/mb/", "/en/nb/",
        "/en/ns/", "/en/pe/", "/en/nl/", "/en/nt/", "/en/yk/", "/en/nu/",
    ],
    print_css=TELECOM_PRINT_CSS,
    pre_pdf_js=TELECOM_PRE_PDF_JS,
    banner_border_color="#1a1a2e",
    extra_expansion_steps=[
        (EXPAND_TELECOM_ACCORDIONS, 2000),   # click-expand, wait 2s
    ],
    error_title_keywords=[
        "503", "403", "temporarily unavailable",
        "access denied", "forbidden", "just a moment",
    ],
)


# ── Budget tier ──

publicmobile = SiteProfile(
    name="Public Mobile",
    domains=["www.publicmobile.ca", "publicmobile.ca"],
    **_TELECOM_PROFILE_DEFAULTS,
)
register(publicmobile)

luckymobile = SiteProfile(
    name="Lucky Mobile",
    domains=["www.luckymobile.ca", "luckymobile.ca"],
    **_TELECOM_PROFILE_DEFAULTS,
)
register(luckymobile)

chatr = SiteProfile(
    name="Chatr",
    domains=["www.chatrwireless.com", "chatrwireless.com"],
    **_TELECOM_PROFILE_DEFAULTS,
)
register(chatr)


# ── Flanker tier ──

fido = SiteProfile(
    name="Fido",
    domains=["www.fido.ca", "fido.ca"],
    **_TELECOM_PROFILE_DEFAULTS,
)
register(fido)

koodo = SiteProfile(
    name="Koodo",
    domains=["www.koodomobile.com", "koodomobile.com"],
    **_TELECOM_PROFILE_DEFAULTS,
)
register(koodo)

virginplus = SiteProfile(
    name="Virgin Plus",
    domains=["www.virginplus.ca", "virginplus.ca"],
    **_TELECOM_PROFILE_DEFAULTS,
)
register(virginplus)

freedom = SiteProfile(
    name="Freedom Mobile",
    domains=["www.freedommobile.ca", "freedommobile.ca"],
    **_TELECOM_PROFILE_DEFAULTS,
)
register(freedom)


# ── ISP (Home Internet) tier ──

bell = SiteProfile(
    name="Bell",
    domains=["www.bell.ca", "bell.ca"],
    **_TELECOM_PROFILE_DEFAULTS,
)
register(bell)

rogers = SiteProfile(
    name="Rogers",
    domains=["www.rogers.com", "rogers.com"],
    **_TELECOM_PROFILE_DEFAULTS,
)
register(rogers)

teksavvy = SiteProfile(
    name="TekSavvy",
    domains=["www.teksavvy.com", "teksavvy.com"],
    **_TELECOM_PROFILE_DEFAULTS,
)
register(teksavvy)
