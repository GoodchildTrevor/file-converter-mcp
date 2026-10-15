import pytest

from formats.content import (
    ContentValidationError,
    validate_block,
    validate_blocks,
    validate_slides,
)


GOOD_BLOCKS = [
    {"type": "title", "text": "Title"},
    {"type": "subtitle", "text": "Subtitle"},
    {"type": "heading", "level": 1, "text": "Heading 1"},
    {"type": "heading", "level": 9, "text": "Heading 9"},
    {"type": "paragraph", "text": "Body text"},
    {"type": "list", "items": ["a", "b", "c"]},
    {"type": "table", "data": [["H1", "H2"], ["v1", "v2"]]},
    "plain string block",
]


def test_validate_blocks_accepts_all_known_types():
    result = validate_blocks(GOOD_BLOCKS)
    assert len(result) == len(GOOD_BLOCKS)


def test_validate_blocks_accepts_plain_string():
    assert validate_blocks("just text") == ["just text"]


@pytest.mark.parametrize("payload,reason", [
    ([{"type": "greeting", "text": "hi"}], "unknown type"),
    ([{"text": "no type field"}], "missing type"),
    ([{"type": "paragraph"}], "missing text field"),
    ([{"type": "list"}], "missing items field"),
    ([{"type": "table"}], "missing data field"),
    ([42], "non-dict block"),
])
def test_validate_blocks_rejects_bad_blocks(payload, reason):
    with pytest.raises(ContentValidationError):
        validate_blocks(payload)


def test_validate_blocks_rejects_outer_dict():
    with pytest.raises(ContentValidationError):
        validate_blocks({"content": GOOD_BLOCKS})


def test_validation_error_names_block_index():
    blocks = [
        {"type": "paragraph", "text": "ok"},
        {"type": "unknown_type", "text": "bad"},
    ]
    with pytest.raises(ContentValidationError) as exc_info:
        validate_blocks(blocks)
    assert "Block #1" in str(exc_info.value)
    assert exc_info.value.index == 1


def test_table_data_must_be_list_of_lists():
    with pytest.raises(ContentValidationError):
        validate_blocks([{"type": "table", "data": "not a table"}])
    with pytest.raises(ContentValidationError):
        validate_blocks([{"type": "table", "data": [["ok"], "row not a list"]}])
    with pytest.raises(ContentValidationError):
        validate_blocks([{"type": "table", "data": [42]}])


def test_list_items_must_be_list():
    with pytest.raises(ContentValidationError):
        validate_blocks([{"type": "list", "items": "abc"}])


def test_heading_level_must_be_int_1_to_9():
    with pytest.raises(ContentValidationError):
        validate_blocks([{"type": "heading", "level": "2", "text": "T"}])
    with pytest.raises(ContentValidationError):
        validate_blocks([{"type": "heading", "level": 0, "text": "T"}])
    with pytest.raises(ContentValidationError):
        validate_blocks([{"type": "heading", "level": 10, "text": "T"}])
    # level omitted -> renderer defaults to 1, still valid
    validate_blocks([{"type": "heading", "text": "no level"}])


def test_validate_blocks_does_not_mutate_input():
    block = {"type": "list", "items": [1, 2]}
    original = {**block, "items": list(block["items"])}
    validate_blocks([block])
    assert block == original


# ── Slides ────────────────────────────────────────────────────────────────────

GOOD_SLIDES = [
    {"title": "S1", "content": ["a", "b"]},
    {"title": "S2", "content": "plain string"},
    {"title": "S3"},
    "string slide",
    {
        "title": "S4",
        "content": ["x"],
        "image_query": "cat",
        "image_position": "left",
        "image_size": "small",
    },
]


def test_validate_slides_accepts_good_slides():
    result = validate_slides(GOOD_SLIDES)
    assert len(result) == len(GOOD_SLIDES)


def test_validate_slides_accepts_plain_string():
    assert validate_slides("one slide text") == ["one slide text"]


@pytest.mark.parametrize("payload", [
    [42],                              # non-dict slide
    [{"title": "x", "foo": "bar"}],    # unknown slide field
    {"slides": []},                    # outer dict
])
def test_validate_slides_rejects_bad_slides(payload):
    with pytest.raises(ContentValidationError):
        validate_slides(payload)
