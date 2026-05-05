"""
Algonquin College site profile.
亚岗昆学院网站 profile — 学术项目页面、学费、奖学金。

Characteristics:
  - Monograph tabbed content (tabs-monograph-content, #monograph-tabs-content)
  - Course accordions (.course-accordion / .course-panel)
  - FooTable paginated tables (scholarships)
  - Checklist toggles (.checklistToggleHead / .checklistToggleBody)
  - Whistle accordions (.whistle-title for "Step 1: Choose a Program")
  - "Read More" links with data-description swap
  - Freshchat + Wysdom AI chatbot widgets
  - Slick sliders, apply buttons, program banners
"""

from engine_v2.crawling import js_snippets as JS
from engine_v2.crawling.site_profile import SiteProfile, register

algonquin = SiteProfile(
    name="Algonquin College",
    domains=["algonquincollege.com", "www.algonquincollege.com"],

    # ── Discovery ──
    scope_strategy="first_segment",

    # ── Algonquin-specific content expansion ──
    # These run AFTER the generic expansion steps (details, bootstrap, etc.)
    extra_expansion_steps=[
        (JS.ALGONQUIN_READ_MORE, 1000),       # a.link-read-more + data-description
        (JS.ALGONQUIN_TABS, 1500),            # monograph tabs + course accordions + reorder
        (JS.ALGONQUIN_WHISTLE, 1000),         # whistle-title step accordions
        (JS.ALGONQUIN_FOOTABLE, 1500),        # FooTable paginated tables
        (JS.ALGONQUIN_CHECKLIST_TOGGLE, 1000),  # checklistToggleHead/Body
    ],

    # ── Noise Removal ──
    extra_noise_removal_js=JS.ALGONQUIN_CHATBOT,  # Wysdom + Freshchat

    # ── Pre-PDF Cleanup ──
    pre_pdf_js=JS.ALGONQUIN_PRE_PDF,  # Remove sliders, apply buttons, banners

    # ── Print CSS ──
    print_css=JS.PRINT_CSS_GENERIC,

    # ── Validation: skip blank program pages ──
    skip_rules=[
        lambda info, url: info["wordCount"] < 30 and "/program/" in url,
    ],

    # ── Rate Limiting ──
    min_delay_between=5.0,
)

register(algonquin)
