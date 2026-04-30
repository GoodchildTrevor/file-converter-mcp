"""Low-level file read / write / list / delete operations.

All functions work with plain file paths (str).
No MCP, no format rendering, no HTTP.
"""
from __future__ import annotations

import csv
import logging
import os
from typing import Any

from app.core.models import FileRef, ExportError
from storage.paths import new_export_folder, resolve_output_path, public_url, is_safe_path

log = logging.getLogger(__name__)


def write_text(content: str, filename: str | None, ext: str = "txt") -> FileRef:
    """Write a text string to a new file and return a FileRef."""
    folder = new_export_folder()
    filepath, fname = resolve_output_path(folder, filename or "", ext)
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(content or "")
    log.debug("write_text → %s", filepath)
    return FileRef(path=filepath, name=fname, url=public_url(folder, fname))


def write_bytes(data: bytes, filename: str | None, ext: str) -> FileRef:
    """Write raw bytes to a new file and return a FileRef."""
    folder = new_export_folder()
    filepath, fname = resolve_output_path(folder, filename or "", ext)
    with open(filepath, "wb") as f:
        f.write(data)
    log.debug("write_bytes → %s", filepath)
    return FileRef(path=filepath, name=fname, url=public_url(folder, fname))


def write_csv(rows: list[list[Any]], filename: str | None) -> FileRef:
    """Write a 2-D list of rows as CSV and return a FileRef."""
    folder = new_export_folder()
    filepath, fname = resolve_output_path(folder, filename or "", "csv")
    with open(filepath, "w", newline="", encoding="utf-8") as f:
        csv.writer(f).writerows(rows)
    log.debug("write_csv → %s", filepath)
    return FileRef(path=filepath, name=fname, url=public_url(folder, fname))


def list_folder(folder: str) -> list[dict[str, str]]:
    """Return metadata for all items inside *folder*."""
    if not os.path.exists(folder):
        raise ExportError(message="Folder not found", code="NOT_FOUND")
    result = []
    for item in os.listdir(folder):
        item_path = os.path.join(folder, item)
        result.append({
            "name": item,
            "type": "folder" if os.path.isdir(item_path) else "file",
            "path": item_path,
            "url": public_url(folder, item),
        })
    return result


def delete_file(filepath: str) -> None:
    """Delete a single file after verifying it is inside FILE_EXPORT_DIR."""
    if not is_safe_path(filepath):
        raise ExportError(
            message="Access denied: path is outside the export directory",
            code="ACCESS_DENIED",
        )
    if not os.path.exists(filepath):
        raise ExportError(message="File not found", code="NOT_FOUND")
    os.remove(filepath)
    log.info("deleted: %s", filepath)
