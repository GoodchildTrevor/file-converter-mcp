"""FastMCP application — entry point for tool registration and lifespan."""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager
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
    """Startup / shutdown handler.

    Initialise template registry and output directory on startup.
    """
    from storage.paths import ensure_export_dir
    from app.core.templates import TemplateRegistry

    ensure_export_dir(settings.FILE_EXPORT_DIR)
    TemplateRegistry.init(settings.DOCS_TEMPLATE_PATH)
    log.info("file-converter-mcp started (v%s)", settings.VERSION)
    yield
    log.info("file-converter-mcp stopped")


mcp = FastMCP(
    name="file-converter-mcp",
    instructions=(
        "Export and convert content to DOCX, PPTX, XLSX, PDF, CSV and other formats. "
        "Optionally upload results to OpenWebUI."
    ),
    lifespan=lifespan,
)

# ── Register tool groups ─────────────────────────────────────────────────────
# Import side-effects register @mcp.tool() decorators.
import tools.export_tools   # noqa: F401, E402
import tools.fs_tools       # noqa: F401, E402
import tools.archive_tools  # noqa: F401, E402
import tools.owui_tools     # noqa: F401, E402
