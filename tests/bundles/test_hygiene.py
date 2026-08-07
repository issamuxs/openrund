from __future__ import annotations

import inspect
from pathlib import Path

import openrund.bundles as bundles
from tests._quality import import_names, parse_python, python_sources, read_python

SOURCE_ROOT = Path(__file__).resolve().parents[2] / "src" / "openrund"
BUNDLE_ROOT = SOURCE_ROOT / "bundles"


def test_bundle_layer_has_no_engine_storage_or_presentation_dependency() -> None:
    forbidden = (
        "openrund.engine",
        "openrund.storage",
        "openrund.providers",
        "openrund.capabilities",
        "openrund.assembly",
        "openrund.cli",
        "openrund.ui",
        "openrund._testing",
    )
    for source in python_sources(BUNDLE_ROOT):
        imports = import_names(parse_python(source))
        assert all(not item.startswith(forbidden) for item in imports), source


def test_bundle_layer_has_no_authority_or_graphical_ui_surface() -> None:
    forbidden_names = {
        "append",
        "approve",
        "authorize",
        "decide_legality",
        "execute",
        "grant",
        "resume",
        "submit",
    }
    for name in bundles.__all__:
        value = getattr(bundles, name)
        if inspect.isclass(value):
            assert all(not callable(getattr(value, item, None)) for item in forbidden_names)
    source = "\n".join(read_python(item) for item in python_sources(BUNDLE_ROOT))
    assert all(
        token not in source
        for token in ("tkinter", "selenium", "playwright", "UI-SPEC", "subprocess")
    )


def test_bundle_public_surface_is_explicit_and_typed() -> None:
    assert tuple(bundles.__all__) == tuple(sorted(bundles.__all__))
    for name in bundles.__all__:
        value = getattr(bundles, name)
        if inspect.isfunction(value):
            signature = inspect.signature(value)
            assert signature.return_annotation is not inspect.Signature.empty
