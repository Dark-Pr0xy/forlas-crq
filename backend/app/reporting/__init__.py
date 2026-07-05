"""HTML / PDF / DOCX report rendering."""

from app.reporting.data import build_report_context
from app.reporting.docx_report import build_docx_report
from app.reporting.html_report import render_html_report

__all__ = ["build_docx_report", "build_report_context", "render_html_report"]
