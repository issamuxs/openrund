from __future__ import annotations

import ast
import asyncio
import hashlib
import inspect
import sqlite3
from collections.abc import Iterator
from pathlib import Path, PurePosixPath
from typing import Final

import pytest
from tests._quality import import_names, parse_python, python_sources

import openrund.storage as storage
from openrund.contracts.ids import ArtifactId
from openrund.contracts.time import Timestamp
from openrund.errors import StorageError
from openrund.ports.artifacts import ArtifactBlob, ArtifactEntry
from openrund.storage import SqliteArtifactStore, SqliteRunEventStore

PROJECT_ROOT: Final = Path(__file__).resolve().parents[2]
STORAGE_ROOT: Final = PROJECT_ROOT / "src" / "openrund" / "storage"

_PUBLIC_EXPORTS: Final = (
    "ArtifactRecoverySummary",
    "PostCommitEventLog",
    "PostCommitSubscriberFailure",
    "RunHome",
    "SqliteArtifactStore",
    "SqliteExecutionLeaseStore",
    "SqliteRunEventStore",
    "default_openrund_home",
    "materialize_run_home",
    "run_home",
)
_FORBIDDEN_IMPORT_PREFIXES: Final = (
    "openrund.assembly",
    "openrund.bundles",
    "openrund.cli",
    "openrund.contracts.capabilities",
    "openrund.contracts.portable",
    "openrund.engine",
    "openrund.ports.capabilities",
    "openrund.ports.providers",
    "openrund.ui",
)
_FORBIDDEN_PUBLIC_METHODS: Final = frozenset(
    {
        "authorize",
        "decide_legality",
        "display",
        "grant_authority",
        "main",
        "render",
        "revoke_authority",
        "serve",
    }
)


def _sources() -> tuple[Path, ...]:
    return python_sources(STORAGE_ROOT)


def _tree(source: Path) -> ast.Module:
    return parse_python(source)


def _imports(tree: ast.Module) -> tuple[str, ...]:
    return import_names(tree)


def _direct_nodes(root: ast.AST) -> Iterator[ast.AST]:
    for child in ast.iter_child_nodes(root):
        if isinstance(child, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda)):
            continue
        yield child
        yield from _direct_nodes(child)


def _function_body_nodes(
    function: ast.FunctionDef | ast.AsyncFunctionDef,
) -> Iterator[ast.AST]:
    for statement in function.body:
        if isinstance(statement, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        yield statement
        yield from _direct_nodes(statement)


def _is_sqlite_connect(node: ast.AST) -> bool:
    return (
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and isinstance(node.func.value, ast.Name)
        and node.func.value.id == "sqlite3"
        and node.func.attr == "connect"
    )


def test_public_storage_surface_is_exact_typed_and_infrastructure_free() -> None:
    assert tuple(storage.__all__) == _PUBLIC_EXPORTS
    assert all(hasattr(storage, name) for name in _PUBLIC_EXPORTS)
    assert not hasattr(storage, "_Database")
    assert not hasattr(storage, "_ArtifactCrash")
    assert not hasattr(storage, "sqlite3")

    for name in _PUBLIC_EXPORTS:
        value = getattr(storage, name)
        if callable(value):
            assert "sqlite3" not in str(inspect.signature(value))


def test_storage_dependency_direction_has_no_authority_or_presentation_surface() -> None:
    public_names: set[str] = set()
    for source in _sources():
        tree = _tree(source)
        imports = _imports(tree)
        assert all(
            not name.startswith(prefix) for name in imports for prefix in _FORBIDDEN_IMPORT_PREFIXES
        ), source
        for node in tree.body:
            if isinstance(
                node, (ast.FunctionDef, ast.AsyncFunctionDef)
            ) and not node.name.startswith("_"):
                public_names.add(node.name)
            elif isinstance(node, ast.ClassDef):
                public_names.update(
                    member.name
                    for member in node.body
                    if isinstance(member, (ast.FunctionDef, ast.AsyncFunctionDef))
                    and not member.name.startswith("_")
                )

    assert public_names.isdisjoint(_FORBIDDEN_PUBLIC_METHODS)
    assert not (STORAGE_ROOT.parent / "ui.py").exists()
    assert not (STORAGE_ROOT.parent / "ui").exists()
    assert not (STORAGE_ROOT / "cli.py").exists()
    assert not (STORAGE_ROOT / "cli").exists()


def test_sqlite_connections_are_private_short_lived_and_never_span_awaits() -> None:
    connect_owners: list[tuple[Path, str]] = []
    for source in _sources():
        tree = _tree(source)
        assert not any(_is_sqlite_connect(node) for node in _direct_nodes(tree)), source
        for function in (
            node
            for node in ast.walk(tree)
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        ):
            direct = tuple(_function_body_nodes(function))
            if any(_is_sqlite_connect(node) for node in direct):
                connect_owners.append((source, function.name))
            if isinstance(function, ast.AsyncFunctionDef):
                assert not any(
                    isinstance(node, ast.Name) and node.id == "sqlite3" for node in direct
                ), f"{source}:{function.lineno}"
                assert not any(
                    isinstance(node, ast.Constant)
                    and isinstance(node.value, str)
                    and any(
                        token in node.value.upper() for token in ("BEGIN ", "COMMIT", "ROLLBACK")
                    )
                    for node in direct
                ), f"{source}:{function.lineno}"

    assert connect_owners == [(STORAGE_ROOT / "_database.py", "_connect")]


def test_public_storage_failures_do_not_leak_paths_content_or_sqlite_errors(
    tmp_path: Path,
) -> None:
    secret = "never-expose-this-storage-secret"
    database_path = tmp_path / secret
    database_path.mkdir()

    with pytest.raises(StorageError) as caught:
        SqliteRunEventStore(database_path)

    rendered = str(caught.value)
    assert secret not in rendered
    assert str(database_path) not in rendered
    assert not isinstance(caught.value, sqlite3.Error)
    assert not isinstance(caught.value.__cause__, sqlite3.Error)

    artifact_root = tmp_path / f"{secret}-content"
    artifact_root.write_text(secret, encoding="utf-8")
    with pytest.raises(StorageError) as artifact_failure:
        SqliteArtifactStore(tmp_path / "runtime.sqlite", artifact_root)
    assert secret not in str(artifact_failure.value)
    assert str(artifact_root) not in str(artifact_failure.value)


def test_persisted_blob_paths_are_relative_custody_references(tmp_path: Path) -> None:
    database_path = tmp_path / "runtime.sqlite"
    artifact_root = tmp_path / "artifacts"
    content = b"immutable artifact bytes"
    artifact = ArtifactEntry(
        artifact_id=ArtifactId(value="artifact-relative"),
        kind="document",
        created_at=Timestamp(value="2026-01-02T03:04:05.000Z"),
        content_type="application/octet-stream",
        byte_length=len(content),
        sha256=hashlib.sha256(content).hexdigest(),
    )
    store = SqliteArtifactStore(database_path, artifact_root)
    asyncio.run(
        store.put(
            artifact,
            blob=ArtifactBlob(content=content, content_type="application/octet-stream"),
        )
    )

    connection = sqlite3.connect(database_path)
    try:
        row = connection.execute(
            "SELECT blob_path FROM artifacts WHERE artifact_id = ?",
            (artifact.artifact_id.value,),
        ).fetchone()
    finally:
        connection.close()
    assert row is not None
    assert row[0] == "blobs/artifact-relative.blob"
    assert not PurePosixPath(str(row[0])).is_absolute()
