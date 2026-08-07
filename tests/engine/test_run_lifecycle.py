from __future__ import annotations

import asyncio

from openrund._testing.memory import MemoryEventStore
from openrund.contracts.commands import (
    AcceptedCommandDecision,
    BootstrapRunOperation,
    CancelRunOperation,
    Command,
    CommandOrigin,
    FailRunOperation,
    RejectedCommandDecision,
    StartRunOperation,
)
from openrund.contracts.events import (
    CoreEventType,
    RunCancelledPayload,
    RunCreatedPayload,
    RunFailedPayload,
    RunStartedPayload,
)
from openrund.contracts.ids import CommandId, RunId
from openrund.engine import EngineDependencies, RuntimeEngine
from openrund.ports.events import AppendEventsInput
from tests.engine.conftest import runtime_event

RUN_ID = RunId(value="run_1")


def _command(command_id: str, operation: object, *, run_id: RunId = RUN_ID) -> Command:
    return Command(
        command_id=CommandId(value=command_id),
        run_id=run_id,
        origin=CommandOrigin.SYSTEM,
        operation=operation,  # type: ignore[arg-type]
    )


def test_bootstrap_preserves_root_and_child_descriptors(
    engine_dependencies: EngineDependencies,
    event_store: MemoryEventStore,
) -> None:
    child_id = RunId(value="run_child")
    parent_id = RunId(value="run_parent")
    operation = BootstrapRunOperation(
        root_id=RUN_ID,
        parent_run_id=parent_id,
        title="child",
        objective="bounded work",
        metadata={"contract": "one"},  # type: ignore[arg-type]
        start_reason="delegated",
    )

    result = asyncio.run(
        RuntimeEngine(engine_dependencies).submit(
            _command("bootstrap_child", operation, run_id=child_id)
        )
    )
    history = asyncio.run(event_store.read(child_id))

    assert isinstance(result.decision, AcceptedCommandDecision)
    created = history.events[1].payload
    started = history.events[2].payload
    assert isinstance(created, RunCreatedPayload)
    assert created.root_id == RUN_ID
    assert created.parent_run_id == parent_id
    assert created.title == "child"
    assert created.objective == "bounded work"
    assert created.metadata["contract"] == "one"  # type: ignore[index]
    assert isinstance(started, RunStartedPayload)
    assert started.reason == "delegated"


def test_created_run_can_start_through_the_same_submit_path(
    engine_dependencies: EngineDependencies,
    event_store: MemoryEventStore,
) -> None:
    created = runtime_event(
        CoreEventType.RUN_CREATED,
        RunCreatedPayload(root_id=RUN_ID, initial_status="created"),
        1,
    )
    asyncio.run(
        event_store.append(AppendEventsInput(run_id=RUN_ID, expected_position=0, events=(created,)))
    )

    result = asyncio.run(
        RuntimeEngine(engine_dependencies).submit(
            _command("start", StartRunOperation(reason="resume"))
        )
    )
    history = asyncio.run(event_store.read(RUN_ID))

    assert isinstance(result.decision, AcceptedCommandDecision)
    assert tuple(event.event_type for event in history.events[-2:]) == (
        CoreEventType.COMMAND_RECORDED,
        CoreEventType.RUN_STARTED,
    )


def test_fail_and_cancel_are_permanent_terminal_transitions(
    engine_dependencies: EngineDependencies,
    event_store: MemoryEventStore,
) -> None:
    engine = RuntimeEngine(engine_dependencies)
    asyncio.run(engine.submit(_command("bootstrap", BootstrapRunOperation(root_id=RUN_ID))))

    failed = asyncio.run(
        engine.submit(_command("fail", FailRunOperation(message="failed", retryable=True)))
    )
    late_cancel = asyncio.run(engine.submit(_command("cancel", CancelRunOperation(reason="late"))))
    history = asyncio.run(event_store.read(RUN_ID))

    assert isinstance(failed.decision, AcceptedCommandDecision)
    assert isinstance(late_cancel.decision, RejectedCommandDecision)
    assert late_cancel.decision.reason == "run_terminal"
    failure = next(
        event.payload for event in history.events if event.event_type is CoreEventType.RUN_FAILED
    )
    assert isinstance(failure, RunFailedPayload)
    assert failure.message == "failed"
    assert failure.retryable is True
    assert not any(isinstance(event.payload, RunCancelledPayload) for event in history.events)
