from __future__ import annotations

import hashlib
import json
import stat
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path, PurePosixPath, PureWindowsPath
from types import MappingProxyType
from typing import Final

import pytest

type FrozenJson = (
    bool | int | float | str | tuple[FrozenJson, ...] | Mapping[str, FrozenJson] | None
)
type FrozenManifest = Mapping[str, FrozenJson]

CORPUS_ROOT: Final = Path(__file__).parent / "fixtures" / "compatibility" / "v1"
MANIFEST_PATH: Final = CORPUS_ROOT / "manifest.json"
_PHASE28_REJECTION_KEYS: Final = frozenset(
    {
        "rejection:unsupported-event-version-0",
        "rejection:unsupported-event-version-2",
        "rejection:malformed-json",
        "rejection:malformed-jsonl",
        "rejection:missing-required-envelope-field",
        "rejection:unknown-envelope-field",
        "rejection:payload-field-not-allowlisted",
        "rejection:absolute-path",
        "rejection:drive-path",
        "rejection:nul-path",
        "rejection:symlink",
        "rejection:bad-file-hash",
        "rejection:bad-byte-count",
        "rejection:bad-position",
        "rejection:wrong-null-absence-state",
        "rejection:orphan-file",
        "rejection:non-finite-number",
        "rejection:bigint",
        "rejection:unsafe-integer",
    }
)


class CorpusIntegrityError(ValueError):
    """Frozen compatibility evidence failed a trust-boundary check."""


@dataclass(frozen=True, slots=True, kw_only=True)
class CorpusEntry:
    """One immutable manifest row selected for Phase 28 contract tests."""

    category: str
    key: str
    relative_path: str
    byte_length: int
    sha256: str
    decoded_meaning: FrozenJson
    required_pointers: tuple[str, ...]
    absent_pointers: tuple[str, ...]
    null_pointers: tuple[str, ...]
    manifest_entry: Mapping[str, FrozenJson]

    def __post_init__(self) -> None:
        if not self.category or not self.key:
            raise ValueError("corpus_entry_identity_invalid")
        if isinstance(self.byte_length, bool) or self.byte_length < 0:
            raise ValueError("corpus_entry_byte_length_invalid")
        if len(self.sha256) != 64 or any(
            character not in "0123456789abcdef" for character in self.sha256
        ):
            raise ValueError("corpus_entry_sha256_invalid")


def _freeze_json(value: object) -> FrozenJson:
    if value is None or isinstance(value, (bool, int, float, str)):
        return value
    if isinstance(value, list):
        return tuple(_freeze_json(item) for item in value)
    if isinstance(value, dict):
        frozen: dict[str, FrozenJson] = {}
        for key, item in value.items():
            if not isinstance(key, str):
                raise CorpusIntegrityError("manifest_key_not_string")
            frozen[key] = _freeze_json(item)
        return MappingProxyType(frozen)
    raise CorpusIntegrityError("manifest_value_not_json")


def _mapping(value: FrozenJson, *, code: str) -> Mapping[str, FrozenJson]:
    if not isinstance(value, Mapping):
        raise CorpusIntegrityError(code)
    return value


def _sequence(value: FrozenJson, *, code: str) -> tuple[FrozenJson, ...]:
    if not isinstance(value, tuple):
        raise CorpusIntegrityError(code)
    return value


def _string(value: FrozenJson, *, code: str) -> str:
    if not isinstance(value, str):
        raise CorpusIntegrityError(code)
    return value


def _integer(value: FrozenJson, *, code: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise CorpusIntegrityError(code)
    return value


def _strings(value: FrozenJson, *, code: str) -> tuple[str, ...]:
    items = _sequence(value, code=code)
    return tuple(_string(item, code=code) for item in items)


def _load_manifest(path: Path = MANIFEST_PATH) -> FrozenManifest:
    parsed: object = json.loads(path.read_text(encoding="utf-8"))
    manifest = _mapping(_freeze_json(parsed), code="manifest_root_not_object")
    if manifest.get("schemaVersion") != 1 or manifest.get("corpusVersion") != "v1":
        raise CorpusIntegrityError("manifest_version_unsupported")
    return manifest


def _corpus_entry(category: str, value: FrozenJson) -> CorpusEntry:
    row = _mapping(value, code="manifest_entry_not_object")
    return CorpusEntry(
        category=category,
        key=_string(row.get("key"), code="manifest_entry_key_invalid"),
        relative_path=_string(row.get("relativePath"), code="manifest_entry_relative_path_invalid"),
        byte_length=_integer(row.get("byteLength"), code="manifest_entry_byte_length_invalid"),
        sha256=_string(row.get("sha256"), code="manifest_entry_sha256_invalid"),
        decoded_meaning=row.get("decodedMeaning"),
        required_pointers=_strings(
            row.get("requiredPointers"), code="manifest_entry_required_pointers_invalid"
        ),
        absent_pointers=_strings(
            row.get("absentPointers"), code="manifest_entry_absent_pointers_invalid"
        ),
        null_pointers=_strings(
            row.get("nullPointers"), code="manifest_entry_null_pointers_invalid"
        ),
        manifest_entry=row,
    )


def _select_phase28_entries(manifest: FrozenManifest) -> tuple[CorpusEntry, ...]:
    selected: list[CorpusEntry] = []
    wire = _mapping(manifest.get("wire"), code="manifest_wire_invalid")
    wire_categories = (
        ("wire", "encoding"),
        ("number", "numbers"),
        ("field-policy", "unknownFields"),
    )
    for category, manifest_key in wire_categories:
        rows = _sequence(wire.get(manifest_key), code=f"manifest_{manifest_key}_invalid")
        selected.extend(_corpus_entry(category, row) for row in rows)

    for category, manifest_key in (("event", "events"), ("command-decision", "commands")):
        rows = _sequence(manifest.get(manifest_key), code=f"manifest_{manifest_key}_invalid")
        selected.extend(_corpus_entry(category, row) for row in rows)

    rejection_rows = _sequence(manifest.get("rejections"), code="manifest_rejections_invalid")
    for row_value in rejection_rows:
        row = _mapping(row_value, code="manifest_rejection_not_object")
        key = _string(row.get("key"), code="manifest_rejection_key_invalid")
        if key in _PHASE28_REJECTION_KEYS:
            selected.append(_corpus_entry("rejection", row))

    keys = tuple(entry.key for entry in selected)
    if len(keys) != len(set(keys)):
        raise CorpusIntegrityError("manifest_selected_key_duplicate")
    return tuple(selected)


def _contained_relative_path(value: str) -> PurePosixPath:
    if not value or "\0" in value or "\\" in value:
        raise CorpusIntegrityError("corpus_path_invalid")
    windows_path = PureWindowsPath(value)
    if value.startswith("/") or windows_path.is_absolute() or windows_path.drive:
        raise CorpusIntegrityError("corpus_path_absolute")
    components = value.split("/")
    if any(component in {"", ".", ".."} for component in components):
        raise CorpusIntegrityError("corpus_path_escaping")
    return PurePosixPath(*components)


def read_corpus_entry(
    entry: CorpusEntry,
    *,
    corpus_root: Path = CORPUS_ROOT,
) -> bytes:
    """Authenticate one contained regular file before exposing its inert bytes."""

    relative_path = _contained_relative_path(entry.relative_path)
    root = corpus_root.absolute()
    try:
        root_status = root.lstat()
    except OSError:
        raise CorpusIntegrityError("corpus_root_unavailable") from None
    if stat.S_ISLNK(root_status.st_mode) or not stat.S_ISDIR(root_status.st_mode):
        raise CorpusIntegrityError("corpus_root_not_directory")

    target = root.joinpath(*relative_path.parts)
    try:
        target.relative_to(root)
    except ValueError:
        raise CorpusIntegrityError("corpus_path_escaping") from None

    current = root
    for index, component in enumerate(relative_path.parts):
        current /= component
        try:
            component_status = current.lstat()
        except OSError:
            raise CorpusIntegrityError("corpus_entry_unavailable") from None
        if stat.S_ISLNK(component_status.st_mode):
            raise CorpusIntegrityError("corpus_path_symlink")
        is_final = index == len(relative_path.parts) - 1
        if not is_final and not stat.S_ISDIR(component_status.st_mode):
            raise CorpusIntegrityError("corpus_path_component_not_directory")
        if is_final and not stat.S_ISREG(component_status.st_mode):
            raise CorpusIntegrityError("corpus_entry_not_regular_file")

    try:
        resolved_root = root.resolve(strict=True)
        resolved_target = target.resolve(strict=True)
        resolved_target.relative_to(resolved_root)
        evidence = target.read_bytes()
    except (OSError, ValueError):
        raise CorpusIntegrityError("corpus_entry_unavailable") from None

    if len(evidence) != entry.byte_length:
        raise CorpusIntegrityError("corpus_entry_byte_length_mismatch")
    if hashlib.sha256(evidence).hexdigest() != entry.sha256:
        raise CorpusIntegrityError("corpus_entry_sha256_mismatch")
    return evidence


@pytest.fixture(scope="session")
def phase28_manifest() -> FrozenManifest:
    """Return the v1 manifest as recursively immutable JSON values."""

    return _load_manifest()


@pytest.fixture(scope="session")
def phase28_entries(phase28_manifest: FrozenManifest) -> tuple[CorpusEntry, ...]:
    """Return only the inert compatibility evidence owned by Phase 28."""

    return _select_phase28_entries(phase28_manifest)
