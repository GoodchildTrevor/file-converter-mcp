"""CSV exporter.
"""
from __future__ import annotations

from typing import Any

from app.core.models import FileRef
from storage.files import write_csv


def export_csv(rows: list[list[Any]], filename: str | None) -> FileRef:
    """Write *rows* as a CSV file."""
    raise NotImplementedError(
        "TODO: copy _create_csv logic from old repo (essentially: write_csv(rows, filename))"
    )


def _create_csv(data: list[list[str]], filename: str, folder_path: str | None = None) -> dict:
    """Create a CSV file from 2D data.

    :param data: 2D list of strings representing table data
    :param filename: Output filename
    :param folder_path: Optional output folder path
    :return: dict with keys 'url' and 'path'
    """
    log.debug("Creating CSV file")
    if folder_path is None:
        folder_path = _generate_unique_folder()

    if filename:
        filename = os.path.basename(filename)
        filepath = os.path.join(folder_path, filename)
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        fname = filename
    else:
        filepath, fname = _generate_filename(folder_path, "csv")

    with open(filepath, "w", newline="", encoding="utf-8") as f:
        if isinstance(data, list):
            csv.writer(f).writerows(data)
        else:
            csv.writer(f).writerow([data])

    return {"url": _public_url(folder_path, fname), "path": filepath}
