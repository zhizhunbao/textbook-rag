"""
Bank site profile — configuration for Canadian bank websites.
银行网站 profile，针对 BMO/RBC/TD/Scotiabank/CIBC 的反爬策略优化。

Key differences from generic:
  - Higher min_delay (15s) to avoid WAF rate-limiting
  - scope_strategy="root" to accept all same-domain personal banking paths
  - Extra noise removal for chatbots (LivePerson, Drift, etc.)
"""

from engine_v2.crawling import js_snippets as JS
from engine_v2.crawling.site_profile import SiteProfile, register

# ── Bank-specific noise removal JS ──
REMOVE_BANK_NOISE = """
(() => {
    // Remove footer — navigation noise repeated in every PDF
    const structuralSelectors = [
        'footer', '[role="contentinfo"]',
        '[data-section="footer"]',
        '[id*="Footer"]', '[id*="footer"]',
        '[class*="site-footer"]',
    ];
    // Remove fixed-position elements (floating headers that overlap content)
    document.querySelectorAll('*').forEach(el => {
        if (getComputedStyle(el).position === 'fixed') el.remove();
    });
    // Remove common bank chatbot widgets
    const widgetSelectors = [
        '[id*="lpChat"]', '[id*="live-chat"]', '[id*="livechat"]',
        '[class*="chatbot"]', '[class*="ChatBot"]', '[class*="live-chat"]',
        '[id*="drift"]', '[id*="intercom"]', '[id*="zendesk"]',
        '[class*="cookie-banner"]', '[class*="CookieBanner"]',
        '[id*="onetrust"]', '[class*="onetrust"]',
        '[class*="survey"]', '[id*="survey"]',
        '[class*="feedback"]', '[id*="feedback-button"]',
        'iframe[src*="chat"]', 'iframe[src*="survey"]',
    ];
    [...structuralSelectors, ...widgetSelectors].forEach(sel => {
        document.querySelectorAll(sel).forEach(el => el.remove());
    });
    // Force all collapsed/accordion content visible via CSS !important
    const forceStyle = document.createElement('style');
    forceStyle.textContent = `
        .collapse:not(.navbar-collapse),
        .collapse-content,
        .panel-collapse,
        .accordion-collapse,
        .accordion .content,
        .accordion-navigation .content,
        [class*="collapsible-content"] {
            display: block !important;
            height: auto !important;
            overflow: visible !important;
            visibility: visible !important;
            opacity: 1 !important;
        }
    `;
    document.head.appendChild(forceStyle);
    // Remove inline style="display: none" on accordion content (CIBC pattern)
    document.querySelectorAll('.accordion .content, .accordion-navigation .content').forEach(el => {
        el.style.removeProperty('display');
    });
    // Radix UI accordion (BMO pattern) — data-state="closed" + height: 0px
    document.querySelectorAll('[data-accordion-item]').forEach(item => {
        item.setAttribute('data-state', 'open');
        const btn = item.querySelector('button[data-state]');
        if (btn) {
            btn.setAttribute('data-state', 'open');
            btn.setAttribute('aria-expanded', 'true');
        }
        const panel = item.querySelector('[role="region"]');
        if (panel) {
            panel.setAttribute('data-state', 'open');
            panel.setAttribute('aria-hidden', 'false');
            panel.style.height = 'auto';
            panel.style.overflow = 'visible';
        }
        // Also fix h3 wrapper
        const h3 = item.querySelector('h3[data-state]');
        if (h3) h3.setAttribute('data-state', 'open');
    });
})();
"""

# ── Shared bank profile config ──
_BANK_PROFILE_DEFAULTS = dict(
    scope_strategy="root",
    min_delay_between=5.0,        # 5s between pages — serial mode handles WAF
    retry_backoff_sec=30.0,       # 30s backoff on error (WAF recovery)
    wait_after_load_ms=3000,      # 3s wait — banks have heavy JS
    serial_discovery=False,       # Use concurrent BFS; switch to True if WAF blocks
    extra_noise_removal_js=REMOVE_BANK_NOISE,
    print_css=JS.PRINT_CSS_GENERIC,
    banner_border_color="#1a1a2e",
    error_title_keywords=[
        "503", "403", "temporarily unavailable",
        "access denied", "forbidden", "just a moment",
        "something doesn't seem right",       # RBC WAF block
        "account access",                     # RBC WAF block
    ],
)


# ── BMO ──
bmo = SiteProfile(
    name="BMO",
    domains=["www.bmo.com", "bmo.com"],
    **_BANK_PROFILE_DEFAULTS,
)
register(bmo)


# ── RBC ──
rbc = SiteProfile(
    name="RBC",
    domains=["www.rbc.com", "rbc.com", "www.rbcroyalbank.com", "rbcroyalbank.com"],
    **_BANK_PROFILE_DEFAULTS,
)
register(rbc)


# ── TD ──
td = SiteProfile(
    name="TD",
    domains=["www.td.com", "td.com"],
    **_BANK_PROFILE_DEFAULTS,
)
register(td)


# ── Scotiabank ──
scotiabank = SiteProfile(
    name="Scotiabank",
    domains=["www.scotiabank.com", "scotiabank.com"],
    **_BANK_PROFILE_DEFAULTS,
)
register(scotiabank)


# ── CIBC ──
cibc = SiteProfile(
    name="CIBC",
    domains=["www.cibc.com", "cibc.com"],
    **_BANK_PROFILE_DEFAULTS,
)
register(cibc)
