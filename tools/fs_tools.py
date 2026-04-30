"""MCP tools: save_file, list_files, delete_file, get_version."""
from __future__ import annotations

from typing import Any

from app import mcp, settings
from app.core.models import ExportError


@mcp.tool()
async def save_file(
    content: str,
    filename: str,
    folder_path: str | None = None,
) -> dict[str, Any]:
    """Save a raw string to a file in the output directory.

    Args:
        content: String content to save.
        filename: Output filename (with extension).
        folder_path: Optional existing subfolder path; new folder created if None.
    """
    try:
        from storage.files import write_text
        from storage.paths import new_export_folder
        import os
        ext = os.path.splitext(filename)[1].lstrip(".") or "txt"
        # If folder_path provided, write there; otherwise create a new folder
        if folder_path:
            from storage.paths import resolve_output_path, public_url
            from app.core.models import FileRef
            filepath, fname = resolve_output_path(folder_path, filename, ext)
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(content or "")
            ref = FileRef(path=filepath, name=fname, url=public_url(folder_path, fname))
        else:
            ref = write_text(content, filename, ext)
        return ref.to_dict()
    except ExportError as exc:
        return exc.to_dict()
    except Exception as exc:
        return ExportError(message=str(exc)).to_dict()


@mcp.tool()
async def list_files(folder_path: str | None = None) -> dict[str, Any]:
    """List files in an output folder.

    Args:
        folder_path: Folder to list. If None, lists the export root directory.
    """
    try:
        from storage.files import list_folder
        from storage.paths import export_dir
        folder = folder_path or export_dir()
        return {"folder": folder, "files": list_folder(folder)}
    except ExportError as exc:
        return exc.to_dict()
    except Exception as exc:
        return ExportError(message=str(exc)).to_dict()


@mcp.tool()
async def delete_file(filepath: str) -> dict[str, Any]:
    """Delete a generated file.

    Args:
        filepath: Absolute path to the file (must be inside the export directory).
    """
    try:
        from storage.files import delete_file as _delete
        _delete(filepath)
        return {"success": True, "deleted": filepath}
    except ExportError as exc:
        return exc.to_dict()
    except Exception as exc:
        return ExportError(message=str(exc)).to_dict()


@mcp.tool()
def get_version() -> dict[str, Any]:
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
