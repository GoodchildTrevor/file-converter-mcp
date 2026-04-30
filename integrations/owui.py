"""OpenWebUI HTTP client.
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


async def upload_file(file_path: str, filename: str, file_type: str, token: str) -> dict:
    """Upload a file to OpenWebUI server.
    
    :param file_path: Path to the file to upload
    :param filename: Filename to use on the server
    :param file_type: Type of file (for display)
    :param token: Authorization token   
    :returns: dict with download URL or error
    """
    url = f"{URL}/api/v1/files/"
    headers = {
        'Authorization': token,
        'Accept': 'application/json'
    }

    async with httpx.AsyncClient() as client:
        with open(file_path, 'rb') as f:
            files = {'file': f}
            response = await client.post(url, headers=headers, files=files)

    if response.status_code != 200:
        return {"error": {"message": f'Error uploading file: {response.status_code}'}}
    else:
        return {
            "file_path_download": f"[Download {filename}.{file_type}](/api/v1/files/{response.json()['id']}/content)"
        }
