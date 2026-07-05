"""Render an HTML report from the shared context dictionary.

The frontend opens the response in a new window and lets the browser handle
print-to-PDF — exactly the workflow the Alpha used, and the most portable
option that doesn't require GTK or a headless browser at install time.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader, select_autoescape

from app.runtime import is_frozen, resource_path

# Templates ship next to this module in source mode; in a frozen build they're
# bundled as data under the PyInstaller root (see the .spec datas entry).
_TEMPLATE_DIR = (
    resource_path("app", "reporting", "templates")
    if is_frozen()
    else Path(__file__).parent / "templates"
)

_env = Environment(
    loader=FileSystemLoader(_TEMPLATE_DIR),
    autoescape=select_autoescape(["html", "xml"]),
    trim_blocks=True,
    lstrip_blocks=True,
)


from app.reporting.currency import format_currency_aud


def _money(value: Any) -> str:
    return format_currency_aud(value)


def _pct(value: Any, decimals: int = 1) -> str:
    if value is None:
        return "—"
    try:
        return f"{float(value) * 100:.{decimals}f}%"
    except (TypeError, ValueError):
        return "—"


def _date(value: Any) -> str:
    if value is None:
        return "—"
    if hasattr(value, "isoformat"):
        return value.isoformat()[:10]
    return str(value)[:10]


_env.filters.update({"money": _money, "pct": _pct, "date": _date})


def render_html_report(context: dict[str, Any]) -> str:
    template_name = (
        "report_executive.html" if context.get("kind") == "executive" else "report_board.html"
    )
    template = _env.get_template(template_name)
    return template.render(**context)
