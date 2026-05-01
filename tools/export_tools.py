"""MCP tools: export_text_file, export_document.

Thin wrappers only — no business logic here.
All work is delegated to formats/* modules.
"""
from __future__ import annotations

from typing import Any

from app import mcp
from app.core.models import ExportError, ExportFormat
from formats.csv import export_csv
from formats.docx import export_docx
from formats.pdf import export_pdf
from formats.pptx import export_pptx
from formats.raw import export_raw
from formats.xlsx import export_xlsx


@mcp.tool()
async def export_text_file(
    text: str | list,
    filename: str | None = None,
    format: str = "txt",
) -> dict[str, Any]:
    """Export text or structured content to a file.

    :param text: Plain text string or list of content objects.
    :param filename: Optional output filename (extension may be overridden by format).
    :param format: One of: txt, md, html, json, xml, docx, pptx, xlsx, pdf.
    :returns: {"url": "...", "path": "..."} on success, or {"error": {...}} on failure.
    """
    try:
        fmt = ExportFormat(format.lower())
    except ValueError:
        return ExportError(
            message=f"Unsupported format: {format}",
            code="UNSUPPORTED_FORMAT"
        ).to_dict()

    try:
        if fmt in ExportFormat.text_formats():
            return export_raw(text, filename, fmt).to_dict()

        elif fmt == ExportFormat.CSV:
            if not isinstance(text, list):
                return ExportError(message="CSV format requires list input").to_dict()
            return export_csv(text, filename).to_dict()

        elif fmt == ExportFormat.DOCX:
            return export_docx(text, filename).to_dict()

        elif fmt == ExportFormat.PPTX:
            return export_pptx(text, filename).to_dict()

        elif fmt == ExportFormat.XLSX:
            if not isinstance(text, list):
                return ExportError(message="XLSX format requires list input").to_dict()
            return export_xlsx(text, filename).to_dict()

        elif fmt == ExportFormat.PDF:
            return (await export_pdf(text, filename)).to_dict()

    except ExportError as exc:
        return exc.to_dict()
    except NotImplementedError as exc:
        return ExportError(message=str(exc), code="NOT_IMPLEMENTED").to_dict()
    except Exception as exc:
        return ExportError(message=str(exc), code="INTERNAL_ERROR").to_dict()


@mcp.tool()
async def export_document(
    data: list[list[str]],
    filename: str | None = None,
    format: str = "csv",
    title: str | None = None,
) -> dict[str, Any]:

    try:
        fmt = ExportFormat(format.lower())
    except ValueError:
        return ExportError(
            message=f"Unsupported format: {format}",
            code="UNSUPPORTED_FORMAT"
        ).to_dict()

    try:
        if fmt == ExportFormat.CSV:
            return export_csv(data, filename).to_dict()

        elif fmt == ExportFormat.XLSX:
            return export_xlsx(data, filename, title=title).to_dict()

        elif fmt == ExportFormat.DOCX:
            text = "\n".join(
                ["\t".join(str(c) for c in row) for row in data]
            )
            return export_docx(text, filename).to_dict()

        elif fmt == ExportFormat.PPTX:
            slides = [
                {
                    "title": row[0] if row else "Slide",
                    "content": "\n".join(str(c) for c in row),
                }
                for row in data
            ]
            return export_pptx(slides, filename).to_dict()

        else:
            return ExportError(
                message=f"Unsupported format: {format}",
                code="UNSUPPORTED_FORMAT"
            ).to_dict()

    except ExportError as exc:
        return exc.to_dict()
    except NotImplementedError as exc:
        return ExportError(
            message=str(exc),
            code="NOT_IMPLEMENTED"
        ).to_dict()
    except Exception as exc:
        return ExportError(
            message=str(exc),
            code="INTERNAL_ERROR"
        ).to_dict()
        