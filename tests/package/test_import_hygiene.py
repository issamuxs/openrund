from __future__ import annotations

import ast
import importlib
from pathlib import Path
from typing import Final

import pytest
from tests._quality import import_names, parse_python, python_sources, read_python

import openrund

PROJECT_ROOT: Final = Path(__file__).resolve().parents[2]
SOURCE_ROOT: Final = PROJECT_ROOT / "src" / "openrund"

_FORBIDDEN_IMPORT_PREFIXES: Final = (
    "openrund.bundles",
    "openrund.ui",
)
_WIRE_ONLY_TOKENS: Final = (
    '"runID"',
    '"commandID"',
    '"modelCallID"',
    '"resultEventIDs"',
    '"targetEvent"',
    '"decisionTrace"',
)


def test_shared_quality_helpers_enumerate_parse_and_extract_imports(tmp_path: Path) -> None:
    nested = tmp_path / "nested"
    nested.mkdir()
    first = tmp_path / "a.py"
    second = tmp_path / "z.py"
    nested_source = nested / "middle.py"
    first.write_text("value = 1\n", encoding="utf-8")
    second.write_text(
        "import beta, gamma\n"
        "from alpha import value\n"
        'label = "caf\N{LATIN SMALL LETTER E WITH ACUTE}"\n',
        encoding="utf-8",
    )
    nested_source.write_text("import nested_dependency\n", encoding="utf-8")
    (tmp_path / "ignored.txt").write_text("not Python\n", encoding="utf-8")

    assert python_sources(tmp_path) == (first, second)
    assert python_sources(tmp_path, recursive=True) == (first, nested_source, second)

    tree = parse_python(second)
    assert import_names(tree) == ("beta", "gamma", "alpha")
    assert any(
        isinstance(node, ast.Constant) and node.value == "caf\N{LATIN SMALL LETTER E WITH ACUTE}"
        for node in ast.walk(tree)
    )

    invalid = tmp_path / "invalid.py"
    invalid.write_text("def incomplete(:\n", encoding="utf-8")
    with pytest.raises(SyntaxError) as caught:
        parse_python(invalid)
    assert caught.value.filename == str(invalid)


def _python_sources() -> tuple[Path, ...]:
    return python_sources(SOURCE_ROOT, recursive=True)


def _imports(source: Path) -> tuple[str, ...]:
    return import_names(parse_python(source))


def test_dependency_direction_excludes_predecessor_and_later_subsystems() -> None:
    for source in _python_sources():
        imports = _imports(source)
        relative = source.relative_to(SOURCE_ROOT)
        forbidden_prefixes = tuple(
            prefix
            for prefix in _FORBIDDEN_IMPORT_PREFIXES
            if prefix != "openrund.bundles"
            or relative.parts[0] not in ("bundles", "operator", "cli.py", "__init__.py")
        )
        assert all(not name.endswith((".ts", ".js")) for name in imports), source
        assert all(
            not name.startswith(prefix) for name in imports for prefix in forbidden_prefixes
        ), source

        if relative.parts[0] == "contracts":
            assert all(
                not name.startswith(
                    (
                        "openrund.codec",
                        "openrund.ports",
                        "openrund.storage",
                        "openrund.engine",
                        "openrund._testing",
                    )
                )
                for name in imports
            ), source
        if relative.parts[0] == "ports":
            assert all(
                not name.startswith(
                    ("openrund.codec", "openrund.storage", "openrund.engine", "openrund._testing")
                )
                for name in imports
            ), source
        if relative.parts[0] == "views":
            assert all(
                not name.startswith(
                    (
                        "openrund.codec",
                        "openrund.ports",
                        "openrund.storage",
                        "openrund.engine",
                        "openrund._testing",
                    )
                )
                for name in imports
            ), source
        if relative.parts[0] == "storage":
            assert all(not name.startswith("openrund.engine") for name in imports), source


def test_wire_aliases_and_generic_dumping_remain_confined() -> None:
    forbidden_calls = ("asdict(", ".model_dump(", ".to_dict(", ".dict(")
    for source in _python_sources():
        text = read_python(source)
        assert all(token not in text for token in forbidden_calls), source
        relative = source.relative_to(SOURCE_ROOT)
        if (
            "codec" not in relative.parts
            and "bundles" not in relative.parts
            and relative != Path("storage/_events.py")
        ):
            assert all(token not in text for token in _WIRE_ONLY_TOKENS), source


def test_root_surface_is_deliberate_and_private_testing_is_not_reexported() -> None:
    assert openrund.__all__ == sorted(openrund.__all__)
    assert len(openrund.__all__) == len(set(openrund.__all__))
    assert all(not name.startswith("_") for name in openrund.__all__)
    assert all(hasattr(openrund, name) for name in openrund.__all__)
    assert not hasattr(openrund, "MemoryEventStore")
    assert not hasattr(openrund, "SeededClock")


def test_protocols_are_static_only_and_expose_no_authority_methods() -> None:
    modules = tuple(
        importlib.import_module(name)
        for name in (
            "openrund.ports.events",
            "openrund.ports.artifacts",
            "openrund.ports.leases",
            "openrund.ports.providers",
            "openrund.ports.capabilities",
            "openrund.ports.runtime",
        )
    )
    forbidden = {"create_event", "append_event", "decide_legality", "grant_authority"}

    for module in modules:
        for value in vars(module).values():
            if isinstance(value, type) and getattr(value, "_is_protocol", False):
                assert not getattr(value, "_is_runtime_protocol", False)
                assert forbidden.isdisjoint(dir(value))


def test_phase_has_no_graphical_ui_implementation() -> None:
    source_paths = {path.relative_to(SOURCE_ROOT).as_posix() for path in _python_sources()}

    assert all(not path.startswith("ui/") for path in source_paths)
    assert not (SOURCE_ROOT / "ui.py").exists()


def test_only_engine_and_custody_decorators_await_event_append() -> None:
    allowed = {
        Path("assembly/_events.py"),
        Path("engine/_engine.py"),
        Path("storage/_event_log.py"),
    }
    observed: set[Path] = set()

    for source in _python_sources():
        tree = parse_python(source)
        relative = source.relative_to(SOURCE_ROOT)
        for node in ast.walk(tree):
            if (
                isinstance(node, ast.Await)
                and isinstance(node.value, ast.Call)
                and isinstance(node.value.func, ast.Attribute)
                and node.value.func.attr == "append"
            ):
                observed.add(relative)
                assert relative in allowed, source

    assert observed == allowed


def test_cli_has_no_store_append_authority_or_interrupt_swallowing() -> None:
    source = SOURCE_ROOT / "cli.py"
    tree = parse_python(source)

    assert not any(
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr == "append"
        and not isinstance(node.func.value, ast.Name)
        for node in ast.walk(tree)
    )
    assert "except BaseException" not in read_python(source)
