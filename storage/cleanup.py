"""File cleanup — single implementation.

Previous repo had two conflicting cleanup mechanisms (_cleanup_output_folder
in file_export_mcp.py and _cleanup_files in utils.py). This module is the
only cleanup implementation.
"""
from __future__ import annotations

import logging
import os
import shutil
import threading
import time

from storage.paths import export_dir

log = logging.getLogger(__name__)


def schedule_cleanup(folder_path: str, delay_seconds: int) -> None:
    """Delete *folder_path* after *delay_seconds* in a background daemon thread."""
    def _run() -> None:
        time.sleep(delay_seconds)
        _delete_folder(folder_path)

    t = threading.Thread(target=_run, daemon=True)
    t.start()


def cleanup_old_folders(max_age_seconds: int) -> dict[str, int]:
    """Scan FILE_EXPORT_DIR and delete folders older than *max_age_seconds*.

    Returns statistics: {"deleted": N, "bytes_freed": N}.
    """
    root = export_dir()
    deleted = 0
    bytes_freed = 0

    if not os.path.exists(root):
        return {"deleted": 0, "bytes_freed": 0}

    now = time.time()
    for entry in os.scandir(root):
        if not entry.is_dir():
            continue
        age = now - entry.stat().st_mtime
        if age > max_age_seconds:
            size = _folder_size(entry.path)
            if _delete_folder(entry.path):
                deleted += 1
                bytes_freed += size

    return {"deleted": deleted, "bytes_freed": bytes_freed}


def _folder_size(path: str) -> int:
    total = 0
    for root, _, files in os.walk(path):
        for f in files:
            try:
                total += os.path.getsize(os.path.join(root, f))
            except OSError:
                pass
    return total


def _delete_folder(path: str) -> bool:
    try:
        shutil.rmtree(path)
        log.info("cleanup: deleted %s", path)
        return True
    except Exception as exc:
        log.error("cleanup: failed to delete %s — %s", path, exc)
        return False
