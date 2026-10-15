"""Defensive coercion for MCP tool arguments.

Some MCP clients send list and dict arguments as JSON strings.
This module recovers the original data from these strings.

Recovery covers:
- a clean JSON string;
- a JSON string with a byte order mark;
- a JSON string inside a code fence;
- a JSON string with prose text before or after it.

The function returns the value unchanged when it is not such a string.
``coerce_or_error`` adds typed errors for JSON-like input that does not
parse, so raw markup never reaches an exported document.
"""
from __future__ import annotations

import json
import logging
import re
from typing import Any

log = logging.getLogger(__name__)

_FENCE_RE = re.compile(r"^```[a-zA-Z0-9_-]*\s*\n?(.*?)\n?```\s*$", re.DOTALL)

# Error codes for a failed coercion. The caller decides how to present them.
TRUNCATED_JSON = "TRUNCATED_JSON"
MALFORMED_JSON = "MALFORMED_JSON"

_TRUNCATION_MARKERS = ("...", "\u2026")


def strip_code_fence(value: str) -> str:
    """Remove a markdown code fence wrapper from the text.

    Return only the fenced payload when the text has a fence.
    Return the text unchanged when it has none.
    """
    match = _FENCE_RE.match(value.strip())
    if match:
        return match.group(1).strip()
    return value


def _clean(value: str) -> str:
    """Remove a byte order mark and code fences from a string."""
    value = value.lstrip("\ufeff").strip()
    return strip_code_fence(value)


def _candidates(value: str):
    """Yield strings that may hold JSON data.

    The function yields the cleaned string first.
    Then it yields the part from the first bracket to the last bracket.
    """
    value = _clean(value)
    yield value
    start = re.search(r"[\[{]", value)
    if start is None:
        return
    start_at = start.start()
    closer = "]" if value[start_at] == "[" else "}"
    end_at = value.rfind(closer)
    if end_at > start_at:
        yield value[start_at:end_at + 1]


def coerce(value):
    """Recover list or dict data from a JSON string argument.

    :param value: The raw argument as the tool handler receives it.
    :return: The recovered list or dict. Or the value unchanged.
    """
    if not isinstance(value, str) or len(value) == 0:
        return value
    for candidate in _candidates(value):
        try:
            parsed = json.loads(candidate)
        except (json.JSONDecodeError, ValueError):
            continue
        if isinstance(parsed, (list, dict)):
            log.warning(
                "MCP argument arrived as a JSON string. "
                "The tool recovered %s data from it.",
                type(parsed).__name__,
            )
            return parsed
    return value


def _classify_json_failure(exc: json.JSONDecodeError, candidate: str) -> str:
    """Return the error code for a JSON string that did not parse.

    The failure is truncated when the parser ran out of text: an
    unterminated string, or an error at the very end of the input.
    Any other failure means the text is not valid JSON.
    """
    if "Unterminated string" in exc.msg or exc.pos >= len(candidate):
        return TRUNCATED_JSON
    return MALFORMED_JSON


def coerce_or_error(
    value: Any,
    fmt_name: str = "docx",
) -> tuple[Any, dict[str, Any] | None]:
    """Recover data from a JSON string argument, or return a typed error.

    Like :func:`coerce`, but when the input starts as JSON and does not
    parse, the function returns a typed error instead of the raw string:

    - TRUNCATED_JSON — the text ends before the JSON value is complete;
    - MALFORMED_JSON — the text is not valid JSON.

    Plain prose strings and native list/dict values pass through
    unchanged, like in coerce.

    :param value: The raw argument as the tool handler receives it.
    :param fmt_name: The export format name, used in the error message.
    :return: A tuple ``(value, error)``. On success error is None.
        On failure value is None and error is ``{"error": {...}}``.
    """
    if not isinstance(value, str):
        return value, None

    recovered = coerce(value)
    if not isinstance(recovered, str):
        # coerce() parsed the JSON string into a structure.
        return recovered, None

    cleaned = _clean(value)
    if not cleaned.startswith(("[", "{")):
        # Prose text, not JSON. Pass it through unchanged.
        return value, None

    last_error: json.JSONDecodeError | None = None
    last_candidate = cleaned
    for candidate in _candidates(value):
        last_candidate = candidate
        try:
            json.loads(candidate)
        except json.JSONDecodeError as exc:
            last_error = exc
            continue
        # A parseable candidate that coerce skipped (a JSON scalar).
        return value, None

    code = _classify_json_failure(last_error, last_candidate)
    if code == TRUNCATED_JSON:
        reason = "the JSON text ends before the value is complete"
    else:
        reason = "the JSON text is not valid"
    message = (
        f"{fmt_name.upper()} export received JSON-like input that could "
        f"not be parsed: {reason}. Send valid JSON, or send the data as "
        f"a native list or dict instead of a string."
    )
    log.warning("Rejected %s JSON-like input with code %s", fmt_name, code)
    return None, {"error": {"code": code, "message": message}}
