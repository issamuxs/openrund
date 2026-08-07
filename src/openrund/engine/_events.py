"""Explicit core operation to lifecycle Event intent mapping."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, final

from openrund.contracts.commands import (
    AddMessageOperation,
    BootstrapRunOperation,
    CancelActionOperation,
    CancelDelegationOperation,
    CancelModelCallOperation,
    CancelRunOperation,
    CancelWaitOperation,
    Command,
    CompleteActionOperation,
    CompleteDelegationOperation,
    CompleteModelCallOperation,
    CompleteRunOperation,
    CreateActionOperation,
    CreateCheckpointOperation,
    ExpireWaitOperation,
    FailActionOperation,
    FailDelegationOperation,
    FailModelCallOperation,
    FailRunOperation,
    FireTimerWaitOperation,
    GrantCapabilityAuthorityOperation,
    GrantPolicyAuthorityOperation,
    MarkActionUnknownOperation,
    MessageDeltaOperation,
    OpenApprovalWaitOperation,
    OpenInteractionWaitOperation,
    OpenJoinWaitOperation,
    OpenTimerWaitOperation,
    ReconcileActionOperation,
    RecordAnnotationOperation,
    RecordCheckOperation,
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
from openrund.contracts.events import (
    ActionCancelledPayload,
    ActionCompletedPayload,
    ActionCreatedPayload,
    ActionFailedPayload,
    ActionReconciledCancelledPayload,
    ActionReconciledCompletedPayload,
    ActionReconciledFailedPayload,
    ActionStartedPayload,
    ActionUnknownPayload,
    ApprovalWaitCreatedPayload,
    ArtifactMetadataCreatedPayload,
    ArtifactPreviewCreatedPayload,
    CanonicalAnnotationRecordedPayload,
    CanonicalMessageAddedPayload,
    CapabilityAuthorityGrantedPayload,
    CapabilityAuthorityRevokedPayload,
    CheckpointRangeCreatedPayload,
    CheckRecordedReportPayload,
    CoreEventType,
    EventPayload,
    MessageDeltaPayload,
    ModelCallCancelledPayload,
    ModelCallCompletedPayload,
    ModelCallFailedPayload,
    ModelCallStartedPayload,
    PolicyAuthorityGrantedPayload,
    PolicyAuthorityRevokedPayload,
    ReconciliationWaitCreatedPayload,
    ReconciliationWaitResolvedPayload,
    RunCancelledPayload,
    RunCompletedPayload,
    RunCreatedPayload,
    RunFailedPayload,
    RunStartedPayload,
)
from openrund.contracts.ids import (
    AnnotationId,
    ArtifactId,
    AuthorityId,
    CheckId,
    CheckpointId,
    MessageId,
    WaitId,
)
from openrund.contracts.json import JsonObject, freeze_json
from openrund.contracts.time import Timestamp
from openrund.engine._coordination import (
    allocate_wait_id,
    materialize_wait_request,
    materialize_wait_terminal,
    reconciliation_wait,
)
from openrund.engine._delegation import (
    late_handoff_policy,
    materialize_delegation_handoff,
)
from openrund.engine._governance import GovernanceContext, approved_action_operation
from openrund.errors import ValidationError
from openrund.ports.runtime import IdFactory
from openrund.views import CompleteViewReplay
from openrund.views._model import RunViewBundle


@final
@dataclass(frozen=True, slots=True, kw_only=True)
class EventIntent:
    event_type: CoreEventType
    payload: EventPayload


def _artifact_ids(operation: AddMessageOperation) -> tuple[ArtifactId, ...]:
    content = operation.message
    return tuple(
        dict.fromkeys(
            (
                *content.artifact_ids,
                *(reference.artifact_id for reference in content.artifact_refs),
            )
        )
    )


def materialize_event_intents(
    command: Command,
    *,
    message_ids: IdFactory[MessageId],
    wait_ids: IdFactory[WaitId] | None = None,
    authority_ids: IdFactory[AuthorityId] | None = None,
    check_ids: IdFactory[CheckId] | None = None,
    checkpoint_ids: IdFactory[CheckpointId] | None = None,
    annotation_ids: IdFactory[AnnotationId] | None = None,
    replay: CompleteViewReplay[RunViewBundle] | None = None,
    now: Timestamp | None = None,
    governance: GovernanceContext | None = None,
    delegated_child_replay: CompleteViewReplay[RunViewBundle] | None = None,
) -> tuple[EventIntent, ...]:
    """Build target payload intents for one accepted core Command."""

    operation = command.operation
    if isinstance(operation, BootstrapRunOperation):
        return (
            EventIntent(
                event_type=CoreEventType.RUN_CREATED,
                payload=RunCreatedPayload(
                    root_id=operation.root_id,
                    initial_status="created",
                    parent_run_id=operation.parent_run_id,
                    title=operation.title,
                    objective=operation.objective,
                    metadata=operation.metadata,
                ),
            ),
            EventIntent(
                event_type=CoreEventType.RUN_STARTED,
                payload=RunStartedPayload(reason=operation.start_reason),
            ),
        )
    if isinstance(operation, StartRunOperation):
        return (
            EventIntent(
                event_type=CoreEventType.RUN_STARTED,
                payload=RunStartedPayload(reason=operation.reason),
            ),
        )
    if isinstance(operation, CompleteRunOperation):
        return (
            EventIntent(
                event_type=CoreEventType.RUN_COMPLETED,
                payload=RunCompletedPayload(
                    result=operation.result,
                    artifact_ids=operation.result.artifact_ids,
                ),
            ),
        )
    if isinstance(operation, FailRunOperation):
        return (
            EventIntent(
                event_type=CoreEventType.RUN_FAILED,
                payload=RunFailedPayload(
                    message=operation.message,
                    retryable=operation.retryable,
                ),
            ),
        )
    if isinstance(operation, CancelRunOperation):
        return (
            EventIntent(
                event_type=CoreEventType.RUN_CANCELLED,
                payload=RunCancelledPayload(reason=operation.reason),
            ),
        )
    if isinstance(operation, AddMessageOperation):
        preview = operation.message.preview
        return (
            EventIntent(
                event_type=CoreEventType.MESSAGE_ADDED,
                payload=CanonicalMessageAddedPayload(
                    message_id=message_ids.new_id(),
                    content_preview=preview if isinstance(preview, str) else "",
                    artifact_ids=_artifact_ids(operation),
                    metadata=operation.message.metadata,
                ),
            ),
        )
    if isinstance(operation, MessageDeltaOperation):
        return (
            EventIntent(
                event_type=CoreEventType.MESSAGE_DELTA,
                payload=MessageDeltaPayload(
                    message_id=operation.message_id,
                    delta=operation.delta,
                ),
            ),
        )
    if isinstance(operation, StartModelCallOperation):
        return (
            EventIntent(
                event_type=CoreEventType.MODEL_CALL_STARTED,
                payload=ModelCallStartedPayload(model_call_id=operation.model_call_id),
            ),
        )
    if isinstance(operation, CompleteModelCallOperation):
        return (
            EventIntent(
                event_type=CoreEventType.MODEL_CALL_COMPLETED,
                payload=ModelCallCompletedPayload(
                    model_call_id=operation.model_call_id,
                    outcome=operation.outcome,
                    metadata=operation.metadata,
                ),
            ),
        )
    if isinstance(operation, FailModelCallOperation):
        return (
            EventIntent(
                event_type=CoreEventType.MODEL_CALL_FAILED,
                payload=ModelCallFailedPayload(
                    model_call_id=operation.model_call_id,
                    message=operation.message,
                    classification=operation.classification,
                    retryable=operation.retryable,
                    evidence=operation.evidence,
                ),
            ),
        )
    if isinstance(operation, CancelModelCallOperation):
        return (
            EventIntent(
                event_type=CoreEventType.MODEL_CALL_CANCELLED,
                payload=ModelCallCancelledPayload(
                    model_call_id=operation.model_call_id,
                    reason=operation.reason,
                ),
            ),
        )
    if isinstance(operation, CreateActionOperation):
        return (
            EventIntent(
                event_type=CoreEventType.ACTION_CREATED,
                payload=ActionCreatedPayload(
                    action_id=operation.action_id,
                    capability_id=operation.capability_id,
                    action_name=operation.action_name,
                    input=operation.input,
                    mutation=operation.mutation,
                ),
            ),
        )
    if isinstance(operation, ResumeApprovedActionOperation):
        if replay is None:
            raise ValidationError(code="approval_replay_required")
        approved, reason = approved_action_operation(operation.wait_id, replay)
        if approved is None:
            raise ValidationError(code=reason)
        return (
            EventIntent(
                event_type=CoreEventType.ACTION_CREATED,
                payload=ActionCreatedPayload(
                    action_id=approved.action_id,
                    capability_id=approved.capability_id,
                    action_name=approved.action_name,
                    input=approved.input,
                    mutation=approved.mutation,
                ),
            ),
        )
    if isinstance(operation, StartActionOperation):
        return (
            EventIntent(
                event_type=CoreEventType.ACTION_STARTED,
                payload=ActionStartedPayload(
                    action_id=operation.action_id,
                    capability_id=operation.capability_id,
                    action_name=operation.action_name,
                ),
            ),
        )
    if isinstance(operation, CompleteActionOperation):
        intents: list[EventIntent] = []
        for artifact in operation.produced_artifacts:
            artifact_metadata: dict[str, object] = {
                "byteLength": artifact.byte_length,
                "sha256": artifact.sha256,
            }
            if isinstance(artifact.content_type, str):
                artifact_metadata["contentType"] = artifact.content_type
            if isinstance(artifact.metadata, JsonObject):
                artifact_metadata["worker"] = artifact.metadata
            frozen_metadata = freeze_json(artifact_metadata)
            assert isinstance(frozen_metadata, JsonObject)
            payload: EventPayload
            if isinstance(artifact.preview, str):
                payload = ArtifactPreviewCreatedPayload(
                    artifact_id=artifact.artifact_id,
                    kind=artifact.kind,
                    metadata=frozen_metadata,
                    content_preview=artifact.preview,
                    hash=artifact.sha256,
                )
            else:
                payload = ArtifactMetadataCreatedPayload(
                    artifact_id=artifact.artifact_id,
                    kind=artifact.kind,
                    metadata=frozen_metadata,
                    hash=artifact.sha256,
                )
            intents.append(EventIntent(event_type=CoreEventType.ARTIFACT_CREATED, payload=payload))
        intents.append(
            EventIntent(
                event_type=CoreEventType.ACTION_COMPLETED,
                payload=ActionCompletedPayload(
                    action_id=operation.action_id,
                    result=operation.result,
                    effects=operation.effects,
                    artifact_ids=operation.artifact_ids,
                ),
            )
        )
        return tuple(intents)
    if isinstance(operation, FailActionOperation):
        return (
            EventIntent(
                event_type=CoreEventType.ACTION_FAILED,
                payload=ActionFailedPayload(
                    action_id=operation.action_id,
                    error=operation.error,
                    effects=operation.effects,
                    evidence=operation.evidence,
                ),
            ),
        )
    if isinstance(operation, CancelActionOperation):
        return (
            EventIntent(
                event_type=CoreEventType.ACTION_CANCELLED,
                payload=ActionCancelledPayload(
                    action_id=operation.action_id,
                    reason=operation.reason,
                ),
            ),
        )
    if isinstance(operation, (GrantCapabilityAuthorityOperation, GrantPolicyAuthorityOperation)):
        authority_id = operation.authority_id
        if not isinstance(authority_id, AuthorityId):
            if authority_ids is None:
                raise ValidationError(code="engine_authority_ids_required")
            authority_id = authority_ids.new_id()
        if isinstance(operation, GrantCapabilityAuthorityOperation):
            authority_payload: EventPayload = CapabilityAuthorityGrantedPayload(
                capability_id=operation.capability_id,
                authority_id=authority_id,
                constraints=operation.constraints,
                granted_by=operation.granted_by,
                metadata=operation.metadata,
            )
        else:
            authority_payload = PolicyAuthorityGrantedPayload(
                rule_id=operation.rule_id,
                rule=operation.rule,
                authority_id=authority_id,
                constraints=operation.constraints,
                granted_by=operation.granted_by,
            )
        return (
            EventIntent(
                event_type=CoreEventType.AUTHORITY_GRANTED,
                payload=authority_payload,
            ),
        )
    if isinstance(operation, RevokeCapabilityAuthorityOperation):
        return (
            EventIntent(
                event_type=CoreEventType.AUTHORITY_REVOKED,
                payload=CapabilityAuthorityRevokedPayload(
                    capability_id=operation.capability_id,
                    authority_id=operation.authority_id,
                    reason=operation.reason,
                ),
            ),
        )
    if isinstance(operation, RevokePolicyAuthorityOperation):
        return (
            EventIntent(
                event_type=CoreEventType.AUTHORITY_REVOKED,
                payload=PolicyAuthorityRevokedPayload(
                    rule_id=operation.rule_id,
                    authority_id=operation.authority_id,
                    reason=operation.reason,
                ),
            ),
        )
    if isinstance(
        operation,
        (CompleteDelegationOperation, FailDelegationOperation, CancelDelegationOperation),
    ):
        if replay is None or delegated_child_replay is None:
            raise ValidationError(code="delegation_handoff_replay_required")
        intents = [
            EventIntent(
                event_type=(
                    CoreEventType.DELEGATION_COMPLETED
                    if isinstance(operation, CompleteDelegationOperation)
                    else CoreEventType.DELEGATION_FAILED
                    if isinstance(operation, FailDelegationOperation)
                    else CoreEventType.DELEGATION_CANCELLED
                ),
                payload=materialize_delegation_handoff(
                    operation,
                    replay,
                    delegated_child_replay,
                ),
            )
        ]
        if (
            replay.views.run_status.status in ("completed", "failed", "cancelled")
            and late_handoff_policy(operation, replay) == "add_to_context"
        ):
            if annotation_ids is None:
                raise ValidationError(code="engine_annotation_ids_required")
            metadata = freeze_json(
                {
                    "kind": "delegation_late_handoff",
                    "delegatedRunId": operation.delegated_run_id.value,
                }
            )
            assert isinstance(metadata, JsonObject)
            intents.append(
                EventIntent(
                    event_type=CoreEventType.ANNOTATION_RECORDED,
                    payload=CanonicalAnnotationRecordedPayload(
                        annotation_id=annotation_ids.new_id(),
                        content_preview=(f"Late handoff from {operation.delegated_run_id.value}"),
                        metadata=metadata,
                    ),
                )
            )
        return tuple(intents)
    if isinstance(operation, MarkActionUnknownOperation):
        if wait_ids is None:
            raise ValidationError(code="engine_wait_ids_required")
        wait_id = wait_ids.new_id()
        return (
            EventIntent(
                event_type=CoreEventType.ACTION_UNKNOWN,
                payload=ActionUnknownPayload(
                    action_id=operation.action_id,
                    reliability=operation.reliability,
                    reason=operation.reason,
                    message=operation.message,
                    note=operation.note,
                    evidence=operation.evidence,
                ),
            ),
            EventIntent(
                event_type=CoreEventType.WAIT_CREATED,
                payload=ReconciliationWaitCreatedPayload(
                    wait_id=wait_id,
                    action_id=operation.action_id,
                    reason=operation.reason,
                ),
            ),
        )
    if isinstance(operation, ReconcileActionOperation):
        if replay is None:
            raise ValidationError(code="reconciliation_replay_required")
        wait = reconciliation_wait(replay, operation.action_id)
        if wait is None:
            raise ValidationError(code="reconciliation_wait_not_found")
        reconciliation_common: dict[str, object] = {
            "action_id": operation.action_id,
            "unknown_event_id": operation.unknown_event_id,
            "command_id": command.command_id,
            "evidence": operation.evidence,
            "note": operation.note,
            "reconciled_by": operation.reconciled_by,
        }
        if operation.outcome == "completed":
            reconciliation_payload: EventPayload = ActionReconciledCompletedPayload(
                **reconciliation_common  # type: ignore[arg-type]
            )
        elif operation.outcome == "failed":
            reconciliation_payload = ActionReconciledFailedPayload(
                **reconciliation_common  # type: ignore[arg-type]
            )
        else:
            reconciliation_payload = ActionReconciledCancelledPayload(
                **reconciliation_common  # type: ignore[arg-type]
            )
        return (
            EventIntent(
                event_type=CoreEventType.ACTION_RECONCILED,
                payload=reconciliation_payload,
            ),
            EventIntent(
                event_type=CoreEventType.WAIT_RESOLVED,
                payload=ReconciliationWaitResolvedPayload(
                    wait_id=wait.wait_id,
                    outcome=operation.outcome,
                ),
            ),
        )
    if isinstance(operation, RecordCheckOperation):
        check_id = operation.check_id
        if not isinstance(check_id, CheckId):
            if check_ids is None:
                raise ValidationError(code="engine_check_ids_required")
            check_id = check_ids.new_id()
        return (
            EventIntent(
                event_type=CoreEventType.CHECK_RECORDED,
                payload=CheckRecordedReportPayload(
                    check_id=check_id,
                    subject=operation.subject,
                    rule=operation.rule,
                    status=operation.status,
                    validator=operation.validator,
                    summary=operation.summary,
                    check_count=operation.check_count,
                    result=operation.result,
                    message=operation.message,
                    evidence=operation.evidence,
                ),
            ),
        )
    if isinstance(operation, CreateCheckpointOperation):
        checkpoint_id = operation.checkpoint_id
        if not isinstance(checkpoint_id, CheckpointId):
            if checkpoint_ids is None:
                raise ValidationError(code="engine_checkpoint_ids_required")
            checkpoint_id = checkpoint_ids.new_id()
        source: Literal["model", "runtime", "operator"]
        if command.origin.value == "model":
            source = "model"
        elif command.origin.value == "operator":
            source = "operator"
        else:
            source = "runtime"
        return (
            EventIntent(
                event_type=CoreEventType.CHECKPOINT_CREATED,
                payload=CheckpointRangeCreatedPayload(
                    checkpoint_id=checkpoint_id,
                    from_position=operation.from_position,
                    to_position=operation.to_position,
                    source=source,
                    summary=operation.summary,
                    retained_context=operation.retained_context,
                    protected_event_types=tuple(
                        CoreEventType(value) for value in operation.protected_event_types
                    ),
                    artifact_ids=operation.artifact_ids,
                ),
            ),
        )
    if isinstance(operation, RecordAnnotationOperation):
        annotation_id = operation.annotation_id
        if not isinstance(annotation_id, AnnotationId):
            if annotation_ids is None:
                raise ValidationError(code="engine_annotation_ids_required")
            annotation_id = annotation_ids.new_id()
        preview = operation.content.preview
        return (
            EventIntent(
                event_type=CoreEventType.ANNOTATION_RECORDED,
                payload=CanonicalAnnotationRecordedPayload(
                    annotation_id=annotation_id,
                    content_preview=preview if isinstance(preview, str) else "",
                    metadata=operation.metadata,
                ),
            ),
        )
    if isinstance(
        operation,
        (
            OpenApprovalWaitOperation,
            OpenInteractionWaitOperation,
            OpenTimerWaitOperation,
            OpenJoinWaitOperation,
        ),
    ):
        wait_id = allocate_wait_id(operation, wait_ids)
        return (
            EventIntent(
                event_type=CoreEventType.WAIT_CREATED,
                payload=materialize_wait_request(operation, wait_id),
            ),
        )
    if isinstance(
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
        if replay is None or now is None:
            raise ValidationError(code="wait_materialization_context_required")
        if isinstance(operation, CancelWaitOperation):
            event_type = CoreEventType.WAIT_CANCELLED
        elif isinstance(operation, ExpireWaitOperation):
            event_type = CoreEventType.WAIT_EXPIRED
        else:
            event_type = CoreEventType.WAIT_RESOLVED
        return (
            EventIntent(
                event_type=event_type,
                payload=materialize_wait_terminal(operation, replay, now, governance),
            ),
        )
    raise ValidationError(code="accepted_operation_not_materializable")


def materialize_deferred_approval(
    operation: CreateActionOperation,
    wait_id: WaitId,
    replay: CompleteViewReplay[RunViewBundle],
) -> EventIntent:
    """Build the sole target fact appended for a policy-deferred Action."""

    from openrund.engine._governance import approval_wait_payload

    payload: ApprovalWaitCreatedPayload = approval_wait_payload(operation, wait_id, replay)
    return EventIntent(event_type=CoreEventType.WAIT_CREATED, payload=payload)
