import json

from formats.coerce import coerce, coerce_or_error


def test_coerce_parses_json_list_string():
    assert coerce('["a", "b"]') == ["a", "b"]


def test_coerce_parses_json_dict_string():
    assert coerce('{"x": 1}') == {"x": 1}


def test_coerce_returns_plain_string_unchanged():
    assert coerce("hello world") == "hello world"


def test_coerce_returns_list_unchanged():
    assert coerce([1, 2]) == [1, 2]


def test_coerce_invalid_json_returns_original():
    s = "[not json"
    assert coerce(s) == s


def test_coerce_empty_string_unchanged():
    assert coerce("") == ""


def test_coerce_strips_markdown_fence_and_parses():
    s = "```json\n[{\"type\": \"paragraph\", \"text\": \"hi\"}]\n```"
    assert coerce(s) == [{"type": "paragraph", "text": "hi"}]


def test_coerce_fenced_truncated_json_returns_original():
    s = "```json\n[{\"type\": \"paragraph\", \"text\": \"...\"\n```"
    assert coerce(s) == s


def test_coerce_truncated_json_returns_original():
    s = '[{"type": "paragraph", "text": "hi"'
    assert coerce(s) == s


def test_coerce_or_error_fenced_valid_list():
    s = "```json\n[{\"type\": \"paragraph\", \"text\": \"hi\"}]\n```"
    value, error = coerce_or_error(s, "docx")
    assert error is None
    assert value == [{"type": "paragraph", "text": "hi"}]


def test_coerce_or_error_truncated_returns_error():
    s = "```json\n[{\"type\": \"paragraph\", \"text\": \"...\n```"
    value, error = coerce_or_error(s, "docx")
    assert value is None
    assert error["error"]["code"] == "TRUNCATED_JSON"


def test_coerce_or_error_malformed_returns_error():
    s = "[this is not json"
    value, error = coerce_or_error(s, "docx")
    assert value is None
    assert error["error"]["code"] == "MALFORMED_JSON"


def test_coerce_or_error_plain_string_ok():
    value, error = coerce_or_error("just some text", "docx")
    assert error is None
    assert value == "just some text"


def test_coerce_or_error_list_unchanged():
    value, error = coerce_or_error([{"type": "paragraph", "text": "hi"}], "docx")
    assert error is None
    assert value == [{"type": "paragraph", "text": "hi"}]
