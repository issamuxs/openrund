from __future__ import annotations

import asyncio

from openrund._testing.memory import MemoryEventStore
from openrund.contracts.commands import (
    AcceptedCommandDecision,
    AddMessageOperation,
    BootstrapRunOperation,
    Command,
    CommandOrigin,
    OpenInteractionWaitOperation,
)
from openrund.contracts.content import Content
from openrund.contracts.events import (
    CoreEventType,
    ModelCommandRecordedPayload,
    RuntimeCommandRecordedPayload,
)
from openrund.contracts.ids import CommandId, ModelCallId, RunId
from openrund.engine import (
    EngineDependencies,
    RuntimeEngine,
    command_from_model_proposal,
    submit_model_proposal,
)
from openrund.ports.providers import ModelProposal

RUN_ID = RunId(value="run_1")


def _bootstrap() -> Command:
    return Command(
        command_id=CommandId(value="bootstrap"),
        run_id=RUN_ID,
        origin=CommandOrigin.SYSTEM,
        operation=BootstrapRunOperation(root_id=RUN_ID),
    )


def _proposal(operation: object) -> ModelProposal:
    return ModelProposal(
        model_call_id=ModelCallId(value="model_1"),
        operation=operation,  # type: ignore[arg-type]
        response=Content(preview="provider response"),
        provider="fixed-provider",
        metadata={"request": "one"},  # type: ignore[arg-type]
    )


def test_proposal_is_inert_until_submitted_as_model_command(
    engine_dependencies: EngineDependencies,
    event_store: MemoryEventStore,
) -> None:
    engine = RuntimeEngine(engine_dependencies)
    asyncio.run(engine.submit(_bootstrap()))
    proposal = _proposal(AddMessageOperation(message=Content(preview="assistant answer")))
    command = command_from_model_proposal(
        RUN_ID,
        CommandId(value="proposal_command"),
        proposal,
        idempotency_key="proposal_key",
    )
    before = asyncio.run(event_store.read(RUN_ID))

    assert command.origin is CommandOrigin.MODEL
    assert command.actor == "fixed-provider"
    assert command.model_call_id == ModelCallId(value="model_1")
    assert asyncio.run(event_store.read(RUN_ID)) == before

    result = asyncio.run(
        submit_model_proposal(
            engine,
            RUN_ID,
            CommandId(value="proposal_command"),
            proposal,
            idempotency_key="proposal_key",
        )
    )
    history = asyncio.run(event_store.read(RUN_ID))

    assert isinstance(result.decision, AcceptedCommandDecision)
    record = history.events[-2]
    assert isinstance(record.payload, ModelCommandRecordedPayload)
    assert record.payload.provider == "fixed-provider"
    assert record.payload.model_call_id == ModelCallId(value="model_1")
    assert record.payload.metadata["commandOrigin"] == "model"  # type: ignore[index]
    assert history.events[-1].event_type is CoreEventType.MESSAGE_ADDED


def test_newly_supported_wait_proposal_remains_engine_evaluated_not_provider_authority(
    engine_dependencies: EngineDependencies,
    event_store: MemoryEventStore,
) -> None:
    engine = RuntimeEngine(engine_dependencies)
    asyncio.run(engine.submit(_bootstrap()))
    proposal = _proposal(OpenInteractionWaitOperation(prompt="Need input"))

    result = asyncio.run(
        submit_model_proposal(
            engine,
            RUN_ID,
            CommandId(value="illegal_proposal"),
            proposal,
        )
    )
    history = asyncio.run(event_store.read(RUN_ID))

    assert isinstance(result.decision, AcceptedCommandDecision)
    assert history.events[-2].event_type is CoreEventType.COMMAND_RECORDED
    assert isinstance(history.events[-2].payload, ModelCommandRecordedPayload)
    assert history.events[-1].event_type is CoreEventType.WAIT_CREATED
    assert not any(event.event_type is CoreEventType.MODEL_CALL_FAILED for event in history.events)


def test_every_origin_uses_the_same_submit_and_command_record_path(
    engine_dependencies: EngineDependencies,
    event_store: MemoryEventStore,
) -> None:
    engine = RuntimeEngine(engine_dependencies)
    for index, origin in enumerate(CommandOrigin, start=1):
        asyncio.run(
            engine.submit(
                Command(
                    command_id=CommandId(value=f"origin_{index}"),
                    run_id=RUN_ID,
                    origin=origin,
                    operation=AddMessageOperation(message=Content(preview="attempt")),
                    actor="actor",
                )
            )
        )
    history = asyncio.run(event_store.read(RUN_ID))
    records = tuple(
        event.payload
        for event in history.events
        if isinstance(
            event.payload,
            (ModelCommandRecordedPayload, RuntimeCommandRecordedPayload),
        )
    )

    assert len(records) == len(CommandOrigin)
    assert tuple(record.metadata["commandOrigin"] for record in records) == tuple(  # type: ignore[index]
        origin.value for origin in CommandOrigin
    )
    assert all(record.decision_record.branch.decision == "rejected" for record in records)
