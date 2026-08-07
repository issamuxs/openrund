from __future__ import annotations

from collections.abc import Iterator
from typing import cast

import pytest

from openrund._testing.memory import MemoryEventStore
from openrund.contracts.events import CoreEventType, Event, EventActor, EventPayload, RuntimeEvent
from openrund.contracts.ids import (
    AnnotationId,
    AuthorityId,
    CheckId,
    CheckpointId,
    CommandId,
    DelegationId,
    EventId,
    MessageId,
    RunId,
    RuntimeId,
    WaitId,
)
from openrund.contracts.json import MISSING, MissingType
from openrund.contracts.time import Timestamp
from openrund.engine import EngineDependencies


class FixedClock:
    def now(self) -> Timestamp:
        return Timestamp(value="2026-08-05T12:00:00.000Z")


class SequenceIdFactory[TId: RuntimeId]:
    def __init__(self, values: Iterator[TId]) -> None:
        self._values = values

    def new_id(self) -> TId:
        return next(self._values)


def _event_ids() -> Iterator[EventId]:
    index = 1
    while True:
        yield EventId(value=f"evt_{index}")
        index += 1


def _message_ids() -> Iterator[MessageId]:
    index = 1
    while True:
        yield MessageId(value=f"msg_{index}")
        index += 1


def _run_ids() -> Iterator[RunId]:
    index = 1
    while True:
        yield RunId(value=f"child_{index}")
        index += 1


def _wait_ids() -> Iterator[WaitId]:
    index = 1
    while True:
        yield WaitId(value=f"wait_{index}")
        index += 1


def _delegation_ids() -> Iterator[DelegationId]:
    index = 1
    while True:
        yield DelegationId(value=f"delegation_{index}")
        index += 1


def _check_ids() -> Iterator[CheckId]:
    index = 1
    while True:
        yield CheckId(value=f"check_{index}")
        index += 1


def _checkpoint_ids() -> Iterator[CheckpointId]:
    index = 1
    while True:
        yield CheckpointId(value=f"checkpoint_{index}")
        index += 1


def _annotation_ids() -> Iterator[AnnotationId]:
    index = 1
    while True:
        yield AnnotationId(value=f"annotation_{index}")
        index += 1


def _authority_ids() -> Iterator[AuthorityId]:
    index = 1
    while True:
        yield AuthorityId(value=f"authority_{index}")
        index += 1


@pytest.fixture
def event_store() -> MemoryEventStore:
    return MemoryEventStore()


@pytest.fixture
def engine_dependencies(event_store: MemoryEventStore) -> EngineDependencies:
    return EngineDependencies(
        event_store=event_store,
        clock=FixedClock(),
        event_ids=SequenceIdFactory(_event_ids()),
        message_ids=SequenceIdFactory(_message_ids()),
        run_ids=SequenceIdFactory(_run_ids()),
        wait_ids=SequenceIdFactory(_wait_ids()),
        delegation_ids=SequenceIdFactory(_delegation_ids()),
        check_ids=SequenceIdFactory(_check_ids()),
        checkpoint_ids=SequenceIdFactory(_checkpoint_ids()),
        annotation_ids=SequenceIdFactory(_annotation_ids()),
        authority_ids=SequenceIdFactory(_authority_ids()),
        atomic_event_store=event_store,
    )


def runtime_event(
    event_type: CoreEventType,
    payload: EventPayload,
    position: int,
    *,
    run_id: RunId | None = None,
    command_id: CommandId | MissingType = MISSING,
) -> RuntimeEvent:
    return cast(
        RuntimeEvent,
        Event(
            event_id=EventId(value=f"history_{position}"),
            run_id=RunId(value="run_1") if run_id is None else run_id,
            position=position,
            event_type=event_type,
            timestamp=Timestamp(value="2026-08-05T12:00:00.000Z"),
            actor=EventActor.SYSTEM,
            payload=payload,
            command_id=command_id,
        ),
    )
