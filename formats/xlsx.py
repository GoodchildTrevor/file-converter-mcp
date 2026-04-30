"""XLSX exporter.

TODO: Copy logic from old repo:
  - tools/spreadsheets.py → _create_excel()

Template path:
  from app.core.templates import TemplateRegistry
  template = TemplateRegistry.get("xlsx")  # str | None
"""
from __future__ import annotations

from typing import Any

from app.core.models import FileRef
from app.core.templates import TemplateRegistry


def export_xlsx(
    rows: list[list[Any]],
    filename: str | None,
    title: str | None = None,
) -> FileRef:
    """Export *rows* as an Excel workbook."""
    raise NotImplementedError(
        "TODO: copy _create_excel from tools/spreadsheets.py.\n"
        "Use TemplateRegistry.get('xlsx') instead of module-level globals."
    )
