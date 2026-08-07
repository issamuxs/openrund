"""Bounded strict JSONL parsing and exact v1 JSON rendering."""

from __future__ import annotations

import json
import math
from dataclasses import dataclass
from typing import Final

from openrund.contracts.json import JsonArray, JsonObject, JsonValue
from openrund.errors import DecodeError, EncodeError

MAX_INPUT_BYTES: Final = 8 * 1024 * 1024
MAX_NESTING_DEPTH: Final = 64
MAX_COLLECTION_ITEMS: Final = 100_000
_MAX_SAFE_INTEGER: Final = 9_007_199_254_740_991


@dataclass(slots=True)
class _ObjectPairs:
    pairs: list[tuple[str, object]]


def _parse_pairs(pairs: list[tuple[str, object]]) -> _ObjectPairs:
    return _ObjectPairs(pairs=pairs)


def _parse_integer(token: str) -> int:
    value = int(token)
    if abs(value) > _MAX_SAFE_INTEGER:
        raise DecodeError(code="json_integer_unsafe")
    return value


def _parse_float(token: str) -> float:
    value = float(token)
    if not math.isfinite(value):
        raise DecodeError(code="json_number_non_finite")
    if value.is_integer() and abs(value) > _MAX_SAFE_INTEGER:
        raise DecodeError(code="json_integer_unsafe")
    return value


def _reject_constant(_token: str) -> object:
    raise DecodeError(code="json_number_non_finite")


def _pointer(parent: str, component: str | int) -> str:
    encoded = str(component).replace("~", "~0").replace("/", "~1")
    return f"{parent}/{encoded}"


def _freeze_parsed(value: object, *, pointer: str = "", depth: int = 0) -> JsonValue:
    if value is None or isinstance(value, (bool, int, float, str)):
        return value
    next_depth = depth + 1
    if next_depth > MAX_NESTING_DEPTH:
        raise DecodeError(code="json_nesting_too_deep", pointer=pointer)
    if isinstance(value, _ObjectPairs):
        if len(value.pairs) > MAX_COLLECTION_ITEMS:
            raise DecodeError(code="json_collection_too_large", pointer=pointer)
        seen: set[str] = set()
        entries: list[tuple[str, JsonValue]] = []
        for key, item in value.pairs:
            item_pointer = _pointer(pointer, key)
            if key in seen:
                raise DecodeError(code="json_object_key_duplicate", pointer=item_pointer)
            seen.add(key)
            entries.append(
                (
                    key,
                    _freeze_parsed(item, pointer=item_pointer, depth=next_depth),
                )
            )
        return JsonObject(entries=tuple(entries))
    if isinstance(value, list):
        if len(value) > MAX_COLLECTION_ITEMS:
            raise DecodeError(code="json_collection_too_large", pointer=pointer)
        return JsonArray(
            values=tuple(
                _freeze_parsed(
                    item,
                    pointer=_pointer(pointer, index),
                    depth=next_depth,
                )
                for index, item in enumerate(value)
            )
        )
    raise DecodeError(code="json_value_type_invalid", pointer=pointer)


def _wire_bytes(data: bytes | str) -> bytes:
    if isinstance(data, bytes):
        return data
    if isinstance(data, str):
        try:
            return data.encode("utf-8", errors="strict")
        except UnicodeEncodeError:
            raise DecodeError(code="json_utf8_invalid") from None
    raise DecodeError(code="json_input_type_invalid")


def decode_json_value(data: bytes | str) -> JsonValue:
    """Decode exactly one bounded canonical JSON value followed by one LF."""

    wire = _wire_bytes(data)
    if len(wire) > MAX_INPUT_BYTES:
        raise DecodeError(code="json_input_too_large")
    if wire.startswith(b"\xef\xbb\xbf"):
        raise DecodeError(code="jsonl_bom_forbidden")
    if wire.endswith(b"\r\n"):
        raise DecodeError(code="jsonl_crlf_forbidden")
    if not wire.endswith(b"\n"):
        raise DecodeError(code="jsonl_final_lf_required")
    body = wire[:-1]
    if b"\n" in body or b"\r" in body:
        raise DecodeError(code="jsonl_multiple_frames")
    if not body:
        raise DecodeError(code="json_malformed")
    if body[0] in b" \t\r\n" or body[-1] in b" \t\r\n":
        raise DecodeError(code="jsonl_surrounding_whitespace")
    try:
        text = body.decode("utf-8", errors="strict")
    except UnicodeDecodeError:
        raise DecodeError(code="json_utf8_invalid") from None
    try:
        parsed: object = json.loads(
            text,
            object_pairs_hook=_parse_pairs,
            parse_int=_parse_integer,
            parse_float=_parse_float,
            parse_constant=_reject_constant,
        )
    except DecodeError:
        raise
    except (json.JSONDecodeError, RecursionError, ValueError):
        raise DecodeError(code="json_malformed") from None
    return _freeze_parsed(parsed)


def _render_string(value: str) -> str:
    try:
        rendered = json.dumps(value, ensure_ascii=False, separators=(",", ":"))
        rendered.encode("utf-8", errors="strict")
    except (TypeError, UnicodeEncodeError):
        raise EncodeError(code="json_string_invalid") from None
    return rendered


def _fixed_number(token: str) -> str:
    coefficient, raw_exponent = token.lower().split("e")
    exponent = int(raw_exponent)
    if "." in coefficient:
        whole, fraction = coefficient.split(".")
    else:
        whole, fraction = coefficient, ""
    digits = whole + fraction
    decimal_index = len(whole) + exponent
    if decimal_index <= 0:
        rendered = "0." + ("0" * -decimal_index) + digits
    elif decimal_index >= len(digits):
        rendered = digits + ("0" * (decimal_index - len(digits)))
    else:
        rendered = digits[:decimal_index] + "." + digits[decimal_index:]
    if "." in rendered:
        rendered = rendered.rstrip("0").rstrip(".")
    return rendered


def _exponent_number(token: str) -> str:
    coefficient, raw_exponent = token.lower().split("e")
    exponent = int(raw_exponent)
    sign = "+" if exponent >= 0 else "-"
    return f"{coefficient}e{sign}{abs(exponent)}"


def _render_number(value: int | float, *, canonical: bool = False) -> str:
    if isinstance(value, bool):
        raise EncodeError(code="json_number_unsupported")
    if isinstance(value, int):
        if abs(value) > _MAX_SAFE_INTEGER:
            if canonical and abs(value) <= 1_000_000_000_000_000_000_000:
                return str(value)
            code = (
                "json_bigint_unsupported"
                if abs(value) > 9_223_372_036_854_775_807
                else "json_number_unsupported"
            )
            raise EncodeError(code=code)
        return str(value)
    if not math.isfinite(value):
        raise EncodeError(code="json_number_unsupported")
    if value == 0:
        return "0"
    negative = value < 0
    magnitude = -value if negative else value
    token = repr(magnitude)
    if 1e-6 <= magnitude < 1e21:
        if "e" in token.lower():
            rendered = _fixed_number(token)
        else:
            rendered = token[:-2] if token.endswith(".0") else token
    elif "e" in token.lower():
        rendered = _exponent_number(token)
    else:
        rendered = token
    return f"-{rendered}" if negative else rendered


def _render_value(value: JsonValue, *, canonical: bool = False) -> str:
    if value is None:
        return "null"
    if value is True:
        return "true"
    if value is False:
        return "false"
    if isinstance(value, (int, float)):
        return _render_number(value, canonical=canonical)
    if isinstance(value, str):
        return _render_string(value)
    if isinstance(value, JsonArray):
        return "[" + ",".join(_render_value(item, canonical=canonical) for item in value) + "]"
    if isinstance(value, JsonObject):
        entries = value.entries
        if canonical:
            entries = tuple(sorted(entries, key=lambda entry: _utf16_sort_key(entry[0])))
        return (
            "{"
            + ",".join(
                f"{_render_string(key)}:{_render_value(item, canonical=canonical)}"
                for key, item in entries
            )
            + "}"
        )
    raise EncodeError(code="json_value_unsupported")


def _utf16_sort_key(value: str) -> tuple[int, ...]:
    encoded = value.encode("utf-16-be", errors="surrogatepass")
    return tuple(
        int.from_bytes(encoded[index : index + 2], "big") for index in range(0, len(encoded), 2)
    )


def encode_json_value(value: JsonValue) -> bytes:
    """Render one compact v1 JSON value followed by exactly one LF."""

    try:
        return (_render_value(value) + "\n").encode("utf-8", errors="strict")
    except UnicodeEncodeError:
        raise EncodeError(code="json_string_invalid") from None


def canonical_json_bytes(value: JsonValue) -> bytes:
    """Render a no-LF canonical preimage ordered by UTF-16 code units."""

    try:
        return _render_value(value, canonical=True).encode("utf-8", errors="strict")
    except UnicodeEncodeError:
        raise EncodeError(code="json_string_invalid") from None
