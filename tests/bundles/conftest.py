from __future__ import annotations

import asyncio
import hashlib
import json
from dataclasses import dataclass

import pytest

from openrund._testing.memory import MemoryArtifactStore, MemoryEventStore
from openrund.codec import decode_event
from openrund.contracts.events import RuntimeEvent
from openrund.contracts.ids import ArtifactId, RunId
from openrund.contracts.time import Timestamp
from openrund.ports.artifacts import ArtifactBlob, ArtifactEntry
from openrund.ports.events import AppendEventsInput


@dataclass(frozen=True, slots=True)
class BundleSource:
    run_id: RunId
    timestamp: Timestamp
    event_store: MemoryEventStore
    artifact_store: MemoryArtifactStore
    events: tuple[RuntimeEvent, ...]
    artifact_id: ArtifactId
    artifact_bytes: bytes


def _wire(value: object) -> bytes:
    return (json.dumps(value, ensure_ascii=False, separators=(",", ":")) + "\n").encode()


@pytest.fixture
def bundle_source() -> BundleSource:
    run_id = RunId(value="run_bundle_test")
    timestamp = Timestamp(value="2026-08-06T12:00:00.000Z")
    artifact_id = ArtifactId(value="art_bundle_test")
    raw_events = (
        {
            "id": "evt_bundle_created",
            "runID": run_id.value,
            "position": 1,
            "type": "run.created",
            "version": 1,
            "timestamp": timestamp.value,
            "actor": "system",
            "payload": {
                "rootID": run_id.value,
                "initialStatus": "created",
                "title": "Portable test",
            },
        },
        {
            "id": "evt_bundle_started",
            "runID": run_id.value,
            "position": 2,
            "type": "run.started",
            "version": 1,
            "timestamp": timestamp.value,
            "actor": "system",
            "causationID": "evt_bundle_created",
            "payload": {"reason": "test"},
        },
        {
            "id": "evt_bundle_artifact",
            "runID": run_id.value,
            "position": 3,
            "type": "artifact.created",
            "version": 1,
            "timestamp": timestamp.value,
            "actor": "system",
            "causationID": "evt_bundle_started",
            "payload": {
                "artifactID": artifact_id.value,
                "kind": "report",
                "metadata": {"fixture": "bundle"},
                "contentPreview": "portable artifact",
            },
        },
    )
    events = tuple(decode_event(_wire(value)) for value in raw_events)
    event_store = MemoryEventStore()
    artifact_bytes = b"portable artifact"
    artifact_store = MemoryArtifactStore()

    async def setup() -> None:
        await event_store.append(
            AppendEventsInput(run_id=run_id, expected_position=0, events=events)
        )
        await artifact_store.put(
            ArtifactEntry(
                artifact_id=artifact_id,
                kind="report",
                created_at=timestamp,
                content_type="text/plain",
                byte_length=len(artifact_bytes),
                sha256=hashlib.sha256(artifact_bytes).hexdigest(),
            ),
            blob=ArtifactBlob(content=artifact_bytes, content_type="text/plain"),
        )

    asyncio.run(setup())
    return BundleSource(
        run_id=run_id,
        timestamp=timestamp,
        event_store=event_store,
        artifact_store=artifact_store,
        events=events,
        artifact_id=artifact_id,
        artifact_bytes=artifact_bytes,
    )
