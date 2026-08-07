from __future__ import annotations

import inspect
from dataclasses import FrozenInstanceError
from typing import assert_type

import pytest

from openrund.contracts.events import (
    CoreEventType,
    Event,
    EventActor,
    RunStartedPayload,
    RuntimeEvent,
)
from openrund.contracts.ids import ArtifactId, EventId, LeaseId, RunId
from openrund.contracts.json import MISSING, JsonArray, JsonObject
from openrund.contracts.runs import Lease
from openrund.contracts.time import Timestamp
from openrund.errors import ExpectedPositionConflict, ValidationError
from openrund.ports.artifacts import ArtifactBlob, ArtifactEntry, ArtifactStore
from openrund.ports.events import (
    AppendEventsInput,
    AppendEventsResult,
    AppendManyEventsInput,
    AppendManyEventsResult,
    AtomicEventStore,
    EventSlice,
    EventStore,
)
from openrund.ports.leases import LeaseAcquireInput, LeaseRenewInput, LeaseStore


def _timestamp(second: int = 5) -> Timestamp:
    return Timestamp(value=f"2026-01-02T03:04:{second:02d}.000Z")


def _event(position: int = 1) -> RuntimeEvent:
    return Event(
        event_id=EventId(value=f"e{position}"),
        run_id=RunId(value="r1"),
        position=position,
        event_type=CoreEventType.RUN_STARTED,
        timestamp=_timestamp(),
        actor=EventActor.SYSTEM,
        payload=RunStartedPayload(),
    )


class ConformingEventStore:
    async def append(self, value: AppendEventsInput, /) -> AppendEventsResult:
        return AppendEventsResult(
            run_id=value.run_id,
            appended=value.events,
            next_position=value.events[-1].position,
        )

    async def read(
        self,
        run_id: RunId,
        /,
        *,
        from_position: int = 1,
        limit: int | None = None,
    ) -> EventSlice:
        del from_position, limit
        return EventSlice(run_id=run_id, events=(), next_position=0)

    async def has_event(self, event_id: EventId, /) -> bool:
        return event_id.value == "present"

    async def append_many(self, value: AppendManyEventsInput, /) -> AppendManyEventsResult:
        return AppendManyEventsResult(
            results=tuple(
                AppendEventsResult(
                    run_id=batch.run_id,
                    appended=batch.events,
                    next_position=batch.events[-1].position,
                )
                for batch in value.batches
            )
        )


class ConformingArtifactStore:
    async def put(self, artifact: ArtifactEntry, /, *, blob: ArtifactBlob | None = None) -> None:
        del artifact, blob

    async def get(self, artifact_id: ArtifactId, /) -> ArtifactEntry | None:
        del artifact_id
        return None

    async def get_blob(self, artifact_id: ArtifactId, /) -> ArtifactBlob | None:
        del artifact_id
        return None

    async def mark_unavailable(self, artifact_id: ArtifactId, unavailable_at: Timestamp, /) -> None:
        del artifact_id, unavailable_at


class ConformingLeaseStore:
    async def acquire(self, value: LeaseAcquireInput, /) -> Lease | None:
        del value
        return None

    async def renew(self, value: LeaseRenewInput, /) -> Lease | None:
        del value
        return None

    async def release(self, lease_id: LeaseId, token: str, /) -> bool:
        del lease_id, token
        return True

    async def get_active(self, run_id: RunId, now: Timestamp, /) -> Lease | None:
        del run_id, now
        return None


EVENT_STORE: EventStore = ConformingEventStore()
ATOMIC_EVENT_STORE: AtomicEventStore = ConformingEventStore()
ARTIFACT_STORE: ArtifactStore = ConformingArtifactStore()
LEASE_STORE: LeaseStore = ConformingLeaseStore()


def test_store_protocols_are_static_async_structural_contracts() -> None:
    assert_type(EVENT_STORE, EventStore)
    assert_type(ATOMIC_EVENT_STORE, AtomicEventStore)
    assert_type(ARTIFACT_STORE, ArtifactStore)
    assert_type(LEASE_STORE, LeaseStore)
    assert inspect.iscoroutinefunction(EventStore.append)
    assert inspect.iscoroutinefunction(ArtifactStore.put)
    assert inspect.iscoroutinefunction(LeaseStore.acquire)
    assert not hasattr(EventStore, "__runtime_protocol__")


def test_event_values_are_frozen_ordered_and_position_checked() -> None:
    event = _event()
    value = AppendEventsInput(run_id=RunId(value="r1"), expected_position=0, events=(event,))
    event_slice = EventSlice(run_id=value.run_id, events=value.events, next_position=1)

    assert event_slice.events == (event,)
    with pytest.raises(FrozenInstanceError):
        value.expected_position = 1  # type: ignore[misc]
    with pytest.raises(ValidationError, match="append_events_positions_invalid"):
        AppendEventsInput(run_id=value.run_id, expected_position=1, events=(event,))

    other_run_event = Event(
        event_id=event.event_id,
        run_id=RunId(value="r2"),
        position=1,
        event_type=event.event_type,
        timestamp=event.timestamp,
        actor=event.actor,
        payload=event.payload,
    )
    with pytest.raises(ValidationError, match="append_events_events_invalid"):
        AppendEventsInput(run_id=value.run_id, expected_position=0, events=(other_run_event,))
    with pytest.raises(ValidationError, match="append_many_run_duplicate"):
        AppendManyEventsInput(batches=(value, value))


def test_artifact_blob_and_entry_are_immutable_custody_values() -> None:
    blob = ArtifactBlob(content=b"abc", content_type="text/plain")
    artifact = ArtifactEntry(
        artifact_id=ArtifactId(value="a1"),
        kind="text",
        created_at=_timestamp(),
        content_type="text/plain",
        byte_length=3,
        sha256="a" * 64,
        metadata={"nested": [1]},  # type: ignore[arg-type]
    )

    assert blob.content == b"abc"
    assert artifact.unavailable_at is MISSING
    assert isinstance(artifact.metadata, JsonObject)
    nested = artifact.metadata["nested"]
    assert isinstance(nested, JsonArray)
    assert tuple(nested) == (1,)
    with pytest.raises(ValidationError, match="artifact_blob_content_invalid"):
        ArtifactBlob(content=bytearray(b"abc"))  # type: ignore[arg-type]
    with pytest.raises(ValidationError, match="artifact_entry_byte_length_invalid"):
        ArtifactEntry(
            artifact_id=artifact.artifact_id,
            kind=artifact.kind,
            created_at=artifact.created_at,
            byte_length=True,
        )
    with pytest.raises(ValidationError, match="artifact_entry_sha256_invalid"):
        ArtifactEntry(
            artifact_id=artifact.artifact_id,
            kind=artifact.kind,
            created_at=artifact.created_at,
            byte_length=3,
            sha256="not-a-digest",
        )


def test_lease_inputs_are_frozen_and_exactly_typed() -> None:
    acquire = LeaseAcquireInput(
        run_id=RunId(value="r1"), owner="worker-1", ttl_ms=1_000, now=_timestamp()
    )
    renew = LeaseRenewInput(
        lease_id=LeaseId(value="l1"),
        run_id=acquire.run_id,
        owner=acquire.owner,
        token="token-1",
        ttl_ms=acquire.ttl_ms,
        now=acquire.now,
    )

    assert renew.run_id == acquire.run_id
    with pytest.raises(ValidationError, match="lease_renew_token_invalid"):
        LeaseRenewInput(
            lease_id=renew.lease_id,
            run_id=renew.run_id,
            owner=renew.owner,
            token="",
            ttl_ms=renew.ttl_ms,
            now=renew.now,
        )
    with pytest.raises(ValidationError, match="lease_acquire_ttl_invalid"):
        LeaseAcquireInput(run_id=acquire.run_id, owner=acquire.owner, ttl_ms=True, now=acquire.now)
    with pytest.raises(ValidationError, match="lease_acquire_timestamp_invalid"):
        LeaseAcquireInput(
            run_id=acquire.run_id,
            owner=acquire.owner,
            ttl_ms=acquire.ttl_ms,
            now=object(),  # type: ignore[arg-type]
        )


def test_expected_position_conflict_remains_infrastructure_failure() -> None:
    conflict = ExpectedPositionConflict(run_id="r1", expected_position=2, actual_position=3)

    assert conflict.code == "expected_position_conflict"
    assert conflict.expected_position == 2
    assert conflict.actual_position == 3
