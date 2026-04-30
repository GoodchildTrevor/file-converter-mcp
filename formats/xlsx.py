"""XLSX exporter.
"""
from __future__ import annotations

from typing import Any

from app.core.models import FileRef
from app.core.templates import TemplateRegistry

from app.core.templates import TemplateRegistry
template = TemplateRegistry.get("xlsx")  # str | None


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


def _create_excel(
    data: list[list[str]],
    filename: str,
    folder_path: str | None = None,
    title: str | None = None,
    template_path: str | None = None,
    template_obj=None
) -> dict:
    """Create an Excel file from data with optional template support.
    
    :param data: 2D list of strings representing spreadsheet data
    :param filename: Output filename
    :param folder_path: Optional output folder path
    :param title: Optional title for the worksheet
    :param template_path: Path to XLSX template file (overrides module-level template)
    :param template_obj: Pre-loaded Workbook object to use as template
    :return: dict with keys 'url' and 'path'
    """
    log = logging.getLogger(__name__)
    log.debug("Creating Excel file with optional template")
    
    if folder_path is None:
        folder_path = _generate_unique_folder()

    if filename:
        filename = os.path.basename(filename)
        filepath = os.path.join(folder_path, filename)
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        fname = filename
    else:
        filepath, fname = _generate_filename(folder_path, "xlsx")

    # Determine which template to use
    wb = None
    
    if template_obj is not None:
        try:
            wb = copy.deepcopy(template_obj)
            log.debug("Excel template workbook cloned from provided object")
        except Exception as e:
            log.warning(f"Failed to clone provided template: {e}")
            wb = None
    
    if wb is None and template_path and os.path.exists(template_path):
        try:
            wb = load_workbook(template_path)
            log.debug(f"Excel template loaded from: {template_path}")
        except Exception as e:
            log.warning(f"Failed to load XLSX template from {template_path}: {e}")
            wb = None
    
    if wb is None and XLSX_TEMPLATE is not None:
        try:
            wb = copy.deepcopy(XLSX_TEMPLATE)
            log.debug("XLSX template workbook cloned from in-memory object")
        except Exception as e:
            log.warning(f"Failed to load XLSX template: {e}")
            wb = None

    if wb is None:
        log.debug("No XLSX template available, creating new workbook")
        wb = Workbook()

    ws = wb.active

    if title:
        ws.title = "".join(c for c in title if c.isalnum() or c in (' ', '-', '_')).strip()[:31]
        title_cell_found = False
        for row in ws.iter_rows():
            for cell in row:
                if cell.value and isinstance(cell.value, str) and "title" in cell.value.lower():
                    cell.value = title
                    log.debug(f"Title '{title}' replaced in the cell {get_column_letter(cell.column)}{cell.row} containing 'title'")
                    title_cell_found = True
                    break
            if title_cell_found:
                break

    start_row, start_col = 1, 1
    if ws.auto_filter and ws.auto_filter.ref:
        try:
            start_col, start_row, _, _ = range_boundaries(ws.auto_filter.ref)
        except Exception as e:
            log.debug(f"Could not parse auto_filter ref: {e}")

    if not data:
        wb.save(filepath)
        return {"success": True, "filepath": filepath, "filename": filename}

    template_border = ws.cell(start_row, start_col).border
    has_borders = template_border and any([
        template_border.top.style,
        template_border.bottom.style,
        template_border.left.style,
        template_border.right.style
    ])

    for r in range(max(len(data) + 10, 50)):
        for c in range(max(len(data[0]) + 5, 20)):
            cell = ws.cell(row=start_row + r, column=start_col + c)

            if r < len(data) and c < len(data[0]):
                cell.value = data[r][c]
                if r == 0 and data[r][c]:
                    cell.font = Font(bold=True)
                if has_borders:
                    cell.border = Border(
                        top=template_border.top,
                        bottom=template_border.bottom,
                        left=template_border.left,
                        right=template_border.right
                    )
            else:
                cell.value = None
                if cell.has_style:
                    cell.font, cell.fill, cell.border, cell.alignment = (
                        Font(), PatternFill(), Border(), Alignment()
                    )

    if ws.auto_filter:
        ws.auto_filter.ref = (
            f"{get_column_letter(start_col)}{start_row}:"
            f"{get_column_letter(start_col + len(data[0]) - 1)}{start_row + len(data) - 1}"
        )

    for c in range(len(data[0])):
        max_len = max(len(str(data[r][c])) for r in range(len(data)))
        ws.column_dimensions[get_column_letter(start_col + c)].width = min(max_len + 2, 150)

    wb.save(filepath)

    return {"url": _public_url(folder_path, fname), "path": filepath}
