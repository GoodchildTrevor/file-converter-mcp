"""CSV exporter.

TODO: Copy logic from old repo:
  - file_export_mcp.py → _create_csv()
"""
from __future__ import annotations

from typing import Any

from app.core.models import FileRef
from storage.files import write_csv


def export_csv(rows: list[list[Any]], filename: str | None) -> FileRef:
    """Write *rows* as a CSV file."""
    raise NotImplementedError(
        "TODO: copy _create_csv logic from old repo (essentially: write_csv(rows, filename))"
    )
