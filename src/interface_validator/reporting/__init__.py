"""Integración de los resultados consolidados con el reporte Allure."""
from .allure_helpers import (
    attach_executive_report,
    collect_failures,
    report_document,
    report_section,
)
from .html_report import generate_report, render_html

__all__ = [
    "report_document",
    "report_section",
    "attach_executive_report",
    "collect_failures",
    "generate_report",
    "render_html",
]
