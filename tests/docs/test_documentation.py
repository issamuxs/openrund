from __future__ import annotations

import re
from pathlib import Path
from typing import Final

PROJECT_ROOT: Final = Path(__file__).resolve().parents[2]
LIVE_DOCUMENTS: Final = (
    PROJECT_ROOT / "README.md",
    PROJECT_ROOT / "CHANGELOG.md",
    PROJECT_ROOT / "SECURITY.md",
    *(path for path in sorted((PROJECT_ROOT / "docs").glob("*.md"))),
    *(path for path in sorted((PROJECT_ROOT / "examples").glob("*.md"))),
)
LINK: Final = re.compile(r"\[[^]]+\]\(([^)]+)\)")
LEGACY_STACK_TERMS: Final = ("typescript", "javascript", "node.js", "pnpm")
QUALITY_COMMANDS: Final = (
    "uv run coverage run -m pytest -q",
    "uv run coverage report",
    "uv run mypy --strict src/openrund tests examples",
    "uv run ruff check src tests examples",
    "uv run ruff format --check src tests examples",
    "uv lock --check",
    "uv build",
    "git diff --check",
)


def test_live_documentation_uses_only_current_python_product_language() -> None:
    for document in LIVE_DOCUMENTS:
        content = document.read_text(encoding="utf-8")
        lowered = content.lower()
        assert all(term not in lowered for term in LEGACY_STACK_TERMS), document
        assert "UI-SPEC" not in content, document
        assert "@openrund/" not in content, document


def test_local_markdown_links_resolve() -> None:
    for document in LIVE_DOCUMENTS:
        for target in LINK.findall(document.read_text(encoding="utf-8")):
            location = target.split("#", 1)[0]
            if location == "" or "://" in location or location.startswith("mailto:"):
                continue
            resolved = (document.parent / location).resolve()
            assert resolved.exists(), f"{document.relative_to(PROJECT_ROOT)} -> {target}"


def test_quality_commands_have_one_canonical_documentation_owner() -> None:
    canonical = PROJECT_ROOT / "docs" / "contributing.md"
    readme = PROJECT_ROOT / "README.md"
    docs_readme = PROJECT_ROOT / "docs" / "README.md"
    complete_block = "\n".join(QUALITY_COMMANDS)

    assert complete_block in canonical.read_text(encoding="utf-8")
    owners = tuple(
        document.relative_to(PROJECT_ROOT)
        for document in LIVE_DOCUMENTS
        if complete_block in document.read_text(encoding="utf-8")
    )
    assert owners == (Path("docs/contributing.md"),)
    assert "[Development setup](./docs/contributing.md#development-setup)" in readme.read_text(
        encoding="utf-8"
    )
    assert "[Development setup](./contributing.md#development-setup)" in docs_readme.read_text(
        encoding="utf-8"
    )


def test_control_has_one_normative_authority_loop_owner() -> None:
    control = PROJECT_ROOT / "docs" / "control.md"
    readme = PROJECT_ROOT / "README.md"
    concepts = PROJECT_ROOT / "docs" / "concepts.md"
    architecture = PROJECT_ROOT / "docs" / "architecture.md"
    api = PROJECT_ROOT / "docs" / "api.md"
    normative = "Operation -> Command -> CommandDecision -> Events -> Views"
    control_text = control.read_text(encoding="utf-8")

    assert "normative owner of OpenRund's authority loop" in control_text
    assert "sole procedural mutation-authority boundary" in control_text
    assert "authoritative result of one attempted mutation" in control_text
    assert normative in control_text
    assert "[Control](./docs/control.md)" in readme.read_text(encoding="utf-8")
    assert "[Control](./control.md)" in concepts.read_text(encoding="utf-8")
    assert "[Control](./control.md)" in architecture.read_text(encoding="utf-8")
    assert "[Control](./control.md)" in api.read_text(encoding="utf-8")
    assert all(
        "sole procedural mutation-authority boundary" not in document.read_text(encoding="utf-8")
        for document in LIVE_DOCUMENTS
        if document != control
    )
    assert tuple(
        document.relative_to(PROJECT_ROOT)
        for document in LIVE_DOCUMENTS
        if normative in document.read_text(encoding="utf-8")
    ) == (Path("docs/control.md"),)


def test_core_documents_have_distinct_content_owners() -> None:
    markers = {
        Path("docs/concepts.md"): "## Core vocabulary",
        Path("docs/control.md"): "## Decision outcomes",
        Path("docs/architecture.md"): "## Package map",
        Path("docs/api.md"): "## CLI",
        Path("docs/contributing.md"): "## Development setup",
    }

    for expected_owner, marker in markers.items():
        owners = tuple(
            document.relative_to(PROJECT_ROOT)
            for document in LIVE_DOCUMENTS
            if marker in document.read_text(encoding="utf-8")
        )
        assert owners == (expected_owner,), marker


def test_public_docs_cover_installed_assembly_cli_and_demo() -> None:
    corpus = "\n".join(document.read_text(encoding="utf-8") for document in LIVE_DOCUMENTS)
    for sentinel in (
        "LocalAssemblyConfig",
        "RuntimeEngine",
        "OperatorService",
        "openrund --home",
        "demo governed-coding",
        "bundles verify",
        "unknown-outcome reconciliation",
    ):
        assert sentinel in corpus
    assert "OpenRund has no graphical interface" in corpus


def test_api_docs_freeze_root_facade_for_2x_and_prefer_named_subpackages() -> None:
    api = (PROJECT_ROOT / "docs" / "api.md").read_text(encoding="utf-8")

    assert "package-root facade is frozen for the 2.x release line" in api
    assert "advanced" in api and "typed result payloads" in api
    assert "Contracting the root facade is a major-release change" in api
