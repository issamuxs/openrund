"""Single authoritative replay, evaluate, and atomic append pipeline."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Self, cast, final

from openrund.contracts.commands import (
    AcceptedCommandDecision,
    CancelDelegationOperation,
    CancelRunOperation,
    Command,
    CommandDecision,
    CommandResult,
    CompleteDelegationOperation,
    CreateActionOperation,
    CreateDelegationOperation,
    DeferredCommandDecision,
    FailDelegationOperation,
    RejectedCommandDecision,
    SupersededCommandDecision,
)
from openrund.contracts.events import (
    CoreEventType,
    Event,
    EventActor,
    ModelCommandRecordedPayload,
    RuntimeCommandRecordedPayload,
    RuntimeEvent,
)
from openrund.contracts.ids import CommandId, EventId, RunId, WaitId
from openrund.contracts.json import JsonObject
from openrund.contracts.runs import WaitKind
from openrund.engine._delegation import (
    CancellationBatches,
    ChildCancellationState,
    DelegationBatches,
    build_delegation_batches,
    build_parent_cancellation_batches,
)
from openrund.engine._events import (
    EventIntent,
    materialize_deferred_approval,
    materialize_event_intents,
)
from openrund.engine._legality import CommandAttemptFacts, evaluate_command
from openrund.engine._model import EngineDependencies
from openrund.engine._records import build_command_recorded_payload
from openrund.errors import ExpectedPositionConflict, ResourceClosedError, StorageIntegrityError
from openrund.ports.events import AppendEventsInput, AppendManyEventsInput, EventSlice
from openrund.views import CompleteViewReplay, rebuild_views
from openrund.views._model import RunViewBundle


def _actor(command: Command) -> EventActor:
    by_origin = {
        "model": EventActor.ASSISTANT,
        "user": EventActor.USER,
        "client": EventActor.CLIENT,
        "operator": EventActor.OPERATOR,
        "capability": EventActor.CAPABILITY,
    }
    return by_origin.get(command.origin.value, EventActor.SYSTEM)


def _runtime_decision(
    payload: ModelCommandRecordedPayload | RuntimeCommandRecordedPayload,
) -> CommandDecision:
    branch = payload.decision_record.branch
    if branch.decision == "accepted":
        return AcceptedCommandDecision(
            trace=branch.decision_trace,
            result_event_ids=branch.result_event_ids,
        )
    if branch.decision == "rejected":
        return RejectedCommandDecision(
            reason=branch.rejection.code,
            trace=branch.decision_trace,
        )
    if branch.decision == "deferred":
        reason = next(
            (
                item.reason
                for item in reversed(branch.decision_trace)
                if isinstance(item.reason, str)
            ),
            "deferred",
        )
        return DeferredCommandDecision(
            reason=reason,
            trace=branch.decision_trace,
            wait_ids=(branch.wait.wait_id,),
        )
    return SupersededCommandDecision(
        reason="superseded",
        trace=branch.decision_trace,
        superseded_by_command_id=branch.replacement_command_id,
    )


def _recorded_payload(
    event: RuntimeEvent,
) -> ModelCommandRecordedPayload | RuntimeCommandRecordedPayload | None:
    if isinstance(event.payload, (ModelCommandRecordedPayload, RuntimeCommandRecordedPayload)):
        return event.payload
    return None


def _find_command(events: tuple[RuntimeEvent, ...], command_id: CommandId) -> CommandResult | None:
    matches = tuple(
        payload
        for event in events
        if (payload := _recorded_payload(event)) is not None and payload.command_id == command_id
    )
    if not matches:
        return None
    if len(matches) != 1:
        raise StorageIntegrityError(code="command_history_duplicate")
    return CommandResult(command_id=command_id, decision=_runtime_decision(matches[0]))


def _idempotency_owner(events: tuple[RuntimeEvent, ...], command: Command) -> CommandId | None:
    if not isinstance(command.idempotency_key, str):
        return None
    owners: list[CommandId] = []
    for event in events:
        payload = _recorded_payload(event)
        if payload is None or not isinstance(payload.metadata, JsonObject):
            continue
        if payload.decision_record.branch.decision == "superseded":
            continue
        if payload.metadata.get("idempotencyKey") == command.idempotency_key:
            owners.append(payload.command_id)
    unique = tuple(dict.fromkeys(owners))
    if len(unique) > 1:
        raise StorageIntegrityError(code="command_idempotency_conflict")
    return unique[0] if unique else None


@final
@dataclass(frozen=True, slots=True)
class _LoadedHistory:
    events: tuple[RuntimeEvent, ...]
    watermark: int
    replay: CompleteViewReplay[RunViewBundle]


def _history(event_slice: EventSlice) -> _LoadedHistory:
    events = event_slice.events
    watermark = events[-1].position if events else 0
    if event_slice.next_position != watermark + 1:
        raise StorageIntegrityError(code="event_history_incomplete")
    replay = rebuild_views(events, watermark=watermark)
    if not isinstance(replay, CompleteViewReplay):
        raise StorageIntegrityError(code="event_history_incomplete")
    return _LoadedHistory(events=events, watermark=watermark, replay=replay)


def _target_events(
    command: Command,
    intents: tuple[EventIntent, ...],
    event_ids: tuple[EventId, ...],
    *,
    first_position: int,
    timestamp: object,
    command_event_id: EventId,
) -> tuple[RuntimeEvent, ...]:
    from openrund.contracts.time import Timestamp

    assert isinstance(timestamp, Timestamp)
    actor = _actor(command)
    return tuple(
        cast(
            RuntimeEvent,
            Event(
                event_id=event_id,
                run_id=command.run_id,
                position=first_position + index,
                event_type=intent.event_type,
                timestamp=timestamp,
                actor=actor,
                payload=intent.payload,
                causation_id=command_event_id,
                command_id=command.command_id,
            ),
        )
        for index, (intent, event_id) in enumerate(zip(intents, event_ids, strict=True))
    )


@final
class RuntimeEngine:
    """The sole supported core lifecycle mutation authority."""

    __slots__ = ("_closed", "_dependencies")

    def __init__(self, dependencies: EngineDependencies) -> None:
        if not isinstance(dependencies, EngineDependencies):
            raise TypeError("engine_dependencies_invalid")
        self._dependencies = dependencies
        self._closed = False

    async def __aenter__(self) -> Self:
        if self._closed:
            raise ResourceClosedError(resource="engine")
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: object | None,
    ) -> None:
        await self.aclose()

    async def aclose(self) -> None:
        self._closed = True

    async def submit(self, command: Command, /) -> CommandResult:
        if self._closed:
            raise ResourceClosedError(resource="engine")
        if not isinstance(command, Command):
            raise TypeError("engine_command_invalid")
        last_conflict: ExpectedPositionConflict | None = None
        for _attempt in range(self._dependencies.conflict_retries + 1):
            event_slice = await self._dependencies.event_store.read(
                command.run_id,
                from_position=1,
                limit=None,
            )
            history = _history(event_slice)
            events = history.events
            watermark = history.watermark
            existing = _find_command(events, command.command_id)
            if existing is not None:
                return existing
            replay = history.replay
            timestamp = self._dependencies.clock.now()
            owner = _idempotency_owner(events, command)
            approval_wait_id: WaitId | None = None
            delegated_run_id: RunId | None = None
            delegated_run_exists = False
            delegated_child_replay: CompleteViewReplay[RunViewBundle] | None = None
            cancellation_states: list[ChildCancellationState] = []
            cancellation_child_missing = False
            if owner is not None:
                decision: CommandDecision = SupersededCommandDecision(
                    reason="idempotency_key_committed",
                    trace=(),
                    superseded_by_command_id=owner,
                )
            else:
                if (
                    isinstance(command.operation, CreateActionOperation)
                    and self._dependencies.wait_ids is not None
                ):
                    approval_wait_id = self._dependencies.wait_ids.new_id()
                if isinstance(command.operation, CreateDelegationOperation):
                    requested = command.operation.delegated_run_id
                    if isinstance(requested, RunId):
                        delegated_run_id = requested
                    elif self._dependencies.run_ids is not None:
                        delegated_run_id = self._dependencies.run_ids.new_id()
                    if (
                        delegated_run_id is not None
                        and self._dependencies.atomic_event_store is not None
                    ):
                        child_slice = await self._dependencies.atomic_event_store.read(
                            delegated_run_id,
                            from_position=1,
                            limit=None,
                        )
                        delegated_run_exists = bool(child_slice.events)
                if isinstance(
                    command.operation,
                    (
                        CompleteDelegationOperation,
                        FailDelegationOperation,
                        CancelDelegationOperation,
                    ),
                ):
                    child_slice = await self._dependencies.event_store.read(
                        command.operation.delegated_run_id,
                        from_position=1,
                        limit=None,
                    )
                    if child_slice.events:
                        delegated_child_replay = _history(child_slice).replay
                if isinstance(command.operation, CancelRunOperation):
                    for entry in replay.views.delegation.delegated_runs.values():
                        if (
                            entry.establishment is None
                            or entry.terminal is not None
                            or entry.creation.contract.on_parent_cancel != "cancel"
                        ):
                            continue
                        child_slice = await self._dependencies.event_store.read(
                            entry.delegated_run_id,
                            from_position=1,
                            limit=None,
                        )
                        if not child_slice.events:
                            cancellation_child_missing = True
                            continue
                        child_history = _history(child_slice)
                        child_replay = child_history.replay
                        if child_replay.views.run_status.status not in (
                            "completed",
                            "failed",
                            "cancelled",
                        ):
                            cancellation_states.append(
                                ChildCancellationState(
                                    run_id=entry.delegated_run_id,
                                    watermark=child_history.watermark,
                                    delegation_id=entry.creation.delegation_id,
                                )
                            )
                decision = evaluate_command(
                    command,
                    replay,
                    events,
                    facts=CommandAttemptFacts(
                        now=timestamp,
                        governance=self._dependencies.governance,
                        approval_wait_id=approval_wait_id,
                        delegated_run_id=delegated_run_id,
                        delegated_run_exists=delegated_run_exists,
                        delegation_atomic_available=(
                            self._dependencies.atomic_event_store is not None
                        ),
                        delegation_factories_available=(
                            self._dependencies.delegation_ids is not None
                            and self._dependencies.authority_ids is not None
                        ),
                        delegated_child_replay=delegated_child_replay,
                        parent_cancel_requires_atomic=bool(cancellation_states),
                        parent_cancel_atomic_available=(
                            self._dependencies.atomic_event_store is not None
                        ),
                        parent_cancel_child_missing=cancellation_child_missing,
                    ),
                )

            command_event_id = self._dependencies.event_ids.new_id()
            target_events: tuple[RuntimeEvent, ...] = ()
            delegation_batches: DelegationBatches | None = None
            cancellation_batches: CancellationBatches | None = None
            if isinstance(decision, AcceptedCommandDecision) and isinstance(
                command.operation, CreateDelegationOperation
            ):
                if (
                    delegated_run_id is None
                    or self._dependencies.delegation_ids is None
                    or self._dependencies.authority_ids is None
                ):
                    raise StorageIntegrityError(code="delegation_factories_required")
                delegation_batches = build_delegation_batches(
                    command,
                    command.operation,
                    delegated_run_id,
                    replay,
                    command_event_id=command_event_id,
                    first_parent_position=watermark + 2,
                    timestamp=timestamp,
                    parent_actor=_actor(command),
                    event_ids=self._dependencies.event_ids,
                    delegation_ids=self._dependencies.delegation_ids,
                    authority_ids=self._dependencies.authority_ids,
                )
                decision = AcceptedCommandDecision(
                    trace=decision.trace,
                    result_event_ids=delegation_batches.result_event_ids,
                )
            elif (
                isinstance(decision, AcceptedCommandDecision)
                and isinstance(command.operation, CancelRunOperation)
                and cancellation_states
            ):
                cancellation_batches = build_parent_cancellation_batches(
                    command,
                    command.operation,
                    tuple(cancellation_states),
                    command_event_id=command_event_id,
                    first_parent_position=watermark + 2,
                    timestamp=timestamp,
                    parent_actor=_actor(command),
                    event_ids=self._dependencies.event_ids,
                )
                decision = AcceptedCommandDecision(
                    trace=decision.trace,
                    result_event_ids=cancellation_batches.result_event_ids,
                )
            elif isinstance(decision, AcceptedCommandDecision):
                intents = materialize_event_intents(
                    command,
                    message_ids=self._dependencies.message_ids,
                    wait_ids=self._dependencies.wait_ids,
                    authority_ids=self._dependencies.authority_ids,
                    check_ids=self._dependencies.check_ids,
                    checkpoint_ids=self._dependencies.checkpoint_ids,
                    annotation_ids=self._dependencies.annotation_ids,
                    replay=replay,
                    now=timestamp,
                    governance=self._dependencies.governance,
                    delegated_child_replay=delegated_child_replay,
                )
                target_ids = tuple(self._dependencies.event_ids.new_id() for _ in intents)
                decision = AcceptedCommandDecision(
                    trace=decision.trace,
                    result_event_ids=target_ids,
                )
                target_events = _target_events(
                    command,
                    intents,
                    target_ids,
                    first_position=watermark + 2,
                    timestamp=timestamp,
                    command_event_id=command_event_id,
                )
            elif isinstance(decision, DeferredCommandDecision):
                operation = command.operation
                if not isinstance(operation, CreateActionOperation):
                    raise StorageIntegrityError(code="deferred_operation_unsupported")
                intent = materialize_deferred_approval(operation, decision.wait_ids[0], replay)
                target_id = self._dependencies.event_ids.new_id()
                target_events = _target_events(
                    command,
                    (intent,),
                    (target_id,),
                    first_position=watermark + 2,
                    timestamp=timestamp,
                    command_event_id=command_event_id,
                )
            payload = build_command_recorded_payload(
                command,
                decision,
                deferred_wait_kind=(
                    WaitKind.APPROVAL if isinstance(decision, DeferredCommandDecision) else None
                ),
            )
            command_event = cast(
                RuntimeEvent,
                Event(
                    event_id=command_event_id,
                    run_id=command.run_id,
                    position=watermark + 1,
                    event_type=CoreEventType.COMMAND_RECORDED,
                    timestamp=timestamp,
                    actor=_actor(command),
                    payload=payload,
                ),
            )
            try:
                if delegation_batches is not None:
                    atomic_store = self._dependencies.atomic_event_store
                    if atomic_store is None or delegated_run_id is None:
                        raise StorageIntegrityError(code="atomic_event_store_required")
                    await atomic_store.append_many(
                        AppendManyEventsInput(
                            batches=(
                                AppendEventsInput(
                                    run_id=command.run_id,
                                    expected_position=watermark,
                                    events=(command_event, *delegation_batches.parent_events),
                                ),
                                AppendEventsInput(
                                    run_id=delegated_run_id,
                                    expected_position=0,
                                    events=delegation_batches.child_events,
                                ),
                            )
                        )
                    )
                elif cancellation_batches is not None:
                    atomic_store = self._dependencies.atomic_event_store
                    if atomic_store is None:
                        raise StorageIntegrityError(code="atomic_event_store_required")
                    await atomic_store.append_many(
                        AppendManyEventsInput(
                            batches=(
                                AppendEventsInput(
                                    run_id=command.run_id,
                                    expected_position=watermark,
                                    events=(
                                        command_event,
                                        *cancellation_batches.parent_events,
                                    ),
                                ),
                                *(
                                    AppendEventsInput(
                                        run_id=run_id,
                                        expected_position=child_watermark,
                                        events=child_events,
                                    )
                                    for (
                                        run_id,
                                        child_watermark,
                                        child_events,
                                    ) in cancellation_batches.child_batches
                                ),
                            )
                        )
                    )
                else:
                    await self._dependencies.event_store.append(
                        AppendEventsInput(
                            run_id=command.run_id,
                            expected_position=watermark,
                            events=(command_event, *target_events),
                        )
                    )
                return CommandResult(command_id=command.command_id, decision=decision)
            except ExpectedPositionConflict as conflict:
                last_conflict = conflict
        assert last_conflict is not None
        raise last_conflict
