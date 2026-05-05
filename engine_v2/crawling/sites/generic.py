"""
Generic site profile — fallback for any unrecognized website.
通用 profile，适用于所有未注册专属 profile 的网站。
"""

from engine_v2.crawling import js_snippets as JS
from engine_v2.crawling.site_profile import SiteProfile, register

generic = SiteProfile(
    name="Generic",
    domains=["*"],                     # Wildcard — fallback for all domains
    scope_strategy="first_segment",
    print_css=JS.PRINT_CSS_GENERIC,
    min_delay_between=5.0,
)

register(generic)
