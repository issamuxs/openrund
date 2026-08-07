from __future__ import annotations

import math

import pytest

from openrund.codec._json import (
    MAX_COLLECTION_ITEMS,
    MAX_INPUT_BYTES,
    MAX_NESTING_DEPTH,
    decode_json_value,
)
from openrund.contracts.json import JsonArray, JsonObject
from openrund.errors import DecodeError


@pytest.mark.parametrize(
    ("wire", "expected"),
    [
        (b"null\n", None),
        (b"false\n", False),
        (b"0\n", 0),
        (b"-0.0\n", -0.0),
        (b"0.125\n", 0.125),
        ('"Ω😀"\n'.encode(), "Ω😀"),
    ],
)
def test_valid_scalar_frames_preserve_exact_values(wire: bytes, expected: object) -> None:
    value = decode_json_value(wire)

    assert value == expected
    if wire == b"-0.0\n":
        assert isinstance(value, float)
        assert math.copysign(1.0, value) == -1.0


def test_valid_containers_are_ordered_and_deeply_immutable() -> None:
    value = decode_json_value('{"z":1,"a":[false,null,{"x":"é"}]}\n')

    assert isinstance(value, JsonObject)
    assert tuple(value) == ("z", "a")
    nested = value["a"]
    assert isinstance(nested, JsonArray)
    assert nested[0] is False
    assert nested[1] is None
    assert isinstance(nested[2], JsonObject)


@pytest.mark.parametrize(
    ("wire", "code"),
    [
        (b"{}", "jsonl_final_lf_required"),
        (b"{}\r\n", "jsonl_crlf_forbidden"),
        (b"{}\n\n", "jsonl_multiple_frames"),
        (b" {}\n", "jsonl_surrounding_whitespace"),
        (b"{} \n", "jsonl_surrounding_whitespace"),
        (b"{}\ntrailing", "jsonl_final_lf_required"),
        (b"\xef\xbb\xbf{}\n", "jsonl_bom_forbidden"),
        (b"\xff\n", "json_utf8_invalid"),
        (b"{\n}\n", "jsonl_multiple_frames"),
    ],
)
def test_framing_rejects_noncanonical_jsonl(wire: bytes, code: str) -> None:
    with pytest.raises(DecodeError) as raised:
        decode_json_value(wire)

    assert raised.value.code == code


def test_duplicate_keys_reject_before_immutable_object_construction() -> None:
    with pytest.raises(DecodeError) as raised:
        decode_json_value(b'{"outer":{"same":1,"same":2}}\n')

    assert raised.value.code == "json_object_key_duplicate"
    assert raised.value.pointer == "/outer/same"


@pytest.mark.parametrize(
    ("wire", "code"),
    [
        (b"NaN\n", "json_number_non_finite"),
        (b"Infinity\n", "json_number_non_finite"),
        (b"-Infinity\n", "json_number_non_finite"),
        (b"9007199254740992\n", "json_integer_unsafe"),
        (b"-9007199254740992\n", "json_integer_unsafe"),
        (b"9007199254740992.0\n", "json_integer_unsafe"),
    ],
)
def test_unsupported_numbers_reject(wire: bytes, code: str) -> None:
    with pytest.raises(DecodeError) as raised:
        decode_json_value(wire)

    assert raised.value.code == code


def test_safe_integer_edges_are_accepted() -> None:
    assert decode_json_value(b"9007199254740991\n") == 9_007_199_254_740_991
    assert decode_json_value(b"-9007199254740991\n") == -9_007_199_254_740_991


def test_byte_limit_rejects_before_utf8_or_json_parsing() -> None:
    wire = b'"' + (b"x" * MAX_INPUT_BYTES) + b'"\n'

    with pytest.raises(DecodeError) as raised:
        decode_json_value(wire)

    assert raised.value.code == "json_input_too_large"


def test_depth_limit_rejects_nested_arrays() -> None:
    wire = (b"[" * (MAX_NESTING_DEPTH + 1)) + b"0" + (b"]" * (MAX_NESTING_DEPTH + 1)) + b"\n"

    with pytest.raises(DecodeError) as raised:
        decode_json_value(wire)

    assert raised.value.code == "json_nesting_too_deep"


def test_collection_limit_rejects_arrays_and_objects() -> None:
    array_wire = ("[" + ("0," * MAX_COLLECTION_ITEMS) + "0]\n").encode()
    object_wire = (
        "{" + ",".join(f'"k{index}":0' for index in range(MAX_COLLECTION_ITEMS + 1)) + "}\n"
    ).encode()

    for wire in (array_wire, object_wire):
        with pytest.raises(DecodeError) as raised:
            decode_json_value(wire)
        assert raised.value.code == "json_collection_too_large"


def test_malformed_json_is_safe_and_does_not_echo_hostile_input() -> None:
    hostile = b'Bearer secret-value {"unterminated":'

    with pytest.raises(DecodeError) as raised:
        decode_json_value(hostile + b"\n")

    assert raised.value.code == "json_malformed"
    assert "secret-value" not in str(raised.value)
    assert hostile.decode() not in str(raised.value)


def test_runtime_types_outside_bytes_and_text_reject() -> None:
    with pytest.raises(DecodeError, match="json_input_type_invalid"):
        decode_json_value(bytearray(b"null\n"))  # type: ignore[arg-type]
