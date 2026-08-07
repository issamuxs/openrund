"""Pure bounded Delegation validation and atomic establishment batches."""

from __future__ import annotations

from dataclasses import dataclass
from typing import cast, final

from openrund.contracts.commands import (
    AcceptedCommandDecision,
    CancelDelegationOperation,
    CancelRunOperation,
    Command,
    CommandDecision,
    CommandDecisionTraceEntry,
    CompleteDelegationOperation,
    CreateDelegationOperation,
    FailDelegationOperation,
    LegalityCriterion,
    LegalityCriterionResult,
    RejectedCommandDecision,
)
from openrund.contracts.content import Content, RunResult
from openrund.contracts.events import (
    CapabilityAuthorityGrantedPayload,
    CoreEventType,
    DelegationCancelledPayload,
    DelegationCompletedPayload,
    DelegationContractCreatedPayload,
    DelegationFailedPayload,
    DelegationHandoffCreatedPayload,
    Event,
    EventActor,
    EventPayload,
    PolicyAuthorityGrantedPayload,
    RunCancelledPayload,
    RunCompletedPayload,
    RunCreatedPayload,
    RunFailedPayload,
    RunStartedPayload,
    RuntimeEvent,
)
from openrund.contracts.ids import AuthorityId, DelegationId, EventId, RunId
from openrund.contracts.json import (
    MISSING,
    JsonArray,
    JsonObject,
    JsonValue,
    MissingType,
    freeze_json,
)
from openrund.contracts.runs import AuthorityGrant, DelegatedRunKind
from openrund.contracts.time import Timestamp
from openrund.errors import ValidationError
from openrund.ports.runtime import IdFactory
from openrund.views import CompleteViewReplay
from openrund.views._delegation import DelegatedRunEntry
from openrund.views._model import RunViewBundle

type DelegationTerminalOperation = (
    CompleteDelegationOperation | FailDelegationOperation | CancelDelegationOperation
)


def _trace(
    criterion: LegalityCriterion,
    result: LegalityCriterionResult,
    reason: str,
    *related: str,
) -> CommandDecisionTraceEntry:
    return CommandDecisionTraceEntry(
        criterion=criterion,
        result=result,
        reason=reason,
        related_entity_ids=related,
    )


def _reject(
    trace: list[CommandDecisionTraceEntry],
    criterion: LegalityCriterion,
    reason: str,
    *related: str,
) -> RejectedCommandDecision:
    trace.append(_trace(criterion, LegalityCriterionResult.FAIL, reason, *related))
    return RejectedCommandDecision(reason=reason, trace=tuple(trace))


def _pass(
    trace: list[CommandDecisionTraceEntry],
    criterion: LegalityCriterion,
    reason: str,
    *related: str,
) -> None:
    trace.append(_trace(criterion, LegalityCriterionResult.PASS, reason, *related))


def _object(value: object) -> JsonObject | None:
    return value if isinstance(value, JsonObject) else None


def _strings(value: object) -> tuple[str, ...] | None:
    if not isinstance(value, JsonArray) or any(not isinstance(item, str) for item in value):
        return None
    return tuple(item for item in value if isinstance(item, str))


def _parent_delegation_contract(
    replay: CompleteViewReplay[RunViewBundle],
) -> JsonObject | None:
    run = replay.views.run_status.run
    if run is None:
        return None
    metadata = _object(run.creation.metadata)
    return _object(metadata.get("delegation_contract")) if metadata is not None else None


def _artifact_ids(operation: CreateDelegationOperation) -> tuple[str, ...]:
    values = [item.value for item in operation.input.artifact_ids]
    for part in operation.input.parts:
        values.extend(item.value for item in part.artifact_ids)
        values.extend(item.artifact_id.value for item in part.artifact_refs)
    return tuple(dict.fromkeys(values))


def evaluate_delegation(
    operation: CreateDelegationOperation,
    child_run_id: RunId | None,
    replay: CompleteViewReplay[RunViewBundle],
    *,
    child_exists: bool,
    atomic_available: bool,
    factories_available: bool,
) -> CommandDecision:
    """Prove a child contract is a strict subset of current parent facts."""

    trace: list[CommandDecisionTraceEntry] = []
    parent = replay.views.run_status.run
    if parent is None:
        return _reject(trace, LegalityCriterion.DELEGATION_LINEAGE, "delegation_parent_missing")
    if child_run_id is None:
        return _reject(trace, LegalityCriterion.CONTRACT, "delegated_run_id_factory_unavailable")
    if not atomic_available:
        return _reject(trace, LegalityCriterion.CONTRACT, "atomic_event_store_required")
    if not factories_available:
        return _reject(trace, LegalityCriterion.CONTRACT, "delegation_factories_required")
    if child_run_id in (parent.run_id, parent.root_id):
        return _reject(
            trace,
            LegalityCriterion.DELEGATION_LINEAGE,
            "delegation_lineage_cycle",
            child_run_id.value,
        )
    if child_exists or child_run_id in replay.views.delegation.delegated_runs:
        return _reject(
            trace,
            LegalityCriterion.DELEGATION_LINEAGE,
            "delegated_run_already_exists",
            child_run_id.value,
        )
    parent_contract = _parent_delegation_contract(replay)
    if parent.creation.parent_run_id not in (MISSING, None) and (
        parent_contract is None or parent_contract.get("allow_nested_delegation") is not True
    ):
        return _reject(
            trace,
            LegalityCriterion.DELEGATION_LINEAGE,
            "nested_delegation_forbidden",
        )
    if (
        operation.contract.run_kind is DelegatedRunKind.WORKER
        and operation.contract.allow_nested_delegation
    ):
        return _reject(
            trace,
            LegalityCriterion.DELEGATION_LINEAGE,
            "worker_nested_delegation_forbidden",
        )
    _pass(
        trace,
        LegalityCriterion.DELEGATION_LINEAGE,
        "delegation_lineage_valid",
        parent.run_id.value,
        child_run_id.value,
    )

    seen_capabilities: set[object] = set()
    for requested in operation.contract.authority_grants:
        if requested.capability_id in seen_capabilities:
            return _reject(
                trace,
                LegalityCriterion.AUTHORITY,
                "delegation_authority_duplicate",
                requested.capability_id.value,
            )
        seen_capabilities.add(requested.capability_id)
        current = replay.views.run_status.capability_authority.get(requested.capability_id)
        if current is None:
            return _reject(
                trace,
                LegalityCriterion.AUTHORITY,
                "delegation_authority_expansion",
                requested.capability_id.value,
            )
        constraints = _object(current.payload.constraints)
        parent_actions = _strings(constraints.get("actions")) if constraints is not None else None
        if parent_actions is not None and any(
            action not in parent_actions for action in requested.actions
        ):
            return _reject(
                trace,
                LegalityCriterion.AUTHORITY,
                "delegation_action_expansion",
                requested.capability_id.value,
            )
        for rule_id in requested.policy_rule_ids:
            if rule_id not in replay.views.run_status.policy_authority:
                return _reject(
                    trace,
                    LegalityCriterion.AUTHORITY,
                    "delegation_policy_expansion",
                    rule_id.value,
                )
    _pass(trace, LegalityCriterion.AUTHORITY, "delegation_authority_subset")

    if parent_contract is not None:
        budget = _object(parent_contract.get("budget"))
        if budget is not None:
            parent_requests = budget.get("max_requests")
            parent_timeout = budget.get("wall_clock_timeout_ms")
            if isinstance(parent_requests, int) and (
                operation.contract.budget.max_requests > parent_requests
            ):
                return _reject(
                    trace, LegalityCriterion.BUDGET, "delegation_request_budget_expansion"
                )
            if isinstance(parent_timeout, int) and (
                operation.contract.budget.wall_clock_timeout_ms > parent_timeout
            ):
                return _reject(
                    trace, LegalityCriterion.BUDGET, "delegation_timeout_budget_expansion"
                )
    _pass(trace, LegalityCriterion.BUDGET, "delegation_budget_bounded")

    known_artifacts = frozenset(item.value for item in replay.views.artifact_index)
    missing = tuple(item for item in _artifact_ids(operation) if item not in known_artifacts)
    if missing:
        return _reject(
            trace,
            LegalityCriterion.ARTIFACT_DISCIPLINE,
            "delegation_artifact_not_found",
            *missing,
        )
    _pass(trace, LegalityCriterion.ARTIFACT_DISCIPLINE, "delegation_input_valid")
    return AcceptedCommandDecision(trace=tuple(trace))


def _delegation_entry(
    operation: DelegationTerminalOperation,
    replay: CompleteViewReplay[RunViewBundle],
) -> DelegatedRunEntry | None:
    return replay.views.delegation.delegated_runs.get(operation.delegated_run_id)


def late_handoff_policy(
    operation: DelegationTerminalOperation,
    replay: CompleteViewReplay[RunViewBundle],
) -> str | None:
    entry = _delegation_entry(operation, replay)
    return entry.creation.contract.late_handoff if entry is not None else None


def evaluate_delegation_handoff(
    operation: DelegationTerminalOperation,
    replay: CompleteViewReplay[RunViewBundle],
    child_replay: CompleteViewReplay[RunViewBundle] | None,
) -> CommandDecision:
    """Require an explicit parent Command backed by exact child terminal facts."""

    trace: list[CommandDecisionTraceEntry] = []
    entry = _delegation_entry(operation, replay)
    if entry is None or entry.establishment is None:
        return _reject(
            trace,
            LegalityCriterion.DELEGATION_LINEAGE,
            "delegation_not_established",
            operation.delegated_run_id.value,
        )
    if entry.terminal is not None:
        return _reject(
            trace,
            LegalityCriterion.DELEGATION_LINEAGE,
            "delegation_already_terminal",
            operation.delegated_run_id.value,
        )
    if operation.delegation_id not in (MISSING, None) and (
        operation.delegation_id != entry.creation.delegation_id
    ):
        return _reject(
            trace,
            LegalityCriterion.DELEGATION_LINEAGE,
            "delegation_id_mismatch",
            operation.delegated_run_id.value,
        )
    if child_replay is None:
        return _reject(
            trace,
            LegalityCriterion.DELEGATION_LINEAGE,
            "delegated_child_not_found",
            operation.delegated_run_id.value,
        )
    child_status = child_replay.views.run_status.status
    expected = (
        "completed"
        if isinstance(operation, CompleteDelegationOperation)
        else "failed"
        if isinstance(operation, FailDelegationOperation)
        else "cancelled"
    )
    if child_status != expected:
        return _reject(
            trace,
            LegalityCriterion.DELEGATION_LINEAGE,
            "delegated_child_terminal_mismatch",
            child_status,
            expected,
        )
    if isinstance(operation, CompleteDelegationOperation):
        terminal = child_replay.views.run_status.terminal
        if not isinstance(terminal, RunCompletedPayload) or not isinstance(
            terminal.result, RunResult
        ):
            return _reject(trace, LegalityCriterion.CONTRACT, "delegated_child_result_missing")
        if terminal.result.kind != entry.creation.contract.result_kind:
            return _reject(
                trace,
                LegalityCriterion.CONTRACT,
                "delegation_result_kind_mismatch",
                entry.creation.contract.result_kind,
            )
        if isinstance(operation.result, RunResult) and operation.result != terminal.result:
            return _reject(trace, LegalityCriterion.CONTRACT, "delegation_result_evidence_mismatch")
        referenced = frozenset(terminal.result.artifact_ids)
        observed_kinds = frozenset(
            item.kind
            for artifact_id, item in child_replay.views.artifact_index.items()
            if artifact_id in referenced
        )
        missing_kinds = tuple(
            kind
            for kind in entry.creation.contract.required_artifact_kinds
            if kind not in observed_kinds
        )
        if missing_kinds:
            return _reject(
                trace,
                LegalityCriterion.ARTIFACT_DISCIPLINE,
                "delegation_required_artifact_missing",
                *missing_kinds,
            )
    elif isinstance(operation, FailDelegationOperation):
        terminal = child_replay.views.run_status.terminal
        if not isinstance(terminal, RunFailedPayload):
            return _reject(trace, LegalityCriterion.CONTRACT, "delegated_child_failure_missing")
        if operation.message != terminal.message:
            return _reject(
                trace,
                LegalityCriterion.CONTRACT,
                "delegation_failure_evidence_mismatch",
            )
        if operation.evidence not in (MISSING, None) and operation.evidence != terminal.evidence:
            return _reject(
                trace,
                LegalityCriterion.CONTRACT,
                "delegation_failure_evidence_mismatch",
            )
    else:
        terminal = child_replay.views.run_status.terminal
        if not isinstance(terminal, RunCancelledPayload):
            return _reject(
                trace,
                LegalityCriterion.CONTRACT,
                "delegated_child_cancellation_missing",
            )
        if operation.reason not in (MISSING, None) and operation.reason != terminal.reason:
            return _reject(
                trace,
                LegalityCriterion.CONTRACT,
                "delegation_cancellation_evidence_mismatch",
            )

    parent_terminal = replay.views.run_status.status in ("completed", "failed", "cancelled")
    policy = entry.creation.contract.late_handoff
    if parent_terminal and policy == "ignore":
        return _reject(
            trace,
            LegalityCriterion.DELEGATION_LINEAGE,
            "late_handoff_ignored",
            operation.delegated_run_id.value,
        )
    _pass(
        trace,
        LegalityCriterion.DELEGATION_LINEAGE,
        "delegation_handoff_allowed" if not parent_terminal else f"late_handoff_{policy}",
        operation.delegated_run_id.value,
    )
    return AcceptedCommandDecision(trace=tuple(trace))


def materialize_delegation_handoff(
    operation: DelegationTerminalOperation,
    replay: CompleteViewReplay[RunViewBundle],
    child_replay: CompleteViewReplay[RunViewBundle],
) -> EventPayload:
    entry = _delegation_entry(operation, replay)
    if entry is None:
        raise ValidationError(code="delegation_not_found")
    delegation_id = entry.creation.delegation_id
    if isinstance(operation, CompleteDelegationOperation):
        terminal = child_replay.views.run_status.terminal
        if not isinstance(terminal, RunCompletedPayload):
            raise ValidationError(code="delegated_child_terminal_mismatch")
        return DelegationCompletedPayload(
            delegated_run_id=operation.delegated_run_id,
            delegation_id=delegation_id,
            result=terminal.result,
            note=operation.note,
        )
    if isinstance(operation, FailDelegationOperation):
        terminal = child_replay.views.run_status.terminal
        if not isinstance(terminal, RunFailedPayload):
            raise ValidationError(code="delegated_child_terminal_mismatch")
        return DelegationFailedPayload(
            delegated_run_id=operation.delegated_run_id,
            delegation_id=delegation_id,
            message=terminal.message,
            evidence=terminal.evidence,
        )
    terminal = child_replay.views.run_status.terminal
    if not isinstance(terminal, RunCancelledPayload):
        raise ValidationError(code="delegated_child_terminal_mismatch")
    return DelegationCancelledPayload(
        delegated_run_id=operation.delegated_run_id,
        delegation_id=delegation_id,
        reason=terminal.reason,
    )


def _constraints_for_child(
    grant: AuthorityGrant,
    replay: CompleteViewReplay[RunViewBundle],
) -> JsonObject | MissingType:
    parent = replay.views.run_status.capability_authority[grant.capability_id].payload.constraints
    entries: list[tuple[str, JsonValue]] = []
    if isinstance(parent, JsonObject):
        entries.extend((key, value) for key, value in parent.entries if key != "actions")
    if grant.actions:
        entries.append(("actions", freeze_json(grant.actions)))
    elif isinstance(parent, JsonObject) and "actions" in parent:
        entries.append(("actions", parent["actions"]))
    return JsonObject(entries=tuple(entries)) if entries else MISSING


def _contract_metadata(operation: CreateDelegationOperation, parent_run_id: RunId) -> JsonObject:
    contract = operation.contract
    value = freeze_json(
        {
            "parent_run_id": parent_run_id.value,
            "delegation_contract": {
                "run_kind": contract.run_kind.value,
                "objective": contract.objective,
                "authority_drift": contract.authority_drift,
                "budget": {
                    "max_requests": contract.budget.max_requests,
                    "wall_clock_timeout_ms": contract.budget.wall_clock_timeout_ms,
                    "on_budget_expired": contract.budget.on_budget_expired,
                },
                "result_kind": contract.result_kind,
                "required_artifact_kinds": contract.required_artifact_kinds,
                "allow_nested_delegation": contract.allow_nested_delegation,
                "on_parent_cancel": contract.on_parent_cancel,
                "late_handoff": contract.late_handoff,
            },
            "run_contract": {
                "output": {"kind": contract.result_kind},
                "required_artifact_kinds": contract.required_artifact_kinds,
                "completion": {"kind": "known_action_outcomes"},
            },
        }
    )
    assert isinstance(value, JsonObject)
    return value


@final
@dataclass(frozen=True, slots=True, kw_only=True)
class DelegationBatches:
    result_event_ids: tuple[EventId, ...]
    parent_events: tuple[RuntimeEvent, ...]
    child_events: tuple[RuntimeEvent, ...]


@final
@dataclass(frozen=True, slots=True, kw_only=True)
class ChildCancellationState:
    run_id: RunId
    watermark: int
    delegation_id: DelegationId | MissingType | None


@final
@dataclass(frozen=True, slots=True, kw_only=True)
class CancellationBatches:
    result_event_ids: tuple[EventId, ...]
    parent_events: tuple[RuntimeEvent, ...]
    child_batches: tuple[tuple[RunId, int, tuple[RuntimeEvent, ...]], ...]


def build_parent_cancellation_batches(
    command: Command,
    operation: CancelRunOperation,
    states: tuple[ChildCancellationState, ...],
    *,
    command_event_id: EventId,
    first_parent_position: int,
    timestamp: Timestamp,
    parent_actor: EventActor,
    event_ids: IdFactory[EventId],
) -> CancellationBatches:
    """Build contract-driven parent and child cancellation facts."""

    parent_cancel_id = event_ids.new_id()
    parent_specs: list[tuple[EventId, CoreEventType, EventPayload, EventId]] = [
        (
            parent_cancel_id,
            CoreEventType.RUN_CANCELLED,
            RunCancelledPayload(reason=operation.reason),
            command_event_id,
        )
    ]
    child_specs: list[tuple[RunId, int, EventId, EventId]] = []
    for state in states:
        delegation_cancel_id = event_ids.new_id()
        child_cancel_id = event_ids.new_id()
        parent_specs.append(
            (
                delegation_cancel_id,
                CoreEventType.DELEGATION_CANCELLED,
                DelegationCancelledPayload(
                    delegated_run_id=state.run_id,
                    delegation_id=state.delegation_id,
                    reason=operation.reason,
                ),
                parent_cancel_id,
            )
        )
        child_specs.append((state.run_id, state.watermark, child_cancel_id, delegation_cancel_id))
    parent_events = tuple(
        cast(
            RuntimeEvent,
            Event(
                event_id=event_id,
                run_id=command.run_id,
                position=first_parent_position + index,
                event_type=event_type,
                timestamp=timestamp,
                actor=parent_actor,
                payload=payload,
                causation_id=causation_id,
                command_id=command.command_id,
            ),
        )
        for index, (event_id, event_type, payload, causation_id) in enumerate(parent_specs)
    )
    child_batches = tuple(
        (
            run_id,
            watermark,
            (
                cast(
                    RuntimeEvent,
                    Event(
                        event_id=child_event_id,
                        run_id=run_id,
                        position=watermark + 1,
                        event_type=CoreEventType.RUN_CANCELLED,
                        timestamp=timestamp,
                        actor=EventActor.SYSTEM,
                        payload=RunCancelledPayload(reason=operation.reason),
                        causation_id=parent_delegation_event_id,
                        command_id=command.command_id,
                    ),
                ),
            ),
        )
        for run_id, watermark, child_event_id, parent_delegation_event_id in child_specs
    )
    return CancellationBatches(
        result_event_ids=(
            *(event.event_id for event in parent_events),
            *(event.event_id for _run_id, _watermark, events in child_batches for event in events),
        ),
        parent_events=parent_events,
        child_batches=child_batches,
    )


def build_delegation_batches(
    command: Command,
    operation: CreateDelegationOperation,
    child_run_id: RunId,
    replay: CompleteViewReplay[RunViewBundle],
    *,
    command_event_id: EventId,
    first_parent_position: int,
    timestamp: Timestamp,
    parent_actor: EventActor,
    event_ids: IdFactory[EventId],
    delegation_ids: IdFactory[DelegationId],
    authority_ids: IdFactory[AuthorityId],
) -> DelegationBatches:
    """Preallocate exact parent and child facts for one atomic append."""

    parent = replay.views.run_status.run
    if parent is None:
        raise ValidationError(code="delegation_parent_missing")
    delegation_id = delegation_ids.new_id()
    contract_event_id = event_ids.new_id()
    handoff_event_id = event_ids.new_id()
    child_created_id = event_ids.new_id()
    child_started_id = event_ids.new_id()

    parent_payloads: tuple[tuple[EventId, CoreEventType, EventPayload, EventId], ...] = (
        (
            contract_event_id,
            CoreEventType.DELEGATION_CREATED,
            DelegationContractCreatedPayload(
                delegated_run_id=child_run_id,
                contract=operation.contract,
                input=operation.input,
                delegation_id=delegation_id,
                contract_preview=Content(preview=operation.contract.objective),
            ),
            command_event_id,
        ),
        (
            handoff_event_id,
            CoreEventType.DELEGATION_CREATED,
            DelegationHandoffCreatedPayload(
                delegated_run_id=child_run_id,
                parent_spawn_event_id=contract_event_id,
                delegated_run_first_position=1,
                delegation_id=delegation_id,
            ),
            contract_event_id,
        ),
    )
    child_payloads: list[tuple[EventId, CoreEventType, EventPayload, EventId]] = [
        (
            child_created_id,
            CoreEventType.RUN_CREATED,
            RunCreatedPayload(
                root_id=parent.root_id,
                initial_status="created",
                parent_run_id=parent.run_id,
                objective=operation.contract.objective,
                metadata=_contract_metadata(operation, parent.run_id),
            ),
            contract_event_id,
        ),
        (
            child_started_id,
            CoreEventType.RUN_STARTED,
            RunStartedPayload(reason="delegation_established"),
            child_created_id,
        ),
    ]
    for grant in operation.contract.authority_grants:
        child_payloads.append(
            (
                event_ids.new_id(),
                CoreEventType.AUTHORITY_GRANTED,
                CapabilityAuthorityGrantedPayload(
                    capability_id=grant.capability_id,
                    authority_id=authority_ids.new_id(),
                    constraints=_constraints_for_child(grant, replay),
                    granted_by=f"delegation:{parent.run_id.value}",
                    metadata=grant.metadata,
                ),
                child_started_id,
            )
        )
        for rule_id in grant.policy_rule_ids:
            policy = replay.views.run_status.policy_authority[rule_id]
            child_payloads.append(
                (
                    event_ids.new_id(),
                    CoreEventType.AUTHORITY_GRANTED,
                    PolicyAuthorityGrantedPayload(
                        rule_id=rule_id,
                        rule=policy.payload.rule,
                        authority_id=authority_ids.new_id(),
                        constraints=policy.payload.constraints,
                        granted_by=f"delegation:{parent.run_id.value}",
                    ),
                    child_started_id,
                )
            )

    parent_events = tuple(
        cast(
            RuntimeEvent,
            Event(
                event_id=event_id,
                run_id=command.run_id,
                position=first_parent_position + index,
                event_type=event_type,
                timestamp=timestamp,
                actor=parent_actor,
                payload=payload,
                causation_id=causation_id,
                command_id=command.command_id,
            ),
        )
        for index, (event_id, event_type, payload, causation_id) in enumerate(parent_payloads)
    )
    child_events = tuple(
        cast(
            RuntimeEvent,
            Event(
                event_id=event_id,
                run_id=child_run_id,
                position=index,
                event_type=event_type,
                timestamp=timestamp,
                actor=EventActor.SYSTEM,
                payload=payload,
                causation_id=causation_id,
                command_id=command.command_id,
            ),
        )
        for index, (event_id, event_type, payload, causation_id) in enumerate(
            child_payloads, start=1
        )
    )
    result_ids = tuple(
        (
            *(event.event_id for event in parent_events),
            *(event.event_id for event in child_events),
        )
    )
    return DelegationBatches(
        result_event_ids=result_ids,
        parent_events=parent_events,
        child_events=child_events,
    )
