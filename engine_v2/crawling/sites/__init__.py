"""
Site profiles — auto-import all profiles on package load.
导入这个包时自动注册所有网站 profile 到注册表。
"""

# Import all site profile modules to trigger register() calls
from engine_v2.crawling.sites import (  # noqa: F401
    generic,
    canada_gov,
    algonquin,
    provincial,
    banks,
    telecom,
    federal_cdic,
    taxtips,
)
