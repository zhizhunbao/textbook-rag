"""
Reusable JavaScript snippets for browser-based content rendering.
提取自 web_crawler.py 的所有内联 JS 字符串，按功能分类。

Each snippet is a self-contained function string ready for page.evaluate().
"""

# ══════════════════════════════════════════════════════════════════════════════
#  Early Validation
# ══════════════════════════════════════════════════════════════════════════════

EARLY_PAGE_INFO = """() => {
    const main = document.querySelector('main') || document.body;
    const text = main.innerText || '';
    const wordCount = text.split(/\\s+/).filter(w => w.length > 0).length;
    const forms = main.querySelectorAll('form').length;
    const requiredFields = main.querySelectorAll('[required]').length;
    return { wordCount, forms, requiredFields };
}"""


# ══════════════════════════════════════════════════════════════════════════════
#  Cookie Consent Dismissal
# ══════════════════════════════════════════════════════════════════════════════

DISMISS_COOKIE_CONSENT = """() => {
    const allBtns = document.querySelectorAll('button, a.btn, [role="button"]');
    for (const btn of allBtns) {
        const text = (btn.textContent || '').toLowerCase().trim();
        if (
            text === 'allow all' || text === 'accept all' ||
            text === 'accept all cookies' || text === 'accept cookies' ||
            text === 'essential only' || text === 'i agree' ||
            text === 'got it' ||
            text.includes('accept all') || text.includes('allow all')
        ) {
            try { btn.click(); return; } catch(e) {}
        }
    }
    document.querySelectorAll(
        '[class*="cookie"], [id*="cookie"], [class*="consent"], [id*="consent"], ' +
        '[class*="CookieConsent"], [id*="CookieConsent"], ' +
        '[class*="privacy-banner"], [id*="privacy-banner"], ' +
        '#onetrust-consent-sdk, #CybotCookiebotDialog, .cc-window, .cc-banner'
    ).forEach(el => el.remove());
}"""


# ══════════════════════════════════════════════════════════════════════════════
#  Content Loading
# ══════════════════════════════════════════════════════════════════════════════

FORCE_LAZY_IMAGES = """() => {
    document.querySelectorAll('img[loading="lazy"]').forEach(img => {
        img.loading = 'eager';
        const src = img.src;
        img.src = '';
        img.src = src;
    });
}"""

SCROLL_TO_BOTTOM = """async () => {
    const delay = ms => new Promise(r => setTimeout(r, ms));
    const height = () => document.body.scrollHeight;
    let prev = 0;
    while (height() !== prev) {
        prev = height();
        window.scrollTo(0, height());
        await delay(500);
    }
}"""

WAIT_FOR_IMAGES = """() => {
    return Promise.all(
        Array.from(document.images)
            .filter(img => !img.complete)
            .map(img => new Promise(r => {
                img.onload = img.onerror = r;
            }))
    );
}"""


# ══════════════════════════════════════════════════════════════════════════════
#  Generic Content Expansion (works on all sites)
# ══════════════════════════════════════════════════════════════════════════════

EXPAND_DETAILS = """() => {
    const main = document.querySelector('main') || document.body;
    main.querySelectorAll('details').forEach(d => d.open = true);
}"""

EXPAND_SHOW_MORE = """() => {
    const main = document.querySelector('main') || document.body;
    const btns = main.querySelectorAll(
        'button, a, [role="button"], .show-more, .expand-all'
    );
    for (const btn of btns) {
        if (btn.tagName === 'A') {
            const href = (btn.getAttribute('href') || '').trim();
            if (href && !href.startsWith('#') && !href.startsWith('javascript:')) {
                continue;
            }
        }
        const text = (btn.textContent || '').toLowerCase().trim();
        if (
            text.includes('show all') || text.includes('expand all') ||
            text.includes('show more') || text.includes('view all') ||
            text.includes('load more') || text.includes('see all')
        ) {
            try { btn.click(); } catch(e) {}
        }
    }
}"""

EXPAND_GENERIC_TABS = """() => {
    const main = document.querySelector('main') || document.body;
    const panels = main.querySelectorAll(
        '[role="tabpanel"], .tab-pane, .tab-content > div, ' +
        '[class*="tab-panel"]'
    );
    for (const panel of panels) {
        try {
            if (!panel || !panel.style) continue;
            // GC WET: hidden via `hidden` attr or classes `out` / `noheight`
            panel.removeAttribute('hidden');
            panel.classList.remove('out', 'noheight');
            panel.classList.add('active', 'show', 'in');
            panel.setAttribute('aria-hidden', 'false');
            panel.setAttribute('aria-expanded', 'true');
            panel.style.display = 'block';
            panel.style.visibility = 'visible';
            panel.style.opacity = '1';
            panel.style.height = 'auto';
            panel.style.overflow = 'visible';
        } catch(e) {}
    }
    // Do NOT click tab triggers — clicking re-triggers WET/Bootstrap JS
    // which hides the panels we just forced open. CSS forcing is sufficient.
}"""

EXPAND_BOOTSTRAP_COLLAPSE = """() => {
    const main = document.querySelector('main') || document.body;

    // A. Bootstrap collapse — disable JS handlers, then force-show via CSS
    //    Removing data-toggle prevents Bootstrap from re-collapsing panels
    main.querySelectorAll('[data-parent], [data-bs-parent]').forEach(el => {
        el.removeAttribute('data-parent');
        el.removeAttribute('data-bs-parent');
    });
    main.querySelectorAll('[data-toggle="collapse"], [data-bs-toggle="collapse"]').forEach(el => {
        el.removeAttribute('data-toggle');
        el.removeAttribute('data-bs-toggle');
        el.setAttribute('aria-expanded', 'true');
        el.classList.remove('collapsed');
    });
    main.querySelectorAll('.collapse, .panel-collapse, .collapse-content').forEach(panel => {
        try {
            panel.classList.add('show', 'in');
            panel.classList.remove('collapse');
            panel.style.display = 'block';
            panel.style.height = 'auto';
            panel.style.overflow = 'visible';
            panel.style.visibility = 'visible';
        } catch(e) {}
    });

    // B. Generic aria-expanded buttons
    main.querySelectorAll('[aria-expanded="false"]').forEach(btn => {
        try {
            btn.setAttribute('aria-expanded', 'true');
            btn.click();
        } catch(e) {}
    });

    // C. Accordion panels: force all visible
    main.querySelectorAll(
        '.accordion-collapse, .accordion-body, .accordion-content, ' +
        '.panel-body, .panel-content, ' +
        '[class*="accordion-panel"], [class*="accordion-item"] > div:last-child, ' +
        '.wp-block-details, .toggle-content, ' +
        '[class*="collapsible-content"], [class*="expandable"]'
    ).forEach(panel => {
        try {
            panel.style.display = 'block';
            panel.style.visibility = 'visible';
            panel.style.height = 'auto';
            panel.style.maxHeight = 'none';
            panel.style.overflow = 'visible';
            panel.style.opacity = '1';
            panel.classList.add('show', 'in', 'active', 'open');
            panel.classList.remove('collapsed', 'hidden');
            panel.removeAttribute('hidden');
        } catch(e) {}
    });

    // D. Generic aria-selected
    main.querySelectorAll('[aria-selected="false"]').forEach(el => {
        try {
            el.setAttribute('aria-selected', 'true');
            el.click();
        } catch(e) {}
    });

    // E. Generic toggle-items / step-accordions
    main.querySelectorAll(
        '.toggle-item, .step-accordion, ' +
        '[class*="toggle-trigger"], [class*="step-toggle"]'
    ).forEach(trigger => {
        try {
            trigger.classList.add('active', 'open');
            trigger.setAttribute('aria-expanded', 'true');
            const next = trigger.nextElementSibling;
            if (next) {
                next.style.display = 'block';
                next.style.height = 'auto';
                next.removeAttribute('hidden');
            }
        } catch(e) {}
    });
}"""


# ══════════════════════════════════════════════════════════════════════════════
#  Noise Removal (popups, chatbots, modals)
# ══════════════════════════════════════════════════════════════════════════════

REMOVE_POPUPS_AND_OVERLAYS = """() => {
    const keepTags = new Set(['BODY', 'HTML', 'MAIN', 'ARTICLE', 'SECTION']);

    // Cookie consent (second pass) + survey/feedback popups
    document.querySelectorAll(
        '.gc-popup, .modal, ' +
        '[class*="survey"], [id*="survey"], ' +
        '[class*="popup"], [id*="popup"], ' +
        '.foresee-invitation, [class*="medallia"], ' +
        '[role="dialog"], [aria-modal="true"], ' +
        '[class*="cookie-banner"], [class*="cookie-consent"], ' +
        '[id*="cookie-banner"], [id*="cookie-consent"], ' +
        '[class*="CookieConsent"], [id*="CookieConsent"], ' +
        '[class*="privacy-banner"], [id*="privacy-banner"], ' +
        '#onetrust-consent-sdk, .onetrust-pc-dark-filter, ' +
        '#CybotCookiebotDialog, .cc-window, .cc-banner'
    ).forEach(el => {
        if (!keepTags.has(el.tagName)) el.remove();
    });

    // Backdrop / overlay masks
    document.querySelectorAll(
        '.modal-backdrop, .overlay-mask'
    ).forEach(el => {
        if (!keepTags.has(el.tagName)) el.remove();
    });

    // Restore body scroll
    if (document.body) {
        document.body.style.overflow = 'auto';
        document.body.classList.remove('modal-open');
    }
}"""

REMOVE_GENERIC_CHATBOTS = """() => {
    const keepTags = new Set(['BODY', 'HTML', 'MAIN', 'ARTICLE', 'SECTION']);
    document.querySelectorAll(
        '[class*="chat-widget"], [id*="chat-widget"], ' +
        '[class*="chatbot"], [id*="chatbot"], ' +
        '[class*="live-chat"], [id*="live-chat"], ' +
        '[class*="livechat"], [id*="livechat"], ' +
        '[class*="webchat"], [id*="webchat"], ' +
        '#drift-widget, #hubspot-messages-iframe-container, ' +
        '#intercom-container, .intercom-lightweight-app, ' +
        '[class*="Intercom"], [id*="intercom"], ' +
        'iframe[title*="chat" i], iframe[title*="Chat" i], ' +
        'iframe[src*="chat"], iframe[src*="livechat"]'
    ).forEach(el => {
        if (!keepTags.has(el.tagName)) el.remove();
    });

    // Catch-all: nuke small position:fixed elements near bottom-right
    document.querySelectorAll('div, iframe, button').forEach(el => {
        if (keepTags.has(el.tagName)) return;
        const s = window.getComputedStyle(el);
        if (s.position !== 'fixed') return;
        const r = el.getBoundingClientRect();
        if (r.width < 400 && r.height < 400 &&
            r.bottom > window.innerHeight - 100 &&
            r.right > window.innerWidth - 100) {
            el.remove();
        }
    });
}"""


# ══════════════════════════════════════════════════════════════════════════════
#  Algonquin College — Site-specific snippets
# ══════════════════════════════════════════════════════════════════════════════

ALGONQUIN_READ_MORE = """() => {
    const main = document.querySelector('main') || document.body;
    // Click course description "Read More" links
    main.querySelectorAll('a.link-read-more').forEach(link => {
        try { link.click(); } catch(e) {}
    });
    // Fallback: swap data-description into DOM directly
    main.querySelectorAll('a.link-read-more[data-description]').forEach(link => {
        try {
            const full = link.getAttribute('data-description');
            const descSpan = link.previousElementSibling;
            if (descSpan && descSpan.classList.contains('course-description')) {
                descSpan.innerHTML = full;
            }
            link.style.display = 'none';
        } catch(e) {}
    });
}"""

ALGONQUIN_TABS = """() => {
    const main = document.querySelector('main') || document.body;

    // Force Algonquin monograph tab panels visible
    main.querySelectorAll('.tabs-monograph-content').forEach(panel => {
        try {
            if (!panel || !panel.style) return;
            panel.style.display = 'block';
            panel.style.visibility = 'visible';
            panel.style.opacity = '1';
            panel.style.height = 'auto';
            panel.style.overflow = 'visible';
            panel.classList.add('active', 'show', 'in');
        } catch(e) {}
    });

    // Expand course accordions
    main.querySelectorAll('.course-accordion').forEach(btn => {
        try {
            btn.setAttribute('aria-expanded', 'true');
            btn.classList.add('active');
        } catch(e) {}
    });
    main.querySelectorAll('.course-panel').forEach(panel => {
        try {
            panel.removeAttribute('hidden');
            panel.style.display = 'block';
        } catch(e) {}
    });

    // Reorder content panels to match sidebar nav order
    const container = document.getElementById('monograph-tabs-content');
    const navButtons = document.querySelectorAll('#tab-menu .monograph-tab');
    if (container && navButtons.length > 0) {
        const order = [];
        navButtons.forEach(btn => {
            const match = (btn.getAttribute('onclick') || '').match(/'([^']+)'/);
            if (match) order.push(match[1]);
        });
        order.forEach(id => {
            const panel = document.getElementById(id);
            if (panel) container.appendChild(panel);
        });
    }
}"""

ALGONQUIN_WHISTLE = """() => {
    const main = document.querySelector('main') || document.body;
    // Algonquin "whistle" accordions (day-time-programs steps)
    main.querySelectorAll('.whistle-title').forEach(trigger => {
        try {
            trigger.setAttribute('aria-selected', 'true');
            trigger.classList.add('active', 'open');
            trigger.click();
        } catch(e) {}
    });
}"""

ALGONQUIN_FOOTABLE = """() => {
    // Method 1: trigger FooTable API to show all rows
    const tables = document.querySelectorAll('.footable, table.footable');
    tables.forEach(table => {
        try {
            const ft = FooTable.get(table);
            if (ft && ft.rows && ft.rows.all) {
                ft.pageSize(9999);
            }
        } catch(e) {}
    });
    // Method 2: select max from page-size dropdown
    document.querySelectorAll('.nt_pager_selection').forEach(sel => {
        try {
            const opts = Array.from(sel.options);
            if (opts.length > 0) {
                const maxOpt = opts[opts.length - 1];
                sel.value = maxOpt.value;
                sel.dispatchEvent(new Event('change', {bubbles: true}));
            }
        } catch(e) {}
    });
    // Method 3: brute-force — unhide all footable rows
    document.querySelectorAll('.footable-page, tr.footable-detail-row')
        .forEach(row => {
            row.style.display = '';
            row.classList.remove('footable-paging-hidden');
        });
    document.querySelectorAll('tr').forEach(row => {
        if (row.style.display === 'none' &&
            row.closest('.footable, table.footable')) {
            row.style.display = '';
        }
    });
}"""

ALGONQUIN_CHECKLIST_TOGGLE = """() => {
    // Click all toggle headers to trigger their JS expansion
    document.querySelectorAll('.checklistToggleHead, [class*="ToggleHead"]').forEach(head => {
        try { head.click(); } catch(e) {}
    });
    // Brute-force: show all toggle body siblings
    document.querySelectorAll(
        '.checklistToggleBody, [class*="ToggleBody"], [class*="toggle-body"]'
    ).forEach(body => {
        try {
            body.style.display = 'block';
            body.style.visibility = 'visible';
            body.style.height = 'auto';
            body.style.overflow = 'visible';
        } catch(e) {}
    });
    // Fallback: for any toggleHead, force-show next sibling
    document.querySelectorAll('[class*="ToggleHead"], [class*="toggle-head"]').forEach(head => {
        try {
            const next = head.nextElementSibling;
            if (next) {
                next.style.display = 'block';
                next.style.visibility = 'visible';
                next.style.height = 'auto';
            }
        } catch(e) {}
    });
}"""

ALGONQUIN_CHATBOT = """() => {
    const keepTags = new Set(['BODY', 'HTML', 'MAIN', 'ARTICLE', 'SECTION']);
    // Freshchat, Wysdom AI, Tawk, Zendesk, Tidio, Crisp, etc.
    document.querySelectorAll(
        '#fc_frame, #fc-widget-container, [class*="freshchat"], ' +
        '#tawkto-chat, .tawk-widget, [id*="tawk-"], ' +
        '#launcher[data-testid], iframe[title*="Messaging" i], ' +
        '#tidio-chat, [class*="tidio"], ' +
        '#zsiq_float, .zsiq_theme1, ' +
        '#crisp-chatbox, [class*="crisp-client"], ' +
        '#wysdom-highlight, #wysdom-chat-bot, [id*="wysdom"], [class*="wysdom"]'
    ).forEach(el => {
        if (!keepTags.has(el.tagName)) el.remove();
    });
}"""

ALGONQUIN_PRE_PDF = """() => {
    // ── 1. Remove interactive widgets, sliders, and application buttons ──
    document.querySelectorAll(
        '.slick-slider, ' +
        '.card-program-information, #apply-btn, ' +
        '#monograph-type-btn, .dropdown.show, ' +
        '.footer-nav-wrapper, ' +
        '#program-banner'
    ).forEach(el => el.remove());

    // ── 2. Remove "Get Started" section (green CTA buttons) ──
    //    Matches by class/id AND by heading text content
    document.querySelectorAll(
        '[class*="get-started"], [id*="get-started"], ' +
        '[class*="getStarted"], [id*="getStarted"], ' +
        '[class*="cta-block"], [class*="cta-section"], ' +
        '[class*="future-students-cta"], ' +
        '.campus-tour-block, [class*="campus-tour"]'
    ).forEach(el => el.remove());
    // Text-based fallback: find headings containing "Get Started"
    document.querySelectorAll('h2, h3, h4').forEach(h => {
        const text = (h.textContent || '').trim();
        if (/^get\\s+started$/i.test(text)) {
            // Remove the heading and its parent section/container
            const section = h.closest('section, .widget, .block, .row, .container')
                          || h.parentElement;
            if (section) section.remove();
        }
    });

    // ── 3. Remove "Related Programs" section ──
    document.querySelectorAll(
        '[class*="related-program"], [class*="relatedProgram"], ' +
        '[id*="related-program"], [id*="relatedProgram"], ' +
        '[class*="RelatedProgram"], [id*="RelatedProgram"], ' +
        'section.related-programs, .related-programs-section'
    ).forEach(el => el.remove());
    // Text-based fallback: find headings containing "Related Programs"
    document.querySelectorAll('h2, h3, h4').forEach(h => {
        const text = (h.textContent || '').trim();
        if (/related\\s+programs?/i.test(text)) {
            const section = h.closest('section, .widget, .block, .row, .container, table')
                          || h.parentElement;
            if (section) section.remove();
        }
    });

    // ── 4. Remove bottom promotional cards ──
    //    ("What careers...", "Explore our campuses...", "Want to learn more about AC?")
    document.querySelectorAll(
        '[class*="explore-career"], [class*="explore-campus"], ' +
        '[class*="learn-more-ac"], [class*="promo-card"], ' +
        '[class*="promoCard"], [class*="future-student-promo"], ' +
        '[class*="card-deck-cta"], [class*="card-group-cta"]'
    ).forEach(el => el.remove());
    // Text-based fallback: find promo cards by known titles
    const promoTexts = [
        /what\\s+careers/i,
        /explore\\s+our\\s+campus/i,
        /want\\s+to\\s+learn\\s+more\\s+about\\s+ac/i,
        /take\\s+a\\s+virtual\\s+tour/i,
        /view\\s+events/i,
        /explore\\s+careers/i
    ];
    document.querySelectorAll('a, h3, h4, h5, p, span').forEach(el => {
        const text = (el.textContent || '').trim();
        if (promoTexts.some(re => re.test(text))) {
            // Walk up to find the card/section container
            const card = el.closest(
                '.card, .card-body, [class*="card"], ' +
                'section, .widget, .block, .col, .col-md-4, .col-lg-4'
            );
            if (card) {
                // Remove the entire card row/group if it's a promotional row
                const row = card.closest('.row, .card-deck, .card-group, .d-flex');
                if (row && row.querySelectorAll('.card, [class*="card"]').length <= 3) {
                    row.remove();
                } else {
                    card.remove();
                }
            }
        }
    });

    // ── 5. Remove site footer, disclaimer, and social icons ──
    document.querySelectorAll(
        'footer, .footer, .site-footer, ' +
        '.footer-nav-wrapper, [class*="footer-nav"], ' +
        '[role="contentinfo"], ' +
        '[class*="social-media"], [class*="social-icons"], [class*="socialMedia"], ' +
        '[class*="disclaimer"], [class*="Disclaimer"]'
    ).forEach(el => el.remove());
    // Text-based: remove disclaimer paragraph
    document.querySelectorAll('p, div, span').forEach(el => {
        const text = (el.textContent || '').trim();
        if (/every attempt is made to ensure/i.test(text) &&
            /reserves the right/i.test(text)) {
            const container = el.closest('section, .row, .container, div')
                            || el.parentElement;
            if (container && container.querySelectorAll('p, div').length <= 3) {
                container.remove();
            } else {
                el.remove();
            }
        }
    });

    // ── 6. Remove green CTA button rows by button text ──
    const ctaLabels = [
        /take a campus tour/i,
        /attend a recruitment/i,
        /create a custom viewbook/i,
        /financial aid/i,
        /co-op education/i,
        /ac pathways/i
    ];
    document.querySelectorAll('a, button, [role="button"]').forEach(el => {
        const text = (el.textContent || '').trim();
        if (ctaLabels.some(re => re.test(text))) {
            const row = el.closest('.row, section, .container, .d-flex, .grid, div');
            if (row) {
                // Check if this row contains multiple CTA buttons
                const btns = row.querySelectorAll('a, button, [role="button"]');
                const matchCount = Array.from(btns).filter(b =>
                    ctaLabels.some(re => re.test((b.textContent || '').trim()))
                ).length;
                if (matchCount >= 2) {
                    row.remove();
                }
            }
        }
    });
}"""


# ══════════════════════════════════════════════════════════════════════════════
#  Strip Print Media — force screen layout in PDF rendering
# ══════════════════════════════════════════════════════════════════════════════

STRIP_PRINT_MEDIA = """() => {
    // 1. Remove <link media="print"> stylesheets entirely
    document.querySelectorAll('link[media="print"]').forEach(el => el.remove());

    // 2. Walk all stylesheets and delete @media print rules
    for (const sheet of document.styleSheets) {
        try {
            const rules = sheet.cssRules || sheet.rules;
            if (!rules) continue;
            // Walk backwards so deletion doesn't shift indices
            for (let i = rules.length - 1; i >= 0; i--) {
                const rule = rules[i];
                if (rule.type === CSSRule.MEDIA_RULE &&
                    rule.conditionText &&
                    rule.conditionText.includes('print')) {
                    sheet.deleteRule(i);
                }
            }
        } catch(e) {
            // Cross-origin stylesheets throw SecurityError — skip them
        }
    }

    // 3. Force all elements to use screen-visible styles
    //    (override common print-only hiding patterns)
    const style = document.createElement('style');
    style.textContent = `
        @media print {
            * {
                color-adjust: exact !important;
                -webkit-print-color-adjust: exact !important;
                print-color-adjust: exact !important;
            }
            body, html {
                width: 100% !important;
                font-size: inherit !important;
            }
            /* Force all elements to stay as screen layout */
            .container, .row, [class*="col-"],
            main, article, section, div {
                width: auto !important;
                max-width: none !important;
                float: none !important;
                position: static !important;
                display: block !important;
                overflow: visible !important;
            }
            /* Don't hide navigation/headers (keeps original look) */
            header, nav, aside,
            [role="banner"], [role="navigation"] {
                display: block !important;
                visibility: visible !important;
                position: relative !important;
            }
            img {
                display: inline-block !important;
                visibility: visible !important;
                max-width: 100% !important;
            }
        }
    `;
    document.head.appendChild(style);
}"""


# ══════════════════════════════════════════════════════════════════════════════
#  Print CSS (legacy — used by sites without STRIP_PRINT_MEDIA)
# ══════════════════════════════════════════════════════════════════════════════

PRINT_CSS_GENERIC = """
@media print {
    * {
        color-adjust: exact !important;
        -webkit-print-color-adjust: exact !important;
        print-color-adjust: exact !important;
    }
    body, html { width: 100% !important; }
    [style*="position: fixed"], [style*="position: sticky"],
    header, footer, nav, aside {
        position: relative !important;
        top: auto !important;
        z-index: auto !important;
        display: block !important;
        visibility: visible !important;
        opacity: 1 !important;
        height: auto !important;
        overflow: visible !important;
    }
    img {
        display: inline-block !important;
        visibility: visible !important;
        max-width: 100% !important;
    }
    .noprint { display: none !important; }
}
"""

# canada.ca specific: includes GC Web Experience Toolkit selectors
PRINT_CSS_CANADA_GOV = """
@media print {
    * {
        color-adjust: exact !important;
        -webkit-print-color-adjust: exact !important;
        print-color-adjust: exact !important;
    }
    body, html { width: 100% !important; }

    /* ── HIDE site footer only (identical on every page → pollutes RAG) ── */
    #wb-info, footer, [role="contentinfo"] {
        display: none !important;
    }

    /* ── Keep main content visible with proper layout ── */
    [style*="position: fixed"], [style*="position: sticky"],
    header, nav, aside,
    [role="banner"], [role="navigation"] {
        position: relative !important;
        top: auto !important;
        z-index: auto !important;
        display: block !important;
        visibility: visible !important;
        opacity: 1 !important;
        height: auto !important;
        overflow: visible !important;
    }
    img {
        display: inline-block !important;
        visibility: visible !important;
        max-width: 100% !important;
    }
    .noprint, .wb-inv { display: none !important; }
}
"""


# ══════════════════════════════════════════════════════════════════════════════
#  Source URL Banner
# ══════════════════════════════════════════════════════════════════════════════

SOURCE_BANNER = """(args) => {
    const banner = document.createElement('div');
    banner.innerHTML = `
        <div style="
            background: #f0f0f0;
            border-bottom: 2px solid ${args.borderColor || '#26374a'};
            padding: 8px 16px;
            font-family: Arial, sans-serif;
            font-size: 12px;
            color: #333;
            display: flex;
            justify-content: space-between;
            align-items: center;
        ">
            <span>
                Source: <a href="${args.url}" style="color: #2b4380; text-decoration: underline; font-size: 12px;">${args.url}</a>
            </span>
            <span style="color: #666; font-size: 11px;">
                Captured: ${args.date}
            </span>
        </div>
    `;
    document.body.insertBefore(banner, document.body.firstChild);
}"""


# ══════════════════════════════════════════════════════════════════════════════
#  Remove GC Site Footer (DOM removal — more reliable than CSS display:none)
# ══════════════════════════════════════════════════════════════════════════════

REMOVE_GC_FOOTER = """() => {
    // Remove the entire site footer — it's identical on every page
    // and pollutes RAG vector store with duplicated non-informative chunks
    const footer = document.getElementById('wb-info');
    if (footer) footer.remove();
    // Fallback: remove any <footer> or .global-footer elements
    document.querySelectorAll('footer, .global-footer').forEach(el => el.remove());
}"""

