"""DOCX exporter."""
from __future__ import annotations

import logging
from typing import Any

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.shared import Pt

from app.core.models import FileRef
from app.core.templates import TemplateRegistry
from storage.paths import new_export_folder, public_url, resolve_output_path

log = logging.getLogger(__name__)


def _normalize_content(content: list[dict] | str) -> list[dict]:
    """Normalize content to a list of structured dicts."""
    if isinstance(content, str):
        return [
            {"type": "paragraph", "text": line}
            for line in content.splitlines()
            if line.strip()
        ]
    if isinstance(content, list):
        return content
    return []


def _load_document(template_path: str | None) -> Any:
    """Load a style template or create an empty document.

    Clears all content from the template so we start with a blank
    slate but retain the style definitions.
    """
    if not template_path:
        return Document()

    try:
        doc = Document(template_path)
        body = doc.element.body
        for child in list(body):
            if child.tag.endswith("}sectPr"):
                continue
            body.remove(child)
        return doc
    except Exception:
        log.exception("Failed to load DOCX style template '%s'; falling back to blank document", template_path)
        return Document()


def _process_template_replacements(template_path: str | None, replacements: dict[str, str]) -> Any:
    """Open a template file and replace placeholder tokens with values."""
    if not template_path:
        log.warning("No 'docx' template registered; using empty document for template-fill mode")
        doc = Document()
    else:
        try:
            doc = Document(template_path)
        except Exception:
            log.exception("Failed to open DOCX template '%s'", template_path)
            doc = Document()

    for paragraph in doc.paragraphs:
        for key, value in replacements.items():
            if key in paragraph.text:
                # Replace while preserving the first run's formatting.
                if paragraph.runs:
                    paragraph.runs[0].text = paragraph.text.replace(key, str(value))
                    for run in paragraph.runs[1:]:
                        run.text = ""
                else:
                    paragraph.text = paragraph.text.replace(key, str(value))

    return doc


def _render_title(doc: Any, item: dict) -> None:
    p = doc.add_paragraph(item.get("text", ""))
    try:
        p.style = doc.styles["Heading 1"]
    except KeyError:
        run = p.runs[0] if p.runs else p.add_run(item.get("text", ""))
        run.font.size = Pt(18)
        run.font.bold = True
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER


def _render_subtitle(doc: Any, item: dict) -> None:
    p = doc.add_paragraph(item.get("text", ""))
    try:
        p.style = doc.styles["Heading 2"]
    except KeyError:
        run = p.runs[0] if p.runs else p.add_run(item.get("text", ""))
        run.font.size = Pt(14)
        run.font.bold = True
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER


def _render_heading(doc: Any, item: dict) -> None:
    level = item.get("level", 1)
    if level == 1:
        _render_title(doc, item)
    elif level == 2:
        _render_subtitle(doc, item)
    else:
        p = doc.add_paragraph(item.get("text", ""))
        style_name = f"Heading {min(level, 9)}"
        try:
            p.style = doc.styles[style_name]
        except KeyError:
            run = p.runs[0] if p.runs else p.add_run(item.get("text", ""))
            run.font.bold = True


def _render_paragraph(doc: Any, item: dict) -> None:
    p = doc.add_paragraph(item.get("text", ""))
    try:
        p.style = doc.styles["Normal"]
    except KeyError:
        pass


def _render_list(doc: Any, item: dict) -> None:
    for text in item.get("items", []):
        p = doc.add_paragraph(str(text))
        for style_name in ("List Bullet", "List Paragraph", "Normal"):
            try:
                p.style = doc.styles[style_name]
                break
            except KeyError:
                continue


def _render_table(doc: Any, item: dict) -> None:
    data = item.get("data", [])
    if not data:
        return

    cols = max(len(row) for row in data)
    table = doc.add_table(rows=len(data), cols=cols)

    for i, row in enumerate(data):
        for j, cell_value in enumerate(row):
            cell = table.cell(i, j)
            cell.text = str(cell_value)
            if i == 0:
                for para in cell.paragraphs:
                    for run in para.runs:
                        run.font.bold = True
                    para.alignment = WD_ALIGN_PARAGRAPH.CENTER


_RENDERERS = {
    "title": _render_title,
    "subtitle": _render_subtitle,
    "heading": _render_heading,
    "paragraph": _render_paragraph,
    "list": _render_list,
    "table": _render_table,
}


def _append_content(doc: Any, content: list[dict]) -> None:
    """Append structured content items to the document."""
    for item in content:
        if isinstance(item, str):
            _render_paragraph(doc, {"text": item})
            continue
        if not isinstance(item, dict):
            continue

        item_type = item.get("type")

        if item_type == "image_query":
            log.warning("image_query items are not supported in the DOCX exporter — skipped")
            continue

        renderer = _RENDERERS.get(item_type)
        if renderer:
            renderer(doc, item)
        elif "text" in item:
            # Unknown type but has text — treat as paragraph.
            _render_paragraph(doc, item)


def export_docx(
    content: list[dict] | str,
    filename: str | None,
    template_vars: dict[str, str] | None = None,
) -> FileRef:
    """Export *content* as a Word document and return a FileRef.

    :param content: Structured content list or plain markdown string.
    :param filename: Desired output filename (extension added if missing).
    :param template_vars: When provided, opens the registered DOCX template
        and performs placeholder substitution instead of building the document
        from *content*.
    :return: FileRef with url, path, and name.
    """
    folder = new_export_folder()
    filepath, fname = resolve_output_path(folder, filename or "", "docx")
    url = public_url(folder, fname)

    template_path = TemplateRegistry.get("docx")

    # --- Template-fill mode ---
    if template_vars:
        doc = _process_template_replacements(template_path, template_vars)
        doc.save(filepath)
        return FileRef(url=url, path=filepath, name=fname)

    # --- Content-build mode ---
    doc = _load_document(template_path)
    _append_content(doc, _normalize_content(content))
    doc.save(filepath)
    return FileRef(url=url, path=filepath, name=fname)


def _create_docx(
    content: list[dict] | str,
    filename: str,
    folder_path: str | None = None,
    template_vars: dict[str, str] | None = None,
) -> dict[str, str]:
    """Legacy helper returning ``{"url", "path"}`` — delegates to export_docx."""
    ref = export_docx(content=content, filename=filename, template_vars=template_vars)
    return {"url": ref.url, "path": ref.path}
    