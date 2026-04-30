"""MCP tools: create_archive, cleanup_old_files.

TODO: Copy archive logic from old repo:
  - file_export_mcp.py → create_archive() (zip/tar/tar.gz/7z branches)
"""
from __future__ import annotations

import logging
import os
import tarfile
import zipfile
from typing import Any

import py7zr

from app import mcp, settings
from app.core.models import ArchiveFormat, ExportError
from storage.paths import new_export_folder, public_url

log = logging.getLogger(__name__)


@mcp.tool()
async def create_archive(
    files: list[str],
    archive_name: str | None = None,
    format: str = "zip",
) -> dict[str, Any]:
    """Pack multiple files into an archive.

    Args:
        files: List of absolute file paths to include.
        archive_name: Optional archive filename.
        format: One of: zip, tar, tar.gz, 7z.

    Returns:
        {"url": "...", "path": "...", "files": N}
    """
    if not files:
        return ExportError(message="No files specified").to_dict()

    try:
        fmt = ArchiveFormat(format)
    except ValueError:
        return ExportError(message=f"Unsupported archive format: {format}").to_dict()

    folder = new_export_folder()
    name = os.path.basename(archive_name) if archive_name else f"archive.{format}"
    archive_path = os.path.join(folder, name)

    try:
        if fmt == ArchiveFormat.ZIP:
            with zipfile.ZipFile(archive_path, "w", zipfile.ZIP_DEFLATED) as zf:
                for fp in files:
                    if os.path.exists(fp):
                        zf.write(fp, os.path.basename(fp))

        elif fmt == ArchiveFormat.TAR:
            with tarfile.open(archive_path, "w") as tf:
                for fp in files:
                    if os.path.exists(fp):
                        tf.add(fp, os.path.basename(fp))

        elif fmt == ArchiveFormat.TAR_GZ:
            with tarfile.open(archive_path, "w:gz") as tf:
                for fp in files:
                    if os.path.exists(fp):
                        tf.add(fp, os.path.basename(fp))

        elif fmt == ArchiveFormat.SEVEN_Z:
            with py7zr.SevenZipFile(archive_path, "w") as szf:
                for fp in files:
                    if os.path.exists(fp):
                        szf.write(fp, os.path.basename(fp))

        return {
            "url": public_url(folder, name),
            "path": archive_path,
            "files": len(files),
        }
    except Exception as exc:
        return ExportError(message=str(exc)).to_dict()


@mcp.tool()
def cleanup_old_files(max_age_seconds: int | None = None) -> dict[str, Any]:
    """Remove generated files older than *max_age_seconds*.

    Args:
        max_age_seconds: Age threshold in seconds. Defaults to FILES_DELAY env var.
    """
    if settings.PERSISTENT_FILES:
        return {"message": "Cleanup disabled — PERSISTENT_FILES=true"}

    age = max_age_seconds if max_age_seconds is not None else settings.FILES_DELAY
    if age <= 0:
        return {"message": "Cleanup skipped — FILES_DELAY=0 (keep forever)"}

    try:
        from storage.cleanup import cleanup_old_folders
        stats = cleanup_old_folders(age)
        return {"success": True, **stats}
    except Exception as exc:
        return ExportError(message=str(exc)).to_dict()
