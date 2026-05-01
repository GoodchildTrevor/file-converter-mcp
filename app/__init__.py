"""FastMCP application — entry point for tool registration and lifespan."""
from __future__ import annotations

from contextlib import asynccontextmanager
import logging
import httpx
from typing import Any

from fastmcp import FastMCP
from app.core.config import get_settings

settings = get_settings()
logging.basicConfig(
    level=settings.LOG_LEVEL,
    format="%(asctime)s %(levelname)s %(name)s - %(message)s",
)
log = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: Any):
    from storage.paths import ensure_export_dir
    from app.core.templates import TemplateRegistry

    ensure_export_dir(settings.FILE_EXPORT_DIR)
    TemplateRegistry.init(settings.DOCS_TEMPLATE_PATH)

    app.state.http = httpx.AsyncClient(
        timeout=settings.HTTP_TIMEOUT,
        headers={"User-Agent": "mcp-client/1.0"},
    )

    log.info("file-converter-mcp started (v%s)", settings.VERSION)
    yield

    await app.state.http.aclose()
    log.info("file-converter-mcp stopped")

mcp = FastMCP(
    name="file-converter-mcp",
    instructions=(
        "Export and convert content to DOCX, PPTX, XLSX, PDF, CSV and other formats. "
        "Optionally upload results to OpenWebUI."
    ),
    lifespan=lifespan,
)
