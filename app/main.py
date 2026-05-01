"""ASGI entry-point.

Run with::
    uvicorn app.main:mcp_app --host 0.0.0.0 --port 8000
"""
from __future__ import annotations

from app import mcp
from app.middleware import BearerAuthMiddleware
from core.settings import Settings

import tools.export_tools   # noqa: F401
import tools.fs_tools       # noqa: F401
import tools.archive_tools  # noqa: F401
import tools.owui_tools     # noqa: F401

_token = Settings.MCP_AUTH_TOKEN
mcp_app = BearerAuthMiddleware(mcp.http_app(), token=_token)
