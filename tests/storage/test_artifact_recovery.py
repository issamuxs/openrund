from __future__ import annotations

import asyncio
import hashlib
from pathlib import Path

import pytest

from openrund.contracts.ids import ArtifactId
from openrund.contracts.time import Timestamp
from openrund.ports.artifacts import ArtifactBlob, ArtifactEntry
from openrund.storage import ArtifactRecoverySummary, SqliteArtifactStore
from openrund.storage._artifacts import _ArtifactCrash


def _timestamp(second: int = 5) -> Timestamp:
    return Timestamp(value=f"2026-01-02T03:04:{second:02d}.000Z")


def _entry(identifier: str, content: bytes) -> ArtifactEntry:
    return ArtifactEntry(
        artifact_id=ArtifactId(value=identifier),
        kind="recovery",
        created_at=_timestamp(),
        byte_length=len(content),
        sha256=hashlib.sha256(content).hexdigest(),
    )


@pytest.mark.parametrize(
    "fault_point",
    ["after_staging", "after_publish", "before_metadata_commit", "after_metadata_commit"],
)
def test_every_put_crash_window_recovers_idempotently(
    database_path: Path, tmp_path: Path, fault_point: str
) -> None:
    async def scenario() -> None:
        root = tmp_path / "artifacts"
        content = b"durable"
        artifact = _entry("artifact-1", content)
        crashing = SqliteArtifactStore(database_path, root, _fail_at=fault_point)
        with pytest.raises(_ArtifactCrash):
            await crashing.put(artifact, blob=ArtifactBlob(content=content))

        assert len(tuple((root / "staging").iterdir())) == 1
        fresh = SqliteArtifactStore(database_path, root)
        first = await fresh.recover(_timestamp(6))
        second = await fresh.recover(_timestamp(7))
        assert first.removed_stages == 1
        assert second.removed_stages == 0
        assert second.quarantined_orphans == ()
        assert second.unavailable_artifacts == ()

        if fault_point == "after_staging":
            assert first.quarantined_orphans == ()
            assert await fresh.get(artifact.artifact_id) is None
            assert tuple((root / "blobs").iterdir()) == ()
        elif fault_point in {"after_publish", "before_metadata_commit"}:
            assert first.quarantined_orphans == (artifact.artifact_id,)
            assert await fresh.get(artifact.artifact_id) is None
            assert tuple((root / "blobs").iterdir()) == ()
            assert (root / "orphans" / "artifact-1.blob").read_bytes() == content
        else:
            assert first.verified_artifacts == (artifact.artifact_id,)
            assert second.verified_artifacts == (artifact.artifact_id,)
            assert await fresh.get_blob(artifact.artifact_id) == ArtifactBlob(content=content)
        assert tuple((root / "staging").iterdir()) == ()

    asyncio.run(scenario())


@pytest.mark.parametrize("damage", ["missing", "corrupt", "symlink"])
def test_recovery_marks_committed_missing_or_corrupt_blob_unavailable(
    database_path: Path, tmp_path: Path, damage: str
) -> None:
    async def scenario() -> None:
        root = tmp_path / "artifacts"
        content = b"durable"
        artifact = _entry("artifact-1", content)
        store = SqliteArtifactStore(database_path, root)
        await store.put(artifact, blob=ArtifactBlob(content=content))
        path = root / "blobs" / "artifact-1.blob"
        path.unlink()
        if damage == "corrupt":
            path.write_bytes(b"bad")
        elif damage == "symlink":
            outside = tmp_path / "outside"
            outside.write_bytes(content)
            path.symlink_to(outside)

        summary = await SqliteArtifactStore(database_path, root).recover(_timestamp(6))
        assert summary.unavailable_artifacts == (artifact.artifact_id,)
        recovered = await store.get(artifact.artifact_id)
        assert recovered is not None and recovered.unavailable_at == _timestamp(6)
        assert await store.get_blob(artifact.artifact_id) is None
        assert (await store.recover(_timestamp(7))).unavailable_artifacts == ()

    asyncio.run(scenario())


def test_recovery_preserves_matching_pairs_and_ignores_unrelated_or_symlinked_files(
    database_path: Path, tmp_path: Path
) -> None:
    async def scenario() -> None:
        root = tmp_path / "artifacts"
        content = b"durable"
        artifact = _entry("artifact-1", content)
        store = SqliteArtifactStore(database_path, root)
        await store.put(artifact, blob=ArtifactBlob(content=content))

        unrelated_stage = root / "staging" / "notes.txt"
        unrelated_blob = root / "blobs" / "notes.txt"
        unrelated_stage.write_text("keep", encoding="utf-8")
        unrelated_blob.write_text("keep", encoding="utf-8")
        outside = tmp_path / "outside"
        outside.write_text("outside", encoding="utf-8")
        stage_link = root / "staging" / ("linked." + ("a" * 32) + ".stage")
        blob_link = root / "blobs" / "linked.blob"
        stage_link.symlink_to(outside)
        blob_link.symlink_to(outside)

        summary = await store.recover(_timestamp(6))
        assert summary == ArtifactRecoverySummary(
            removed_stages=0,
            quarantined_orphans=(),
            unavailable_artifacts=(),
            verified_artifacts=(artifact.artifact_id,),
        )
        assert unrelated_stage.read_text(encoding="utf-8") == "keep"
        assert unrelated_blob.read_text(encoding="utf-8") == "keep"
        assert stage_link.is_symlink()
        assert blob_link.is_symlink()
        assert outside.read_text(encoding="utf-8") == "outside"
        assert await store.get_blob(artifact.artifact_id) == ArtifactBlob(content=content)

    asyncio.run(scenario())
