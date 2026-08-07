from __future__ import annotations

import inspect
from dataclasses import replace
from pathlib import Path

import pytest

import openrund.engine as engine_api
from openrund._testing.memory import MemoryEventStore
from openrund.engine import EngineDependencies, RuntimeEngine
from openrund.errors import ValidationError
from tests._quality import import_names, parse_python, python_sources, read_python

SOURCE_ROOT = Path(__file__).parents[2] / "src" / "openrund"
ENGINE_ROOT = SOURCE_ROOT / "engine"


def _engine_sources() -> tuple[Path, ...]:
    return python_sources(ENGINE_ROOT)


def test_coordination_keeps_one_public_engine_authority_surface() -> None:
    assert engine_api.__all__ == [
        "EngineDependencies",
        "GovernanceContext",
        "RuntimeEngine",
        "command_from_model_proposal",
        "schema_violations",
        "submit_model_proposal",
    ]
    assert tuple(
        name
        for name, value in inspect.getmembers(RuntimeEngine)
        if not name.startswith("_") and callable(value)
    ) == ("aclose", "submit")
    assert "event_store" in EngineDependencies.__dataclass_fields__
    assert "atomic_event_store" in EngineDependencies.__dataclass_fields__
    assert not hasattr(RuntimeEngine, "append")
    assert not hasattr(RuntimeEngine, "grant_authority")


def test_coordination_imports_no_effect_assembly_or_interface_layer() -> None:
    forbidden_prefixes = (
        "openrund.assembly",
        "openrund.bundles",
        "openrund.capabilities",
        "openrund.cli",
        "openrund.storage",
        "openrund.ui",
    )
    for source in _engine_sources():
        imports = import_names(parse_python(source))
        assert all(
            not imported.startswith(prefix) for imported in imports for prefix in forbidden_prefixes
        ), source


def test_coordination_has_no_worker_effect_or_raw_store_escape_hatch() -> None:
    engine_text = "\n".join(read_python(source) for source in _engine_sources())
    forbidden_symbols = (
        "ArtifactStore",
        "CapabilityTransport",
        "LeaseStore",
        "ModelProvider",
        "execute_action",
        "invoke_capability",
    )
    assert all(symbol not in engine_text for symbol in forbidden_symbols)

    for source in _engine_sources():
        text = read_python(source)
        if source.name != "_engine.py":
            assert "AppendEventsInput" not in text
            assert "AppendManyEventsInput" not in text


def test_coordination_adds_no_graphical_interface_artifacts() -> None:
    paths = {path.relative_to(SOURCE_ROOT).as_posix() for path in SOURCE_ROOT.rglob("*.py")}
    assert all(not path.startswith("ui/") for path in paths)
    assert "ui.py" not in paths
    assert not any(path.name == "UI-SPEC.md" for path in Path(__file__).parents[2].rglob("*.md"))


def test_atomic_coordination_cannot_split_event_store_custody(
    engine_dependencies: EngineDependencies,
) -> None:
    with pytest.raises(ValidationError, match="engine_event_store_custody_mismatch"):
        replace(engine_dependencies, atomic_event_store=MemoryEventStore())
