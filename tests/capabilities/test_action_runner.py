from __future__ import annotations

import asyncio
from collections.abc import Iterator

import pytest

from openrund._testing.memory import MemoryArtifactStore, MemoryEventStore
from openrund.capabilities import (
    ActionRunner,
    ActionRunnerDependencies,
    ActionTransportBinding,
    CapabilityRegistry,
    InProcessTransport,
    RegisteredCapability,
)
from openrund.contracts.capabilities import (
    Capability,
    CapabilityAccessMode,
    CapabilityAction,
    CapabilityArtifact,
    CapabilityCancellation,
    CapabilityInlineArtifact,
    CapabilityReliability,
    CapabilityResult,
    CapabilityTransportKind,
    CapabilityTransportMetadata,
)
from openrund.contracts.commands import (
    AcceptedCommandDecision,
    CancelActionOperation,
    Command,
    CommandOrigin,
    CompleteActionOperation,
    RejectedCommandDecision,
    StartActionOperation,
)
from openrund.contracts.content import Content, EffectEntry
from openrund.contracts.events import (
    ActionCreatedPayload,
    CoreEventType,
    RunCreatedPayload,
    RunStartedPayload,
    RuntimeEvent,
)
from openrund.contracts.ids import (
    ActionId,
    ArtifactId,
    CapabilityId,
    CommandId,
    EventId,
    MessageId,
    RunId,
    RuntimeId,
    WaitId,
)
from openrund.contracts.json import JsonObject, freeze_json
from openrund.contracts.time import Timestamp
from openrund.engine import EngineDependencies, RuntimeEngine
from openrund.errors import (
    CapabilityExecutionError,
    CapabilityProtocolError,
    CapabilityTransportError,
)
from openrund.ports.capabilities import CapabilityInvocation
from openrund.ports.events import AppendEventsInput
from openrund.views import CompleteViewReplay, rebuild_views
from tests.engine.conftest import runtime_event

RUN_ID = RunId(value="run-1")
ACTION_ID = ActionId(value="action-1")
CAPABILITY_ID = CapabilityId(value="cap.test")


class FixedClock:
    def now(self) -> Timestamp:
        return Timestamp(value="2026-08-05T12:00:00.000Z")


class SequenceFactory[TId: RuntimeId]:
    def __init__(self, values: Iterator[TId]) -> None:
        self._values = values

    def new_id(self) -> TId:
        return next(self._values)


def _ids(factory: type[RuntimeId], prefix: str) -> Iterator[RuntimeId]:
    index = 1
    while True:
        yield factory(value=f"{prefix}-{index}")
        index += 1


def _schema(value: object) -> JsonObject:
    frozen = freeze_json(value)
    assert isinstance(frozen, JsonObject)
    return frozen


def _invocation(value: str = "go") -> CapabilityInvocation:
    return CapabilityInvocation(
        action_id=ACTION_ID,
        capability_id=CAPABILITY_ID,
        action_name="execute",
        input=Content(data={"value": value}),  # type: ignore[arg-type]
    )


def _definition(*, interruptible: bool = False) -> Capability:
    return Capability(
        capability_id=CAPABILITY_ID,
        version="1",
        actions=(
            CapabilityAction(
                name="execute",
                description="Execute one governed test action",
                posture=CapabilityAccessMode.READ_WRITE,
                reliability=(
                    CapabilityReliability.INTERRUPTIBLE
                    if interruptible
                    else CapabilityReliability.IDEMPOTENT_MUTATION
                ),
                input_schema=_schema(
                    {
                        "type": "object",
                        "required": ["value"],
                        "properties": {"value": {"type": "string"}},
                        "additionalProperties": False,
                    }
                ),
                output_schema=_schema(
                    {
                        "type": "object",
                        "required": ["ok"],
                        "properties": {"ok": {"type": "boolean"}},
                        "additionalProperties": False,
                    }
                ),
                cancellation=CapabilityCancellation(supported=interruptible),
                artifacts=(CapabilityArtifact(kind="receipt", required=True),),
                transport=CapabilityTransportMetadata(kind=CapabilityTransportKind.IN_PROCESS),
            ),
        ),
    )


def _registry(handler: object, *, interruptible: bool = False) -> CapabilityRegistry:
    return CapabilityRegistry(
        (
            RegisteredCapability(
                definition=_definition(interruptible=interruptible),
                bindings=(
                    ActionTransportBinding(
                        action_name="execute",
                        transport=InProcessTransport(handler),  # type: ignore[arg-type]
                    ),
                ),
            ),
        )
    )


def _seed(store: MemoryEventStore, invocation: CapabilityInvocation) -> None:
    asyncio.run(
        store.append(
            AppendEventsInput(
                run_id=RUN_ID,
                expected_position=0,
                events=(
                    runtime_event(
                        CoreEventType.RUN_CREATED,
                        RunCreatedPayload(root_id=RUN_ID, initial_status="created"),
                        1,
                        run_id=RUN_ID,
                    ),
                    runtime_event(
                        CoreEventType.RUN_STARTED,
                        RunStartedPayload(),
                        2,
                        run_id=RUN_ID,
                    ),
                    runtime_event(
                        CoreEventType.ACTION_CREATED,
                        ActionCreatedPayload(
                            action_id=invocation.action_id,
                            capability_id=invocation.capability_id,
                            action_name=invocation.action_name,
                            input=invocation.input,
                        ),
                        3,
                        run_id=RUN_ID,
                    ),
                ),
            )
        )
    )


def _engine(store: MemoryEventStore) -> RuntimeEngine:
    return RuntimeEngine(
        EngineDependencies(
            event_store=store,
            clock=FixedClock(),
            event_ids=SequenceFactory(_ids(EventId, "event")),  # type: ignore[arg-type]
            message_ids=SequenceFactory(_ids(MessageId, "message")),  # type: ignore[arg-type]
            wait_ids=SequenceFactory(_ids(WaitId, "wait")),  # type: ignore[arg-type]
        )
    )


def _runner(
    store: MemoryEventStore,
    artifacts: MemoryArtifactStore,
    registry: CapabilityRegistry,
) -> ActionRunner:
    return ActionRunner(
        ActionRunnerDependencies(
            engine=_engine(store),
            registry=registry,
            artifact_store=artifacts,
            clock=FixedClock(),
            command_ids=SequenceFactory(_ids(CommandId, "command")),  # type: ignore[arg-type]
            artifact_ids=SequenceFactory(_ids(ArtifactId, "artifact")),  # type: ignore[arg-type]
        )
    )


async def _events(store: MemoryEventStore) -> tuple[RuntimeEvent, ...]:
    return (await store.read(RUN_ID, from_position=1, limit=None)).events


def test_runner_commits_start_before_dispatch_then_artifacts_before_terminal() -> None:
    store = MemoryEventStore()
    artifacts = MemoryArtifactStore()
    invocation = _invocation()
    _seed(store, invocation)

    async def handler(_invocation: CapabilityInvocation) -> CapabilityResult:
        current = await _events(store)
        replay = rebuild_views(current, watermark=len(current))
        assert isinstance(replay, CompleteViewReplay)
        assert replay.views.action_receipts[ACTION_ID].status == "started"
        assert not artifacts.calls
        return CapabilityResult(
            output={"ok": True},  # type: ignore[arg-type]
            effects=(EffectEntry(kind="test.executed", summary="done"),),
            inline_artifacts=(
                CapabilityInlineArtifact(
                    kind="receipt",
                    content=b"durable evidence",
                    content_type="text/plain",
                    preview="evidence",
                ),
            ),
        )

    terminal = asyncio.run(
        _runner(store, artifacts, _registry(handler)).execute(RUN_ID, invocation)
    )

    assert isinstance(terminal.decision, AcceptedCommandDecision)
    events = asyncio.run(_events(store))
    assert [event.event_type for event in events[3:]] == [
        CoreEventType.COMMAND_RECORDED,
        CoreEventType.ACTION_STARTED,
        CoreEventType.COMMAND_RECORDED,
        CoreEventType.ARTIFACT_CREATED,
        CoreEventType.ACTION_COMPLETED,
    ]
    blob = asyncio.run(artifacts.get_blob(ArtifactId(value="artifact-1")))
    assert blob is not None and blob.content == b"durable evidence"
    replay = rebuild_views(events, watermark=len(events))
    assert isinstance(replay, CompleteViewReplay)
    receipt = replay.views.action_receipts[ACTION_ID]
    assert receipt.status == "completed"
    assert receipt.artifact_ids == (ArtifactId(value="artifact-1"),)


def test_runner_rejects_changed_input_before_dispatch() -> None:
    store = MemoryEventStore()
    artifacts = MemoryArtifactStore()
    original = _invocation("original")
    _seed(store, original)
    called = False

    async def handler(_invocation: CapabilityInvocation) -> CapabilityResult:
        nonlocal called
        called = True
        return CapabilityResult(output={"ok": True})  # type: ignore[arg-type]

    with pytest.raises(CapabilityProtocolError, match="action_start_rejected"):
        asyncio.run(
            _runner(store, artifacts, _registry(handler)).execute(RUN_ID, _invocation("changed"))
        )
    assert not called
    assert not artifacts.calls


def test_runner_records_confirmed_failure_and_ambiguous_transport_loss() -> None:
    async def rejected(_invocation: CapabilityInvocation) -> CapabilityResult:
        raise CapabilityExecutionError(code="denied_by_worker")

    rejected_store = MemoryEventStore()
    rejected_invocation = _invocation()
    _seed(rejected_store, rejected_invocation)
    failed = asyncio.run(
        _runner(rejected_store, MemoryArtifactStore(), _registry(rejected)).execute(
            RUN_ID, rejected_invocation
        )
    )
    assert isinstance(failed.decision, AcceptedCommandDecision)
    failed_replay = rebuild_views(
        asyncio.run(_events(rejected_store)),
        watermark=7,
    )
    assert isinstance(failed_replay, CompleteViewReplay)
    assert failed_replay.views.action_receipts[ACTION_ID].status == "failed"

    async def lost(_invocation: CapabilityInvocation) -> CapabilityResult:
        raise CapabilityTransportError(code="capability_worker_timeout")

    lost_store = MemoryEventStore()
    lost_invocation = _invocation()
    _seed(lost_store, lost_invocation)
    unknown = asyncio.run(
        _runner(lost_store, MemoryArtifactStore(), _registry(lost)).execute(RUN_ID, lost_invocation)
    )
    assert isinstance(unknown.decision, AcceptedCommandDecision)
    lost_events = asyncio.run(_events(lost_store))
    lost_replay = rebuild_views(lost_events, watermark=len(lost_events))
    assert isinstance(lost_replay, CompleteViewReplay)
    receipt = lost_replay.views.action_receipts[ACTION_ID]
    assert receipt.status == "outcome_unknown"
    assert receipt.unknown is not None
    assert receipt.unknown.reliability.value == "timeout_after_dispatch"


def test_interruptible_cancellation_records_one_cancelled_outcome() -> None:
    store = MemoryEventStore()
    invocation = _invocation()
    _seed(store, invocation)

    async def cancelled(_invocation: CapabilityInvocation) -> CapabilityResult:
        raise asyncio.CancelledError

    with pytest.raises(asyncio.CancelledError):
        asyncio.run(
            _runner(
                store,
                MemoryArtifactStore(),
                _registry(cancelled, interruptible=True),
            ).execute(RUN_ID, invocation)
        )
    events = asyncio.run(_events(store))
    replay = rebuild_views(events, watermark=len(events))
    assert isinstance(replay, CompleteViewReplay)
    assert replay.views.action_receipts[ACTION_ID].status == "cancelled"


def test_engine_rejects_untrusted_duplicate_and_unstarted_terminal_commands() -> None:
    store = MemoryEventStore()
    invocation = _invocation()
    _seed(store, invocation)
    engine = _engine(store)
    start = StartActionOperation(
        action_id=ACTION_ID,
        capability_id=CAPABILITY_ID,
        action_name="execute",
        input_hash="0" * 64,
    )
    untrusted = asyncio.run(
        engine.submit(
            Command(
                command_id=CommandId(value="untrusted"),
                run_id=RUN_ID,
                origin=CommandOrigin.MODEL,
                operation=start,
            )
        )
    )
    assert isinstance(untrusted.decision, RejectedCommandDecision)
    assert untrusted.decision.reason == "action_lifecycle_origin_forbidden"

    premature = asyncio.run(
        engine.submit(
            Command(
                command_id=CommandId(value="premature"),
                run_id=RUN_ID,
                origin=CommandOrigin.CAPABILITY,
                operation=CompleteActionOperation(action_id=ACTION_ID),
            )
        )
    )
    assert isinstance(premature.decision, RejectedCommandDecision)
    assert premature.decision.reason == "action_not_started"

    cancellation = asyncio.run(
        engine.submit(
            Command(
                command_id=CommandId(value="cancel"),
                run_id=RUN_ID,
                origin=CommandOrigin.CAPABILITY,
                operation=CancelActionOperation(action_id=ACTION_ID),
            )
        )
    )
    assert isinstance(cancellation.decision, RejectedCommandDecision)
    assert cancellation.decision.reason == "action_not_started"
