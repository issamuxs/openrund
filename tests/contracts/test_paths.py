from __future__ import annotations

import os
from dataclasses import FrozenInstanceError
from pathlib import Path

import pytest

from openrund.errors import ValidationError
from openrund.paths import LocalPath, PortablePath, normalize_local_path


class CountingPathLike(os.PathLike[str]):
    def __init__(self, value: str) -> None:
        self.value = value
        self.calls = 0

    def __fspath__(self) -> str:
        self.calls += 1
        return self.value


class BytesPathLike(os.PathLike[bytes]):
    def __fspath__(self) -> bytes:
        return b"private"


@pytest.mark.parametrize(
    "value",
    [
        "workspace/caf\N{LATIN SMALL LETTER E WITH ACUTE}.md",
        Path("workspace") / "report.md",
    ],
)
def test_local_path_accepts_string_and_path_without_resolution(
    value: str | Path,
) -> None:
    normalized = normalize_local_path(value)

    assert isinstance(normalized, LocalPath)
    assert normalized.raw == os.fspath(value)
    assert normalized.path == Path(os.fspath(value))
    assert os.fspath(normalized) == os.fspath(value)


def test_custom_pathlike_is_evaluated_exactly_once() -> None:
    value = CountingPathLike("workspace/e\N{COMBINING ACUTE ACCENT}.md")

    normalized = normalize_local_path(value)

    assert value.calls == 1
    assert normalized.raw == value.value


@pytest.mark.parametrize(
    ("value", "code"),
    [
        (b"bytes", "local_path_bytes_invalid"),
        (BytesPathLike(), "local_path_bytes_invalid"),
        ("contains\x00nul", "local_path_nul"),
        (None, "local_path_type_invalid"),
        (True, "local_path_type_invalid"),
        (object(), "local_path_type_invalid"),
    ],
)
def test_local_path_rejects_bytes_nul_and_wrong_runtime_kinds(value: object, code: str) -> None:
    with pytest.raises(ValidationError, match=code):
        normalize_local_path(value)  # type: ignore[arg-type]


def test_local_path_preserves_lexical_spelling_without_filesystem_io() -> None:
    raw = "./workspace/../workspace/cafe\N{COMBINING ACUTE ACCENT}.md"

    normalized = normalize_local_path(raw)

    assert normalized.raw == raw
    assert ".." in normalized.raw
    assert normalized.path.is_absolute() is False
    with pytest.raises(FrozenInstanceError):
        normalized.raw = "changed"  # type: ignore[misc]


@pytest.mark.parametrize(
    "value",
    [
        "artifact.txt",
        "artifacts/run-1/output.json",
        "caf\N{LATIN SMALL LETTER E WITH ACUTE}/e\N{COMBINING ACUTE ACCENT}.md",
        "emoji/\N{GRINNING FACE}.txt",
    ],
)
def test_portable_path_preserves_exact_relative_posix_components(value: str) -> None:
    portable = PortablePath(value=value)

    assert portable.value == value
    assert portable.components == tuple(value.split("/"))
    assert portable.path.as_posix() == value
    assert os.fspath(portable) == value


@pytest.mark.parametrize(
    ("value", "code"),
    [
        ("", "portable_path_empty"),
        ("/rooted", "portable_path_rooted"),
        ("C:/drive", "portable_path_drive"),
        ("C:\\drive", "portable_path_backslash"),
        ("a\\b", "portable_path_backslash"),
        ("a//b", "portable_path_component_empty"),
        ("a/", "portable_path_component_empty"),
        ("./a", "portable_path_component_dot"),
        ("a/./b", "portable_path_component_dot"),
        ("../a", "portable_path_component_parent"),
        ("a/../b", "portable_path_component_parent"),
        ("a\x00b", "portable_path_nul"),
    ],
)
def test_portable_path_rejects_ambiguous_or_unsafe_spellings(value: str, code: str) -> None:
    with pytest.raises(ValidationError, match=code):
        PortablePath(value=value)


@pytest.mark.parametrize("value", [None, True, b"bytes", Path("local")])
def test_portable_path_rejects_non_string_runtime_kinds(value: object) -> None:
    with pytest.raises(ValidationError, match="portable_path_type_invalid"):
        PortablePath(value=value)  # type: ignore[arg-type]


def test_local_and_portable_paths_are_not_interchangeable() -> None:
    local = normalize_local_path("artifacts/value.txt")
    portable = PortablePath(value="artifacts/value.txt")

    assert local != portable  # type: ignore[comparison-overlap]
    with pytest.raises(ValidationError, match="portable_path_type_invalid"):
        PortablePath(value=local)  # type: ignore[arg-type]
    with pytest.raises(ValidationError, match="local_path_type_invalid"):
        LocalPath(raw=portable)  # type: ignore[arg-type]
