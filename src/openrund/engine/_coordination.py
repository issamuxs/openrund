"""Pure Wait lifecycle checks and exact payload materialization."""

from __future__ import annotations

from typing import TYPE_CHECKING

from openrund.contracts.commands import (
    CancelWaitOperation,
    ExpireWaitOperation,
    FireTimerWaitOperation,
    MarkActionUnknownOperation,
    OpenApprovalWaitOperation,
    OpenInteractionWaitOperation,
    OpenJoinWaitOperation,
    OpenTimerWaitOperation,
    ReconcileActionOperation,
    ResolveApprovalOperation,
    ResolveInteractionWaitOperation,
    ResolveJoinWaitOperation,
)
from openrund.contracts.content import Content
from openrund.contracts.events import (
    ApprovalWaitCancelledPayload,
    ApprovalWaitCreatedPayload,
    ApprovalWaitExpiredPayload,
    ApprovalWaitResolvedPayload,
    EventPayload,
    InteractionWaitCancelledPayload,
    InteractionWaitCreatedPayload,
    InteractionWaitExpiredPayload,
    InteractionWaitResolvedPayload,
    JoinWaitCancelledPayload,
    JoinWaitCreatedPayload,
    JoinWaitExpiredPayload,
    JoinWaitResolvedPayload,
    ReconciliationWaitCancelledPayload,
    ReconciliationWaitCreatedPayload,
    ReconciliationWaitExpiredPayload,
    TimerWaitCancelledPayload,
    TimerWaitCreatedPayload,
    TimerWaitExpiredPayload,
    TimerWaitResolvedPayload,
)
from openrund.contracts.ids import ActionId, CapabilityId, WaitId
from openrund.contracts.json import MISSING, JsonObject, MissingType
from openrund.contracts.runs import WaitKind
from openrund.contracts.time import Timestamp
from openrund.errors import ValidationError
from openrund.ports.runtime import IdFactory
from openrund.views import CompleteViewReplay
from openrund.views._model import RunViewBundle
from openrund.views._waits import PendingWait

if TYPE_CHECKING:
    from openrund.engine._governance import GovernanceContext

type OpenWaitOperation = (
    OpenApprovalWaitOperation
    | OpenInteractionWaitOperation
    | OpenTimerWaitOperation
    | OpenJoinWaitOperation
)
type TerminalWaitOperation = (
    ResolveApprovalOperation
    | ResolveInteractionWaitOperation
    | FireTimerWaitOperation
    | ResolveJoinWaitOperation
    | CancelWaitOperation
    | ExpireWaitOperation
)
type ConcreteWaitOperation = OpenWaitOperation | TerminalWaitOperation


def _substantive(content: Content) -> bool:
    return (
        isinstance(content.preview, str)
        or isinstance(content.data, JsonObject)
        or bool(content.artifact_refs)
        or bool(content.artifact_ids)
        or isinstance(content.metadata, JsonObject)
    )


def reconciliation_wait(
    replay: CompleteViewReplay[RunViewBundle],
    action_id: ActionId,
) -> PendingWait | None:
    return next(
        (
            wait
            for wait in replay.views.waits.all_pending
            if isinstance(wait.request, ReconciliationWaitCreatedPayload)
            and wait.request.action_id == action_id
        ),
        None,
    )


def check_recovery_operation(
    operation: object,
    replay: CompleteViewReplay[RunViewBundle],
) -> tuple[bool, str, tuple[str, ...]] | None:
    """Check exact unknown/reconciliation state without mutating replay."""

    if isinstance(operation, MarkActionUnknownOperation):
        action = replay.views.action_status.get(operation.action_id)
        if action is None:
            return False, "action_not_found", (operation.action_id.value,)
        if action.status != "started":
            return False, "action_already_terminal", (operation.action_id.value,)
        return True, "action_unknown_allowed", (operation.action_id.value,)
    if not isinstance(operation, ReconcileActionOperation):
        return None
    action = replay.views.action_status.get(operation.action_id)
    if action is None:
        return False, "action_not_found", (operation.action_id.value,)
    if action.status != "outcome_unknown":
        reason = (
            "action_already_reconciled" if action.status == "reconciled" else "action_not_unknown"
        )
        return False, reason, (operation.action_id.value,)
    if action.unknown_event_id != operation.unknown_event_id:
        return (
            False,
            "unknown_event_mismatch",
            (
                operation.action_id.value,
                operation.unknown_event_id.value,
            ),
        )
    pending = next(
        (
            item
            for item in replay.views.action_reconciliation.pending
            if item.action_id == operation.action_id
            and item.unknown_event_id == operation.unknown_event_id
        ),
        None,
    )
    if pending is None:
        return False, "unknown_outcome_not_pending", (operation.action_id.value,)
    if not _substantive(operation.evidence):
        return False, "reconciliation_evidence_required", (operation.action_id.value,)
    wait = reconciliation_wait(replay, operation.action_id)
    if wait is None:
        return False, "reconciliation_wait_not_found", (operation.action_id.value,)
    return (
        True,
        "action_reconciliation_allowed",
        (
            operation.action_id.value,
            operation.unknown_event_id.value,
            wait.wait_id.value,
        ),
    )


def _open_kind(operation: OpenWaitOperation) -> WaitKind:
    if isinstance(operation, OpenApprovalWaitOperation):
        return WaitKind.APPROVAL
    if isinstance(operation, OpenInteractionWaitOperation):
        return WaitKind.INTERACTION
    if isinstance(operation, OpenTimerWaitOperation):
        return WaitKind.TIMER
    return WaitKind.JOIN


def _terminal_kind(operation: TerminalWaitOperation) -> WaitKind:
    if isinstance(operation, ResolveApprovalOperation):
        return WaitKind.APPROVAL
    if isinstance(operation, ResolveInteractionWaitOperation):
        return WaitKind.INTERACTION
    if isinstance(operation, FireTimerWaitOperation):
        return WaitKind.TIMER
    if isinstance(operation, ResolveJoinWaitOperation):
        return WaitKind.JOIN
    return operation.wait_kind


def _operation_wait_id(operation: ConcreteWaitOperation) -> WaitId | None:
    value = operation.wait_id
    return value if isinstance(value, WaitId) else None


def allocate_wait_id(operation: OpenWaitOperation, factory: IdFactory[WaitId] | None) -> WaitId:
    existing = _operation_wait_id(operation)
    if existing is not None:
        return existing
    if factory is None:
        raise ValidationError(code="engine_wait_ids_required")
    return factory.new_id()


def pending_wait(
    replay: CompleteViewReplay[RunViewBundle],
    wait_id: WaitId,
    kind: WaitKind,
) -> PendingWait | None:
    return next(
        (
            wait
            for wait in replay.views.waits.all_pending
            if wait.wait_id == wait_id and wait.kind is kind
        ),
        None,
    )


def _wait_id_seen(replay: CompleteViewReplay[RunViewBundle], wait_id: WaitId) -> bool:
    return any(item.wait_id == wait_id for item in replay.views.waits.all_pending) or any(
        item.wait_id == wait_id for item in replay.views.waits.all_terminal
    )


def _missing_terminal_reason(
    replay: CompleteViewReplay[RunViewBundle],
    wait_id: WaitId,
    kind: WaitKind,
) -> str:
    if any(item.wait_id == wait_id for item in replay.views.waits.all_pending):
        return "wait_kind_mismatch"
    if any(
        item.wait_id == wait_id and item.kind is not kind
        for item in replay.views.waits.all_terminal
    ):
        return "wait_kind_mismatch"
    return "wait_terminal" if _wait_id_seen(replay, wait_id) else "wait_not_found"


def _approval_complete(operation: OpenApprovalWaitOperation) -> bool:
    return (
        operation.action_id not in (MISSING, None)
        and operation.capability_id not in (MISSING, None)
        and isinstance(operation.action_name, str)
        and operation.request_payload not in (MISSING, None)
        and operation.policy_snapshot not in (MISSING, None)
    )


def check_wait_operation(
    operation: object,
    replay: CompleteViewReplay[RunViewBundle],
    now: Timestamp,
    governance: GovernanceContext | None = None,
) -> tuple[bool, str, tuple[str, ...]] | None:
    """Return an allow/reason tuple for a concrete Wait operation."""

    if isinstance(
        operation,
        (
            OpenApprovalWaitOperation,
            OpenInteractionWaitOperation,
            OpenTimerWaitOperation,
            OpenJoinWaitOperation,
        ),
    ):
        wait_id = _operation_wait_id(operation)
        if wait_id is not None and _wait_id_seen(replay, wait_id):
            return False, "wait_already_exists", (wait_id.value,)
        if isinstance(operation, OpenApprovalWaitOperation) and not _approval_complete(operation):
            return False, "approval_wait_action_required", ()
        if isinstance(operation, OpenJoinWaitOperation):
            for run_id in operation.target_run_ids:
                child = replay.views.delegation.delegated_runs.get(run_id)
                if child is None:
                    return False, "join_target_not_found", (run_id.value,)
                if child.establishment is None:
                    return False, "join_target_not_established", (run_id.value,)
        return True, "wait_open_allowed", (() if wait_id is None else (wait_id.value,))

    if not isinstance(
        operation,
        (
            ResolveApprovalOperation,
            ResolveInteractionWaitOperation,
            FireTimerWaitOperation,
            ResolveJoinWaitOperation,
            CancelWaitOperation,
            ExpireWaitOperation,
        ),
    ):
        return None
    kind = _terminal_kind(operation)
    wait = pending_wait(replay, operation.wait_id, kind)
    if wait is None:
        return (
            False,
            _missing_terminal_reason(replay, operation.wait_id, kind),
            (operation.wait_id.value,),
        )
    if isinstance(operation, ResolveApprovalOperation):
        request = wait.request
        if not isinstance(request, ApprovalWaitCreatedPayload):
            return False, "wait_kind_mismatch", (operation.wait_id.value,)
        if operation.decision == "approved":
            from openrund.engine._governance import validate_approval_revision

            if governance is None:
                return False, "governance_context_required", (operation.wait_id.value,)
            approved = operation.approved_input
            if not isinstance(approved, JsonObject):
                approved = request.request_payload.data
            if not isinstance(approved, JsonObject):
                approved = JsonObject(entries=())
            allowed, reason, _evidence = validate_approval_revision(
                approved,
                request,
                governance,
            )
            if not allowed:
                return False, reason, (operation.wait_id.value,)
    elif isinstance(operation, ResolveInteractionWaitOperation):
        if (
            operation.request_event_id not in (MISSING, None)
            and operation.request_event_id != wait.request_event_id
        ):
            return False, "wait_request_mismatch", (operation.wait_id.value,)
    elif isinstance(operation, FireTimerWaitOperation):
        request = wait.request
        if not isinstance(request, TimerWaitCreatedPayload):
            return False, "wait_kind_mismatch", (operation.wait_id.value,)
        if now.value < request.fire_at.value:
            return False, "timer_not_due", (operation.wait_id.value,)
    elif isinstance(operation, ResolveJoinWaitOperation):
        join = replay.views.delegation.joins.get(operation.wait_id)
        if join is None:
            return False, "join_not_found", (operation.wait_id.value,)
        if not join.satisfied:
            return False, "join_not_satisfied", (operation.wait_id.value,)
    elif isinstance(operation, ExpireWaitOperation):
        request = wait.request
        deadline: Timestamp | None = None
        if isinstance(
            request, (ApprovalWaitCreatedPayload, InteractionWaitCreatedPayload)
        ) and isinstance(request.deadline, Timestamp):
            deadline = request.deadline
        elif isinstance(request, TimerWaitCreatedPayload):
            deadline = request.fire_at
        if deadline is not None and now.value < deadline.value:
            return False, "wait_not_expired", (operation.wait_id.value,)
    return True, "wait_terminal_allowed", (operation.wait_id.value,)


def materialize_wait_request(
    operation: OpenWaitOperation,
    wait_id: WaitId,
) -> EventPayload:
    if isinstance(operation, OpenApprovalWaitOperation):
        if not _approval_complete(operation):
            raise ValidationError(code="approval_wait_action_required")
        assert isinstance(operation.action_id, ActionId)
        assert isinstance(operation.capability_id, CapabilityId)
        assert isinstance(operation.action_name, str)
        assert isinstance(operation.request_payload, Content)
        assert isinstance(operation.policy_snapshot, Content)
        return ApprovalWaitCreatedPayload(
            wait_id=wait_id,
            action_id=operation.action_id,
            capability_id=operation.capability_id,
            action_name=operation.action_name,
            request_payload=operation.request_payload,
            policy_snapshot=operation.policy_snapshot,
            target=operation.target,
            reason=operation.reason,
            deadline=operation.deadline,
        )
    if isinstance(operation, OpenInteractionWaitOperation):
        return InteractionWaitCreatedPayload(
            wait_id=wait_id,
            prompt=Content(preview=operation.prompt, metadata=operation.metadata),
            reason=MISSING,
            deadline=operation.deadline,
        )
    if isinstance(operation, OpenTimerWaitOperation):
        return TimerWaitCreatedPayload(
            wait_id=wait_id,
            fire_at=operation.fire_at,
            reason=operation.reason,
        )
    return JoinWaitCreatedPayload(
        wait_id=wait_id,
        target_run_ids=operation.target_run_ids,
        mode=operation.mode,
        quorum=operation.quorum,
        outcome_filter=operation.outcome_filter,
        failure_policy=operation.failure_policy,
        on_satisfied=operation.on_satisfied,
        late_handoff_policy=operation.late_handoff_policy,
        reason=operation.reason,
    )


def _cancelled_payload(operation: CancelWaitOperation, wait: PendingWait) -> EventPayload:
    if operation.wait_kind is WaitKind.APPROVAL:
        return ApprovalWaitCancelledPayload(
            wait_id=operation.wait_id,
            reason=operation.reason,
            request_event_id=wait.request_event_id,
        )
    if operation.wait_kind is WaitKind.INTERACTION:
        return InteractionWaitCancelledPayload(
            wait_id=operation.wait_id,
            reason=operation.reason,
            request_event_id=wait.request_event_id,
        )
    if operation.wait_kind is WaitKind.TIMER:
        return TimerWaitCancelledPayload(wait_id=operation.wait_id, reason=operation.reason)
    if operation.wait_kind is WaitKind.JOIN:
        request = wait.request
        targets = request.target_run_ids if isinstance(request, JoinWaitCreatedPayload) else ()
        return JoinWaitCancelledPayload(
            wait_id=operation.wait_id,
            reason=operation.reason,
            target_run_ids=targets,
        )
    return ReconciliationWaitCancelledPayload(
        wait_id=operation.wait_id,
        reason=operation.reason,
    )


def _expired_payload(operation: ExpireWaitOperation, now: Timestamp) -> EventPayload:
    if operation.wait_kind is WaitKind.APPROVAL:
        return ApprovalWaitExpiredPayload(
            wait_id=operation.wait_id,
            expired_at=now,
            reason=operation.reason,
        )
    if operation.wait_kind is WaitKind.INTERACTION:
        return InteractionWaitExpiredPayload(
            wait_id=operation.wait_id,
            expired_at=now,
            reason=operation.reason,
        )
    if operation.wait_kind is WaitKind.TIMER:
        return TimerWaitExpiredPayload(
            wait_id=operation.wait_id,
            expired_at=now,
            reason=operation.reason,
        )
    if operation.wait_kind is WaitKind.JOIN:
        return JoinWaitExpiredPayload(
            wait_id=operation.wait_id,
            expired_at=now,
            reason=operation.reason,
        )
    return ReconciliationWaitExpiredPayload(
        wait_id=operation.wait_id,
        expired_at=now,
        reason=operation.reason,
    )


def materialize_wait_terminal(
    operation: TerminalWaitOperation,
    replay: CompleteViewReplay[RunViewBundle],
    now: Timestamp,
    governance: GovernanceContext | None = None,
) -> EventPayload:
    kind = _terminal_kind(operation)
    wait = pending_wait(replay, operation.wait_id, kind)
    if wait is None:
        raise ValidationError(code="wait_not_pending")
    if isinstance(operation, ResolveApprovalOperation):
        validation: JsonObject | MissingType = MISSING
        if operation.decision == "approved":
            from openrund.engine._governance import validate_approval_revision

            if governance is None:
                raise ValidationError(code="governance_context_required")
            request = wait.request
            assert isinstance(request, ApprovalWaitCreatedPayload)
            approved = operation.approved_input
            if not isinstance(approved, JsonObject):
                approved = request.request_payload.data
            if not isinstance(approved, JsonObject):
                approved = JsonObject(entries=())
            allowed, reason, evidence = validate_approval_revision(approved, request, governance)
            if not allowed or evidence is None:
                raise ValidationError(code=reason)
            validation = evidence
        return ApprovalWaitResolvedPayload(
            wait_id=operation.wait_id,
            decision=operation.decision,
            approved_input=operation.approved_input,
            approved_input_validation=validation,
            note=operation.note,
            resolved_by=operation.resolved_by,
        )
    if isinstance(operation, ResolveInteractionWaitOperation):
        return InteractionWaitResolvedPayload(
            wait_id=operation.wait_id,
            response=operation.response,
            request_event_id=(
                wait.request_event_id
                if operation.request_event_id in (MISSING, None)
                else operation.request_event_id
            ),
            responded_by=operation.responded_by,
        )
    if isinstance(operation, FireTimerWaitOperation):
        request = wait.request
        assert isinstance(request, TimerWaitCreatedPayload)
        return TimerWaitResolvedPayload(
            wait_id=operation.wait_id,
            fired_at=now,
            scheduled_for=request.fire_at,
            fired_by=operation.fired_by,
        )
    if isinstance(operation, ResolveJoinWaitOperation):
        join = replay.views.delegation.joins[operation.wait_id]
        return JoinWaitResolvedPayload(
            wait_id=operation.wait_id,
            target_run_ids=join.request.target_run_ids,
            mode=join.request.mode,
            quorum=join.request.quorum,
            completed_run_ids=join.completed_run_ids,
            terminal_run_ids=(
                *join.completed_run_ids,
                *join.failed_run_ids,
                *join.cancelled_run_ids,
            ),
            on_satisfied=join.request.on_satisfied,
        )
    if isinstance(operation, CancelWaitOperation):
        return _cancelled_payload(operation, wait)
    return _expired_payload(operation, now)
