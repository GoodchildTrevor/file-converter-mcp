"""Defensive coercion for MCP tool arguments.

Some MCP clients/bridges serialize list/dict arguments to a JSON string
before invoking the tool handler, even though the tool signature declares
``str | list``. This module gives export tools a single place to recover
the original structure instead of silently treating the JSON string as
plain text.
"""
from __future__ import annotations

import json
import logging

log = logging.getLogger(__name__)


def coerce(value):
    """Best-effort deserialize a JSON string into list/dict.

    If *value* is a string that looks like a JSON array/object, try to
    parse it. On success, return the parsed list/dict and log a warning
    (this should not normally happen -- it means the MCP transport failed
    to deserialize a structured argument). On failure, or if *value* is
    not such a string, return *value* unchanged.

    :param value: The raw argument as received by the tool handler.
    :return: The original value, or the JSON-decoded list/dict if the
        string was a JSON-encoded array/object.
    """
    if isinstance(value, str) and value.strip()[:1] in ("[", "{"):
        try:
            parsed = json.loads(value)
        except json.JSONDecodeError:
            return value
        if isinstance(parsed, (list, dict)):
            log.warning(
                "MCP argument arrived as a JSON-encoded string instead of "
                "list/dict; deserializing defensively"
            )
            return parsed
    return value
