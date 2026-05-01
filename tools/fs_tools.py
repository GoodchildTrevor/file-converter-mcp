"""MCP tools: save_file, list_files, delete_file, get_version."""
from __future__ import annotations

import os
from typing import Any

from app import mcp, settings
from app.core.models import ExportError, FileRef
from storage.paths import export_dir, is_safe_path, new_export_folder, resolve_output_path, public_url
from storage.files import delete_file as _delete, write_text, list_folder


@mcp.tool()
async def save_file(
    content: str,
    filename: str,
    folder_path: str | None = None,
) -> dict[str, Any]:
    """Save a raw string to a file in the output directory.

    :param content: String content to save.
    :param filename: Output filename (with extension).
    :param folder_path: Optional existing subfolder path; new folder created if None.
    """
    try: 
        filename = os.path.basename(filename)

        ext = os.path.splitext(filename)[1].lstrip(".") or "txt"

        if folder_path:
            folder_path = os.path.normpath(folder_path)

            filepath, fname = resolve_output_path(folder_path, filename, ext)

            if not is_safe_path(filepath):
                raise ExportError(message="Unsafe file path")

            with open(filepath, "w", encoding="utf-8") as f:
                f.write(content or "")

            ref = FileRef(
                path=filepath,
                name=fname,
                url=public_url(folder_path, fname),
            )
        else:
            ref = write_text(content, filename, ext)

            if not is_safe_path(ref.path):
                raise ExportError(message="Unsafe file path")

        return ref.to_dict()

    except ExportError as exc:
        return exc.to_dict()
    except Exception as exc:
        return ExportError(message=str(exc)).to_dict()


@mcp.tool()
async def list_files(folder_path: str | None = None) -> dict[str, Any]:
    """List files in an output folder.

    :param folder_path: Folder to list. If None, lists the export root directory.
    """
    try:
        folder = folder_path or export_dir()

        if not is_safe_path(folder):
            return ExportError(message="Unsafe folder path").to_dict()

        return {"folder": folder, "files": list_folder(folder)}
    except ExportError as exc:
        return exc.to_dict()
    except Exception as exc:
        return ExportError(message=str(exc)).to_dict()


@mcp.tool()
async def delete_file(filepath: str) -> dict[str, Any]:
    """Delete a generated file.

    :param filepath: Absolute path to the file (must be inside the export directory).
    """
    try:
        if not is_safe_path(filepath):
            return ExportError(message="Path outside export directory", code="FORBIDDEN").to_dict()
        _delete(filepath)
        return {"success": True, "deleted": filepath}
    except ExportError as exc:
        return exc.to_dict()
    except Exception as exc:
        return ExportError(message=str(exc)).to_dict()


@mcp.tool()
async def get_version() -> dict[str, Any]:
    """Return the service version and list of available tools."""
    return {
        "version": settings.VERSION,
        "tools": [
            "export_text_file",
            "export_document",
            "save_file",
            "list_files",
            "delete_file",
            "create_archive",
            "cleanup_old_files",
            "upload_to_owui",
            "download_from_owui",
        ],
    }
