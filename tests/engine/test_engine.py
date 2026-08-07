from __future__ import annotations

import asyncio
from typing import cast

import pytest

from openrund._testing.memory import MemoryEventStore
from openrund.contracts.commands import (
    AcceptedCommandDecision,
    BootstrapRunOperation,
    Command,
    CommandOrigin,
    RejectedCommandDecision,
)
from openrund.contracts.events import (
    CoreEventType,
    RunCreatedPayload,
    RunStartedPayload,
    RuntimeCommandRecordedPayload,
    RuntimeEvent,
)
from openrund.contracts.ids import CommandId, RunId
from openrund.engine import EngineDependencies, RuntimeEngine
from openrund.errors import StorageIntegrityError
from openrund.ports.events import EventSlice, EventStore
from openrund.views import CompleteViewReplay, rebuild_views
from openrund.views._model import RunViewBundle
from tests.engine.conftest import runtime_event

RUN_ID = RunId(value="run_1")


def _bootstrap(command_id: str = "command_1", *, key: str | None = None) -> Command:
    return Command(
        command_id=CommandId(value=command_id),
        run_id=RUN_ID,
        origin=CommandOrigin.SYSTEM,
        operation=BootstrapRunOperation(
            root_id=RUN_ID,
            title="Engine test",
            objective="prove authority",
        ),
        idempotency_key=key,
    )


def test_submit_bootstrap_commits_one_atomic_audit_and_target_batch(
    engine_dependencies: EngineDependencies,
    event_store: MemoryEventStore,
) -> None:
    engine = RuntimeEngine(engine_dependencies)

    result = asyncio.run(engine.submit(_bootstrap()))
    history = asyncio.run(event_store.read(RUN_ID))

    assert isinstance(result.decision, AcceptedCommandDecision)
    assert len(result.decision.result_event_ids) == 2
    assert tuple(event.event_type for event in history.events) == (
        CoreEventType.COMMAND_RECORDED,
        CoreEventType.RUN_CREATED,
        CoreEventType.RUN_STARTED,
    )
    record, created, started = history.events
    assert isinstance(record.payload, RuntimeCommandRecordedPayload)
    assert isinstance(created.payload, RunCreatedPayload)
    assert isinstance(started.payload, RunStartedPayload)
    assert record.payload.decision_record.branch.result_event_ids == (
        created.event_id,
        started.event_id,
    )
    assert created.command_id == CommandId(value="command_1")
    assert started.command_id == CommandId(value="command_1")
    assert created.causation_id == record.event_id
    append_calls = tuple(call for call in event_store.calls if call.operation == "append")
    assert len(append_calls) == 1


def test_submit_rebuilds_each_loaded_stream_once_per_attempt(
    engine_dependencies: EngineDependencies,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[int] = []

    def counting_rebuild(
        events: tuple[RuntimeEvent, ...], *, watermark: int
    ) -> CompleteViewReplay[RunViewBundle]:
        calls.append(watermark)
        replay = rebuild_views(events, watermark=watermark)
        assert isinstance(replay, CompleteViewReplay)
        return replay

    monkeypatch.setattr("openrund.engine._engine.rebuild_views", counting_rebuild)

    result = asyncio.run(RuntimeEngine(engine_dependencies).submit(_bootstrap()))

    assert isinstance(result.decision, AcceptedCommandDecision)
    assert calls == [0]


def test_rejected_attempt_commits_only_command_record(
    engine_dependencies: EngineDependencies,
    event_store: MemoryEventStore,
) -> None:
    engine = RuntimeEngine(engine_dependencies)
    asyncio.run(engine.submit(_bootstrap()))

    result = asyncio.run(engine.submit(_bootstrap("command_2")))
    history = asyncio.run(event_store.read(RUN_ID))

    assert isinstance(result.decision, RejectedCommandDecision)
    assert result.decision.reason == "run_already_exists"
    assert len(history.events) == 4
    assert history.events[-1].event_type is CoreEventType.COMMAND_RECORDED
    payload = history.events[-1].payload
    assert isinstance(payload, RuntimeCommandRecordedPayload)
    assert payload.decision_record.branch.result_event_ids == ()


class IncompleteStore:
    async def read(
        self,
        run_id: RunId,
        /,
        *,
        from_position: int = 1,
        limit: int | None = None,
    ) -> EventSlice:
        del from_position, limit
        return EventSlice(
            run_id=run_id,
            events=(
                runtime_event(
                    CoreEventType.RUN_CREATED,
                    RunCreatedPayload(root_id=run_id, initial_status="created"),
                    1,
                    run_id=run_id,
                ),
                runtime_event(
                    CoreEventType.RUN_STARTED,
                    RunStartedPayload(),
                    3,
                    run_id=run_id,
                ),
            ),
            next_position=4,
        )


def test_incomplete_history_fails_closed_before_decision(
    engine_dependencies: EngineDependencies,
) -> None:
    dependencies = EngineDependencies(
        event_store=cast(EventStore, IncompleteStore()),
        clock=engine_dependencies.clock,
        event_ids=engine_dependencies.event_ids,
        message_ids=engine_dependencies.message_ids,
    )

    with pytest.raises(StorageIntegrityError, match="event_history_incomplete"):
        asyncio.run(RuntimeEngine(dependencies).submit(_bootstrap()))


def test_public_engine_surface_has_no_append_emit_or_store(
    engine_dependencies: EngineDependencies,
) -> None:
    engine = RuntimeEngine(engine_dependencies)

    assert not hasattr(engine, "append")
    assert not hasattr(engine, "emit")
    assert not hasattr(engine, "event_store")
    assert tuple(name for name in dir(engine) if not name.startswith("_")) == (
        "aclose",
        "submit",
    )
