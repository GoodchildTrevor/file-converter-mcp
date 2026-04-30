"""Raw text exporter — handles txt, md, html, json, xml.

TODO: Copy logic from old repo:
  - file_export_mcp.py  →  _create_raw_file()
  - utils.py            →  _convert_markdown_to_structured()

Fix that was needed in old code:
  _convert_markdown_to_structured() returns list[dict], not str.
  This module must join the structured items back into a plain string
  before writing.
"""
from __future__ import annotations

import json
import logging

from app.core.models import ExportFormat, FileRef
from storage.files import write_text

log = logging.getLogger(__name__)


def export_raw(
    content: str | list | dict,
    filename: str | None,
    fmt: ExportFormat = ExportFormat.TXT,
) -> FileRef:
    """Export *content* as a plain text file.

    Handles: txt, md, html, json, xml.
    """
    raise NotImplementedError(
        "TODO: copy _create_raw_file + _convert_markdown_to_structured from old repo"
    )
