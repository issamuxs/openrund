from __future__ import annotations

import hashlib
import json
import os
import stat
from collections import Counter
from collections.abc import Iterator
from pathlib import Path
from types import MappingProxyType

import pytest
from tests.conftest import CORPUS_ROOT, CorpusEntry, CorpusIntegrityError, read_corpus_entry


def _entry(
    relative_path: str,
    evidence: bytes = b"{}\n",
    *,
    byte_length: int | None = None,
    sha256: str | None = None,
) -> CorpusEntry:
    return CorpusEntry(
        category="event",
        key="test:entry",
        relative_path=relative_path,
        byte_length=len(evidence) if byte_length is None else byte_length,
        sha256=hashlib.sha256(evidence).hexdigest() if sha256 is None else sha256,
        decoded_meaning=None,
        required_pointers=(),
        absent_pointers=(),
        null_pointers=(),
        manifest_entry=MappingProxyType({}),
    )


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
def frozen_corpus_remains_unchanged() -> Iterator[None]:
    before = _tree_state(CORPUS_ROOT)
    yield
    assert _tree_state(CORPUS_ROOT) == before


def test_phase28_selection_has_required_categories_only(
    phase28_entries: tuple[CorpusEntry, ...],
) -> None:
    counts = Counter(entry.category for entry in phase28_entries)

    assert counts == {
        "wire": 18,
        "number": 14,
        "field-policy": 6,
        "event": 65,
        "command-decision": 4,
        "rejection": 19,
    }
    excluded_prefixes = ("view:", "provider:", "sqlite:", "artifact:", "bundle:")
    assert all(not entry.key.startswith(excluded_prefixes) for entry in phase28_entries)
    assert "rejection:artifact-overwrite" not in {entry.key for entry in phase28_entries}


def test_every_selected_entry_authenticates_before_use(
    phase28_entries: tuple[CorpusEntry, ...],
) -> None:
    for entry in phase28_entries:
        evidence = read_corpus_entry(entry)
        assert len(evidence) == entry.byte_length
        assert hashlib.sha256(evidence).hexdigest() == entry.sha256


def test_semantic_parsing_occurs_after_integrity_verification(
    phase28_entries: tuple[CorpusEntry, ...],
) -> None:
    entry = next(item for item in phase28_entries if item.key == "event:run.created:1:canonical")

    evidence = read_corpus_entry(entry)
    decoded: object = json.loads(evidence)

    assert isinstance(decoded, dict)
    assert decoded["type"] == "run.created"


@pytest.mark.parametrize(
    "relative_path",
    [
        "/absolute/evidence.jsonl",
        "C:/drive/evidence.jsonl",
        "../outside.jsonl",
        "evidence/../../outside.jsonl",
        "evidence//entry.jsonl",
        "evidence/./entry.jsonl",
        "evidence\\entry.jsonl",
        "evidence/entry\0.jsonl",
    ],
)
def test_absolute_escaping_and_ambiguous_paths_fail_closed(
    tmp_path: Path,
    relative_path: str,
) -> None:
    corpus_root = tmp_path / "corpus"
    corpus_root.mkdir()

    with pytest.raises(CorpusIntegrityError, match="corpus_path_"):
        read_corpus_entry(_entry(relative_path), corpus_root=corpus_root)


@pytest.mark.parametrize("symlink_position", ["intermediate", "final"])
def test_symlink_at_any_manifest_path_component_fails_closed(
    tmp_path: Path,
    symlink_position: str,
) -> None:
    corpus_root = tmp_path / "corpus"
    corpus_root.mkdir()
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "entry.jsonl").write_bytes(b"{}\n")

    if symlink_position == "intermediate":
        (corpus_root / "evidence").symlink_to(outside, target_is_directory=True)
        relative_path = "evidence/entry.jsonl"
    else:
        (corpus_root / "evidence").mkdir()
        (corpus_root / "evidence" / "entry.jsonl").symlink_to(outside / "entry.jsonl")
        relative_path = "evidence/entry.jsonl"

    with pytest.raises(CorpusIntegrityError, match="corpus_path_symlink"):
        read_corpus_entry(_entry(relative_path), corpus_root=corpus_root)


def test_symlink_corpus_root_fails_closed(tmp_path: Path) -> None:
    actual_root = tmp_path / "actual"
    actual_root.mkdir()
    corpus_root = tmp_path / "corpus"
    corpus_root.symlink_to(actual_root, target_is_directory=True)

    with pytest.raises(CorpusIntegrityError, match="corpus_root_not_directory"):
        read_corpus_entry(_entry("evidence/entry.jsonl"), corpus_root=corpus_root)


def test_non_regular_entry_fails_closed(tmp_path: Path) -> None:
    corpus_root = tmp_path / "corpus"
    (corpus_root / "evidence" / "entry.jsonl").mkdir(parents=True)

    with pytest.raises(CorpusIntegrityError, match="corpus_entry_not_regular_file"):
        read_corpus_entry(_entry("evidence/entry.jsonl"), corpus_root=corpus_root)


def test_intermediate_regular_file_fails_closed(tmp_path: Path) -> None:
    corpus_root = tmp_path / "corpus"
    corpus_root.mkdir()
    (corpus_root / "evidence").write_bytes(b"not-a-directory")

    with pytest.raises(CorpusIntegrityError, match="corpus_path_component_not_directory"):
        read_corpus_entry(_entry("evidence/entry.jsonl"), corpus_root=corpus_root)


@pytest.mark.parametrize("mismatch", ["byte_length", "sha256"])
def test_length_and_hash_mismatches_fail_closed(tmp_path: Path, mismatch: str) -> None:
    evidence = b'{"trusted":true}\n'
    corpus_root = tmp_path / "corpus"
    path = corpus_root / "evidence" / "entry.jsonl"
    path.parent.mkdir(parents=True)
    path.write_bytes(evidence)
    entry = (
        _entry("evidence/entry.jsonl", evidence, byte_length=len(evidence) + 1)
        if mismatch == "byte_length"
        else _entry("evidence/entry.jsonl", evidence, sha256="0" * 64)
    )

    with pytest.raises(CorpusIntegrityError, match=f"corpus_entry_{mismatch}_mismatch"):
        read_corpus_entry(entry, corpus_root=corpus_root)


def test_valid_temporary_entry_is_returned_without_mutation(tmp_path: Path) -> None:
    evidence = b'{"trusted":true}\n'
    corpus_root = tmp_path / "corpus"
    path = corpus_root / "evidence" / "entry.jsonl"
    path.parent.mkdir(parents=True)
    path.write_bytes(evidence)
    before = (
        path.stat().st_size,
        path.stat().st_mtime_ns,
        hashlib.sha256(path.read_bytes()).digest(),
    )

    assert (
        read_corpus_entry(_entry("evidence/entry.jsonl", evidence), corpus_root=corpus_root)
        == evidence
    )

    after = (
        path.stat().st_size,
        path.stat().st_mtime_ns,
        hashlib.sha256(path.read_bytes()).digest(),
    )
    assert after == before


def test_loader_has_no_executable_oracle_dependency() -> None:
    loader_source = (Path(__file__).parents[1] / "conftest.py").read_text(encoding="utf-8")
    forbidden_tokens = (
        "subprocess",
        "node_modules",
        "pnpm",
        "generate-v1-oracle",
        "verify-v1-oracle",
        "scripts/compatibility",
    )

    assert all(token not in loader_source.casefold() for token in forbidden_tokens)
    assert os.access(CORPUS_ROOT, os.R_OK)
