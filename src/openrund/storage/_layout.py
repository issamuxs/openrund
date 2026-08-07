"""Deterministic local Run custody paths without filesystem authority."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path, PureWindowsPath
from typing import final

from openrund._localfs import LocalFilesystemError, secure_directory_tree
from openrund.contracts.ids import RunId
from openrund.errors import StorageError, ValidationError
from openrund.paths import PathInput, normalize_local_path


def _run_component(run_id: object) -> str:
    if not isinstance(run_id, RunId):
        raise ValidationError(code="run_home_id_type_invalid")
    value = run_id.value
    if (
        value == ""
        or value in {".", ".."}
        or "\x00" in value
        or "/" in value
        or "\\" in value
        or PureWindowsPath(value).drive != ""
        or (os.altsep is not None and os.altsep in value)
    ):
        raise ValidationError(code="run_home_component_invalid")
    return value


@final
@dataclass(frozen=True, slots=True, kw_only=True)
class RunHome:
    """Lexical paths reserved for one Run; this value grants no permissions."""

    root: Path
    run_id: RunId
    home: Path
    runtime: Path
    workspace: Path
    exports: Path


def run_home(root: PathInput, run_id: RunId) -> RunHome:
    """Return one deterministic lexical layout without touching the filesystem."""

    root_path = Path(normalize_local_path(root).path)
    component = _run_component(run_id)
    home = root_path / "runs" / component
    return RunHome(
        root=root_path,
        run_id=run_id,
        home=home,
        runtime=home / "runtime",
        workspace=home / "workspace",
        exports=home / "exports",
    )


def default_openrund_home() -> Path:
    """Return the host convention separately from configurable Run layouts."""

    return Path.home() / ".openrund"


def _materialize_path(path: Path) -> None:
    try:
        secure_directory_tree(path, create=True)
    except LocalFilesystemError as error:
        if error.reason == "symlink":
            raise StorageError(code="run_home_symlink") from None
        if error.reason == "not_directory":
            raise StorageError(code="run_home_not_directory") from None
        if error.reason == "create":
            raise StorageError(code="run_home_create_failed") from None
        raise StorageError(code="run_home_inspection_failed") from None


def materialize_run_home(layout: RunHome) -> RunHome:
    """Create only the validated layout and reject redirected path components."""

    if not isinstance(layout, RunHome):
        raise ValidationError(code="run_home_type_invalid")
    expected = run_home(layout.root, layout.run_id)
    if layout != expected:
        raise ValidationError(code="run_home_layout_invalid")

    for path in (
        expected.root,
        expected.root / "runs",
        expected.home,
        expected.runtime,
        expected.workspace,
        expected.exports,
    ):
        _materialize_path(path)

    try:
        resolved_root = expected.root.resolve(strict=True)
        for path in (expected.home, expected.runtime, expected.workspace, expected.exports):
            if not path.resolve(strict=True).is_relative_to(resolved_root):
                raise StorageError(code="run_home_containment_failed")
    except StorageError:
        raise
    except OSError as error:
        raise StorageError(code="run_home_containment_failed") from error
    return expected
