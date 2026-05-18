"""HTML-to-PDF pipeline. Phase 8 installs WeasyPrint and implements this.

The same Jinja templates and CSS files that drive browser preview will be
passed through here, so preview and downloaded PDF stay byte-identical.
"""


def render_pdf(template_name: str, context: dict) -> bytes:
    """Render a Jinja template + context to a PDF byte string.

    Implemented in Phase 8 once WeasyPrint is installed. Browser preview
    routes work without this; PDF download routes will call into it.
    """
    raise NotImplementedError("render_pdf lands in Phase 8 (WeasyPrint integration)")
