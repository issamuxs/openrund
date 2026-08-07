from __future__ import annotations

import asyncio
import hashlib
from pathlib import Path

from openrund.bundles import export_bundle, import_bundle, replay_bundle, verify_bundle
from openrund.ports.artifacts import ArtifactBlob, ArtifactEntry
from openrund.ports.events import AppendEventsInput
from openrund.storage import SqliteArtifactStore, SqliteRunEventStore

from .conftest import BundleSource


def test_sqlite_export_verify_replay_import_assess_lifecycle(
    tmp_path: Path, bundle_source: BundleSource
) -> None:
    async def scenario() -> None:
        database = tmp_path / "runtime.sqlite"
        event_store = SqliteRunEventStore(database)
        artifact_store = SqliteArtifactStore(database, tmp_path / "artifacts")
        await event_store.append(
            AppendEventsInput(
                run_id=bundle_source.run_id,
                expected_position=0,
                events=bundle_source.events,
            )
        )
        await artifact_store.put(
            ArtifactEntry(
                artifact_id=bundle_source.artifact_id,
                kind="report",
                created_at=bundle_source.timestamp,
                content_type="text/plain",
                byte_length=len(bundle_source.artifact_bytes),
                sha256=hashlib.sha256(bundle_source.artifact_bytes).hexdigest(),
            ),
            blob=ArtifactBlob(
                content=bundle_source.artifact_bytes,
                content_type="text/plain",
            ),
        )
        exported = await export_bundle(
            run_id=bundle_source.run_id,
            output_path=tmp_path / "sqlite.orun",
            event_store=event_store,
            artifact_store=artifact_store,
            exported_at=bundle_source.timestamp,
            required_providers=("local",),
        )
        verified = verify_bundle(exported.bundle_path)
        replay = replay_bundle(exported.bundle_path)
        workspace = tmp_path / "workspace"
        workspace.mkdir()
        imported = import_bundle(
            exported.bundle_path,
            runtime_home=tmp_path / "runtime-home",
            root_mappings={"workspace": workspace},
            imported_at=bundle_source.timestamp,
            capture_resume_snapshot=True,
        )
        assert verified.manifest == exported.manifest == imported.manifest
        assert replay.events == bundle_source.events
        assert verify_bundle(imported.bundle_path).manifest == exported.manifest
        await event_store.aclose()
        await artifact_store.aclose()

    asyncio.run(scenario())
