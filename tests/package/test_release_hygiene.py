from __future__ import annotations

import ast
import tomllib
from pathlib import Path
from typing import Final

PROJECT_ROOT: Final = Path(__file__).resolve().parents[2]
SOURCE_ROOT: Final = PROJECT_ROOT / "src" / "openrund"
AMBIENT_CREDENTIAL_KEYS: Final = (
    "ANTHROPIC_API_KEY",
    "OPENAI_API_KEY",
)


def _sources() -> tuple[Path, ...]:
    return tuple(sorted(SOURCE_ROOT.rglob("*.py")))


def test_release_configuration_has_branch_coverage_and_strict_quality_gates() -> None:
    metadata = tomllib.loads((PROJECT_ROOT / "pyproject.toml").read_text(encoding="utf-8"))

    assert metadata["tool"]["coverage"]["run"] == {
        "branch": True,
        "source": ["openrund"],
    }
    assert metadata["tool"]["coverage"]["report"]["fail_under"] == 79
    assert metadata["tool"]["pytest"]["ini_options"]["xfail_strict"] is True
    assert metadata["tool"]["mypy"]["strict"] is True
    assert metadata["tool"]["ruff"]["lint"]["select"]


def test_release_has_public_security_and_change_records() -> None:
    security = (PROJECT_ROOT / "SECURITY.md").read_text(encoding="utf-8")
    changelog = (PROJECT_ROOT / "CHANGELOG.md").read_text(encoding="utf-8")

    assert "Reporting a vulnerability" in security
    assert "Security boundaries" in security
    assert "## 2.0.0" in changelog


def test_production_source_never_reads_ambient_provider_credentials() -> None:
    for source in _sources():
        content = source.read_text(encoding="utf-8")
        assert all(key not in content for key in AMBIENT_CREDENTIAL_KEYS), source


def test_production_source_uses_no_shell_or_dynamic_code_execution() -> None:
    forbidden_names = {"compile", "eval", "exec"}
    for source in _sources():
        tree = ast.parse(source.read_text(encoding="utf-8"), filename=str(source))
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            if isinstance(node.func, ast.Name):
                assert node.func.id not in forbidden_names, source
            assert not any(
                keyword.arg == "shell"
                and isinstance(keyword.value, ast.Constant)
                and keyword.value.value is True
                for keyword in node.keywords
            ), source
