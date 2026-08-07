"""Deterministic in-memory port substitutes with no durability claim."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, replace
from datetime import datetime, timedelta
from typing import final

from openrund.contracts.events import RuntimeEvent
from openrund.contracts.ids import ArtifactId, EventId, LeaseId, RunId
from openrund.contracts.json import MISSING
from openrund.contracts.runs import Lease
from openrund.contracts.time import Timestamp
from openrund.errors import ExpectedPositionConflict, StorageIntegrityError, ValidationError
from openrund.ports.artifacts import ArtifactBlob, ArtifactEntry
from openrund.ports.events import (
    AppendEventsInput,
    AppendEventsResult,
    AppendManyEventsInput,
    AppendManyEventsResult,
    EventSlice,
)
from openrund.ports.leases import LeaseAcquireInput, LeaseRenewInput


@final
@dataclass(frozen=True, slots=True, kw_only=True)
class MemoryCall:
    operation: str
    subject: object


def _position(value: object, code: str, *, minimum: int = 0) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < minimum:
        raise ValidationError(code=code)
    return value


def _add_milliseconds(timestamp: Timestamp, milliseconds: int) -> Timestamp:
    parsed = datetime.strptime(timestamp.value, "%Y-%m-%dT%H:%M:%S.%fZ")
    advanced = parsed + timedelta(milliseconds=milliseconds)
    return Timestamp(value=advanced.strftime("%Y-%m-%dT%H:%M:%S.%f")[:23] + "Z")


@final
class MemoryEventStore:
    """Insertion-ordered EventStore substitute; not production storage."""

    def __init__(self) -> None:
        self._streams: dict[RunId, list[RuntimeEvent]] = {}
        self._event_ids: set[EventId] = set()
        self._calls: list[MemoryCall] = []

    @property
    def calls(self) -> tuple[MemoryCall, ...]:
        return tuple(self._calls)

    async def append(self, value: AppendEventsInput, /) -> AppendEventsResult:
        self._calls.append(MemoryCall(operation="append", subject=value))
        return self._append_batches((value,)).results[0]

    async def append_many(self, value: AppendManyEventsInput, /) -> AppendManyEventsResult:
        self._calls.append(MemoryCall(operation="append_many", subject=value))
        return self._append_batches(value.batches)

    def _append_batches(self, batches: tuple[AppendEventsInput, ...]) -> AppendManyEventsResult:
        for batch in batches:
            stream = self._streams.get(batch.run_id, [])
            actual_position = stream[-1].position if stream else 0
            if batch.expected_position != actual_position:
                raise ExpectedPositionConflict(
                    run_id=batch.run_id.value,
                    expected_position=batch.expected_position,
                    actual_position=actual_position,
                )
        incoming_ids = tuple(event.event_id for batch in batches for event in batch.events)
        if len(set(incoming_ids)) != len(incoming_ids) or any(
            event_id in self._event_ids for event_id in incoming_ids
        ):
            raise StorageIntegrityError(code="event_id_duplicate")

        results: list[AppendEventsResult] = []
        for batch in batches:
            stream = self._streams.setdefault(batch.run_id, [])
            stream.extend(batch.events)
            results.append(
                AppendEventsResult(
                    run_id=batch.run_id,
                    appended=batch.events,
                    next_position=stream[-1].position,
                )
            )
        self._event_ids.update(incoming_ids)
        return AppendManyEventsResult(results=tuple(results))

    async def read(
        self,
        run_id: RunId,
        /,
        *,
        from_position: int = 1,
        limit: int | None = None,
    ) -> EventSlice:
        _position(from_position, "event_read_position_invalid", minimum=1)
        if limit is not None:
            _position(limit, "event_read_limit_invalid", minimum=1)
        self._calls.append(MemoryCall(operation="read", subject=(run_id, from_position, limit)))
        stream = self._streams.get(run_id, [])
        selected = [event for event in stream if event.position >= from_position]
        if limit is not None:
            selected = selected[:limit]
        next_position = selected[-1].position + 1 if selected else from_position
        return EventSlice(
            run_id=run_id,
            events=tuple(selected),
            next_position=next_position,
        )

    async def has_event(self, event_id: EventId, /) -> bool:
        self._calls.append(MemoryCall(operation="has_event", subject=event_id))
        return event_id in self._event_ids


@final
class MemoryArtifactStore:
    """Immutable ArtifactStore substitute; no filesystem custody semantics."""

    def __init__(self) -> None:
        self._artifacts: dict[ArtifactId, ArtifactEntry] = {}
        self._blobs: dict[ArtifactId, ArtifactBlob] = {}
        self._calls: list[MemoryCall] = []

    @property
    def calls(self) -> tuple[MemoryCall, ...]:
        return tuple(self._calls)

    async def put(self, artifact: ArtifactEntry, /, *, blob: ArtifactBlob | None = None) -> None:
        self._calls.append(MemoryCall(operation="put", subject=(artifact, blob)))
        copied_blob = None
        if blob is not None:
            copied_blob = ArtifactBlob(content=bytes(blob.content), content_type=blob.content_type)
            digest = hashlib.sha256(copied_blob.content).hexdigest()
            if artifact.byte_length != len(copied_blob.content) or artifact.sha256 != digest:
                raise StorageIntegrityError(code="artifact_integrity_mismatch")
            if (
                copied_blob.content_type is not MISSING
                and artifact.content_type != copied_blob.content_type
            ):
                raise StorageIntegrityError(code="artifact_content_type_mismatch")
        existing = self._artifacts.get(artifact.artifact_id)
        if existing is not None:
            if existing == artifact and self._blobs.get(artifact.artifact_id) == copied_blob:
                return
            raise StorageIntegrityError(code="artifact_immutable")
        self._artifacts[artifact.artifact_id] = artifact
        if copied_blob is not None:
            self._blobs[artifact.artifact_id] = copied_blob

    async def get(self, artifact_id: ArtifactId, /) -> ArtifactEntry | None:
        self._calls.append(MemoryCall(operation="get", subject=artifact_id))
        return self._artifacts.get(artifact_id)

    async def get_blob(self, artifact_id: ArtifactId, /) -> ArtifactBlob | None:
        self._calls.append(MemoryCall(operation="get_blob", subject=artifact_id))
        blob = self._blobs.get(artifact_id)
        if blob is None:
            return None
        return ArtifactBlob(content=bytes(blob.content), content_type=blob.content_type)

    async def mark_unavailable(self, artifact_id: ArtifactId, unavailable_at: Timestamp, /) -> None:
        self._calls.append(
            MemoryCall(operation="mark_unavailable", subject=(artifact_id, unavailable_at))
        )
        artifact = self._artifacts.get(artifact_id)
        if artifact is None:
            raise StorageIntegrityError(code="artifact_not_found")
        if artifact.unavailable_at not in (MISSING, None):
            if artifact.unavailable_at == unavailable_at:
                return
            raise StorageIntegrityError(code="artifact_immutable")
        self._artifacts[artifact_id] = replace(artifact, unavailable_at=unavailable_at)


@final
class MemoryLeaseStore:
    """Deterministic LeaseStore substitute; no distributed-lock guarantee."""

    def __init__(self) -> None:
        self._by_run: dict[RunId, Lease] = {}
        self._by_id: dict[LeaseId, Lease] = {}
        self._next_id = 1
        self._calls: list[MemoryCall] = []

    @property
    def calls(self) -> tuple[MemoryCall, ...]:
        return tuple(self._calls)

    async def acquire(self, value: LeaseAcquireInput, /) -> Lease | None:
        self._calls.append(MemoryCall(operation="acquire", subject=value))
        active = self._active(value.run_id, value.now)
        if active is not None:
            return None
        lease = Lease(
            lease_id=LeaseId(value=f"memory-lease-{self._next_id}"),
            run_id=value.run_id,
            owner=value.owner,
            token=f"memory-token-{self._next_id}",
            acquired_at=value.now,
            expires_at=_add_milliseconds(value.now, value.ttl_ms),
        )
        self._next_id += 1
        self._by_run[lease.run_id] = lease
        self._by_id[lease.lease_id] = lease
        return lease

    async def renew(self, value: LeaseRenewInput, /) -> Lease | None:
        self._calls.append(MemoryCall(operation="renew", subject=value))
        lease = self._by_id.get(value.lease_id)
        if (
            lease is None
            or lease.run_id != value.run_id
            or lease.owner != value.owner
            or lease.token != value.token
            or lease.expires_at.value <= value.now.value
        ):
            return None
        renewed = replace(
            lease,
            expires_at=_add_milliseconds(value.now, value.ttl_ms),
        )
        self._by_id[renewed.lease_id] = renewed
        self._by_run[renewed.run_id] = renewed
        return renewed

    async def release(self, lease_id: LeaseId, token: str, /) -> bool:
        self._calls.append(MemoryCall(operation="release", subject=(lease_id, token)))
        lease = self._by_id.get(lease_id)
        if lease is None or lease.token != token:
            return False
        del self._by_id[lease_id]
        self._by_run.pop(lease.run_id, None)
        return True

    async def get_active(self, run_id: RunId, now: Timestamp, /) -> Lease | None:
        self._calls.append(MemoryCall(operation="get_active", subject=(run_id, now)))
        return self._active(run_id, now)

    def _active(self, run_id: RunId, now: Timestamp) -> Lease | None:
        lease = self._by_run.get(run_id)
        if lease is None:
            return None
        if lease.expires_at.value > now.value:
            return lease
        self._by_run.pop(run_id, None)
        self._by_id.pop(lease.lease_id, None)
        return None
