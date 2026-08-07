from __future__ import annotations

import ast
from pathlib import Path

from tests._quality import import_names, parse_python, python_sources, read_python

SOURCE_ROOT = Path(__file__).resolve().parents[2] / "src" / "openrund"
CAPABILITY_ROOT = SOURCE_ROOT / "capabilities"

_CONCRETE = (
    "filesystem.py",
    "documents.py",
    "documents_worker.py",
    "process.py",
    "git.py",
)


def test_engine_never_imports_concrete_capability_execution() -> None:
    for source in python_sources(SOURCE_ROOT / "engine"):
        imports = import_names(parse_python(source))
        assert not any(name.startswith("openrund.capabilities") for name in imports), source


def test_concrete_capabilities_have_no_event_or_engine_authority_imports() -> None:
    forbidden_modules = {
        "openrund.engine",
        "openrund.ports.events",
        "openrund.ports.artifacts",
        "openrund.contracts.commands",
        "openrund.contracts.events",
    }
    for name in _CONCRETE:
        source = CAPABILITY_ROOT / name
        imports = import_names(parse_python(source))
        assert forbidden_modules.isdisjoint(imports), source


def test_concrete_capabilities_cannot_construct_authoritative_runtime_types() -> None:
    forbidden_names = {
        "AppendEventsInput",
        "Command",
        "Event",
        "EventStore",
        "RuntimeEngine",
        "RuntimeEvent",
    }
    for name in _CONCRETE:
        source = CAPABILITY_ROOT / name
        tree = parse_python(source)
        constructed = {
            node.func.id
            for node in ast.walk(tree)
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
        }
        assert forbidden_names.isdisjoint(constructed), source


def test_worker_protocol_is_result_only_and_contains_no_authority_fields() -> None:
    transport = read_python(CAPABILITY_ROOT / "_transports.py")
    worker = read_python(CAPABILITY_ROOT / "documents_worker.py")
    assert '"events"' not in transport
    assert '"commands"' not in transport
    assert "EventStore" not in worker
    assert "RuntimeEngine" not in worker
    assert "append_event" not in worker


def test_capability_modules_are_python_only_and_have_no_graphical_ui_dependencies() -> None:
    all_source = "\n".join(read_python(path) for path in python_sources(CAPABILITY_ROOT))
    forbidden = ("react", "electron", "playwright", "selenium", "prompt_toolkit", "UI-SPEC")
    assert all(token not in all_source for token in forbidden)
