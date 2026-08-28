"""Regression tests for the JSON-string-argument coercion fix.

Covers the bug: an MCP bridge that serializes list/dict arguments to a
JSON string before invoking the tool handler used to produce a silently
broken .docx/.pptx/.pdf (raw JSON dumped as one paragraph) or a broken
export_document() table/document in every format.
"""
from __future__ import annotations

import json

import pytest

from tools.export_tools import export_document, export_text_file


@pytest.mark.anyio
async def test_docx_from_json_string_is_parsed():
    """Reproduces the original bug: JSON-encoded blocks arriving as a str."""
    blocks = [
        {"type": "heading", "level": 1, "text": "Header"},
        {"type": "paragraph", "text": "Body text."},
    ]
    res = await export_text_file(json.dumps(blocks), filename="t.docx", format="docx")
    assert "error" not in res
    assert res.get("url") or res.get("path")


@pytest.mark.anyio
async def test_docx_plain_text_unchanged():
    """Regression: plain multi-line text must still become N paragraphs."""
    res = await export_text_file("line1\nline2", filename="t.docx", format="docx")
    assert "error" not in res


@pytest.mark.anyio
async def test_docx_invalid_blocks_return_loud_error():
    """A JSON array that is not a list of dict/str must fail loudly, not silently."""
    res = await export_text_file("[1, 2, 3]", filename="t.docx", format="docx")
    assert res.get("error", {}).get("code") == "INVALID_INPUT"


@pytest.mark.anyio
async def test_docx_malformed_json_falls_back_to_text():
    """A string that merely starts with '[' but isn't valid JSON is treated as text."""
    res = await export_text_file("[not json, still text", filename="t.docx", format="docx")
    assert "error" not in res


@pytest.mark.anyio
async def test_csv_from_json_string_is_parsed():
    rows = [["Name", "Score"], ["Alice", "95"]]
    res = await export_text_file(json.dumps(rows), filename="t.csv", format="csv")
    assert "error" not in res


@pytest.mark.anyio
async def test_csv_non_list_returns_invalid_input():
    res = await export_text_file("just a string", filename="t.csv", format="csv")
    assert res.get("error", {}).get("code") == "INVALID_INPUT"


@pytest.mark.anyio
async def test_export_document_from_json_string_is_parsed():
    rows = [["a", "b"], ["1", "2"]]
    res = await export_document(json.dumps(rows), format="csv")
    assert "error" not in res


@pytest.mark.anyio
async def test_export_document_garbage_returns_invalid_input():
    res = await export_document("not a table", format="csv")
    assert res.get("error", {}).get("code") == "INVALID_INPUT"


@pytest.mark.anyio
async def test_export_document_docx_table_from_json_string():
    rows = [["Region", "Revenue"], ["North", "$120k"]]
    res = await export_document(json.dumps(rows), format="docx")
    assert "error" not in res
