"""Explicit content-block validation shared by document exporters (docx/pdf/pptx).

Historical bug this module fixes: when the tool received malformed input
(e.g. a JSON-encoded string that failed to deserialize, or a dict without
a known "type"), exporters silently fell back to rendering the *raw*
representation of the input — so users received a .docx full of
``{"type": "paragraph", "text": ...}`` markup instead of the document.

Validation strategy (fail loud, never render garbage):

- Plain string   -> passed through, always valid.
- DOCX/PDF blocks -> validated item by item; a block is valid when it is
                    a string, or a dict with a *known* "type" and
                    type-appropriate fields (see _KNOWN_TYPES).
- PPTX slides     -> different schema: dicts with "title" / "content"
                    (see validate_slides).
- Anything else  -> raises ContentValidationError with a precise,
                    actionable message naming the offending index and
                    the expected schema.

Unknown "type" values are no longer silently rendered as paragraphs:
that is exactly how the raw-markup bug manifested.  They now raise.
"""
from __future__ import annotations

import logging
from typing import Any

log = logging.getLogger(__name__)


class ContentValidationError(ValueError):
    """Raised when content blocks do not match the expected schema."""

    def __init__(self, message: str, index: int | None = None):
        self.index = index
        prefix = f"Block #{index}: " if index is not None else ""
        super().__init__(f"{prefix}{message}")


def _as_text(value: Any) -> str:
    if value is None:
        return ""
    return str(value)


def _validate_table(data: Any, index: int | None) -> list[list[Any]]:
    """Table data must be a list of rows, each row a list of cell values."""
    if not isinstance(data, (list, tuple)):
        raise ContentValidationError(
            "'table' block requires 'data' to be a list of rows "
            "(list of lists); got " + type(data).__name__,
            index=index,
        )
    if not data:
        return []
    rows: list[list[Any]] = []
    for r, row in enumerate(data):
        if not isinstance(row, (list, tuple)):
            raise ContentValidationError(
                "table 'data' row #%d must be a list of cell values; got %s"
                % (r, type(row).__name__),
                index=index,
            )
        rows.append(list(row))
    return rows


def _validate_list_items(items: Any, index: int | None) -> list[str]:
    """List block 'items' must be a list of scalar values."""
    if not isinstance(items, (list, tuple)):
        raise ContentValidationError(
            "'list' block requires 'items' to be a list of strings; got "
            + type(items).__name__,
            index=index,
        )
    return [_as_text(x) for x in items]


def _validate_heading(item: dict, index: int | None) -> dict:
    """Optional 'level' must be an int in 1..9 (renderer clamps at 9)."""
    if "level" in item and item["level"] is not None:
        level = item["level"]
        if not isinstance(level, int) or isinstance(level, bool) or not 1 <= level <= 9:
            raise ContentValidationError(
                "'heading' block 'level' must be an integer 1-9; got %r"
                % (level,),
                index=index,
            )
    return item


# Minimal requirements per known block type: required field names.
# A block may carry extra fields (they are preserved by exporters) but the
# required ones must be present and well-typed.
_KNOWN_TYPES: dict[str, tuple[str, ...]] = {
    "title":     ("text",),
    "subtitle":  ("text",),
    "heading":   ("text",),
    "paragraph": ("text",),
    "list":      ("items",),
    "table":     ("data",),
}


def validate_block(item: Any, index: int | None = None) -> dict | str:
    """Validate a single content block, raise ContentValidationError if bad.

    :param item: Candidate block — either a plain string or a dict.
    :param index: Position in the content list, used for error messages.
    :return: The validated block (dict normalized, string unchanged).
    """
    if isinstance(item, str):
        return item

    if not isinstance(item, dict):
        raise ContentValidationError(
            "each block must be a string or a dict with a known 'type' "
            f"one of {sorted(_KNOWN_TYPES)}; got {type(item).__name__}",
            index=index,
        )

    block_type = item.get("type")
    if not isinstance(block_type, str) or block_type not in _KNOWN_TYPES:
        raise ContentValidationError(
            f"unknown block type {block_type!r}; expected one of "
            f"{sorted(_KNOWN_TYPES)} (a missing 'type' field usually means "
            "the caller passed a JSON-serialized string instead of a block)",
            index=index,
        )

    for field_name in _KNOWN_TYPES[block_type]:
        if field_name not in item:
            raise ContentValidationError(
                f"'{block_type}' block is missing required field '{field_name}'",
                index=index,
            )

    # Type-specific deep checks (mutates nothing; returns normalized copy).
    if block_type == "table":
        item = {**item, "data": _validate_table(item["data"], index)}
    elif block_type == "list":
        item = {**item, "items": _validate_list_items(item["items"], index)}
    elif block_type == "heading":
        item = _validate_heading(item, index)
        item = {**item, "text": _as_text(item["text"])}
    else:
        item = {**item, "text": _as_text(item["text"])}

    return item


def validate_blocks(content: Any) -> list[dict | str]:
    """Validate a list of DOCX/PDF content blocks; raise on the first bad one.

    :param content: The (already coerced) content argument.
    :return: A list of validated blocks.
    :raises ContentValidationError: with the index and reason.
    """
    if isinstance(content, str):
        return [content]

    if not isinstance(content, (list, tuple)):
        raise ContentValidationError(
            "content must be a plain string or a flat list of content "
            f"blocks; got {type(content).__name__}"
        )

    return [validate_block(item, i) for i, item in enumerate(content)]


# ── PPTX slides (different schema: title / content, not type-keyed) ──────────

_SLIDE_KEYS = {"title", "content", "image_query", "image_position", "image_size"}


def _validate_slide(item: Any, index: int | None) -> dict | str:
    """Validate a single PPTX slide definition."""
    if isinstance(item, str):
        return item

    if not isinstance(item, dict):
        raise ContentValidationError(
            "each slide must be a string or a dict with 'title'/'content'; "
            f"got {type(item).__name__}",
            index=index,
        )

    slide = dict(item)

    if "title" in slide and slide["title"] is not None and not isinstance(slide["title"], str):
        slide["title"] = _as_text(slide["title"])

    if "content" in slide and slide["content"] is not None:
        content = slide["content"]
        if isinstance(content, (list, tuple)):
            slide["content"] = [_as_text(x) for x in content]
        elif not isinstance(content, str):
            slide["content"] = _as_text(content)

    unknown = set(slide) - _SLIDE_KEYS
    if unknown:
        raise ContentValidationError(
            f"unknown slide fields {sorted(unknown)}; expected subset of "
            f"{sorted(_SLIDE_KEYS)}",
            index=index,
        )

    return slide


def validate_slides(content: Any) -> list[dict | str]:
    """Validate a list of PPTX slide definitions; raise on the first bad one."""
    if isinstance(content, str):
        return [content]

    if not isinstance(content, (list, tuple)):
        raise ContentValidationError(
            "slides must be a plain string or a flat list of slide dicts; "
            f"got {type(content).__name__}"
        )

    return [_validate_slide(item, i) for i, item in enumerate(content)]
