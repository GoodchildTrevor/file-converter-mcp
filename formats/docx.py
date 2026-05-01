"""DOCX exporter.
"""
from __future__ import annotations

import logging
from typing import Any, Optional

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH

from app.core.models import FileRef
from app.core.templates import TemplateRegistry
from storage.paths import new_export_folder, public_url, resolve_output_path

log = logging.getLogger(__name__)
log.debug("DOCX exporter initialized")


def _convert_markdown_to_structured(content: str) -> list[dict]:
    return [{"type": "paragraph", "text": line} for line in content.splitlines() if line.strip()]


def _normalize_content(content: list[dict] | str) -> list[dict]:
    if isinstance(content, str):
        return _convert_markdown_to_structured(content)
    if isinstance(content, list):
        return content
    return []


def _process_docx_template(template_path: str, replacements: dict[str, str]) -> Any:
    doc = Document(template_path)
    for paragraph in doc.paragraphs:
        for key, value in replacements.items():
            if key in paragraph.text:
                paragraph.text = paragraph.text.replace(str(key), str(value))
    return doc


def _load_style_template(template_path: str) -> Any:
    doc = Document(template_path)
    for paragraph in doc.paragraphs[:]:
        for run in paragraph.runs:
            run.text = ""
    return doc


def _maybe_apply_title(
    *, 
    doc: Any, 
    title: str | None, 
    use_template: Optional[str], 
    process_as_template: bool
) -> None:
    if not title or process_as_template:
        return

    title_added = False
    if use_template:
        for paragraph in doc.paragraphs:
            if paragraph.style.name == "Title" or "Title" in paragraph.style.name:
                paragraph.text = title
                title_added = True
                break

    if not title_added:
        title_paragraph = doc.add_paragraph(title)
        try:
            title_paragraph.style = doc.styles["Title"]
        except KeyError:
            try:
                title_paragraph.style = doc.styles["Heading 1"]
            except KeyError:
                run = title_paragraph.runs[0] if title_paragraph.runs else title_paragraph.add_run()
                run.font.size = 20
                run.font.bold = True
        title_paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER


def _append_content(
    *, 
    doc: Any, 
    content: list[dict], 
    use_template: Optional[str], 
    log: logging.Logger
) -> None:
    last_usable_paragraph = None
    if doc.paragraphs:
        for paragraph in reversed(doc.paragraphs):
            if not paragraph.text.strip():
                last_usable_paragraph = paragraph
                break

    for item in content or []:
        if isinstance(item, str):
            last_usable_paragraph = _render_paragraph_item(
                doc=doc,
                item={"type": "paragraph", "text": item},
                use_template=use_template,
                last_usable_paragraph=last_usable_paragraph,
                log=log,
            )
            continue
        if not isinstance(item, dict):
            continue

        item_type = item.get("type")
        if item_type == "image_query":
            log.warning("image_query is not supported in current DOCX exporter")
            continue

        renderer = {
            "title": _render_title_item,
            "subtitle": _render_subtitle_item,
            "heading": _render_heading_item,
            "paragraph": _render_paragraph_item,
            "list": _render_list_item,
            "table": _render_table_item,
        }.get(item_type, _render_text_fallback_item)

        last_usable_paragraph = renderer(
            doc=doc,
            item=item,
            use_template=use_template,
            last_usable_paragraph=last_usable_paragraph,
            log=log,
        )


def _render_title_item(*, doc, item, use_template, last_usable_paragraph, log) -> Any:
    paragraph = doc.add_paragraph(item.get("text", ""))
    try:
        paragraph.style = doc.styles["Heading 1"]
    except KeyError:
        run = paragraph.runs[0] if paragraph.runs else paragraph.add_run()
        run.font.size = 18
        run.font.bold = True
    paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
    return last_usable_paragraph


def _render_subtitle_item(*, doc, item, use_template, last_usable_paragraph, log) -> Any:
    paragraph = doc.add_paragraph(item.get("text", ""))
    try:
        paragraph.style = doc.styles["Heading 2"]
    except KeyError:
        run = paragraph.runs[0] if paragraph.runs else paragraph.add_run()
        run.font.size = 16
        run.font.bold = True
    paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
    return last_usable_paragraph


def _render_heading_item(*, doc, item, use_template, last_usable_paragraph, log) -> Any:
    level = item.get("level")
    if level == 1:
        return _render_title_item(doc=doc, item=item, use_template=use_template, last_usable_paragraph=last_usable_paragraph, log=log)
    if level == 2:
        return _render_subtitle_item(doc=doc, item=item, use_template=use_template, last_usable_paragraph=last_usable_paragraph, log=log)
    return _render_paragraph_item(doc=doc, item=item, use_template=use_template, last_usable_paragraph=last_usable_paragraph, log=log)


def _apply_paragraph_style_if_needed(*, doc, paragraph, use_template) -> None:
    if not use_template:
        return
    try:
        paragraph.style = doc.styles["Normal"]
    except Exception:
        pass


def _render_paragraph_item(*, doc, item, use_template, last_usable_paragraph, log) -> Any:
    if last_usable_paragraph and not last_usable_paragraph.text.strip():
        last_usable_paragraph.text = item.get("text", "")
        return None
    paragraph = doc.add_paragraph(item.get("text", ""))
    _apply_paragraph_style_if_needed(doc=doc, paragraph=paragraph, use_template=use_template)
    return last_usable_paragraph


def _render_list_item(*, doc, item, use_template, last_usable_paragraph, log) -> Any:
    for item_text in item.get("items", []):
        paragraph = doc.add_paragraph(item_text)
        try:
            paragraph.style = doc.styles["List Bullet"]
        except KeyError:
            try:
                paragraph.style = doc.styles["List Paragraph"]
            except KeyError:
                paragraph.style = doc.styles["Normal"]
    return last_usable_paragraph


def _render_table_item(*, doc, item, use_template, last_usable_paragraph, log) -> Any:
    data = item.get("data", [])
    if not data:
        return last_usable_paragraph
    table = doc.add_table(rows=len(data), cols=len(data[0]) if data else 0)
    for i, row in enumerate(data):
        for j, cell in enumerate(row):
            cell_obj = table.cell(i, j)
            cell_obj.text = str(cell)
            if i == 0:
                for paragraph in cell_obj.paragraphs:
                    for run in paragraph.runs:
                        run.font.bold = True
                    paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
    return last_usable_paragraph


def _render_text_fallback_item(*, doc, item, use_template, last_usable_paragraph, log) -> Any:
    if "text" not in item:
        return last_usable_paragraph
    if last_usable_paragraph and not last_usable_paragraph.text.strip():
        last_usable_paragraph.text = item["text"]
        return None
    paragraph = doc.add_paragraph(item["text"])
    _apply_paragraph_style_if_needed(doc=doc, paragraph=paragraph, use_template=use_template)
    return last_usable_paragraph


def export_docx(
    content: list[dict] | str,
    filename: str | None,
    template_vars: dict[str, str] | None = None,
) -> FileRef:
    """Export *content* as a Word document.

    :param content: Structured content list or markdown string.
    :param filename: Output filename.
    :param template_vars: Placeholder → value mapping for template-fill mode.
    :return: FileRef with url and path.
    """
    folder = new_export_folder()
    filepath, fname = resolve_output_path(folder, filename or "", "docx")
    url = public_url(folder, fname)

    process_as_template = bool(template_vars and isinstance(template_vars, dict))
    replacements: dict[str, str] = template_vars if process_as_template else {}
    template_path = TemplateRegistry.get("docx")

    if process_as_template and replacements:
        if template_path:
            doc = _process_docx_template(template_path, replacements)
        else:
            log.warning("TemplateRegistry has no 'docx' template; using empty document")
            doc = Document()
        doc.save(filepath)
        return FileRef(url=url, path=filepath, name=fname)

    if template_path:
        try:
            doc = _load_style_template(template_path)
        except Exception:
            log.exception("Failed to load style template")
            doc = Document()
    else:
        doc = Document()

    _maybe_apply_title(doc=doc, title=None, use_template=None, process_as_template=False)

    structured = _normalize_content(content)
    _append_content(doc=doc, content=structured, use_template=None, log=log)

    doc.save(filepath)
    return FileRef(url=url, path=filepath, name=fname)
