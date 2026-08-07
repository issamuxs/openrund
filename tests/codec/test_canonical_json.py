from __future__ import annotations

import hashlib
from collections.abc import Mapping

from tests.conftest import CorpusEntry, FrozenJson

from openrund.codec import canonical_json_bytes
from openrund.contracts.json import JsonArray, JsonObject, freeze_json


def _mapping(value: FrozenJson) -> Mapping[str, FrozenJson]:
    assert isinstance(value, Mapping)
    return value


def test_every_phase28_semantic_hash_matches_frozen_commitment(
    phase28_entries: tuple[CorpusEntry, ...],
) -> None:
    for entry in phase28_entries:
        expected = _mapping(entry.manifest_entry)["semanticSha256"]
        assert isinstance(expected, str)
        value = freeze_json(entry.decoded_meaning)
        actual = hashlib.sha256(canonical_json_bytes(value)).hexdigest()
        assert actual == expected, entry.key


def test_canonical_bytes_have_no_line_terminator_and_sort_recursively() -> None:
    value = freeze_json(
        {
            "z": {"second": 2, "first": 1},
            "a": [{"d": 4, "c": 3}, 0],
        }
    )

    assert canonical_json_bytes(value) == (b'{"a":[{"c":3,"d":4},0],"z":{"first":1,"second":2}}')
    assert not canonical_json_bytes(value).endswith(b"\n")


def test_utf16_code_unit_order_differs_from_unicode_code_point_order() -> None:
    value = JsonObject(entries=(("\ue000", 1), ("😀", 2)))

    assert canonical_json_bytes(value) == '{"😀":2,"\ue000":1}'.encode()


def test_unicode_normalization_is_never_applied() -> None:
    composed = canonical_json_bytes(freeze_json({"value": "é"}))
    decomposed = canonical_json_bytes(freeze_json({"value": "e\u0301"}))

    assert composed != decomposed
    assert composed == '{"value":"é"}'.encode()
    assert decomposed == '{"value":"e\u0301"}'.encode()


def test_array_order_is_preserved_while_object_keys_sort() -> None:
    value = JsonArray(
        values=(
            JsonObject(entries=(("z", 1), ("a", 2))),
            JsonObject(entries=(("b", 3), ("a", 4))),
        )
    )

    assert canonical_json_bytes(value) == b'[{"a":2,"z":1},{"a":4,"b":3}]'
