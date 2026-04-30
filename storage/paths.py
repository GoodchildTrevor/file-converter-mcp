"""Filesystem path utilities.

This module owns all path construction and validation logic.
No format or MCP code should call os.path directly.
"""
from __future__ import annotations

import datetime
import logging
import os
import uuid
from pathlib import Path

from app.core.config import get_settings

log = logging.getLogger(__name__)


def ensure_export_dir(export_dir: str) -> None:
    """Create the export root directory if it doesn't exist."""
    os.makedirs(export_dir, exist_ok=True)


def new_export_folder() -> str:
    """Create and return a unique subfolder inside FILE_EXPORT_DIR.

    Format: <EXPORT_DIR>/export_<10hex>_<YYYYMMDD_HHMMSS>
    """
    settings = get_settings()
    name = (
        f"export_{uuid.uuid4().hex[:10]}"
        f"_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}"
    )
    path = os.path.join(settings.FILE_EXPORT_DIR, name)
    os.makedirs(path, exist_ok=True)
    return path


def export_dir() -> str:
    """Return the configured export root directory (does NOT create new folders)."""
    return get_settings().FILE_EXPORT_DIR


def resolve_output_path(folder: str, filename: str, ext: str) -> tuple[str, str]:
    """Return (absolute_filepath, safe_filename) inside *folder*.

    - Sanitises filename to prevent path traversal.
    - Forces the correct extension.
    - Appends _1, _2, ... to avoid collisions.
    """
    if filename:
        filename = os.path.basename(filename)
    if not filename:
        filename = f"export_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.{ext}"

    base, current_ext = os.path.splitext(filename)
    if current_ext.lower() != f".{ext.lower()}":
        filename = f"{base}.{ext}"

    filepath = os.path.join(folder, filename)
    counter = 1
    while os.path.exists(filepath):
        filename = f"{base}_{counter}.{ext}"
        filepath = os.path.join(folder, filename)
        counter += 1

    return filepath, filename


def public_url(folder: str, filename: str) -> str:
    """Build a public URL for a generated file.

    Example: http://localhost:9003/files/export_abc123_20260101_120000/report.docx
    """
    settings = get_settings()
    base_url = settings.FILE_EXPORT_BASE_URL.rstrip("/")
    folder_name = os.path.basename(folder)
    return f"{base_url}/{folder_name}/{filename.lstrip('/')}"


def is_safe_path(filepath: str) -> bool:
    """Return True if *filepath* is inside FILE_EXPORT_DIR.

    Uses Path.resolve() — immune to prefix-confusion attacks.
    """
    try:
        root = Path(get_settings().FILE_EXPORT_DIR).resolve()
        target = Path(filepath).resolve()
        return target.is_relative_to(root)
    except Exception:
        return False
