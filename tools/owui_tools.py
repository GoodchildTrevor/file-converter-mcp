"""MCP tools: upload_to_owui, download_from_owui."""
from __future__ import annotations

import os
from typing import Any

from app import mcp
from app.core.models import ExportError
from integrations.owui import download, upload, resolve_token


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
    """Download a file from OpenWebUI and optionally save it to export storage."""
    try:
        import os
        from integrations.owui import download, resolve_token
        from storage.paths import resolve_output_path, new_export_folder, public_url, is_safe_path
        from app.core.models import ExportError, FileRef

        resolved = token or resolve_token(mcpo_headers)
        if not resolved:
            return ExportError(
                message="No authorization token provided",
                code="AUTH_ERROR"
            ).to_dict()

        data = await download(file_id, resolved)

        buf = data.getbuffer()
        size = buf.nbytes

        if not save_path:
            return {"success": True, "size": size}

        filename = os.path.basename(save_path)

        ext = os.path.splitext(filename)[1].lstrip(".") or "bin"

        folder = new_export_folder()

        filepath, fname = resolve_output_path(folder, filename, ext)

        if not is_safe_path(filepath):
            return ExportError(
                message="Unsafe save path",
                code="FORBIDDEN"
            ).to_dict()

        with open(filepath, "wb") as f:
            f.write(buf)

        ref = FileRef(
            path=filepath,
            name=fname,
            url=public_url(folder, fname),
        )

        return {
            "success": True,
            "path": ref.path,
            "url": ref.url,
            "size": size,
        }

    except ExportError as exc:
        return exc.to_dict()
    except NotImplementedError as exc:
        return ExportError(
            message=str(exc),
            code="NOT_IMPLEMENTED"
        ).to_dict()
    except Exception as exc:
        return ExportError(
            message=str(exc),
            code="INTERNAL_ERROR"
        ).to_dict()
