"""DOCX exporter."""
from __future__ import annotations

import logging
from typing import Any, Optional

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.shared import Pt

from app.core.models import FileRef
from app.core.templates import TemplateRegistry
from formats.coerce import coerce, coerce_or_error, strip_code_fence
from formats.content import validate_blocks
from storage.paths import new_export_folder, public_url, resolve_output_path

log = logging.getLogger(__name__)


def _normalize_content(content: list[dict] | str) -> list[dict]:
    """Normalize content to a list of structured dicts.

    If *content* is a JSON-encoded string, deserialize it. If it is a
    JSON-like string that does not parse (truncated or malformed), raise
    ValueError. If it is a plain string, strip a markdown code fence, if
    present, and split the string into one paragraph per line. In all
    other cases, return an empty list.
    """
    content = coerce(content)
    if isinstance(content, str):
        recovered, error = coerce_or_error(content, "docx")
        if error is not None:
            raise ValueError(error["error"]["message"])
        content = strip_code_fence(content)
        return [
            {"type": "paragraph", "text": line}
            for line in content.splitlines()
            if line.strip()
        ]
    return validate_blocks(content)


def _validate_content_blocks(content: list) -> None:
    """Check that every item is a content block that a renderer knows.

    Raise ValueError with the index and the reason when an item is not
    valid. The check runs before the export starts, so a bad input does
    not produce a partial file.

    Known block types and the fields they need:
    - heading:   "text" (str), "level" (int) is optional;
    - title:     "text" (str);
    - subtitle:  "text" (str);
    - paragraph: "text" (str);
    - list:      "items" (list of str);
    - table:     "data" (2-D list; each row is a list of cell values).
    """
    known_types = {
        "heading": ("text", str),
        "title": ("text", str),
        "subtitle": ("text", str),
        "paragraph": ("text", str),
        "list": ("items", list),
        "table": ("data", list),
    }

    for index, item in enumerate(content):
        if isinstance(item, str):
            continue
        if not isinstance(item, dict):
            raise ValueError(
                f"Content item {index} is not a dict or a string. "
                f"Send a content-block dict, for example "
                f'{{"type": "paragraph", "text": "..."}}.'
            )

        item_type = item.get("type")
        if item_type not in known_types:
            raise ValueError(
                f"Content item {index} has unknown type {item_type!r}. "
                f"Use one of: {', '.join(sorted(known_types))}."
            )

        field_name, field_type = known_types[item_type]
        field_value = item.get(field_name)
        if field_value is None:
            raise ValueError(
                f"Content item {index} of type {item_type!r} has no "
                f'"{field_name}" field.'
            )
        if not isinstance(field_value, field_type):
            raise ValueError(
                f"Content item {index} of type {item_type!r} has a "
                f'"{field_name}" field with the wrong type. '
                f"Expected {field_type.__name__}, got "
                f"{type(field_value).__name__}."
            )

        if item_type == "table":
            for row_index, row in enumerate(field_value):
                if not isinstance(row, list):
                    raise ValueError(
                        f"Content item {index} (table) has a row that is "
                        f"not a list (row {row_index})."
                    )


def _load_document(template_path: str | None) -> Any:
    """Load a style template or create an empty document.

    Remove all template content, but keep the style definitions.
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


def _replace_in_paragraph(paragraph: Any, replacements: dict[str, str]) -> None:
    """Replace {{key}} placeholders in a paragraph, handling split runs.

    Word often splits a placeholder like {{Who}} across multiple runs
    (e.g. "{{", "Who", "}}").  We read the full paragraph text, apply all
    replacements, then write the result back into the first run and clear
    the remaining runs -- preserving the formatting of the first run.
    """
    full_text = paragraph.text
    new_text = full_text
    for key, value in replacements.items():
        new_text = new_text.replace(f"{{{{{key}}}}}", str(value))
    if new_text == full_text:
        return
    if paragraph.runs:
        paragraph.runs[0].text = new_text
        for run in paragraph.runs[1:]:
            run.text = ""
    else:
        paragraph.clear()
        paragraph.add_run(new_text)


def _process_template_replacements(template_path: str | None, replacements: dict[str, str]) -> Any:
    """Open a named template file and replace {{key}} placeholders with values."""
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
        _replace_in_paragraph(paragraph, replacements)

    for table in doc.tables:
        for row in table.rows:
            for cell in row.cells:
                for paragraph in cell.paragraphs:
                    _replace_in_paragraph(paragraph, replacements)

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

        renderer = _RENDERERS.get(item_type)
        if renderer:
            renderer(doc, item)


def export_docx(
    content: list[dict] | str,
    filename: str | None,
    template_vars: dict[str, str] | None = None,
    template_path: Optional[str] = None,
) -> FileRef:
    """Export *content* as a Word document and return a FileRef.

    :param content: Structured content list or plain markdown string.
    :param filename: Desired output filename (extension added if missing).
    :param template_vars: When provided, opens the named DOCX template and
        performs ``{{key}}`` placeholder substitution instead of building the
        document from *content*.
    :param template_path: Optional explicit path to a DOCX template file.
    :return: FileRef with url, path, and name.
    :raises formats.content.ContentValidationError: when *content* contains
        malformed blocks (unknown/missing 'type', bad table data, etc.).
    """
    folder = new_export_folder()
    filepath, fname = resolve_output_path(folder, filename or "", "docx")
    url = public_url(folder, fname)

    resolved_path = template_path or TemplateRegistry.get("docx")

    if template_vars:
        doc = _process_template_replacements(resolved_path, template_vars)
        doc.save(filepath)
        return FileRef(url=url, path=filepath, name=fname)

    # --- Content-build mode ---
    normalized = _normalize_content(content)
    _validate_content_blocks(normalized)
    doc = _load_document(template_path)
    _append_content(doc, normalized)
    doc.save(filepath)
    return FileRef(url=url, path=filepath, name=fname)


def _create_docx(
    content: list[dict] | str,
    filename: str | None,
    folder_path: str | None = None,
    template_vars: dict[str, str] | None = None,
) -> dict[str, str]:
    """Legacy helper returning ``{"url", "path"}`` -- delegates to export_docx."""
    ref = export_docx(content=content, filename=filename, template_vars=template_vars)
    return {"url": ref.url, "path": ref.path}
