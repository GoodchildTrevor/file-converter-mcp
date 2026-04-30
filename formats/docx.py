"""DOCX exporter.

TODO: Copy logic from old repo:
  - tools/texts.py → _create_word(), _process_docx_template()

Template path:
  from app.core.templates import TemplateRegistry
  template = TemplateRegistry.get("docx")  # str | None

NO globals here. NO module-level env reads.
"""
from __future__ import annotations

from typing import Any

from app.core.models import FileRef
from app.core.templates import TemplateRegistry


def export_docx(
    content: list[dict] | str,
    filename: str | None,
    template_vars: dict[str, str] | None = None,
) -> FileRef:
    """Export *content* as a Word document.

    Args:
        content: Structured content list or markdown string.
        filename: Output filename.
        template_vars: Placeholder → value mapping for template-fill mode.
    """
    raise NotImplementedError(
        "TODO: copy _create_word + _process_docx_template from tools/texts.py.\n"
        "Use TemplateRegistry.get('docx') instead of module-level globals."
    )
