"""Template tool factory.

Reads TemplateRegistry at startup and registers one @mcp.tool() per named
template, e.g. fill_protocol(...), fill_letter(...), etc.

Each generated tool has explicit named parameters derived from the template's
JSON placeholders — FastMCP does not support **kwargs in tool functions.

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
    """Dynamically build and register one MCP tool for *name*.

    FastMCP inspects the real function signature to build the JSON schema,
    so we must produce a function with explicit named parameters — **kwargs
    is rejected. We use exec() to synthesise a function with the correct
    signature at runtime.
    """
    placeholder_keys = list(placeholders.keys())

    # --- docstring -----------------------------------------------------------
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

    # --- build real signature via exec() ------------------------------------
    # Signature: async def fill_<name>(key1: str = "", key2: str = "", ..., filename: str | None = None)
    params_src = ", ".join(f'{k}: str = ""' for k in placeholder_keys)
    if params_src:
        params_src += ", "
    params_src += "filename: str | None = None"

    # We pass the heavy callables through the exec namespace so the generated
    # function closes over them without relying on globals.
    func_src = (
        f"async def fill_{name}({params_src}) -> dict:\n"
        f"    template_path = _get_named('{name}')\n"
        f"    if not template_path:\n"
        f"        return _export_error(\"Template '{name}' not found.\", \"TEMPLATE_NOT_FOUND\")\n"
        f"    vars_ = {{k: str(locals().get(k, '')) for k in {placeholder_keys!r}}}\n"
        f"    return _export_docx([], filename or '{name}_filled.docx', template_path, vars_)\n"
    )

    ns: dict[str, Any] = {
        "_get_named": TemplateRegistry.get_named,
        "_export_docx": lambda content, fname, tpath, tvars: export_docx(
            content=content,
            filename=fname,
            template_path=tpath,
            template_vars=tvars,
        ).to_dict(),
        "_export_error": lambda msg, code: ExportError(message=msg, code=code).to_dict(),
    }
    exec(func_src, ns)  # noqa: S102

    fn = ns[f"fill_{name}"]
    fn.__doc__ = full_doc
    fn.__module__ = __name__

    mcp.tool()(fn)
    log.info("Registered template tool: fill_%s (params: %s)", name, placeholder_keys)


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

        try:
            _build_tool(tname, tdesc, tplaceholders)
            count += 1
        except Exception as exc:
            log.error("Failed to register tool for template '%s': %s", tname, exc)

    log.info("Template tools registered: %d", count)
    return count
