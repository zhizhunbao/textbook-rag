"""report — Report generation module.

Public API:
    ReportGenerator        — generates Markdown reports from chat + evaluation data
    generate_global_report — cross-session quality report (EC-T3-04)
"""

from .generator import ReportGenerator, generate_global_report

__all__ = ["ReportGenerator", "generate_global_report"]
