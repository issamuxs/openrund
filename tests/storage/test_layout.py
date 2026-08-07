from __future__ import annotations

from pathlib import Path

import pytest

from openrund.contracts.ids import RunId
from openrund.errors import StorageError, ValidationError
from openrund.storage import (
    RunHome,
    default_openrund_home,
    materialize_run_home,
    run_home,
)


def test_run_home_is_pure_deterministic_and_configurable(tmp_path: Path) -> None:
    relative = run_home("var/openrund", RunId(value="run-17"))
    same = run_home(Path("var/openrund"), RunId(value="run-17"))
    assert relative == same
    assert relative == RunHome(
        root=Path("var/openrund"),
        run_id=RunId(value="run-17"),
        home=Path("var/openrund/runs/run-17"),
        runtime=Path("var/openrund/runs/run-17/runtime"),
        workspace=Path("var/openrund/runs/run-17/workspace"),
        exports=Path("var/openrund/runs/run-17/exports"),
    )

    absolute_root = tmp_path / "custody"
    absolute = run_home(absolute_root, RunId(value="run-17"))
    assert absolute.runtime == absolute_root / "runs" / "run-17" / "runtime"
    assert absolute.workspace.name == "workspace"
    assert absolute.exports.name == "exports"
    assert not absolute_root.exists()


@pytest.mark.parametrize(
    "value",
    [".", "..", "a/b", "a\\b", "C:", "C:run", "C:\\run", "\x00", "a\x00b"],
)
def test_run_home_rejects_unsafe_run_components(value: str) -> None:
    with pytest.raises(ValidationError, match="run_home_component_invalid"):
        run_home("custody", RunId(value=value))


def test_materialize_run_home_creates_exact_tree_idempotently(tmp_path: Path) -> None:
    root = tmp_path / "custody"
    layout = run_home(root, RunId(value="run-1"))

    assert materialize_run_home(layout) == layout
    assert materialize_run_home(layout) == layout
    assert sorted(path.relative_to(root).as_posix() for path in root.rglob("*")) == [
        "runs",
        "runs/run-1",
        "runs/run-1/exports",
        "runs/run-1/runtime",
        "runs/run-1/workspace",
    ]
    assert all(
        path.is_dir() for path in (layout.home, layout.runtime, layout.workspace, layout.exports)
    )


def test_materialize_run_home_refuses_symlinked_component(tmp_path: Path) -> None:
    root = tmp_path / "custody"
    outside = tmp_path / "outside"
    root.mkdir()
    outside.mkdir()
    (root / "runs").symlink_to(outside, target_is_directory=True)

    layout = run_home(root, RunId(value="run-1"))
    with pytest.raises(StorageError, match="run_home_symlink"):
        materialize_run_home(layout)
    assert not (outside / "run-1").exists()


def test_materialize_run_home_refuses_non_directory_component(tmp_path: Path) -> None:
    root = tmp_path / "custody"
    root.mkdir()
    (root / "runs").write_text("not a directory", encoding="utf-8")

    with pytest.raises(StorageError, match="run_home_not_directory"):
        materialize_run_home(run_home(root, RunId(value="run-1")))


def test_default_openrund_home_is_only_a_host_convention() -> None:
    assert default_openrund_home() == Path.home() / ".openrund"
