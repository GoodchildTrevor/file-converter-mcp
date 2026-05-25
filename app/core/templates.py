"""Template registry — single source of truth for all document templates.

All format modules import from here. Nobody reads DOCS_TEMPLATE_PATH directly.
"""
from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass
from typing import ClassVar

log = logging.getLogger(__name__)


@dataclass
class TemplateRegistry:
    """Holds resolved template paths after init().

    Use::

        TemplateRegistry.init(settings.DOCS_TEMPLATE_PATH)
        path = TemplateRegistry.get("docx")  # str | None
    """

    _paths: ClassVar[dict[str, str | None]] = {
        "docx": None,
        "pptx": None,
        "xlsx": None,
    }
    _initialised: ClassVar[bool] = False
    # Stores {name: {"path": str, "meta": dict}} for named custom templates
    _named: ClassVar[dict[str, dict]] = {}

    @classmethod
    def init(cls, docs_template_path: str) -> None:
        cls._initialised = True
        base = docs_template_path.strip() if docs_template_path else ""

        if base and os.path.exists(base):
            for f in os.listdir(base):
                if f.lower().endswith(".docx") and f != "Default_Template.docx":
                    name = os.path.splitext(f)[0].lower()
                    docx_path = os.path.join(base, f)

                    # Load sidecar JSON metadata if present
                    json_path = os.path.join(base, f"{os.path.splitext(f)[0]}.json")
                    meta: dict = {}
                    if os.path.exists(json_path):
                        try:
                            with open(json_path, encoding="utf-8") as jf:
                                meta = json.load(jf)
                        except Exception:
                            log.warning("Failed to load metadata for template '%s'", name)

                    cls._named[name] = {"path": docx_path, "meta": meta}
                    log.info("Named template registered [%s]: %s", name, docx_path)

        if not base or not os.path.exists(base):
            if base:
                log.warning("DOCS_TEMPLATE_PATH does not exist: %s", base)
            else:
                log.info("DOCS_TEMPLATE_PATH not set — templates disabled")
            return

        log.info("Scanning templates in: %s", base)
        defaults = {
            "docx": "Default_Template.docx",
            "pptx": "Default_Template.pptx",
            "xlsx": "Default_Template.xlsx",
        }
        for fmt, fname in defaults.items():
            candidate = os.path.join(base, fname)
            if os.path.exists(candidate):
                cls._paths[fmt] = candidate
                log.info("Template found [%s]: %s", fmt, candidate)
            else:
                log.warning("Template not found [%s]: %s", fmt, candidate)

        for fmt in list(cls._paths):
            if cls._paths[fmt] is None:
                cls._find_any(base, fmt)

    @classmethod
    def get_named(cls, name: str) -> str | None:
        """Return the file path for a named template, or None if not found."""
        entry = cls._named.get(name.lower())
        return entry["path"] if entry else None

    @classmethod
    def get_named_meta(cls, name: str) -> dict:
        """Return the metadata dict for a named template (empty dict if none)."""
        entry = cls._named.get(name.lower())
        return entry["meta"] if entry else {}

    @classmethod
    def list_named(cls) -> list[dict]:
        """Return all named templates with their metadata.

        Each entry contains:
            - name: str
            - description: str (from JSON, empty if not set)
            - placeholders: dict[str, str] (key → hint, empty if not set)
        """
        result = []
        for name, entry in sorted(cls._named.items()):
            meta = entry.get("meta", {})
            result.append({
                "name": name,
                "description": meta.get("description", ""),
                "placeholders": meta.get("placeholders", {}),
            })
        return result

    @classmethod
    def _find_any(cls, base: str, fmt: str) -> None:
        """Search for any template file matching the format.

        :param base: Base directory to search in.
        :param fmt: File format to search for (e.g. 'docx', 'pptx', 'xlsx').
        """
        for root, _, files in os.walk(base):
            for f in files:
                if f.lower().endswith(f".{fmt}"):
                    cls._paths[fmt] = os.path.join(root, f)
                    log.info("Template fallback found [%s]: %s", fmt, cls._paths[fmt])
                    return

    @classmethod
    def get(cls, fmt: str) -> str | None:
        """Retrieve a template path by format.

        :param fmt: File format to look up (e.g. 'docx', 'pptx', 'xlsx').
        :return: Absolute path to the template file, or ``None`` if not found.
        """
        if not cls._initialised:
            log.warning("TemplateRegistry.get() called before init()")
        return cls._paths.get(fmt)

    @classmethod
    def reset(cls) -> None:
        """Reset registry to defaults. For use in tests only."""
        cls._paths = {k: None for k in cls._paths}
        cls._named = {}
        cls._initialised = False
