"""HTML-to-PDF pipeline. Renders the same Jinja templates the browser
preview uses, so on-screen and downloaded PDF stay byte-identical.

WeasyPrint requires GTK runtime libraries (gobject, pango, cairo,
gdk-pixbuf). These are present on Linux (the production Railway target)
but commonly missing on a fresh Windows machine. We detect the import
failure at module load time and expose `WEASYPRINT_AVAILABLE` so the
PDF routes can serve a friendly fallback page instead of crashing.
"""
from __future__ import annotations

import logging
import os
import re
from typing import Iterable, Optional

from flask import current_app, render_template

log = logging.getLogger(__name__)

# Defer the actual native-library load until first import — but bail
# gracefully if GTK isn't installed so the rest of the app keeps working.
WEASYPRINT_AVAILABLE = False
_IMPORT_ERROR: Optional[BaseException] = None
HTML = None
CSS = None
try:
    from weasyprint import HTML as _HTML, CSS as _CSS  # noqa: E402
    # Trigger the native library probe by creating a minimal HTML object.
    _HTML(string="<html></html>")
    HTML = _HTML
    CSS = _CSS
    WEASYPRINT_AVAILABLE = True
except Exception as exc:  # ImportError, OSError (missing GTK libs), etc.
    _IMPORT_ERROR = exc
    log.warning("WeasyPrint unavailable — PDF download routes will serve fallback page. %s", exc)


def is_available() -> bool:
    return WEASYPRINT_AVAILABLE


def import_error_message() -> str:
    """Short, user-safe description of why PDF generation is offline."""
    if WEASYPRINT_AVAILABLE:
        return ""
    return f"{type(_IMPORT_ERROR).__name__}: {_IMPORT_ERROR}"


def render_pdf(template_name: str, context: dict, css_files: Optional[Iterable[str]] = None) -> bytes:
    """Render a Jinja template + context through WeasyPrint and return PDF
    bytes.

    Args:
        template_name: Jinja template path (e.g. "reports/sacs.html").
            Must be one of the report templates that include @page +
            @media print rules.
        context: same dict that the browser-preview route would pass.
        css_files: list of static-folder-relative CSS paths to attach.
            We pass these explicitly rather than relying on WeasyPrint's
            URL fetcher to resolve <link> tags — it keeps the network
            stack out of the PDF pipeline.

    Returns:
        PDF bytes (application/pdf).

    Raises:
        RuntimeError: WeasyPrint is not loaded (callers should pre-check
            via `is_available()` to serve a friendly page instead).
    """
    if not WEASYPRINT_AVAILABLE:
        raise RuntimeError(
            "WeasyPrint is not available in this environment. "
            "Install GTK runtime (Windows) or libcairo/libpango/libgdk-pixbuf "
            "(Linux) and re-deploy. "
            f"Original error: {import_error_message()}"
        )

    html_str = render_template(template_name, **context)

    static_folder = current_app.static_folder
    css_objs = []
    for path in (css_files or []):
        full = path if os.path.isabs(path) else os.path.join(static_folder, path)
        if os.path.exists(full):
            css_objs.append(CSS(filename=full))
        else:
            log.warning("PDF render: stylesheet not found at %s", full)

    # base_url so any remaining relative href / src inside the template can
    # resolve against the app's static folder.
    html_obj = HTML(string=html_str, base_url=current_app.root_path)
    return html_obj.write_pdf(stylesheets=css_objs)


# -- filename sanitizer ----------------------------------------------------

_BAD_FILENAME_CHARS = re.compile(r"[^a-z0-9\-]+")
_MULTI_DASH = re.compile(r"-+")


def sanitize_for_filename(text: str) -> str:
    """Convert arbitrary text (household name, quarter label) into a
    safe filename fragment: lowercase, ASCII-ish, hyphen-separated.
    """
    s = (text or "").strip().lower()
    s = _BAD_FILENAME_CHARS.sub("-", s)
    s = _MULTI_DASH.sub("-", s)
    return s.strip("-") or "untitled"


def build_filename(prefix: str, household: str, quarter: str) -> str:
    """Standard PDF filename pattern: <prefix>_<household>_<quarter>.pdf"""
    return f"{prefix}_{sanitize_for_filename(household)}_{sanitize_for_filename(quarter)}.pdf"
