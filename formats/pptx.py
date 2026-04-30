"""PPTX exporter.

TODO: Copy logic from old repo:
  - tools/presentations.py → _create_presentation()

Template path:
  from app.core.templates import TemplateRegistry
  template = TemplateRegistry.get("pptx")  # str | None
"""
from __future__ import annotations

from app.core.models import FileRef
from app.core.templates import TemplateRegistry


def export_pptx(
    slides: list[dict] | str,
    filename: str | None,
) -> FileRef:
    """Export *slides* as a PowerPoint presentation."""
    raise NotImplementedError(
        "TODO: copy _create_presentation from tools/presentations.py.\n"
        "Use TemplateRegistry.get('pptx') instead of module-level globals."
    )
