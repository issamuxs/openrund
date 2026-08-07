from __future__ import annotations

import hashlib
import stat
from collections import Counter
from collections.abc import Iterator, Mapping
from pathlib import Path

import pytest

from tests.conftest import CorpusEntry
from tests.views.conftest import read_view_entry, view_meaning, view_surface


def _tree_state(root: Path) -> tuple[tuple[str, int, int, int, str | None], ...]:
    records: list[tuple[str, int, int, int, str | None]] = []
    for path in sorted(root.rglob("*")):
        status = path.lstat()
        digest = (
            hashlib.sha256(path.read_bytes()).hexdigest() if stat.S_ISREG(status.st_mode) else None
        )
        records.append(
            (
                path.relative_to(root).as_posix(),
                status.st_mode,
                status.st_size,
                status.st_mtime_ns,
                digest,
            )
        )
    return tuple(records)


@pytest.fixture(scope="module", autouse=True)
def frozen_view_corpus_remains_unchanged(view_corpus_root: Path) -> Iterator[None]:
    before = _tree_state(view_corpus_root)
    yield
    assert _tree_state(view_corpus_root) == before


def test_exact_view_inventory(
    view_entries: tuple[CorpusEntry, ...],
    view_surface_counts: Mapping[str, int],
) -> None:
    assert len(view_entries) == 71
    assert Counter(view_surface(entry) for entry in view_entries) == view_surface_counts
    assert len({entry.key for entry in view_entries}) == 71
    assert len({entry.relative_path for entry in view_entries}) == 71


def test_every_view_authenticates_before_semantic_use(
    view_entries: tuple[CorpusEntry, ...],
) -> None:
    for entry in view_entries:
        evidence = read_view_entry(entry)
        assert len(evidence) == entry.byte_length
        assert hashlib.sha256(evidence).hexdigest() == entry.sha256
        meaning = view_meaning(entry)
        assert meaning.get("watermark") is not None
        assert meaning.get("stream") is not None
        assert meaning.get("result") is not None


def test_manifest_inventory_matches_all_view_evidence_files(
    view_entries: tuple[CorpusEntry, ...],
    view_corpus_root: Path,
) -> None:
    expected = {entry.relative_path for entry in view_entries}
    actual = {
        path.relative_to(view_corpus_root).as_posix()
        for path in (view_corpus_root / "evidence").glob("view-*.jsonl")
    }

    assert actual == expected
