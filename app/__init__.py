"""FastMCP application — entry point for tool registration and lifespan."""
from __future__ import annotations

from contextlib import asynccontextmanager
import logging
import httpx
from typing import Any

from fastmcp import FastMCP
from app.core.config import get_settings
from app.core.templates import TemplateRegistry
from storage.paths import ensure_export_dir

settings = get_settings()
logging.basicConfig(
    level=settings.LOG_LEVEL,
    format="%(asctime)s %(levelname)s %(name)s - %(message)s",
)
log = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: Any):

    ensure_export_dir(settings.FILE_EXPORT_DIR)
    TemplateRegistry.init(
        settings.DOCS_TEMPLATE_PATH,
        settings.OWN_TEMPLATES_PATH
    )

    # Register per-template MCP tools after registry is populated
    from tools.template_factory import register_template_tools
    register_template_tools()

    http_client = httpx.AsyncClient(
        timeout=settings.HTTP_TIMEOUT,
        headers={"User-Agent": "mcp-client/1.0"},
    )

    try:
        yield
    finally:
        if http_client is not None:
            await http_client.aclose()
        http_client = None


mcp = FastMCP(
    name="file-converter-mcp",
    instructions=(
        "Export and convert content to DOCX, PPTX, XLSX, PDF, CSV and other formats. "
        "Optionally upload results to OpenWebUI. "
        "For structured business documents (protocols, letters, orders, contracts) "
        "prefer the dedicated fill_<template_name>() tools over generic export."
    ),
    lifespan=lifespan,
)
