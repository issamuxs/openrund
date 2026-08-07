from __future__ import annotations

from pathlib import Path
from typing import Final

PROJECT_ROOT: Final = Path(__file__).resolve().parents[2]
REMOVED_ROOTS: Final = (
    "docs/archive",
    "node_modules",
    "package.json",
    "packages",
    "pnpm-lock.yaml",
    "pnpm-workspace.yaml",
    "python",
    "scripts",
    "tsconfig.base.json",
    "vitest.config.ts",
)
FORBIDDEN_CODE_SUFFIXES: Final = frozenset(
    {".cjs", ".js", ".jsx", ".mjs", ".ts", ".tsx", ".tsbuildinfo"}
)
IGNORED_TREE_PARTS: Final = frozenset(
    {
        ".git",
        ".mypy_cache",
        ".planning",
        ".pytest_cache",
        ".ruff_cache",
        ".venv",
        "__pycache__",
        "dist",
        "htmlcov",
    }
)
REMOVED_COMMAND_MARKERS: Final = ("pnpm ", "tsc ", "vitest")


def _live_files() -> tuple[Path, ...]:
    return tuple(
        candidate
        for candidate in PROJECT_ROOT.rglob("*")
        if candidate.is_file()
        and not any(
            part in IGNORED_TREE_PARTS for part in candidate.relative_to(PROJECT_ROOT).parts
        )
    )


def test_removed_package_and_tool_roots_cannot_return() -> None:
    assert all(not (PROJECT_ROOT / relative_path).exists() for relative_path in REMOVED_ROOTS)


def test_live_repository_contains_only_python_code() -> None:
    offenders = tuple(
        source.relative_to(PROJECT_ROOT).as_posix()
        for source in _live_files()
        if source.suffix.lower() in FORBIDDEN_CODE_SUFFIXES
    )
    assert offenders == ()


def test_live_product_text_uses_only_python_tooling_commands() -> None:
    documents = (
        PROJECT_ROOT / "README.md",
        PROJECT_ROOT / "AGENTS.md",
        PROJECT_ROOT / "pyproject.toml",
        *(PROJECT_ROOT / "docs").rglob("*.md"),
        *(PROJECT_ROOT / "examples").rglob("*.md"),
    )
    offenders = {
        document.relative_to(PROJECT_ROOT).as_posix(): marker
        for document in documents
        for marker in REMOVED_COMMAND_MARKERS
        if marker in document.read_text(encoding="utf-8").lower()
    }
    assert offenders == {}
