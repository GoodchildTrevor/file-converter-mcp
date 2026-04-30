"""Raw text exporter — handles txt, md, html, json, xml.
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


def _create_raw_file(
  content: str, 
  filename: str | None, 
  folder_path: str | None = None
) -> dict:
    """
    :param content: The content to write to the file
    :param filename: The filename to write to
    :param folder_path: The folder path to write to
    :return: A dictionary with the url and path of the file                 
    """
    log.debug("Creating raw file")
    folder = new_export_folder()
    filepath, fname = resolve_output_path(folder, filename or "", ext)

    if fname.lower().endswith(".xml") and isinstance(content, str) and not content.strip().startswith("<?xml"):
        content = f'<?xml version="1.0" encoding="UTF-8"?>\n{content}'

    with open(filepath, "w", encoding="utf-8") as f:
        f.write(content or "")

    return {"url": _public_url(folder_path, fname), "path": filepath}


def _convert_markdown_to_structured(markdown_content: str) -> list[dict[str, str]]:
    """
    Convert lightweight Markdown-like content into a list of structured blocks for document generation (e.g., Word).
    Supports:
    - `# Title`, `## Heading`, `### Subheading`
    - `- Item` or `* Item` for bullets
    - `**bold**` (only full-line bold)
    - Plain paragraphs
    .. note::
        Does *not* support nested lists, links, code blocks, or inline formatting beyond bold.
    :param markdown_content: Raw markdown text
    :type markdown_content: str
    :return: List of dicts with keys `"text"` (str) and `"type"` (str: `"title"`, `"heading"`, `"subheading"`, `"bullet"`, `"bold"`, `"paragraph"`)
    """
    if not markdown_content or not isinstance(markdown_content, str):
        return []

    lines: list[str] = markdown_content.split('\n')
    structured: list[dict[str, str]] = []

    for line in lines:
        stripped_line: str = line.strip()
        if not stripped_line:
            continue

        if stripped_line.startswith('# '):
            structured.append({"text": stripped_line[2:].strip(), "type": "title"})
        elif stripped_line.startswith('## '):
            structured.append({"text": stripped_line[3:].strip(), "type": "heading"})
        elif stripped_line.startswith('### ') or stripped_line.startswith('#### '):
            prefix_len: int = 4 if stripped_line.startswith('### ') else 5
            structured.append({"text": stripped_line[prefix_len:].strip(), "type": "subheading"})
        elif stripped_line.startswith('- ') or stripped_line.startswith('* '):
            structured.append({"text": stripped_line[2:].strip(), "type": "bullet"})
        elif stripped_line.startswith('**') and stripped_line.endswith('**'):
            structured.append({"text": stripped_line[2:-2].strip(), "type": "bold"})
        else:
            structured.append({"text": stripped_line, "type": "paragraph"})

    return structured
