"""Pure hard-invariant evaluation for core Engine Commands."""

from __future__ import annotations

from dataclasses import dataclass
from typing import final

from openrund.codec import canonical_content_hash
from openrund.contracts.commands import (
    AcceptedCommandDecision,
    AddMessageOperation,
    BootstrapRunOperation,
    CancelActionOperation,
    CancelDelegationOperation,
    CancelModelCallOperation,
    CancelRunOperation,
    CancelWaitOperation,
    Command,
    CommandDecision,
    CommandDecisionTraceEntry,
    CommandOrigin,
    CompleteActionOperation,
    CompleteDelegationOperation,
    CompleteModelCallOperation,
    CompleteRunOperation,
    CreateActionOperation,
    CreateCheckpointOperation,
    CreateDelegationOperation,
    ExpireWaitOperation,
    FailActionOperation,
    FailDelegationOperation,
    FailModelCallOperation,
    FailRunOperation,
    FireTimerWaitOperation,
    GrantCapabilityAuthorityOperation,
    GrantPolicyAuthorityOperation,
    LegalityCriterion,
    LegalityCriterionResult,
    MarkActionUnknownOperation,
    MessageDeltaOperation,
    ReconcileActionOperation,
    RecordAnnotationOperation,
    RecordCheckOperation,
    RejectedCommandDecision,
    ResolveApprovalOperation,
    ResolveInteractionWaitOperation,
    ResolveJoinWaitOperation,
    ResumeApprovedActionOperation,
    RevokeCapabilityAuthorityOperation,
    RevokePolicyAuthorityOperation,
    StartActionOperation,
    StartModelCallOperation,
    StartRunOperation,
)
from openrund.contracts.content import Content, RunResult
from openrund.contracts.events import (
    ActionCreatedPayload,
    CanonicalAnnotationRecordedPayload,
    CanonicalMessageAddedPayload,
    CoreEventType,
    LegacyPreviewAnnotationRecordedPayload,
    LegacyPreviewMessageAddedPayload,
    ModelCallCancelledPayload,
    ModelCallCompletedPayload,
    ModelCallFailedPayload,
    ModelCallStartedPayload,
    RuntimeEvent,
)
from openrund.contracts.ids import (
    AnnotationId,
    CheckId,
    CheckpointId,
    MessageId,
    ModelCallId,
    RunId,
    WaitId,
)
from openrund.contracts.json import MISSING, JsonArray, JsonObject
from openrund.contracts.time import Timestamp
from openrund.engine._coordination import check_recovery_operation, check_wait_operation
from openrund.engine._delegation import evaluate_delegation, evaluate_delegation_handoff
from openrund.engine._governance import (
    GovernanceContext,
    approved_action_operation,
    evaluate_governed_action,
)
from openrund.views._model import CompleteViewReplay, RunViewBundle
from openrund.views._run_status import ReadinessBlocker, ReadinessBlockerCode

_TERMINAL_STATUSES = frozenset({"completed", "failed", "cancelled"})


def _coordination_origin_allowed(command: Command) -> bool:
    operation = command.operation
    trusted = (CommandOrigin.OPERATOR, CommandOrigin.SYSTEM, CommandOrigin.RECOVERY)
    if isinstance(operation, ResolveApprovalOperation):
        return command.origin in trusted
    if isinstance(operation, ResolveInteractionWaitOperation):
        return command.origin in (
            *trusted,
            CommandOrigin.USER,
            CommandOrigin.CLIENT,
            CommandOrigin.EXTERNAL,
        )
    if isinstance(
        operation,
        (
            FireTimerWaitOperation,
            ResolveJoinWaitOperation,
            CancelWaitOperation,
            ExpireWaitOperation,
        ),
    ):
        return command.origin in (*trusted, CommandOrigin.TIMER)
    if isinstance(operation, (MarkActionUnknownOperation, ReconcileActionOperation)):
        return command.origin in (*trusted, CommandOrigin.CAPABILITY)
    return True


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


def _accept(*trace: CommandDecisionTraceEntry) -> AcceptedCommandDecision:
    return AcceptedCommandDecision(trace=trace)


def _reject(
    reason: str,
    criterion: LegalityCriterion,
    *related: str,
) -> RejectedCommandDecision:
    return RejectedCommandDecision(
        reason=reason,
        trace=(_trace(criterion, LegalityCriterionResult.FAIL, reason, *related),),
    )


def _message_ids(events: tuple[RuntimeEvent, ...]) -> frozenset[MessageId]:
    return frozenset(
        payload.message_id
        for event in events
        if isinstance(
            (payload := event.payload),
            (CanonicalMessageAddedPayload, LegacyPreviewMessageAddedPayload),
        )
    )


def _model_call_state(events: tuple[RuntimeEvent, ...], model_call_id: ModelCallId) -> str | None:
    state: str | None = None
    for event in events:
        payload = event.payload
        if isinstance(payload, ModelCallStartedPayload) and payload.model_call_id == model_call_id:
            state = "active"
        elif (
            isinstance(
                payload,
                (ModelCallCompletedPayload, ModelCallFailedPayload, ModelCallCancelledPayload),
            )
            and payload.model_call_id == model_call_id
        ):
            state = "terminal"
    return state


def _created_action(
    events: tuple[RuntimeEvent, ...], action_id: object
) -> ActionCreatedPayload | None:
    return next(
        (
            payload
            for event in events
            if isinstance((payload := event.payload), ActionCreatedPayload)
            and payload.action_id == action_id
        ),
        None,
    )


def _evaluate_action_lifecycle(
    command: Command,
    replay: CompleteViewReplay[RunViewBundle],
    events: tuple[RuntimeEvent, ...],
) -> CommandDecision | None:
    operation = command.operation
    if not isinstance(
        operation,
        (
            StartActionOperation,
            CompleteActionOperation,
            FailActionOperation,
            CancelActionOperation,
        ),
    ):
        return None
    if command.origin not in (
        CommandOrigin.CAPABILITY,
        CommandOrigin.SYSTEM,
        CommandOrigin.RECOVERY,
    ):
        return _reject(
            "action_lifecycle_origin_forbidden",
            LegalityCriterion.AUTHORITY,
            command.origin.value,
        )
    receipt = replay.views.action_receipts.get(operation.action_id)
    if receipt is None:
        return _reject("action_not_found", LegalityCriterion.CONTRACT, operation.action_id.value)
    if isinstance(operation, StartActionOperation):
        if receipt.status != "requested":
            return _reject(
                "action_already_started_or_terminal",
                LegalityCriterion.KNOWN_OUTCOMES,
                operation.action_id.value,
            )
        created = _created_action(events, operation.action_id)
        if created is None:
            return _reject(
                "action_creation_missing",
                LegalityCriterion.CONTRACT,
                operation.action_id.value,
            )
        if (
            created.capability_id != operation.capability_id
            or created.action_name != operation.action_name
            or canonical_content_hash(created.input) != operation.input_hash
        ):
            return _reject(
                "action_start_identity_mismatch",
                LegalityCriterion.CONTRACT,
                operation.action_id.value,
            )
        return _accept(
            _trace(
                LegalityCriterion.KNOWN_OUTCOMES,
                LegalityCriterionResult.PASS,
                "action_start_allowed",
                operation.action_id.value,
            )
        )
    if receipt.status != "started":
        reason = (
            "action_not_started" if receipt.status == "requested" else "action_already_terminal"
        )
        return _reject(reason, LegalityCriterion.KNOWN_OUTCOMES, operation.action_id.value)
    if isinstance(operation, CompleteActionOperation):
        produced_ids = {item.artifact_id.value for item in operation.produced_artifacts}
        referenced = (
            _content_artifact_ids(operation.result) if isinstance(operation.result, Content) else ()
        )
        known = frozenset(item.value for item in replay.views.artifact_index)
        missing = tuple(
            dict.fromkeys(
                item
                for item in (
                    *referenced,
                    *(artifact.value for artifact in operation.artifact_ids),
                )
                if item not in produced_ids and item not in known
            )
        )
        if missing:
            return _reject("artifact_not_found", LegalityCriterion.ARTIFACT_DISCIPLINE, *missing)
    return _accept(
        _trace(
            LegalityCriterion.KNOWN_OUTCOMES,
            LegalityCriterionResult.PASS,
            "action_terminal_allowed",
            operation.action_id.value,
        )
    )


def _content_artifact_ids(content: Content) -> tuple[str, ...]:
    return tuple(
        dict.fromkeys(
            (
                *(item.value for item in content.artifact_ids),
                *(reference.artifact_id.value for reference in content.artifact_refs),
            )
        )
    )


def _missing_artifacts(
    replay: CompleteViewReplay[RunViewBundle],
    *contents: Content,
    explicit: tuple[str, ...] = (),
) -> tuple[str, ...]:
    known = frozenset(item.value for item in replay.views.artifact_index)
    referenced = tuple(
        dict.fromkeys(
            (
                *explicit,
                *(
                    artifact_id
                    for content in contents
                    for artifact_id in _content_artifact_ids(content)
                ),
            )
        )
    )
    return tuple(item for item in referenced if item not in known)


def _check_evidence_operation(
    command: Command,
    replay: CompleteViewReplay[RunViewBundle],
    events: tuple[RuntimeEvent, ...],
) -> tuple[bool, str, tuple[str, ...]] | None:
    operation = command.operation
    if isinstance(operation, RecordCheckOperation):
        if command.origin not in (
            CommandOrigin.OPERATOR,
            CommandOrigin.SYSTEM,
            CommandOrigin.RECOVERY,
            CommandOrigin.CAPABILITY,
        ):
            return False, "check_origin_forbidden", (command.origin.value,)
        if (
            isinstance(operation.check_id, CheckId)
            and operation.check_id in replay.views.run_status.checks
        ):
            return False, "check_already_exists", (operation.check_id.value,)
        data = operation.result.data
        checks = data.get("checks") if isinstance(data, JsonObject) else None
        if checks is None:
            observed_count = 0
        elif not isinstance(checks, JsonArray):
            return False, "check_results_invalid", ()
        else:
            observed_count = len(checks)
            for item in checks:
                if not isinstance(item, JsonObject):
                    return False, "check_results_invalid", ()
                name = item.get("check")
                status = item.get("status")
                if (
                    not isinstance(name, str)
                    or name == ""
                    or status
                    not in (
                        "passed",
                        "failed",
                        "blocked",
                    )
                ):
                    return False, "check_results_invalid", ()
        if observed_count != operation.check_count:
            return False, "check_count_mismatch", ()
        contents = [operation.result]
        if isinstance(operation.evidence, Content):
            contents.append(operation.evidence)
        missing = _missing_artifacts(replay, *contents)
        if missing:
            return False, "artifact_not_found", missing
        return True, "check_record_allowed", ()
    if isinstance(operation, CreateCheckpointOperation):
        if not 1 <= operation.from_position <= operation.to_position <= replay.watermark:
            return False, "checkpoint_range_out_of_bounds", ()
        try:
            protected = tuple(CoreEventType(value) for value in operation.protected_event_types)
        except ValueError:
            return False, "checkpoint_event_type_invalid", ()
        if len(set(protected)) != len(protected):
            return False, "checkpoint_event_type_duplicate", ()
        if isinstance(operation.checkpoint_id, CheckpointId) and any(
            item.checkpoint_id == operation.checkpoint_id
            for item in replay.views.checkpoints.checkpoints
        ):
            return False, "checkpoint_already_exists", (operation.checkpoint_id.value,)
        missing = _missing_artifacts(
            replay,
            explicit=tuple(item.value for item in operation.artifact_ids),
        )
        if missing:
            return False, "artifact_not_found", missing
        covered_types = frozenset(
            event.event_type
            for event in events
            if operation.from_position <= event.position <= operation.to_position
        )
        absent = tuple(item.value for item in protected if item not in covered_types)
        if absent:
            return False, "checkpoint_protected_event_absent", absent
        return True, "checkpoint_create_allowed", ()
    if isinstance(operation, RecordAnnotationOperation):
        if isinstance(operation.annotation_id, AnnotationId) and any(
            isinstance(
                event.payload,
                (CanonicalAnnotationRecordedPayload, LegacyPreviewAnnotationRecordedPayload),
            )
            and event.payload.annotation_id == operation.annotation_id
            for event in events
        ):
            return False, "annotation_already_exists", (operation.annotation_id.value,)
        missing = _missing_artifacts(replay, operation.content)
        if missing:
            return False, "artifact_not_found", missing
        return True, "annotation_record_allowed", ()
    return None


def _blocker_trace(blocker: ReadinessBlocker) -> CommandDecisionTraceEntry:
    if blocker.code is ReadinessBlockerCode.PENDING_WAIT:
        related = (blocker.wait_id.value,) if blocker.wait_id is not None else ()
        return _trace(
            LegalityCriterion.WAIT_STATE,
            LegalityCriterionResult.FAIL,
            "completion_pending_wait",
            *related,
        )
    if blocker.code is ReadinessBlockerCode.MISSING_REQUIRED_ARTIFACT:
        related = (blocker.artifact_kind,) if blocker.artifact_kind is not None else ()
        return _trace(
            LegalityCriterion.ARTIFACT_DISCIPLINE,
            LegalityCriterionResult.FAIL,
            "completion_missing_artifact",
            *related,
        )
    if blocker.code is ReadinessBlockerCode.UNRESOLVED_ACTION_OUTCOME:
        related = (blocker.action_id.value,) if blocker.action_id is not None else ()
        return _trace(
            LegalityCriterion.KNOWN_OUTCOMES,
            LegalityCriterionResult.FAIL,
            "completion_unknown_action_outcome",
            *related,
        )
    related = (blocker.check,) if blocker.check is not None else ()
    return _trace(
        LegalityCriterion.REQUIRED_CHECKS,
        LegalityCriterionResult.FAIL,
        "completion_unsatisfied_check",
        *related,
    )


@final
@dataclass(frozen=True, slots=True, kw_only=True)
class CommandAttemptFacts:
    """Complete non-Run facts loaded for one immutable Engine attempt."""

    now: Timestamp | None = None
    governance: GovernanceContext | None = None
    approval_wait_id: WaitId | None = None
    delegated_run_id: RunId | None = None
    delegated_run_exists: bool = False
    delegation_atomic_available: bool = False
    delegation_factories_available: bool = False
    delegated_child_replay: CompleteViewReplay[RunViewBundle] | None = None
    parent_cancel_requires_atomic: bool = False
    parent_cancel_atomic_available: bool = False
    parent_cancel_child_missing: bool = False


def evaluate_command(
    command: Command,
    replay: CompleteViewReplay[RunViewBundle],
    events: tuple[RuntimeEvent, ...],
    *,
    facts: CommandAttemptFacts | None = None,
) -> CommandDecision:
    """Evaluate one Command from complete immutable replay facts."""

    attempt = facts if facts is not None else CommandAttemptFacts()
    now = attempt.now
    governance = attempt.governance
    approval_wait_id = attempt.approval_wait_id
    delegated_run_id = attempt.delegated_run_id
    delegated_run_exists = attempt.delegated_run_exists
    delegation_atomic_available = attempt.delegation_atomic_available
    delegation_factories_available = attempt.delegation_factories_available
    delegated_child_replay = attempt.delegated_child_replay
    parent_cancel_requires_atomic = attempt.parent_cancel_requires_atomic
    parent_cancel_atomic_available = attempt.parent_cancel_atomic_available
    parent_cancel_child_missing = attempt.parent_cancel_child_missing
    status = replay.views.run_status.status
    operation = command.operation
    governance = governance if governance is not None else GovernanceContext()
    if (
        isinstance(
            operation,
            (CompleteDelegationOperation, FailDelegationOperation, CancelDelegationOperation),
        )
        and status != "unknown"
    ):
        return evaluate_delegation_handoff(operation, replay, delegated_child_replay)
    if status == "unknown":
        if not isinstance(operation, BootstrapRunOperation):
            return _reject("run_not_found", LegalityCriterion.RUN_LIFECYCLE)
        if operation.parent_run_id is None or operation.parent_run_id is MISSING:
            invalid_descriptor = operation.root_id != command.run_id
        else:
            invalid_descriptor = operation.parent_run_id == command.run_id
        if invalid_descriptor:
            return _reject(
                "bootstrap_run_id_mismatch",
                LegalityCriterion.OPERATION_SCHEMA,
                command.run_id.value,
                operation.root_id.value,
            )
        return _accept(
            _trace(
                LegalityCriterion.RUN_LIFECYCLE,
                LegalityCriterionResult.PASS,
                "bootstrap_allowed",
            )
        )

    if status in _TERMINAL_STATUSES:
        return _reject(
            "run_terminal",
            LegalityCriterion.RUN_LIFECYCLE,
            status,
        )
    if isinstance(operation, BootstrapRunOperation):
        return _reject("run_already_exists", LegalityCriterion.RUN_LIFECYCLE)

    if status == "created":
        if isinstance(operation, (StartRunOperation, FailRunOperation, CancelRunOperation)):
            return _accept(
                _trace(
                    LegalityCriterion.RUN_LIFECYCLE,
                    LegalityCriterionResult.PASS,
                    "created_transition_allowed",
                )
            )
        return _reject("run_not_started", LegalityCriterion.RUN_LIFECYCLE)

    if isinstance(operation, StartRunOperation):
        return _reject("run_already_started", LegalityCriterion.RUN_LIFECYCLE)
    if not _coordination_origin_allowed(command):
        return _reject(
            "coordination_origin_forbidden",
            LegalityCriterion.AUTHORITY,
            command.origin.value,
        )
    action_lifecycle = _evaluate_action_lifecycle(
        command,
        replay,
        events,
    )
    if action_lifecycle is not None:
        return action_lifecycle
    wait_check = check_wait_operation(
        operation,
        replay,
        now if now is not None else events[-1].timestamp,
        governance,
    )
    if wait_check is not None:
        allowed, reason, related = wait_check
        if not allowed:
            return _reject(reason, LegalityCriterion.WAIT_STATE, *related)
        return _accept(
            _trace(
                LegalityCriterion.WAIT_STATE,
                LegalityCriterionResult.PASS,
                reason,
                *related,
            )
        )
    recovery_check = check_recovery_operation(operation, replay)
    if recovery_check is not None:
        allowed, reason, related = recovery_check
        if allowed and isinstance(operation, ReconcileActionOperation):
            missing = _missing_artifacts(replay, operation.evidence)
            if missing:
                return _reject(
                    "artifact_not_found", LegalityCriterion.ARTIFACT_DISCIPLINE, *missing
                )
        if not allowed:
            return _reject(reason, LegalityCriterion.KNOWN_OUTCOMES, *related)
        return _accept(
            _trace(
                LegalityCriterion.KNOWN_OUTCOMES,
                LegalityCriterionResult.PASS,
                reason,
                *related,
            )
        )
    evidence_check = _check_evidence_operation(command, replay, events)
    if evidence_check is not None:
        allowed, reason, related = evidence_check
        if not allowed:
            criterion = (
                LegalityCriterion.ARTIFACT_DISCIPLINE
                if reason == "artifact_not_found"
                else LegalityCriterion.REQUIRED_CHECKS
            )
            return _reject(reason, criterion, *related)
        return _accept(
            _trace(
                LegalityCriterion.REQUIRED_CHECKS,
                LegalityCriterionResult.PASS,
                reason,
                *related,
            )
        )
    authority_operations = (
        GrantCapabilityAuthorityOperation,
        GrantPolicyAuthorityOperation,
        RevokeCapabilityAuthorityOperation,
        RevokePolicyAuthorityOperation,
    )
    if isinstance(operation, authority_operations):
        if command.origin not in (
            CommandOrigin.OPERATOR,
            CommandOrigin.SYSTEM,
            CommandOrigin.RECOVERY,
        ):
            return _reject(
                "authority_origin_forbidden", LegalityCriterion.AUTHORITY, command.origin.value
            )
        if isinstance(operation, GrantCapabilityAuthorityOperation):
            if governance.capability(operation.capability_id) is None:
                return _reject(
                    "capability_not_registered",
                    LegalityCriterion.CAPABILITY_METADATA,
                    operation.capability_id.value,
                )
        elif isinstance(operation, RevokeCapabilityAuthorityOperation):
            current = replay.views.run_status.capability_authority.get(operation.capability_id)
            if current is None:
                return _reject(
                    "capability_authority_missing",
                    LegalityCriterion.AUTHORITY,
                    operation.capability_id.value,
                )
            if (
                operation.authority_id not in (MISSING, None)
                and current.payload.authority_id != operation.authority_id
            ):
                return _reject(
                    "authority_id_mismatch",
                    LegalityCriterion.AUTHORITY,
                    operation.capability_id.value,
                )
        elif isinstance(operation, RevokePolicyAuthorityOperation):
            current_policy = replay.views.run_status.policy_authority.get(operation.rule_id)
            if current_policy is None:
                return _reject(
                    "policy_authority_missing", LegalityCriterion.AUTHORITY, operation.rule_id.value
                )
            if (
                operation.authority_id not in (MISSING, None)
                and current_policy.payload.authority_id != operation.authority_id
            ):
                return _reject(
                    "authority_id_mismatch", LegalityCriterion.AUTHORITY, operation.rule_id.value
                )
        return _accept(
            _trace(
                LegalityCriterion.AUTHORITY,
                LegalityCriterionResult.PASS,
                "authority_change_allowed",
            )
        )
    if isinstance(operation, CreateActionOperation):
        return evaluate_governed_action(
            operation,
            replay,
            governance,
            approval_wait_id=approval_wait_id,
        )
    if isinstance(operation, ResumeApprovedActionOperation):
        approved, reason = approved_action_operation(operation.wait_id, replay)
        if approved is None:
            return _reject(reason, LegalityCriterion.WAIT_STATE, operation.wait_id.value)
        decision = evaluate_governed_action(
            approved,
            replay,
            governance,
            approval_satisfied=True,
        )
        return decision
    if isinstance(operation, CreateDelegationOperation):
        return evaluate_delegation(
            operation,
            delegated_run_id,
            replay,
            child_exists=delegated_run_exists,
            atomic_available=delegation_atomic_available,
            factories_available=delegation_factories_available,
        )
    if isinstance(operation, CompleteRunOperation):
        run = replay.views.run_status.run
        metadata = run.creation.metadata if run is not None else MISSING
        delegation_contract = (
            metadata.get("delegation_contract") if isinstance(metadata, JsonObject) else None
        )
        expected_result_kind = (
            delegation_contract.get("result_kind")
            if isinstance(delegation_contract, JsonObject)
            else None
        )
        if isinstance(expected_result_kind, str) and (
            not isinstance(operation.result, RunResult)
            or operation.result.kind != expected_result_kind
        ):
            return _reject(
                "delegation_result_kind_mismatch",
                LegalityCriterion.CONTRACT,
                expected_result_kind,
            )
        blockers = replay.views.run_status.completion_readiness.blockers
        if blockers:
            return RejectedCommandDecision(
                reason="completion_blocked",
                trace=tuple(_blocker_trace(blocker) for blocker in blockers),
            )
        return _accept(
            _trace(
                LegalityCriterion.RUN_LIFECYCLE,
                LegalityCriterionResult.PASS,
                "completion_allowed",
            )
        )
    if isinstance(operation, CancelRunOperation) and parent_cancel_child_missing:
        return _reject("delegated_child_not_found", LegalityCriterion.DELEGATION_LINEAGE)
    if (
        isinstance(operation, CancelRunOperation)
        and parent_cancel_requires_atomic
        and not parent_cancel_atomic_available
    ):
        return _reject("atomic_event_store_required", LegalityCriterion.CONTRACT)
    if isinstance(operation, (FailRunOperation, CancelRunOperation, AddMessageOperation)):
        return _accept(
            _trace(
                LegalityCriterion.RUN_LIFECYCLE,
                LegalityCriterionResult.PASS,
                "active_transition_allowed",
            )
        )
    if isinstance(operation, MessageDeltaOperation):
        if operation.message_id not in _message_ids(events):
            return _reject(
                "message_not_found",
                LegalityCriterion.CONTRACT,
                operation.message_id.value,
            )
        return _accept(
            _trace(
                LegalityCriterion.CONTRACT,
                LegalityCriterionResult.PASS,
                "message_delta_allowed",
                operation.message_id.value,
            )
        )
    if isinstance(operation, StartModelCallOperation):
        state = _model_call_state(events, operation.model_call_id)
        if state is not None:
            return _reject(
                "model_call_already_exists",
                LegalityCriterion.CONTRACT,
                operation.model_call_id.value,
            )
        return _accept(
            _trace(
                LegalityCriterion.CONTRACT,
                LegalityCriterionResult.PASS,
                "model_call_start_allowed",
                operation.model_call_id.value,
            )
        )
    if isinstance(
        operation,
        (CompleteModelCallOperation, FailModelCallOperation, CancelModelCallOperation),
    ):
        state = _model_call_state(events, operation.model_call_id)
        if state != "active":
            reason = "model_call_not_found" if state is None else "model_call_terminal"
            return _reject(reason, LegalityCriterion.CONTRACT, operation.model_call_id.value)
        return _accept(
            _trace(
                LegalityCriterion.CONTRACT,
                LegalityCriterionResult.PASS,
                "model_call_terminal_allowed",
                operation.model_call_id.value,
            )
        )
    return _reject("operation_not_enabled", LegalityCriterion.OPERATION_SCHEMA)
