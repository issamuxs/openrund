from __future__ import annotations

import importlib
import inspect
from dataclasses import is_dataclass
from pathlib import Path
from typing import Final

import openrund.views as views
from tests._quality import import_names, parse_python, python_sources, read_python

_SOURCE_ROOT: Final = Path(__file__).parents[2] / "src" / "openrund"
_VIEW_ROOT: Final = _SOURCE_ROOT / "views"
_FORBIDDEN_IMPORTS: Final = (
    "openrund.codec",
    "openrund.ports",
    "openrund._testing",
    "openrund.engine",
    "openrund.storage",
    "openrund.bundles",
    "openrund.assembly",
    "openrund.cli",
    "openrund.ui",
)
_AUTHORITY_METHODS: Final = {
    "append",
    "append_event",
    "approve",
    "authorize",
    "complete",
    "create_event",
    "decide",
    "decide_legality",
    "execute",
    "grant",
    "reject",
    "resolve",
    "revoke",
    "submit",
}


def _sources() -> tuple[Path, ...]:
    return python_sources(_VIEW_ROOT)


def test_views_depend_only_on_semantic_contracts_and_other_views() -> None:
    for source in _sources():
        imports = import_names(parse_python(source))
        assert all(
            not name.startswith(prefix) for name in imports for prefix in _FORBIDDEN_IMPORTS
        ), source
        assert all(not name.endswith((".ts", ".js")) for name in imports), source


def test_views_contain_no_wire_aliases_dumpers_cli_or_graphical_ui() -> None:
    forbidden_tokens = (
        '"runID"',
        '"actionID"',
        '"waitID"',
        "asdict(",
        ".to_dict(",
        ".model_dump(",
        "argparse",
        "click",
        "tkinter",
        "UI-SPEC",
    )
    for source in _sources():
        text = read_python(source)
        assert all(token not in text for token in forbidden_tokens), source

    assert not (_SOURCE_ROOT / "views" / "cli.py").exists()
    assert not (_SOURCE_ROOT / "views" / "ui.py").exists()


def test_every_view_value_is_frozen_and_exposes_no_authority_method() -> None:
    modules = tuple(
        importlib.import_module(f"openrund.views.{path.stem}")
        for path in _sources()
        if path.stem != "__init__"
    )
    classes = tuple(
        value
        for module in modules
        for value in vars(module).values()
        if isinstance(value, type) and value.__module__.startswith("openrund.views")
    )

    for value in classes:
        assert _AUTHORITY_METHODS.isdisjoint(dir(value)), value
        if is_dataclass(value):
            parameters = vars(value)["__dataclass_params__"]
            assert parameters.frozen, value


def test_public_view_surface_is_small_typed_and_non_authoritative() -> None:
    assert views.__all__ == (
        "CompleteViewReplay",
        "IncompleteViewReplay",
        "ReplayIssue",
        "ReplayIssueCode",
        "RunViewBundle",
        "prepare_history",
        "rebuild_views",
    )
    assert _AUTHORITY_METHODS.isdisjoint(dir(views.RunViewBundle))
    assert inspect.signature(views.rebuild_views).return_annotation is not inspect.Signature.empty
