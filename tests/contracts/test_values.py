from __future__ import annotations

import math
from dataclasses import FrozenInstanceError

import pytest

from openrund.contracts.json import (
    MISSING,
    JsonArray,
    JsonObject,
    MissingType,
    freeze_json,
)
from openrund.contracts.time import Timestamp
from openrund.errors import ValidationError


def test_freeze_json_copies_and_deeply_freezes_retained_containers() -> None:
    child = [1, {"active": True}]
    source: dict[str, object] = {"child": child, "empty": {}}

    frozen = freeze_json(source)
    child.append("late")
    source["new"] = "late"
    cast_object = frozen

    assert isinstance(cast_object, JsonObject)
    assert tuple(cast_object) == ("child", "empty")
    assert cast_object["child"] == JsonArray(values=(1, JsonObject(entries=(("active", True),))))
    assert "new" not in cast_object
    with pytest.raises(FrozenInstanceError):
        cast_object.entries = ()  # type: ignore[misc]


def test_presence_distinguishes_missing_null_falsey_and_empty_values() -> None:
    empty_array = freeze_json([])
    empty_object = freeze_json({})

    assert MissingType() is MISSING
    assert MISSING is not None
    assert None is not False
    assert empty_array == JsonArray(values=())
    assert empty_object == JsonObject(entries=())
    assert empty_array != empty_object  # type: ignore[comparison-overlap]


def test_json_object_retains_order_and_rejects_duplicate_or_non_string_keys() -> None:
    value = freeze_json({"second": 2, "first": 1})

    assert isinstance(value, JsonObject)
    assert value.entries == (("second", 2), ("first", 1))
    with pytest.raises(ValidationError, match="json_object_key_duplicate"):
        JsonObject(entries=(("same", 1), ("same", 2)))
    with pytest.raises(ValidationError, match="json_object_key_type_invalid"):
        freeze_json({1: "invalid"})


@pytest.mark.parametrize("value", [float("nan"), float("inf"), float("-inf")])
def test_json_values_reject_non_finite_numbers(value: float) -> None:
    with pytest.raises(ValidationError, match="json_number_non_finite"):
        freeze_json(value)


@pytest.mark.parametrize("value", [b"bytes", bytearray(b"bytes"), object()])
def test_json_values_reject_unsupported_runtime_objects(value: object) -> None:
    with pytest.raises(ValidationError, match="json_value_type_invalid"):
        freeze_json(value)


def test_strings_preserve_exact_code_points_and_utf8_lengths() -> None:
    composed = "caf\N{LATIN SMALL LETTER E WITH ACUTE}"
    decomposed = "cafe\N{COMBINING ACUTE ACCENT}"
    astral = "\N{GRINNING FACE}"

    assert freeze_json(composed) == composed
    assert freeze_json(decomposed) == decomposed
    assert composed != decomposed
    assert len(composed.encode("utf-8")) == len(decomposed.encode("utf-8")) - 1
    assert len(astral.encode("utf-8")) == 4


def test_signed_zero_is_preserved_as_a_value() -> None:
    frozen = freeze_json(-0.0)

    assert isinstance(frozen, float)
    assert math.copysign(1.0, frozen) == -1.0


@pytest.mark.parametrize(
    "value",
    [
        "2026-01-02T03:04:05.678Z",
        "2000-02-29T23:59:59.000Z",
    ],
)
def test_timestamp_accepts_and_preserves_canonical_utc_milliseconds(value: str) -> None:
    timestamp = Timestamp(value=value)

    assert timestamp.value == value
    assert str(timestamp) == value
    with pytest.raises(FrozenInstanceError):
        timestamp.value = "2026-01-02T03:04:05.679Z"  # type: ignore[misc]


@pytest.mark.parametrize(
    "invalid",
    [
        None,
        True,
        b"2026-01-02T03:04:05.678Z",
        "2026-01-02T03:04:05Z",
        "2026-01-02T03:04:05.67Z",
        "2026-01-02T03:04:05.6780Z",
        "2026-01-02T04:04:05.678+01:00",
        "2026-01-02 03:04:05.678Z",
        "2026-02-29T03:04:05.678Z",
        "2026-01-02T03:04:60.678Z",
    ],
)
def test_timestamp_rejects_wrong_kind_precision_offset_or_date(invalid: object) -> None:
    with pytest.raises(ValidationError):
        Timestamp(value=invalid)  # type: ignore[arg-type]
