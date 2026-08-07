from __future__ import annotations

import asyncio
import hashlib
from typing import assert_type

import pytest

from openrund._testing.memory import (
    MemoryArtifactStore,
    MemoryEventStore,
    MemoryLeaseStore,
)
from openrund.contracts.events import CoreEventType, Event, EventActor, RunStartedPayload
from openrund.contracts.ids import ArtifactId, EventId, LeaseId, RunId
from openrund.contracts.time import Timestamp
from openrund.errors import ExpectedPositionConflict, StorageIntegrityError
from openrund.ports.artifacts import ArtifactBlob, ArtifactEntry, ArtifactStore
from openrund.ports.events import (
    AppendEventsInput,
    AppendManyEventsInput,
    AtomicEventStore,
    EventStore,
)
from openrund.ports.leases import LeaseAcquireInput, LeaseRenewInput, LeaseStore


def _timestamp(second: int = 5) -> Timestamp:
    return Timestamp(value=f"2026-01-02T03:04:{second:02d}.000Z")


def _event(position: int) -> Event[CoreEventType, RunStartedPayload]:
    return Event(
        event_id=EventId(value=f"e{position}"),
        run_id=RunId(value="r1"),
        position=position,
        event_type=CoreEventType.RUN_STARTED,
        timestamp=_timestamp(),
        actor=EventActor.SYSTEM,
        payload=RunStartedPayload(),
    )


def test_memory_stores_conform_structurally() -> None:
    events: EventStore = MemoryEventStore()
    atomic_events: AtomicEventStore = MemoryEventStore()
    artifacts: ArtifactStore = MemoryArtifactStore()
    leases: LeaseStore = MemoryLeaseStore()

    assert_type(events, EventStore)
    assert_type(atomic_events, AtomicEventStore)
    assert_type(artifacts, ArtifactStore)
    assert_type(leases, LeaseStore)


def test_event_store_preserves_order_and_typed_conflicts() -> None:
    async def scenario() -> None:
        store = MemoryEventStore()
        first = AppendEventsInput(
            run_id=RunId(value="r1"), expected_position=0, events=(_event(1), _event(2))
        )
        result = await store.append(first)
        selected = await store.read(first.run_id, from_position=1)

        assert result.appended == first.events
        assert selected.events == first.events
        assert selected.next_position == 3
        assert (await store.read(first.run_id, from_position=3)).next_position == 3
        assert await store.has_event(EventId(value="e2")) is True
        with pytest.raises(ExpectedPositionConflict) as raised:
            await store.append(
                AppendEventsInput(
                    run_id=first.run_id,
                    expected_position=0,
                    events=(_event(1),),
                )
            )
        assert raised.value.actual_position == 2
        assert tuple(call.operation for call in store.calls) == (
            "append",
            "read",
            "read",
            "has_event",
            "append",
        )

    asyncio.run(scenario())


def test_event_store_append_many_is_atomic_and_rejects_duplicate_runs() -> None:
    async def scenario() -> None:
        store = MemoryEventStore()
        second_run_event = Event(
            event_id=EventId(value="other-e1"),
            run_id=RunId(value="r2"),
            position=1,
            event_type=CoreEventType.RUN_STARTED,
            timestamp=_timestamp(),
            actor=EventActor.SYSTEM,
            payload=RunStartedPayload(),
        )
        result = await store.append_many(
            AppendManyEventsInput(
                batches=(
                    AppendEventsInput(
                        run_id=RunId(value="r1"), expected_position=0, events=(_event(1),)
                    ),
                    AppendEventsInput(
                        run_id=RunId(value="r2"),
                        expected_position=0,
                        events=(second_run_event,),
                    ),
                )
            )
        )
        assert tuple(item.next_position for item in result.results) == (1, 1)

        with pytest.raises(ExpectedPositionConflict):
            await store.append_many(
                AppendManyEventsInput(
                    batches=(
                        AppendEventsInput(
                            run_id=RunId(value="r1"),
                            expected_position=1,
                            events=(_event(2),),
                        ),
                        AppendEventsInput(
                            run_id=RunId(value="r3"),
                            expected_position=1,
                            events=(
                                Event(
                                    event_id=EventId(value="r3-e2"),
                                    run_id=RunId(value="r3"),
                                    position=2,
                                    event_type=CoreEventType.RUN_STARTED,
                                    timestamp=_timestamp(),
                                    actor=EventActor.SYSTEM,
                                    payload=RunStartedPayload(),
                                ),
                            ),
                        ),
                    )
                )
            )
        assert (await store.read(RunId(value="r1"))).next_position == 2
        assert (await store.read(RunId(value="r3"))).events == ()

    asyncio.run(scenario())


def test_artifact_store_copies_blob_and_enforces_immutable_idempotency() -> None:
    async def scenario() -> None:
        store = MemoryArtifactStore()
        content = b"abc"
        artifact = ArtifactEntry(
            artifact_id=ArtifactId(value="a1"),
            kind="text",
            created_at=_timestamp(),
            content_type="text/plain",
            byte_length=len(content),
            sha256=hashlib.sha256(content).hexdigest(),
        )
        blob = ArtifactBlob(content=content, content_type="text/plain")
        await store.put(artifact, blob=blob)
        await store.put(artifact, blob=blob)

        assert await store.get(artifact.artifact_id) == artifact
        assert await store.get_blob(artifact.artifact_id) == blob
        await store.mark_unavailable(artifact.artifact_id, _timestamp(6))
        unavailable = await store.get(artifact.artifact_id)
        assert unavailable is not None and unavailable.unavailable_at == _timestamp(6)
        with pytest.raises(StorageIntegrityError, match="artifact_immutable"):
            await store.put(
                ArtifactEntry(
                    artifact_id=artifact.artifact_id,
                    kind="different",
                    created_at=artifact.created_at,
                )
            )
        with pytest.raises(StorageIntegrityError, match="artifact_integrity_mismatch"):
            await MemoryArtifactStore().put(artifact, blob=ArtifactBlob(content=b"wrong"))

    asyncio.run(scenario())


def test_lease_store_is_ordered_deterministic_and_owner_scoped() -> None:
    async def scenario() -> None:
        store = MemoryLeaseStore()
        acquire = LeaseAcquireInput(
            run_id=RunId(value="r1"), owner="worker-1", ttl_ms=1_000, now=_timestamp()
        )
        lease = await store.acquire(acquire)
        assert lease is not None
        assert lease.lease_id == LeaseId(value="memory-lease-1")
        assert await store.acquire(acquire) is None

        renewed = await store.renew(
            LeaseRenewInput(
                lease_id=lease.lease_id,
                run_id=lease.run_id,
                owner=lease.owner,
                token=lease.token,
                ttl_ms=3_000,
                now=_timestamp(),
            )
        )
        assert renewed is not None
        assert renewed.expires_at == _timestamp(8)
        assert await store.release(lease.lease_id, "stale-token") is False
        assert await store.release(lease.lease_id, lease.token) is True
        assert await store.get_active(lease.run_id, _timestamp(6)) is None

    asyncio.run(scenario())


def test_private_memory_helpers_make_no_durability_or_authority_claim() -> None:
    forbidden = {
        "commit",
        "transaction",
        "recover",
        "create_event",
        "decide_legality",
        "grant_authority",
    }

    for store_type in (MemoryEventStore, MemoryArtifactStore, MemoryLeaseStore):
        assert forbidden.isdisjoint(dir(store_type))
