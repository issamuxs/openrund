from __future__ import annotations

import ast
from pathlib import Path


def python_sources(root: Path, *, recursive: bool = False) -> tuple[Path, ...]:
    """Return Python sources below ``root`` in deterministic path order."""
    candidates = root.rglob("*.py") if recursive else root.glob("*.py")
    return tuple(sorted(candidates))


def read_python(source: Path) -> str:
    """Read Python source using the repository's required UTF-8 encoding."""
    return source.read_text(encoding="utf-8")


def parse_python(source: Path) -> ast.Module:
    """Parse UTF-8 Python source with its path attached to syntax errors."""
    return ast.parse(read_python(source), filename=str(source))


def import_names(tree: ast.AST) -> tuple[str, ...]:
    """Extract absolute import targets in AST traversal order."""
    names: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module is not None:
            names.append(node.module)
    return tuple(names)
