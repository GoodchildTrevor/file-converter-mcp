"""Template tool factory.

Reads TemplateRegistry._named at call time and registers one @mcp.tool()
per named template, e.g. fill_protocol(...), fill_letter(...), etc.

Each generated tool has explicit keyword parameters derived from the
template's JSON placeholders, so the LLM agent sees a concrete schema
instead of a generic vars: dict argument.

Call register_template_tools() once inside lifespan, AFTER TemplateRegistry.init().
"""
from __future__ import annotations

import logging
from typing import Any

from app import mcp
from app.core.models import ExportError
from app.core.templates import TemplateRegistry
from formats.docx import export_docx

log = logging.getLogger(__name__)


def _build_tool(name: str, description: str, placeholders: dict[str, str]) -> None:
    """Create and register one MCP tool for *name*.

    The generated async function has:
    - One str kwarg per placeholder key (default "").
    - An optional `filename` kwarg.
    - A docstring listing every placeholder with its hint.
    """
    placeholder_keys = list(placeholders.keys())
    param_hints = "\n".join(
        f"    :param {k}: {hint}" for k, hint in placeholders.items()
    )
    full_doc = (
        f"{description}\n\n"
        f"Fill all {{{{key}}}} placeholders and export as .docx.\n\n"
        f"{param_hints}\n"
        f"    :param filename: Optional output filename (e.g. '{name}_filled.docx').\n"
        f"    :returns: {{\"url\": \"...\", \"path\": \"...\", \"name\": \"...\"}} "
        f"or {{\"error\": {{...}}}}."
    )

    # Capture loop variables via default argument trick
    async def _tool(filename: str | None = None, **kwargs: str) -> dict[str, Any]:
        template_path = TemplateRegistry.get_named(name)
        if not template_path:
            return ExportError(
                message=f"Template '{name}' not found.",
                code="TEMPLATE_NOT_FOUND",
            ).to_dict()

        # Collect only declared placeholder keys; ignore unknown kwargs
        vars: dict[str, str] = {
            k: str(kwargs.get(k, "")) for k in placeholder_keys
        }
        return export_docx(
            content=[],
            filename=filename or f"{name}_filled.docx",
            template_path=template_path,
            template_vars=vars,
        ).to_dict()

    tool_name = f"fill_{name}"
    _tool.__name__ = tool_name
    _tool.__qualname__ = tool_name
    _tool.__doc__ = full_doc

    # Set typed annotations so FastMCP can build a proper JSON schema.
    # Every placeholder becomes `str`, filename is optional.
    annotations: dict[str, Any] = {k: str for k in placeholder_keys}
    annotations["filename"] = str | None
    annotations["return"] = dict
    _tool.__annotations__ = annotations

    mcp.tool()(_tool)
    log.info("Registered template tool: %s (params: %s)", tool_name, placeholder_keys)


def register_template_tools() -> int:
    """Register one MCP tool per named template.

    Must be called after TemplateRegistry.init().

    :returns: Number of tools registered.
    """
    entries = TemplateRegistry.list_named()
    if not entries:
        log.info("No named templates found — skipping template tool registration.")
        return 0

    count = 0
    for entry in entries:
        tname = entry["name"]
        tdesc = entry["description"] or f"Fill template: {tname}"
        tplaceholders = entry["placeholders"]

        if not tplaceholders:
            log.warning(
                "Template '%s' has no placeholders in JSON — skipping auto-registration. "
                "Use fill_document_template() for it instead.",
                tname,
            )
            continue

        _build_tool(tname, tdesc, tplaceholders)
        count += 1

    log.info("Template tools registered: %d", count)
    return count
