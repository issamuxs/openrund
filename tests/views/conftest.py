from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from typing import Final

import pytest

from tests.conftest import (
    MANIFEST_PATH,
    CorpusEntry,
    FrozenJson,
    FrozenManifest,
    _corpus_entry,
    _load_manifest,
    _mapping,
    _sequence,
    _string,
    read_corpus_entry,
)

_EXPECTED_SURFACE_COUNTS: Final = {
    "runStatus": 13,
    "timeline": 3,
    "actionStatus": 9,
    "actionReconciliation": 4,
    "actionReceipts": 9,
    "artifactIndex": 3,
    "checkpoints": 4,
    "delegation": 14,
    "waits": 12,
}


def _select_view_entries(manifest: FrozenManifest) -> tuple[CorpusEntry, ...]:
    rows = _sequence(manifest.get("views"), code="manifest_views_invalid")
    entries = tuple(_corpus_entry("view", row) for row in rows)
    if len(entries) != 71 or len({entry.key for entry in entries}) != len(entries):
        raise ValueError("manifest_view_inventory_invalid")
    return entries


def view_surface(entry: CorpusEntry) -> str:
    return _string(entry.manifest_entry.get("surface"), code="manifest_view_surface_invalid")


def view_meaning(entry: CorpusEntry) -> Mapping[str, FrozenJson]:
    return _mapping(entry.decoded_meaning, code="manifest_view_meaning_invalid")


def read_view_entry(entry: CorpusEntry) -> bytes:
    return read_corpus_entry(entry)


@pytest.fixture(scope="session")
def view_manifest() -> FrozenManifest:
    return _load_manifest(MANIFEST_PATH)


@pytest.fixture(scope="session")
def view_entries(view_manifest: FrozenManifest) -> tuple[CorpusEntry, ...]:
    return _select_view_entries(view_manifest)


@pytest.fixture(scope="session")
def view_surface_counts() -> Mapping[str, int]:
    return _EXPECTED_SURFACE_COUNTS


@pytest.fixture(scope="session")
def view_corpus_root() -> Path:
    return Path(__file__).parents[1] / "fixtures" / "compatibility" / "v1"
