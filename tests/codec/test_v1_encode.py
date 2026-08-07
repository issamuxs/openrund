from __future__ import annotations

from collections.abc import Mapping

import pytest
from tests.conftest import CorpusEntry, FrozenJson, read_corpus_entry

from openrund.codec import (
    decode_command_decision,
    encode_command_decision,
    encode_json_value,
)
from openrund.contracts.commands import SupersededDecisionRecord
from openrund.contracts.json import JsonValue, freeze_json
from openrund.errors import EncodeError


def _mapping(value: FrozenJson) -> Mapping[str, FrozenJson]:
    assert isinstance(value, Mapping)
    return value


def test_all_frozen_string_and_container_encodings_match_exact_bytes(
    phase28_entries: tuple[CorpusEntry, ...],
) -> None:
    entries = tuple(entry for entry in phase28_entries if entry.category == "wire")
    assert len(entries) == 18

    for entry in entries:
        meaning = _mapping(entry.decoded_meaning)
        value = freeze_json(meaning["value"])
        assert encode_json_value(value) == read_corpus_entry(entry)


def test_all_supported_frozen_number_spellings_match_exact_bytes(
    phase28_entries: tuple[CorpusEntry, ...],
) -> None:
    entries = tuple(
        entry
        for entry in phase28_entries
        if entry.category == "number" and "wire" in _mapping(entry.decoded_meaning)
    )
    assert len(entries) == 9

    overrides: dict[str, JsonValue] = {
        "number:negative-zero": -0.0,
        "number:exponent-threshold-1e20": 1e20,
        "number:exponent-threshold-1e+21": 1e21,
    }
    for entry in entries:
        meaning = _mapping(entry.decoded_meaning)
        value = overrides.get(entry.key, freeze_json(meaning["value"]))
        assert encode_json_value(value) == read_corpus_entry(entry)


@pytest.mark.parametrize("value", [float("nan"), float("inf"), float("-inf")])
def test_non_finite_numbers_fail_closed(value: float) -> None:
    with pytest.raises(EncodeError, match="json_number_unsupported"):
        encode_json_value(value)


def test_unsafe_integer_fails_closed() -> None:
    with pytest.raises(EncodeError, match="json_number_unsupported"):
        encode_json_value(9_007_199_254_740_992)


def test_big_integer_fails_with_its_distinct_classification() -> None:
    with pytest.raises(EncodeError, match="json_bigint_unsupported"):
        encode_json_value(2**100)


def test_writer_eligible_decisions_match_exact_frozen_bytes(
    phase28_entries: tuple[CorpusEntry, ...],
) -> None:
    entries = tuple(entry for entry in phase28_entries if entry.category == "command-decision")
    encoded = 0
    for entry in entries:
        record = decode_command_decision(read_corpus_entry(entry))
        if isinstance(record.branch, SupersededDecisionRecord):
            with pytest.raises(EncodeError, match="declaration_only_writer"):
                encode_command_decision(record)
            continue
        assert encode_command_decision(record) == read_corpus_entry(entry)
        encoded += 1
    assert encoded == 3


def test_json_encoder_emits_one_final_lf_and_preserves_falsey_values() -> None:
    value = freeze_json({"empty": "", "false": False, "zero": 0, "null": None, "items": []})

    wire = encode_json_value(value)

    assert wire == b'{"empty":"","false":false,"zero":0,"null":null,"items":[]}\n'
    assert wire.endswith(b"\n")
    assert not wire.endswith(b"\n\n")
