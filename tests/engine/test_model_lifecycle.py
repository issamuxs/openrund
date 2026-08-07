from __future__ import annotations

import asyncio

from openrund._testing.memory import MemoryEventStore
from openrund.contracts.commands import (
    AcceptedCommandDecision,
    AddMessageOperation,
    BootstrapRunOperation,
    CancelModelCallOperation,
    Command,
    CommandOrigin,
    CompleteModelCallOperation,
    MessageDeltaOperation,
    RejectedCommandDecision,
    StartModelCallOperation,
)
from openrund.contracts.content import Content
from openrund.contracts.events import (
    CanonicalMessageAddedPayload,
    CoreEventType,
    MessageDeltaPayload,
    ModelCallCompletedPayload,
    ModelCallStartedPayload,
)
from openrund.contracts.ids import CommandId, MessageId, ModelCallId, RunId
from openrund.engine import EngineDependencies, RuntimeEngine

RUN_ID = RunId(value="run_1")


def _command(command_id: str, operation: object) -> Command:
    return Command(
        command_id=CommandId(value=command_id),
        run_id=RUN_ID,
        origin=CommandOrigin.SYSTEM,
        operation=operation,  # type: ignore[arg-type]
    )


def _started_engine(dependencies: EngineDependencies) -> RuntimeEngine:
    engine = RuntimeEngine(dependencies)
    asyncio.run(engine.submit(_command("bootstrap", BootstrapRunOperation(root_id=RUN_ID))))
    return engine


def test_message_add_and_delta_are_linked_replayable_commands(
    engine_dependencies: EngineDependencies,
    event_store: MemoryEventStore,
) -> None:
    engine = _started_engine(engine_dependencies)
    added = asyncio.run(
        engine.submit(
            _command(
                "add_message",
                AddMessageOperation(
                    message=Content(
                        preview="hello",
                        metadata={"role": "assistant"},  # type: ignore[arg-type]
                    )
                ),
            )
        )
    )
    delta = asyncio.run(
        engine.submit(
            _command(
                "delta_message",
                MessageDeltaOperation(
                    message_id=MessageId(value="msg_1"),
                    delta=" world",
                ),
            )
        )
    )
    history = asyncio.run(event_store.read(RUN_ID))

    assert isinstance(added.decision, AcceptedCommandDecision)
    assert isinstance(delta.decision, AcceptedCommandDecision)
    message_event = next(
        event for event in history.events if event.event_type is CoreEventType.MESSAGE_ADDED
    )
    delta_event = next(
        event for event in history.events if event.event_type is CoreEventType.MESSAGE_DELTA
    )
    assert isinstance(message_event.payload, CanonicalMessageAddedPayload)
    assert message_event.payload.message_id == MessageId(value="msg_1")
    assert message_event.payload.content_preview == "hello"
    assert isinstance(delta_event.payload, MessageDeltaPayload)
    assert delta_event.payload.message_id == message_event.payload.message_id
    assert delta_event.payload.delta == " world"
    assert delta_event.command_id == CommandId(value="delta_message")


def test_unknown_message_delta_is_rejected_without_target_event(
    engine_dependencies: EngineDependencies,
    event_store: MemoryEventStore,
) -> None:
    engine = _started_engine(engine_dependencies)

    result = asyncio.run(
        engine.submit(
            _command(
                "delta_missing",
                MessageDeltaOperation(
                    message_id=MessageId(value="missing"),
                    delta="chunk",
                ),
            )
        )
    )
    history = asyncio.run(event_store.read(RUN_ID))

    assert isinstance(result.decision, RejectedCommandDecision)
    assert result.decision.reason == "message_not_found"
    assert not any(event.event_type is CoreEventType.MESSAGE_DELTA for event in history.events)


def test_model_call_has_one_start_and_one_terminal_outcome(
    engine_dependencies: EngineDependencies,
    event_store: MemoryEventStore,
) -> None:
    engine = _started_engine(engine_dependencies)
    model_call_id = ModelCallId(value="model_1")

    started = asyncio.run(
        engine.submit(_command("model_start", StartModelCallOperation(model_call_id=model_call_id)))
    )
    duplicate_start = asyncio.run(
        engine.submit(
            _command("model_start_again", StartModelCallOperation(model_call_id=model_call_id))
        )
    )
    completed = asyncio.run(
        engine.submit(
            _command(
                "model_complete",
                CompleteModelCallOperation(
                    model_call_id=model_call_id,
                    outcome="proposal",
                    metadata={"tokens": 10},  # type: ignore[arg-type]
                ),
            )
        )
    )
    second_terminal = asyncio.run(
        engine.submit(
            _command(
                "model_cancel_late",
                CancelModelCallOperation(model_call_id=model_call_id, reason="late"),
            )
        )
    )
    history = asyncio.run(event_store.read(RUN_ID))

    assert isinstance(started.decision, AcceptedCommandDecision)
    assert isinstance(duplicate_start.decision, RejectedCommandDecision)
    assert duplicate_start.decision.reason == "model_call_already_exists"
    assert isinstance(completed.decision, AcceptedCommandDecision)
    assert isinstance(second_terminal.decision, RejectedCommandDecision)
    assert second_terminal.decision.reason == "model_call_terminal"
    started_payloads = tuple(
        event.payload
        for event in history.events
        if isinstance(event.payload, ModelCallStartedPayload)
    )
    completed_payloads = tuple(
        event.payload
        for event in history.events
        if isinstance(event.payload, ModelCallCompletedPayload)
    )
    assert len(started_payloads) == 1
    assert len(completed_payloads) == 1
    assert completed_payloads[0].outcome == "proposal"


def test_model_terminal_without_start_is_rejected(
    engine_dependencies: EngineDependencies,
) -> None:
    engine = _started_engine(engine_dependencies)

    result = asyncio.run(
        engine.submit(
            _command(
                "model_cancel",
                CancelModelCallOperation(
                    model_call_id=ModelCallId(value="missing"),
                    reason="none",
                ),
            )
        )
    )

    assert isinstance(result.decision, RejectedCommandDecision)
    assert result.decision.reason == "model_call_not_found"
