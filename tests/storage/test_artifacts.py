from __future__ import annotations

import asyncio
import hashlib
import sqlite3
from pathlib import Path

import pytest

from openrund.contracts.ids import ArtifactId
from openrund.contracts.json import JsonObject
from openrund.contracts.time import Timestamp
from openrund.errors import StorageError, StorageIntegrityError, ValidationError
from openrund.ports.artifacts import ArtifactBlob, ArtifactEntry
from openrund.storage import SqliteArtifactStore


def _timestamp(second: int = 5) -> Timestamp:
    return Timestamp(value=f"2026-01-02T03:04:{second:02d}.000Z")


def _entry(identifier: str, content: bytes | None = None) -> ArtifactEntry:
    if content is None:
        return ArtifactEntry(
            artifact_id=ArtifactId(value=identifier),
            kind="document",
            created_at=_timestamp(),
            metadata=JsonObject(entries=(("nested", JsonObject(entries=(("value", 1),))),)),
        )
    return ArtifactEntry(
        artifact_id=ArtifactId(value=identifier),
        kind="document",
        created_at=_timestamp(),
        content_type="application/octet-stream",
        byte_length=len(content),
        sha256=hashlib.sha256(content).hexdigest(),
        metadata=JsonObject(entries=(("nested", JsonObject(entries=(("value", 1),))),)),
    )


def _store(database_path: Path, root: Path) -> SqliteArtifactStore:
    return SqliteArtifactStore(database_path, root)


def test_artifact_store_persists_metadata_only_and_reopens(
    database_path: Path, tmp_path: Path
) -> None:
    async def scenario() -> None:
        root = tmp_path / "artifacts"
        artifact = _entry("metadata-only")
        store = _store(database_path, root)
        await store.put(artifact)
        assert await store.get(artifact.artifact_id) == artifact
        assert await store.get_blob(artifact.artifact_id) is None
        assert await _store(database_path, root).get(artifact.artifact_id) == artifact

        connection = sqlite3.connect(database_path)
        row = connection.execute(
            "SELECT blob_path, metadata_json FROM artifacts WHERE artifact_id = ?",
            (artifact.artifact_id.value,),
        ).fetchone()
        connection.close()
        assert row == (None, '{"nested":{"value":1}}')

    asyncio.run(scenario())


@pytest.mark.parametrize("content", [b"", b"x" * (1024 * 1024)])
def test_artifact_store_publishes_and_verifies_empty_and_large_blobs(
    database_path: Path, tmp_path: Path, content: bytes
) -> None:
    async def scenario() -> None:
        root = tmp_path / "artifacts"
        artifact = _entry(f"blob-{len(content)}", content)
        blob = ArtifactBlob(content=content, content_type="application/octet-stream")
        store = _store(database_path, root)
        await store.put(artifact, blob=blob)
        await store.put(artifact, blob=blob)
        loaded = await store.get_blob(artifact.artifact_id)
        assert loaded == blob

        connection = sqlite3.connect(database_path)
        relative = connection.execute(
            "SELECT blob_path FROM artifacts WHERE artifact_id = ?",
            (artifact.artifact_id.value,),
        ).fetchone()[0]
        connection.close()
        assert relative == f"blobs/{artifact.artifact_id.value}.blob"
        assert not Path(relative).is_absolute()
        assert (root / relative).read_bytes() == content

    asyncio.run(scenario())


def test_artifact_store_rejects_integrity_content_type_and_immutable_reuse(
    database_path: Path, tmp_path: Path
) -> None:
    async def scenario() -> None:
        store = _store(database_path, tmp_path / "artifacts")
        content = b"content"
        artifact = _entry("artifact-1", content)
        blob = ArtifactBlob(content=content, content_type="application/octet-stream")
        await store.put(artifact, blob=blob)

        with pytest.raises(StorageIntegrityError, match="artifact_integrity_mismatch"):
            await store.put(artifact, blob=ArtifactBlob(content=b"different"))
        with pytest.raises(StorageIntegrityError, match="artifact_content_type_mismatch"):
            await store.put(artifact, blob=ArtifactBlob(content=content, content_type="text/plain"))
        with pytest.raises(StorageIntegrityError, match="artifact_immutable"):
            await store.put(
                ArtifactEntry(
                    artifact_id=artifact.artifact_id,
                    kind="other",
                    created_at=artifact.created_at,
                )
            )
        assert await store.get_blob(artifact.artifact_id) == blob

    asyncio.run(scenario())


def test_artifact_store_marks_unavailable_once(database_path: Path, tmp_path: Path) -> None:
    async def scenario() -> None:
        store = _store(database_path, tmp_path / "artifacts")
        content = b"content"
        artifact = _entry("artifact-1", content)
        await store.put(artifact, blob=ArtifactBlob(content=content))
        await store.mark_unavailable(artifact.artifact_id, _timestamp(6))
        await store.mark_unavailable(artifact.artifact_id, _timestamp(6))
        unavailable = await store.get(artifact.artifact_id)
        assert unavailable is not None and unavailable.unavailable_at == _timestamp(6)
        assert await store.get_blob(artifact.artifact_id) is None
        with pytest.raises(StorageIntegrityError, match="artifact_immutable"):
            await store.mark_unavailable(artifact.artifact_id, _timestamp(7))
        with pytest.raises(StorageIntegrityError, match="artifact_not_found"):
            await store.mark_unavailable(ArtifactId(value="missing"), _timestamp(6))

    asyncio.run(scenario())


@pytest.mark.parametrize("identifier", [".", "..", "a/b", "a\\b", "C:", "C:blob", "\x00"])
def test_artifact_store_rejects_unsafe_identifiers(
    database_path: Path, tmp_path: Path, identifier: str
) -> None:
    store = _store(database_path, tmp_path / "artifacts")
    with pytest.raises(ValidationError, match="artifact_id_component_invalid"):
        asyncio.run(store.put(_entry(identifier)))


def test_artifact_store_refuses_symlinked_internal_directory(
    database_path: Path, tmp_path: Path
) -> None:
    root = tmp_path / "artifacts"
    outside = tmp_path / "outside"
    root.mkdir()
    outside.mkdir()
    (root / "staging").symlink_to(outside, target_is_directory=True)
    with pytest.raises(StorageError, match="artifact_root_symlink"):
        _store(database_path, root)
    assert tuple(outside.iterdir()) == ()


@pytest.mark.parametrize("damage", ["missing", "corrupt", "symlink"])
def test_artifact_store_never_returns_missing_corrupt_or_linked_bytes(
    database_path: Path, tmp_path: Path, damage: str
) -> None:
    async def scenario() -> None:
        root = tmp_path / "artifacts"
        content = b"trusted"
        artifact = _entry("artifact-1", content)
        store = _store(database_path, root)
        await store.put(artifact, blob=ArtifactBlob(content=content))
        path = root / "blobs" / "artifact-1.blob"
        path.unlink()
        if damage == "corrupt":
            path.write_bytes(b"corrupt")
        elif damage == "symlink":
            target = tmp_path / "outside"
            target.write_bytes(content)
            path.symlink_to(target)
        with pytest.raises(StorageIntegrityError):
            await store.get_blob(artifact.artifact_id)

    asyncio.run(scenario())
