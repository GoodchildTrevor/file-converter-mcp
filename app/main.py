"""ASGI entry-point.

Run with::

    uvicorn app.main:mcp_app --host 0.0.0.0 --port 8000
"""
from __future__ import annotations

import os

from app import mcp
from app.middleware import BearerAuthMiddleware

_token = os.environ["MCP_AUTH_TOKEN"]
mcp_app = BearerAuthMiddleware(mcp.http_app(), token=_token)
