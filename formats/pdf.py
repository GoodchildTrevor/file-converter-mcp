"""PDF exporter.

TODO: Copy logic from old repo:
  - tools/file_export_mcp.py → _create_pdf()  (async)
  - tools/pdf_renderer.py    → render_html_elements(), styles

Fix that was needed in old code:
  reportlab imports (Paragraph, SimpleDocTemplate) must be at module level,
  not inside the function body.
"""
from __future__ import annotations

from app.core.models import FileRef


async def export_pdf(
    content: str | list,
    filename: str | None,
) -> FileRef:
    """Export markdown/structured *content* as a PDF."""
    raise NotImplementedError(
        "TODO: copy _create_pdf from file_export_mcp.py and render_html_elements\n"
        "from pdf_renderer.py. Move reportlab imports to module level."
    )
