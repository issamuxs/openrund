from __future__ import annotations

from pathlib import Path

from tests._quality import import_names, parse_python, python_sources, read_python

PROJECT_ROOT = Path(__file__).resolve().parents[2]
PROVIDER_ROOT = PROJECT_ROOT / "src" / "openrund" / "providers"
RUNTIME_LOOP = PROJECT_ROOT / "src" / "openrund" / "runtime" / "_loop.py"


def test_provider_adapters_cannot_import_event_or_effect_custody() -> None:
    forbidden = (
        "openrund.contracts.events",
        "openrund.ports.events",
        "openrund.ports.artifacts",
        "openrund.storage",
        "openrund.capabilities",
    )
    for source in python_sources(PROVIDER_ROOT):
        for imported in import_names(parse_python(source)):
            assert not imported.startswith(forbidden), f"{source.name}: {imported}"


def test_provider_adapters_do_not_read_ambient_credentials_or_vendor_sdks() -> None:
    combined = "\n".join(read_python(source) for source in python_sources(PROVIDER_ROOT))

    assert "os.environ" not in combined
    assert "os.getenv" not in combined
    assert "import openai" not in combined
    assert "import anthropic" not in combined
    assert "from openai" not in combined
    assert "from anthropic" not in combined


def test_runtime_loop_uses_engine_submit_without_event_store_authority() -> None:
    imports = import_names(parse_python(RUNTIME_LOOP))
    source = read_python(RUNTIME_LOOP)

    assert not any(name.startswith("openrund.ports.events") for name in imports)
    assert not any(name.startswith("openrund.storage") for name in imports)
    assert ".append(" not in source
    assert "submit_model_proposal" in source
    assert "engine.submit" in source


def test_provider_and_runtime_sources_have_no_graphical_ui_dependency() -> None:
    for root in (PROVIDER_ROOT, RUNTIME_LOOP.parent):
        for source in python_sources(root):
            text = read_python(source).lower()
            assert "tkinter" not in text
            assert "pyqt" not in text
            assert "textual" not in text
            assert "streamlit" not in text
