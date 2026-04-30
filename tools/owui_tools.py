"""MCP tools: upload_to_owui, download_from_owui."""
from __future__ import annotations

import os
from typing import Any

from app import mcp
from app.core.models import ExportError


@mcp.tool()
async def upload_to_owui(
    filepath: str,
    mcpo_headers: dict | None = None,
    token: str | None = None,
) -> dict[str, Any]:
    """Upload a generated file to OpenWebUI.

    Args:
        filepath: Absolute path to the file to upload.
        mcpo_headers: MCP session headers (contains Authorization).
        token: Explicit token override.

    Returns:
        {"file_path_download": "[Download ...](...)"}  or  {"error": {...}}
    """
    try:
        from integrations.owui import upload, resolve_token
        resolved = token or resolve_token(mcpo_headers)
        if not resolved:
            return ExportError(message="No authorization token provided", code="AUTH_ERROR").to_dict()
        if not os.path.exists(filepath):
            return ExportError(message="File not found", code="NOT_FOUND").to_dict()
        link = await upload(filepath, os.path.basename(filepath), resolved)
        return {"file_path_download": link}
    except ExportError as exc:
        return exc.to_dict()
    except NotImplementedError as exc:
        return ExportError(message=str(exc), code="NOT_IMPLEMENTED").to_dict()
    except Exception as exc:
        return ExportError(message=str(exc)).to_dict()


@mcp.tool()
async def download_from_owui(
    file_id: str,
    save_path: str | None = None,
    mcpo_headers: dict | None = None,
    token: str | None = None,
) -> dict[str, Any]:
    """Download a file from OpenWebUI.

    Args:
        file_id: OpenWebUI file ID.
        save_path: Optional path to save the downloaded file.
        mcpo_headers: MCP session headers.
        token: Explicit token override.

    Returns:
        {"success": True, "path": "..."} or {"error": {...}}
    """
    try:
        from integrations.owui import download, resolve_token
        resolved = token or resolve_token(mcpo_headers)
        if not resolved:
            return ExportError(message="No authorization token provided", code="AUTH_ERROR").to_dict()
        data = await download(file_id, resolved)
        if save_path:
            with open(save_path, "wb") as f:
                f.write(data.getvalue())
            return {"success": True, "path": save_path}
        return {"success": True, "size": len(data.getvalue())}
    except ExportError as exc:
        return exc.to_dict()
    except NotImplementedError as exc:
        return ExportError(message=str(exc), code="NOT_IMPLEMENTED").to_dict()
    except Exception as exc:
        return ExportError(message=str(exc)).to_dict()
