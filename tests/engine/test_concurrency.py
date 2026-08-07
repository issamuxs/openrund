from __future__ import annotations

import asyncio

import pytest

from openrund._testing.memory import MemoryEventStore
from openrund.contracts.commands import (
    AcceptedCommandDecision,
    BootstrapRunOperation,
    CancelRunOperation,
    Command,
    CommandOrigin,
    RejectedCommandDecision,
    SupersededCommandDecision,
)
from openrund.contracts.events import CoreEventType, RunCancelledPayload
from openrund.contracts.ids import CommandId, RunId
from openrund.engine import EngineDependencies, RuntimeEngine
from openrund.errors import ExpectedPositionConflict
from openrund.ports.events import AppendEventsInput, AppendEventsResult, EventSlice
from tests.engine.conftest import runtime_event

RUN_ID = RunId(value="run_1")


def _command(
    command_id: str,
    operation: object,
    *,
    key: str | None = None,
) -> Command:
    return Command(
        command_id=CommandId(value=command_id),
        run_id=RUN_ID,
        origin=CommandOrigin.SYSTEM,
        operation=operation,  # type: ignore[arg-type]
        idempotency_key=key,
    )


def _bootstrap(command_id: str = "bootstrap", *, key: str | None = None) -> Command:
    return _command(
        command_id,
        BootstrapRunOperation(root_id=RUN_ID),
        key=key,
    )


class ConflictOnceStore:
    def __init__(self, backing: MemoryEventStore) -> None:
        self.backing = backing
        self.conflicted = False

    async def read(
        self,
        run_id: RunId,
        /,
        *,
        from_position: int = 1,
        limit: int | None = None,
    ) -> EventSlice:
        return await self.backing.read(run_id, from_position=from_position, limit=limit)

    async def append(self, value: AppendEventsInput, /) -> AppendEventsResult:
        if not self.conflicted:
            self.conflicted = True
            external = runtime_event(
                CoreEventType.RUN_CANCELLED,
                RunCancelledPayload(reason="external writer"),
                value.expected_position + 1,
            )
            await self.backing.append(
                AppendEventsInput(
                    run_id=value.run_id,
                    expected_position=value.expected_position,
                    events=(external,),
                )
            )
            raise ExpectedPositionConflict(
                run_id=value.run_id.value,
                expected_position=value.expected_position,
                actual_position=value.expected_position + 1,
            )
        return await self.backing.append(value)

    async def has_event(self, event_id: object, /) -> bool:
        return await self.backing.has_event(event_id)  # type: ignore[arg-type]


def test_conflict_replays_and_rejects_against_intervening_terminal_event(
    engine_dependencies: EngineDependencies,
    event_store: MemoryEventStore,
) -> None:
    base_engine = RuntimeEngine(engine_dependencies)
    asyncio.run(base_engine.submit(_bootstrap()))
    store = ConflictOnceStore(event_store)
    engine = RuntimeEngine(
        EngineDependencies(
            event_store=store,
            clock=engine_dependencies.clock,
            event_ids=engine_dependencies.event_ids,
            message_ids=engine_dependencies.message_ids,
        )
    )

    result = asyncio.run(engine.submit(_command("cancel", CancelRunOperation(reason="requested"))))
    history = asyncio.run(event_store.read(RUN_ID))

    assert isinstance(result.decision, RejectedCommandDecision)
    assert result.decision.reason == "run_terminal"
    assert tuple(event.event_type for event in history.events[-2:]) == (
        CoreEventType.RUN_CANCELLED,
        CoreEventType.COMMAND_RECORDED,
    )


def test_duplicate_command_id_returns_durable_result_without_second_append(
    engine_dependencies: EngineDependencies,
    event_store: MemoryEventStore,
) -> None:
    engine = RuntimeEngine(engine_dependencies)
    command = _bootstrap()
    first = asyncio.run(engine.submit(command))
    append_count = sum(call.operation == "append" for call in event_store.calls)

    second = asyncio.run(engine.submit(command))

    assert second == first
    assert sum(call.operation == "append" for call in event_store.calls) == append_count


def test_idempotency_collision_records_supersession_without_target(
    engine_dependencies: EngineDependencies,
    event_store: MemoryEventStore,
) -> None:
    engine = RuntimeEngine(engine_dependencies)
    first = asyncio.run(engine.submit(_bootstrap("command_1", key="stable")))
    second = asyncio.run(engine.submit(_bootstrap("command_2", key="stable")))
    history = asyncio.run(event_store.read(RUN_ID))

    assert isinstance(first.decision, AcceptedCommandDecision)
    assert isinstance(second.decision, SupersededCommandDecision)
    assert second.decision.superseded_by_command_id == CommandId(value="command_1")
    assert len(history.events) == 4
    assert history.events[-1].event_type is CoreEventType.COMMAND_RECORDED


def test_repeated_idempotency_collisions_keep_the_original_owner(
    engine_dependencies: EngineDependencies,
    event_store: MemoryEventStore,
) -> None:
    engine = RuntimeEngine(engine_dependencies)
    asyncio.run(engine.submit(_bootstrap("command_1", key="stable")))
    second = asyncio.run(engine.submit(_bootstrap("command_2", key="stable")))
    third = asyncio.run(engine.submit(_bootstrap("command_3", key="stable")))

    assert isinstance(second.decision, SupersededCommandDecision)
    assert isinstance(third.decision, SupersededCommandDecision)
    assert second.decision.superseded_by_command_id == CommandId(value="command_1")
    assert third.decision.superseded_by_command_id == CommandId(value="command_1")
    history = asyncio.run(event_store.read(RUN_ID))
    assert tuple(event.event_type for event in history.events[-2:]) == (
        CoreEventType.COMMAND_RECORDED,
        CoreEventType.COMMAND_RECORDED,
    )


class AlwaysConflictStore:
    def __init__(self) -> None:
        self.backing = MemoryEventStore()
        self.append_attempts = 0

    async def read(
        self,
        run_id: RunId,
        /,
        *,
        from_position: int = 1,
        limit: int | None = None,
    ) -> EventSlice:
        return await self.backing.read(run_id, from_position=from_position, limit=limit)

    async def append(self, value: AppendEventsInput, /) -> AppendEventsResult:
        self.append_attempts += 1
        raise ExpectedPositionConflict(
            run_id=value.run_id.value,
            expected_position=value.expected_position,
            actual_position=value.expected_position,
        )

    async def has_event(self, event_id: object, /) -> bool:
        return await self.backing.has_event(event_id)  # type: ignore[arg-type]


def test_conflict_retry_budget_is_finite(
    engine_dependencies: EngineDependencies,
) -> None:
    store = AlwaysConflictStore()
    engine = RuntimeEngine(
        EngineDependencies(
            event_store=store,
            clock=engine_dependencies.clock,
            event_ids=engine_dependencies.event_ids,
            message_ids=engine_dependencies.message_ids,
            conflict_retries=1,
        )
    )

    with pytest.raises(ExpectedPositionConflict):
        asyncio.run(engine.submit(_bootstrap()))
    assert store.append_attempts == 2
