from __future__ import annotations

import json
from collections.abc import Mapping
from pathlib import Path
from typing import Final, cast

from tests.conftest import CorpusEntry, FrozenJson, read_corpus_entry

PROJECT_ROOT: Final = Path(__file__).resolve().parents[2]
EXPECTED_GATES: Final = {
    "RET-01": "RET-01-python-golden-read",
    "RET-02": "RET-02-python-golden-write",
    "RET-03": "RET-03-event-view-parity",
    "RET-04": "RET-04-sqlite-cross-read",
    "RET-05": "RET-05-artifact-cross-read",
    "RET-06": "RET-06-bundle-bidirectional",
    "RET-07": "RET-07-installed-wheel",
    "RET-08": "RET-08-source-surface-clean",
    "RET-09": "RET-09-provenance-preserved",
    "RET-10": "RET-10-no-dual-development",
}
PYTHON_EVIDENCE: Final = {
    "RET-01": ("tests/codec/test_phase28_corpus.py", "tests/codec/test_v1_decode.py"),
    "RET-02": ("tests/codec/test_v1_encode.py", "tests/codec/test_v1_events.py"),
    "RET-03": ("tests/views/test_view_corpus.py", "tests/engine/test_compatibility.py"),
    "RET-04": ("tests/storage/test_compatibility.py",),
    "RET-05": ("tests/storage/test_artifacts.py", "tests/bundles/test_compatibility.py"),
    "RET-06": ("tests/bundles/test_compatibility.py", "tests/bundles/test_integration.py"),
    "RET-07": ("tests/package/test_installed_typing.py",),
    "RET-08": ("src/openrund", "tests/package/test_python_only_cutover.py"),
    "RET-09": ("tests/package/test_fixture_integrity.py",),
    "RET-10": ("pyproject.toml", "src/openrund"),
}


def _mapping(value: object) -> Mapping[str, object]:
    assert isinstance(value, Mapping)
    assert all(isinstance(key, str) for key in value)
    return cast(Mapping[str, object], value)


def _string(value: object) -> str:
    assert isinstance(value, str)
    return value


def _integer(value: object) -> int:
    assert isinstance(value, int) and not isinstance(value, bool)
    return value


def _strings(value: object) -> tuple[str, ...]:
    assert isinstance(value, tuple)
    assert all(isinstance(item, str) for item in value)
    return cast(tuple[str, ...], value)


def _entry(row: Mapping[str, object]) -> CorpusEntry:
    return CorpusEntry(
        category="retirement",
        key=_string(row.get("key")),
        relative_path=_string(row.get("relativePath")),
        byte_length=_integer(row.get("byteLength")),
        sha256=_string(row.get("sha256")),
        decoded_meaning=cast(FrozenJson, row.get("decodedMeaning")),
        required_pointers=_strings(row.get("requiredPointers")),
        absent_pointers=_strings(row.get("absentPointers")),
        null_pointers=_strings(row.get("nullPointers")),
        manifest_entry=cast(Mapping[str, FrozenJson], row),
    )


def test_all_retirement_gates_are_authenticated_and_mapped_to_python_evidence(
    phase28_manifest: Mapping[str, object],
) -> None:
    raw_rows = phase28_manifest.get("retirementGates")
    assert isinstance(raw_rows, tuple)
    rows = tuple(_mapping(value) for value in raw_rows)
    assert tuple(_string(row.get("id")) for row in rows) == tuple(EXPECTED_GATES)

    for row in rows:
        gate_id = _string(row.get("id"))
        entry = _entry(row)
        evidence = read_corpus_entry(entry)
        record = _mapping(json.loads(evidence))
        provenance = _mapping(row.get("provenance"))

        assert entry.key == f"retirement:{gate_id}"
        assert record == _mapping(row.get("decodedMeaning"))
        assert record == {
            "id": gate_id,
            "fullName": EXPECTED_GATES[gate_id],
            "phase": 37,
            "evidence": "Phase 37 cross-SDK compatibility proof",
        }
        assert evidence.endswith(b"\n")
        assert provenance.get("inventoryKey") == entry.key
        assert row.get("decisionIDs") == ("V1-RETIREMENT",)
        assert all(
            (PROJECT_ROOT / relative_path).exists() for relative_path in PYTHON_EVIDENCE[gate_id]
        )
