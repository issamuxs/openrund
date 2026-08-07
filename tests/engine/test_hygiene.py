from __future__ import annotations

import inspect
from pathlib import Path

import openrund.engine as engine_api
from openrund.engine import EngineDependencies, RuntimeEngine

SOURCE_ROOT = Path(__file__).parents[2] / "src" / "openrund"


def _text(relative: str) -> str:
    return (SOURCE_ROOT / relative).read_text(encoding="utf-8")


def test_engine_public_api_is_small_and_has_no_raw_authority_method() -> None:
    assert engine_api.__all__ == [
        "EngineDependencies",
        "GovernanceContext",
        "RuntimeEngine",
        "command_from_model_proposal",
        "schema_violations",
        "submit_model_proposal",
    ]
    public_methods = tuple(
        name
        for name, value in inspect.getmembers(RuntimeEngine)
        if not name.startswith("_") and callable(value)
    )
    assert public_methods == ("aclose", "submit")
    assert not any(
        name in dir(RuntimeEngine)
        for name in ("append", "append_event", "emit", "event_store", "storage")
    )


def test_provider_capability_and_storage_layers_cannot_import_engine_authority() -> None:
    for relative in (
        "ports/providers.py",
        "ports/capabilities.py",
        "storage/__init__.py",
        "storage/_events.py",
        "views/_rebuild.py",
    ):
        source = _text(relative)
        assert "openrund.engine" not in source
        assert "RuntimeEngine" not in source


def test_supported_adapters_do_not_append_lifecycle_events() -> None:
    for relative in ("ports/providers.py", "ports/capabilities.py"):
        source = _text(relative)
        assert "EventStore" not in source
        assert ".append(" not in source
        assert "command.recorded" not in source


def test_engine_contains_no_ui_cli_or_effect_execution_responsibility() -> None:
    engine_sources = "\n".join(
        path.read_text(encoding="utf-8") for path in sorted((SOURCE_ROOT / "engine").glob("*.py"))
    )
    forbidden = ("UI-SPEC", "graphical", "click", "prompt_toolkit", "argparse", "invoke(")
    assert all(token not in engine_sources for token in forbidden)
    assert "CapabilityTransport" not in engine_sources
    assert "ModelProvider" not in engine_sources
    assert "ArtifactStore" not in engine_sources
    assert "LeaseStore" not in engine_sources


def test_dependencies_hide_event_store_from_public_engine_instance(
    engine_dependencies: EngineDependencies,
) -> None:
    engine = RuntimeEngine(engine_dependencies)

    assert not hasattr(engine, "event_store")
    assert not hasattr(engine, "dependencies")
