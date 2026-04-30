"""OpenWebUI HTTP client.

TODO: Copy logic from old repo:
  - file_export_mcp.py → upload_file(), download_file()

All HTTP goes through this module. No other module should call OpenWebUI directly.
"""
from __future__ import annotations

import logging
from io import BytesIO

import httpx

from app.core.config import get_settings
from app.core.models import ExportError

log = logging.getLogger(__name__)


async def upload(file_path: str, filename: str, token: str) -> str:
    """Upload a file to OpenWebUI and return a markdown download link.

    Raises:
        ExportError: on non-200 response or missing OWUI_URL.
    """
    settings = get_settings()
    if not settings.OWUI_URL:
        raise ExportError(message="OWUI_URL is not configured", code="CONFIG_ERROR")
    raise NotImplementedError(
        "TODO: copy upload_file() from file_export_mcp.py"
    )


async def download(file_id: str, token: str) -> BytesIO:
    """Download a file from OpenWebUI and return its contents as BytesIO.

    Raises:
        ExportError: on non-200 response.
    """
    settings = get_settings()
    if not settings.OWUI_URL:
        raise ExportError(message="OWUI_URL is not configured", code="CONFIG_ERROR")
    raise NotImplementedError(
        "TODO: copy download_file() from file_export_mcp.py"
    )


def resolve_token(mcpo_headers: dict | None) -> str | None:
    """Extract Bearer token from mcpo_headers, falling back to JWT_SECRET."""
    if mcpo_headers:
        token = mcpo_headers.get("authorization")
        if token:
            return token
    secret = get_settings().JWT_SECRET
    if secret:
        log.warning("No user token in headers — falling back to JWT_SECRET")
    return secret or None
