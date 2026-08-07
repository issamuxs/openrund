"""Exhaustive immutable semantic Event grammar for OpenRund v1."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from enum import StrEnum
from types import MappingProxyType
from typing import Literal, cast, final

from openrund.contracts.capabilities import ActionFailure as ActionFailure
from openrund.contracts.capabilities import ActionReliability
from openrund.contracts.commands import CommandDecisionRecord
from openrund.contracts.content import Content, EffectEntry, Mutation, RunResult
from openrund.contracts.ids import (
    ActionId,
    AnnotationId,
    ArtifactId,
    AuthorityId,
    CapabilityId,
    CheckId,
    CheckpointId,
    CommandId,
    CorrelationId,
    DelegationId,
    EventId,
    LeaseId,
    MessageId,
    ModelCallId,
    PolicyRuleId,
    RunId,
    WaitId,
)
from openrund.contracts.json import MISSING, JsonObject, MissingType, freeze_json
from openrund.contracts.runs import (
    CheckStatus,
    DelegationContract,
    DelegationInput,
    DelegationJoinMode,
    WaitKind,
)
from openrund.contracts.time import Timestamp
from openrund.errors import ValidationError

_MAX_SAFE_INTEGER = 9_007_199_254_740_991


def _required_text(value: object, code: str) -> str:
    if not isinstance(value, str) or value == "":
        raise ValidationError(code=code)
    return value


def _optional_text(value: object, code: str) -> str | MissingType | None:
    if value is MISSING or value is None:
        return value
    if not isinstance(value, str):
        raise ValidationError(code=code)
    return value


def _optional_bool(value: object, code: str) -> bool | MissingType | None:
    if value is MISSING or value is None:
        return value
    if not isinstance(value, bool):
        raise ValidationError(code=code)
    return value


def _optional_object(value: object, code: str) -> JsonObject | MissingType | None:
    if value is MISSING or value is None:
        return value
    frozen = freeze_json(value)
    if not isinstance(frozen, JsonObject):
        raise ValidationError(code=code)
    return frozen


def _required_object(value: object, code: str) -> JsonObject:
    frozen = freeze_json(value)
    if not isinstance(frozen, JsonObject):
        raise ValidationError(code=code)
    return frozen


def _typed_tuple[U](value: object, expected: type[U], code: str) -> tuple[U, ...]:
    try:
        items: tuple[object, ...] = tuple(value)  # type: ignore[arg-type]
    except TypeError as error:
        raise ValidationError(code=code) from error
    if any(not isinstance(item, expected) for item in items):
        raise ValidationError(code=code)
    return cast(tuple[U, ...], items)


def _text_tuple(value: object, code: str) -> tuple[str, ...]:
    items = _typed_tuple(value, str, code)
    if any(item == "" for item in items):
        raise ValidationError(code=code)
    return items


def _optional_instance[U](value: object, expected: type[U], code: str) -> U | MissingType | None:
    if value is MISSING or value is None:
        return value
    if not isinstance(value, expected):
        raise ValidationError(code=code)
    return value


def _safe_position(value: object, code: str, *, minimum: int = 0) -> int:
    if (
        not isinstance(value, int)
        or isinstance(value, bool)
        or not minimum <= value <= _MAX_SAFE_INTEGER
    ):
        raise ValidationError(code=code)
    return value


class EventActor(StrEnum):
    SYSTEM = "system"
    ASSISTANT = "assistant"
    USER = "user"
    CAPABILITY = "capability"
    CLIENT = "client"
    OPERATOR = "operator"


class CoreEventType(StrEnum):
    RUN_CREATED = "run.created"
    RUN_STARTED = "run.started"
    RUN_COMPLETED = "run.completed"
    RUN_FAILED = "run.failed"
    RUN_CANCELLED = "run.cancelled"
    COMMAND_RECORDED = "command.recorded"
    MESSAGE_ADDED = "message.added"
    MESSAGE_DELTA = "message.delta"
    MODEL_CALL_STARTED = "model_call.started"
    MODEL_CALL_COMPLETED = "model_call.completed"
    MODEL_CALL_FAILED = "model_call.failed"
    MODEL_CALL_CANCELLED = "model_call.cancelled"
    ACTION_CREATED = "action.created"
    ACTION_STARTED = "action.started"
    ACTION_COMPLETED = "action.completed"
    ACTION_FAILED = "action.failed"
    ACTION_CANCELLED = "action.cancelled"
    ACTION_UNKNOWN = "action.unknown"
    ACTION_RECONCILED = "action.reconciled"
    WAIT_CREATED = "wait.created"
    WAIT_RESOLVED = "wait.resolved"
    WAIT_CANCELLED = "wait.cancelled"
    WAIT_EXPIRED = "wait.expired"
    DELEGATION_CREATED = "delegation.created"
    DELEGATION_COMPLETED = "delegation.completed"
    DELEGATION_FAILED = "delegation.failed"
    DELEGATION_CANCELLED = "delegation.cancelled"
    CHECK_RECORDED = "check.recorded"
    CHECKPOINT_CREATED = "checkpoint.created"
    ANNOTATION_RECORDED = "annotation.recorded"
    ARTIFACT_CREATED = "artifact.created"
    ARTIFACT_UNAVAILABLE = "artifact.unavailable"
    AUTHORITY_GRANTED = "authority.granted"
    AUTHORITY_REVOKED = "authority.revoked"
    LEASE_ACQUIRED = "lease.acquired"
    LEASE_RELEASED = "lease.released"
    LEASE_EXPIRED = "lease.expired"


CORE_EVENT_TYPES: tuple[CoreEventType, ...] = tuple(CoreEventType)


@final
@dataclass(frozen=True, slots=True, kw_only=True)
class RunCreatedPayload:
    root_id: RunId
    initial_status: Literal["created"]
    parent_run_id: RunId | MissingType | None = MISSING
    title: str | MissingType | None = MISSING
    objective: str | MissingType | None = MISSING
    metadata: JsonObject | MissingType | None = MISSING

    def __post_init__(self) -> None:
        if not isinstance(self.root_id, RunId):
            raise ValidationError(code="run_created_root_id_invalid")
        if self.initial_status != "created":
            raise ValidationError(code="run_created_status_invalid")
        object.__setattr__(
            self,
            "parent_run_id",
            _optional_instance(self.parent_run_id, RunId, "run_created_parent_id_invalid"),
        )
        object.__setattr__(self, "title", _optional_text(self.title, "run_created_title_invalid"))
        object.__setattr__(
            self,
            "objective",
            _optional_text(self.objective, "run_created_objective_invalid"),
        )
        object.__setattr__(
            self,
            "metadata",
            _optional_object(self.metadata, "run_created_metadata_invalid"),
        )


@final
@dataclass(frozen=True, slots=True, kw_only=True)
class RunStartedPayload:
    reason: str | MissingType | None = MISSING

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "reason", _optional_text(self.reason, "run_started_reason_invalid")
        )


@final
@dataclass(frozen=True, slots=True, kw_only=True)
class RunCompletedPayload:
    result: RunResult | MissingType | None = MISSING
    annotation: Content | MissingType | None = MISSING
    artifact_ids: tuple[ArtifactId, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "result",
            _optional_instance(self.result, RunResult, "run_completed_result_invalid"),
        )
        object.__setattr__(
            self,
            "annotation",
            _optional_instance(self.annotation, Content, "run_completed_annotation_invalid"),
        )
        object.__setattr__(
            self,
            "artifact_ids",
            _typed_tuple(self.artifact_ids, ArtifactId, "run_completed_artifact_ids_invalid"),
        )


@final
@dataclass(frozen=True, slots=True, kw_only=True)
class RunFailedPayload:
    message: str
    retryable: bool | MissingType | None = MISSING
    evidence: Content | MissingType | None = MISSING

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "message", _required_text(self.message, "run_failed_message_invalid")
        )
        object.__setattr__(
            self,
            "retryable",
            _optional_bool(self.retryable, "run_failed_retryable_invalid"),
        )
        object.__setattr__(
            self,
            "evidence",
            _optional_instance(self.evidence, Content, "run_failed_evidence_invalid"),
        )


@final
@dataclass(frozen=True, slots=True, kw_only=True)
class RunCancelledPayload:
    reason: str | MissingType | None = MISSING

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "reason", _optional_text(self.reason, "run_cancelled_reason_invalid")
        )


@dataclass(frozen=True, slots=True, kw_only=True)
class _CommandRecordedPayload:
    command_id: CommandId
    decision_record: CommandDecisionRecord
    operation: str
    content_hash: str
    content: Content
    origin_actor: str | MissingType | None = MISSING
    provider: str | MissingType | None = MISSING
    model_call_id: ModelCallId | MissingType | None = MISSING
    metadata: JsonObject | MissingType | None = MISSING

    def __post_init__(self) -> None:
        if not isinstance(self.command_id, CommandId):
            raise ValidationError(code="command_recorded_id_invalid")
        if not isinstance(self.decision_record, CommandDecisionRecord):
            raise ValidationError(code="command_recorded_decision_invalid")
        if self.decision_record.command_id != self.command_id:
            raise ValidationError(code="command_recorded_decision_id_mismatch")
        object.__setattr__(
            self,
            "operation",
            _required_text(self.operation, "command_recorded_operation_invalid"),
        )
        object.__setattr__(
            self,
            "content_hash",
            _required_text(self.content_hash, "command_recorded_hash_invalid"),
        )
        if not isinstance(self.content, Content):
            raise ValidationError(code="command_recorded_content_invalid")
        object.__setattr__(
            self,
            "origin_actor",
            _optional_text(self.origin_actor, "command_recorded_actor_invalid"),
        )
        object.__setattr__(
            self,
            "provider",
            _optional_text(self.provider, "command_recorded_provider_invalid"),
        )
        object.__setattr__(
            self,
            "model_call_id",
            _optional_instance(
                self.model_call_id, ModelCallId, "command_recorded_model_call_id_invalid"
            ),
        )
        object.__setattr__(
            self,
            "metadata",
            _optional_object(self.metadata, "command_recorded_metadata_invalid"),
        )


@final
@dataclass(frozen=True, slots=True, kw_only=True)
class ModelCommandRecordedPayload(_CommandRecordedPayload):
    origin_type: Literal["model"] = "model"

    def __post_init__(self) -> None:
        super(ModelCommandRecordedPayload, self).__post_init__()
        if self.origin_type != "model":
            raise ValidationError(code="command_recorded_origin_invalid")


@final
@dataclass(frozen=True, slots=True, kw_only=True)
class RuntimeCommandRecordedPayload(_CommandRecordedPayload):
    origin_type: Literal["runtime"] = "runtime"

    def __post_init__(self) -> None:
        super(RuntimeCommandRecordedPayload, self).__post_init__()
        if self.origin_type != "runtime":
            raise ValidationError(code="command_recorded_origin_invalid")


@final
@dataclass(frozen=True, slots=True, kw_only=True)
class CanonicalMessageAddedPayload:
    message_id: MessageId
    content_preview: str
    artifact_ids: tuple[ArtifactId, ...] = ()
    metadata: JsonObject | MissingType | None = MISSING

    def __post_init__(self) -> None:
        if not isinstance(self.message_id, MessageId):
            raise ValidationError(code="message_added_id_invalid")
        if not isinstance(self.content_preview, str):
            raise ValidationError(code="message_added_preview_invalid")
        object.__setattr__(
            self,
            "artifact_ids",
            _typed_tuple(self.artifact_ids, ArtifactId, "message_added_artifact_ids_invalid"),
        )
        object.__setattr__(
            self,
            "metadata",
            _optional_object(self.metadata, "message_added_metadata_invalid"),
        )


@final
@dataclass(frozen=True, slots=True, kw_only=True)
class LegacyPreviewMessageAddedPayload:
    """Historical content-shaped branch; the frozen variant label is `content`."""

    message_id: MessageId
    direction: Literal["inbound", "outbound", "internal"]
    source: Literal["user", "client", "assistant", "system", "external", "capability", "model"]
    content: Content
    role: str | MissingType | None = MISSING

    def __post_init__(self) -> None:
        if not isinstance(self.message_id, MessageId):
            raise ValidationError(code="message_added_id_invalid")
        if self.direction not in ("inbound", "outbound", "internal"):
            raise ValidationError(code="message_added_direction_invalid")
        if self.source not in (
            "user",
            "client",
            "assistant",
            "system",
            "external",
            "capability",
            "model",
        ):
            raise ValidationError(code="message_added_source_invalid")
        if not isinstance(self.content, Content):
            raise ValidationError(code="message_added_content_invalid")
        object.__setattr__(self, "role", _optional_text(self.role, "message_added_role_invalid"))


type MessageAddedPayload = CanonicalMessageAddedPayload | LegacyPreviewMessageAddedPayload


@final
@dataclass(frozen=True, slots=True, kw_only=True)
class MessageDeltaPayload:
    message_id: MessageId
    delta: str

    def __post_init__(self) -> None:
        if not isinstance(self.message_id, MessageId):
            raise ValidationError(code="message_delta_id_invalid")
        if not isinstance(self.delta, str):
            raise ValidationError(code="message_delta_invalid")


@final
@dataclass(frozen=True, slots=True, kw_only=True)
class CanonicalAnnotationRecordedPayload:
    annotation_id: AnnotationId
    content_preview: str
    metadata: JsonObject | MissingType | None = MISSING

    def __post_init__(self) -> None:
        if not isinstance(self.annotation_id, AnnotationId):
            raise ValidationError(code="annotation_recorded_id_invalid")
        if not isinstance(self.content_preview, str):
            raise ValidationError(code="annotation_recorded_preview_invalid")
        object.__setattr__(
            self,
            "metadata",
            _optional_object(self.metadata, "annotation_recorded_metadata_invalid"),
        )


@final
@dataclass(frozen=True, slots=True, kw_only=True)
class LegacyPreviewAnnotationRecordedPayload:
    """Historical content-shaped branch; the frozen variant label is `content`."""

    annotation_id: AnnotationId
    content: Content

    def __post_init__(self) -> None:
        if not isinstance(self.annotation_id, AnnotationId):
            raise ValidationError(code="annotation_recorded_id_invalid")
        if not isinstance(self.content, Content):
            raise ValidationError(code="annotation_recorded_content_invalid")


type AnnotationRecordedPayload = (
    CanonicalAnnotationRecordedPayload | LegacyPreviewAnnotationRecordedPayload
)


@final
@dataclass(frozen=True, slots=True, kw_only=True)
class ModelCallStartedPayload:
    model_call_id: ModelCallId

    def __post_init__(self) -> None:
        if not isinstance(self.model_call_id, ModelCallId):
            raise ValidationError(code="model_call_started_id_invalid")


@final
@dataclass(frozen=True, slots=True, kw_only=True)
class ModelCallCompletedPayload:
    model_call_id: ModelCallId
    outcome: str
    metadata: JsonObject | MissingType | None = MISSING

    def __post_init__(self) -> None:
        if not isinstance(self.model_call_id, ModelCallId):
            raise ValidationError(code="model_call_completed_id_invalid")
        object.__setattr__(
            self,
            "outcome",
            _required_text(self.outcome, "model_call_completed_outcome_invalid"),
        )
        object.__setattr__(
            self,
            "metadata",
            _optional_object(self.metadata, "model_call_completed_metadata_invalid"),
        )


@final
@dataclass(frozen=True, slots=True, kw_only=True)
class ModelCallFailedPayload:
    model_call_id: ModelCallId
    message: str
    classification: str | MissingType | None = MISSING
    retryable: bool | MissingType | None = MISSING
    evidence: Content | MissingType | None = MISSING

    def __post_init__(self) -> None:
        if not isinstance(self.model_call_id, ModelCallId):
            raise ValidationError(code="model_call_failed_id_invalid")
        object.__setattr__(
            self,
            "message",
            _required_text(self.message, "model_call_failed_message_invalid"),
        )
        object.__setattr__(
            self,
            "classification",
            _optional_text(self.classification, "model_call_failed_classification_invalid"),
        )
        object.__setattr__(
            self,
            "retryable",
            _optional_bool(self.retryable, "model_call_failed_retryable_invalid"),
        )
        object.__setattr__(
            self,
            "evidence",
            _optional_instance(self.evidence, Content, "model_call_failed_evidence_invalid"),
        )


@final
@dataclass(frozen=True, slots=True, kw_only=True)
class ModelCallCancelledPayload:
    model_call_id: ModelCallId
    reason: str | MissingType | None = MISSING

    def __post_init__(self) -> None:
        if not isinstance(self.model_call_id, ModelCallId):
            raise ValidationError(code="model_call_cancelled_id_invalid")
        object.__setattr__(
            self,
            "reason",
            _optional_text(self.reason, "model_call_cancelled_reason_invalid"),
        )


@final
@dataclass(frozen=True, slots=True, kw_only=True)
class ActionCreatedPayload:
    action_id: ActionId
    capability_id: CapabilityId
    action_name: str
    input: Content
    mutation: Mutation | MissingType | None = MISSING

    def __post_init__(self) -> None:
        if not isinstance(self.action_id, ActionId):
            raise ValidationError(code="action_created_id_invalid")
        if not isinstance(self.capability_id, CapabilityId):
            raise ValidationError(code="action_created_capability_id_invalid")
        object.__setattr__(
            self,
            "action_name",
            _required_text(self.action_name, "action_created_name_invalid"),
        )
        if not isinstance(self.input, Content):
            raise ValidationError(code="action_created_input_invalid")
        object.__setattr__(
            self,
            "mutation",
            _optional_instance(self.mutation, Mutation, "action_created_mutation_invalid"),
        )


@final
@dataclass(frozen=True, slots=True, kw_only=True)
class ActionStartedPayload:
    action_id: ActionId
    capability_id: CapabilityId
    action_name: str

    def __post_init__(self) -> None:
        if not isinstance(self.action_id, ActionId):
            raise ValidationError(code="action_started_id_invalid")
        if not isinstance(self.capability_id, CapabilityId):
            raise ValidationError(code="action_started_capability_id_invalid")
        object.__setattr__(
            self,
            "action_name",
            _required_text(self.action_name, "action_started_name_invalid"),
        )


@final
@dataclass(frozen=True, slots=True, kw_only=True)
class ActionCompletedPayload:
    action_id: ActionId
    result: Content | MissingType | None = MISSING
    effects: tuple[EffectEntry, ...] = ()
    artifact_ids: tuple[ArtifactId, ...] = ()

    def __post_init__(self) -> None:
        if not isinstance(self.action_id, ActionId):
            raise ValidationError(code="action_completed_id_invalid")
        object.__setattr__(
            self,
            "result",
            _optional_instance(self.result, Content, "action_completed_result_invalid"),
        )
        object.__setattr__(
            self,
            "effects",
            _typed_tuple(self.effects, EffectEntry, "action_completed_effects_invalid"),
        )
        object.__setattr__(
            self,
            "artifact_ids",
            _typed_tuple(self.artifact_ids, ArtifactId, "action_completed_artifact_ids_invalid"),
        )


@final
@dataclass(frozen=True, slots=True, kw_only=True)
class ActionFailedPayload:
    action_id: ActionId
    error: ActionFailure
    effects: tuple[EffectEntry, ...] = ()
    evidence: Content | MissingType | None = MISSING

    def __post_init__(self) -> None:
        if not isinstance(self.action_id, ActionId):
            raise ValidationError(code="action_failed_id_invalid")
        if not isinstance(self.error, ActionFailure):
            raise ValidationError(code="action_failed_error_invalid")
        object.__setattr__(
            self,
            "effects",
            _typed_tuple(self.effects, EffectEntry, "action_failed_effects_invalid"),
        )
        object.__setattr__(
            self,
            "evidence",
            _optional_instance(self.evidence, Content, "action_failed_evidence_invalid"),
        )


@final
@dataclass(frozen=True, slots=True, kw_only=True)
class ActionCancelledPayload:
    action_id: ActionId
    reason: str | MissingType | None = MISSING

    def __post_init__(self) -> None:
        if not isinstance(self.action_id, ActionId):
            raise ValidationError(code="action_cancelled_id_invalid")
        object.__setattr__(
            self,
            "reason",
            _optional_text(self.reason, "action_cancelled_reason_invalid"),
        )


@final
@dataclass(frozen=True, slots=True, kw_only=True)
class ActionUnknownPayload:
    action_id: ActionId
    reliability: ActionReliability
    reason: str
    message: str | MissingType | None = MISSING
    note: Content | MissingType | None = MISSING
    evidence: Content | MissingType | None = MISSING

    def __post_init__(self) -> None:
        if not isinstance(self.action_id, ActionId):
            raise ValidationError(code="action_unknown_id_invalid")
        if not isinstance(self.reliability, ActionReliability):
            raise ValidationError(code="action_unknown_reliability_invalid")
        object.__setattr__(
            self, "reason", _required_text(self.reason, "action_unknown_reason_invalid")
        )
        object.__setattr__(
            self,
            "message",
            _optional_text(self.message, "action_unknown_message_invalid"),
        )
        object.__setattr__(
            self, "note", _optional_instance(self.note, Content, "action_unknown_note_invalid")
        )
        object.__setattr__(
            self,
            "evidence",
            _optional_instance(self.evidence, Content, "action_unknown_evidence_invalid"),
        )


@dataclass(frozen=True, slots=True, kw_only=True)
class _ActionReconciledPayload:
    action_id: ActionId
    unknown_event_id: EventId
    command_id: CommandId | MissingType | None = MISSING
    evidence: Content | MissingType | None = MISSING
    note: Content | MissingType | None = MISSING
    reconciled_by: str | MissingType | None = MISSING

    def __post_init__(self) -> None:
        if not isinstance(self.action_id, ActionId):
            raise ValidationError(code="action_reconciled_id_invalid")
        if not isinstance(self.unknown_event_id, EventId):
            raise ValidationError(code="action_reconciled_unknown_event_id_invalid")
        object.__setattr__(
            self,
            "command_id",
            _optional_instance(self.command_id, CommandId, "action_reconciled_command_id_invalid"),
        )
        object.__setattr__(
            self,
            "evidence",
            _optional_instance(self.evidence, Content, "action_reconciled_evidence_invalid"),
        )
        object.__setattr__(
            self,
            "note",
            _optional_instance(self.note, Content, "action_reconciled_note_invalid"),
        )
        object.__setattr__(
            self,
            "reconciled_by",
            _optional_text(self.reconciled_by, "action_reconciled_actor_invalid"),
        )


@final
@dataclass(frozen=True, slots=True, kw_only=True)
class ActionReconciledCompletedPayload(_ActionReconciledPayload):
    outcome: Literal["completed"] = "completed"

    def __post_init__(self) -> None:
        super(ActionReconciledCompletedPayload, self).__post_init__()
        if self.outcome != "completed":
            raise ValidationError(code="action_reconciled_outcome_invalid")


@final
@dataclass(frozen=True, slots=True, kw_only=True)
class ActionReconciledFailedPayload(_ActionReconciledPayload):
    outcome: Literal["failed"] = "failed"

    def __post_init__(self) -> None:
        super(ActionReconciledFailedPayload, self).__post_init__()
        if self.outcome != "failed":
            raise ValidationError(code="action_reconciled_outcome_invalid")


@final
@dataclass(frozen=True, slots=True, kw_only=True)
class ActionReconciledCancelledPayload(_ActionReconciledPayload):
    outcome: Literal["cancelled"] = "cancelled"

    def __post_init__(self) -> None:
        super(ActionReconciledCancelledPayload, self).__post_init__()
        if self.outcome != "cancelled":
            raise ValidationError(code="action_reconciled_outcome_invalid")


@final
@dataclass(frozen=True, slots=True, kw_only=True)
class WaitReference:
    wait_id: WaitId
    kind: WaitKind

    def __post_init__(self) -> None:
        if not isinstance(self.wait_id, WaitId):
            raise ValidationError(code="wait_reference_id_invalid")
        if not isinstance(self.kind, WaitKind):
            raise ValidationError(code="wait_reference_kind_invalid")


@final
@dataclass(frozen=True, slots=True, kw_only=True)
class AggregateWaitCreatedPayload:
    waiting_on: tuple[WaitReference, ...]
    reason: str | MissingType | None = MISSING

    def __post_init__(self) -> None:
        waiting_on = _typed_tuple(
            self.waiting_on, WaitReference, "aggregate_wait_references_invalid"
        )
        if not waiting_on:
            raise ValidationError(code="aggregate_wait_references_invalid")
        object.__setattr__(self, "waiting_on", waiting_on)
        object.__setattr__(
            self,
            "reason",
            _optional_text(self.reason, "aggregate_wait_reason_invalid"),
        )


@final
@dataclass(frozen=True, slots=True, kw_only=True)
class ApprovalWaitCreatedPayload:
    wait_id: WaitId
    action_id: ActionId
    capability_id: CapabilityId
    action_name: str
    request_payload: Content
    policy_snapshot: Content
    target: str | MissingType | None = MISSING
    reason: str | MissingType | None = MISSING
    deadline: Timestamp | MissingType | None = MISSING
    kind: Literal[WaitKind.APPROVAL] = WaitKind.APPROVAL

    def __post_init__(self) -> None:
        if self.kind is not WaitKind.APPROVAL:
            raise ValidationError(code="wait_payload_kind_invalid")
        if not isinstance(self.wait_id, WaitId):
            raise ValidationError(code="wait_payload_id_invalid")
        if not isinstance(self.action_id, ActionId):
            raise ValidationError(code="approval_wait_action_id_invalid")
        if not isinstance(self.capability_id, CapabilityId):
            raise ValidationError(code="approval_wait_capability_id_invalid")
        object.__setattr__(
            self,
            "action_name",
            _required_text(self.action_name, "approval_wait_action_name_invalid"),
        )
        if not isinstance(self.request_payload, Content):
            raise ValidationError(code="approval_wait_request_invalid")
        if not isinstance(self.policy_snapshot, Content):
            raise ValidationError(code="approval_wait_policy_invalid")
        object.__setattr__(
            self, "target", _optional_text(self.target, "approval_wait_target_invalid")
        )
        object.__setattr__(
            self, "reason", _optional_text(self.reason, "approval_wait_reason_invalid")
        )
        object.__setattr__(
            self,
            "deadline",
            _optional_instance(self.deadline, Timestamp, "approval_wait_deadline_invalid"),
        )


@final
@dataclass(frozen=True, slots=True, kw_only=True)
class InteractionWaitCreatedPayload:
    wait_id: WaitId
    prompt: Content
    reason: str | MissingType | None = MISSING
    deadline: Timestamp | MissingType | None = MISSING
    kind: Literal[WaitKind.INTERACTION] = WaitKind.INTERACTION

    def __post_init__(self) -> None:
        if self.kind is not WaitKind.INTERACTION:
            raise ValidationError(code="wait_payload_kind_invalid")
        if not isinstance(self.wait_id, WaitId):
            raise ValidationError(code="wait_payload_id_invalid")
        if not isinstance(self.prompt, Content):
            raise ValidationError(code="interaction_wait_prompt_invalid")
        object.__setattr__(
            self,
            "reason",
            _optional_text(self.reason, "interaction_wait_reason_invalid"),
        )
        object.__setattr__(
            self,
            "deadline",
            _optional_instance(self.deadline, Timestamp, "interaction_wait_deadline_invalid"),
        )


@final
@dataclass(frozen=True, slots=True, kw_only=True)
class TimerWaitCreatedPayload:
    wait_id: WaitId
    fire_at: Timestamp
    reason: str | MissingType | None = MISSING
    kind: Literal[WaitKind.TIMER] = WaitKind.TIMER

    def __post_init__(self) -> None:
        if self.kind is not WaitKind.TIMER:
            raise ValidationError(code="wait_payload_kind_invalid")
        if not isinstance(self.wait_id, WaitId):
            raise ValidationError(code="wait_payload_id_invalid")
        if not isinstance(self.fire_at, Timestamp):
            raise ValidationError(code="timer_wait_fire_at_invalid")
        object.__setattr__(self, "reason", _optional_text(self.reason, "timer_wait_reason_invalid"))


@final
@dataclass(frozen=True, slots=True, kw_only=True)
class JoinWaitCreatedPayload:
    wait_id: WaitId
    target_run_ids: tuple[RunId, ...]
    mode: DelegationJoinMode
    outcome_filter: Literal["completed_only", "terminal_any", "completed_or_failed"]
    failure_policy: Literal["fail_fast", "wait_for_all_terminal"]
    on_satisfied: Literal["cancel_remaining", "detach_remaining", "keep_bound"]
    late_handoff_policy: Literal["ignore", "surface", "add_to_context"]
    quorum: int | MissingType | None = MISSING
    reason: str | MissingType | None = MISSING
    kind: Literal[WaitKind.JOIN] = WaitKind.JOIN

    def __post_init__(self) -> None:
        if self.kind is not WaitKind.JOIN:
            raise ValidationError(code="wait_payload_kind_invalid")
        if not isinstance(self.wait_id, WaitId):
            raise ValidationError(code="wait_payload_id_invalid")
        targets = _typed_tuple(self.target_run_ids, RunId, "join_wait_target_ids_invalid")
        if not targets or len(set(targets)) != len(targets):
            raise ValidationError(code="join_wait_target_ids_invalid")
        object.__setattr__(self, "target_run_ids", targets)
        if not isinstance(self.mode, DelegationJoinMode):
            raise ValidationError(code="join_wait_mode_invalid")
        if self.outcome_filter not in (
            "completed_only",
            "terminal_any",
            "completed_or_failed",
        ):
            raise ValidationError(code="join_wait_outcome_filter_invalid")
        if self.failure_policy not in ("fail_fast", "wait_for_all_terminal"):
            raise ValidationError(code="join_wait_failure_policy_invalid")
        if self.on_satisfied not in (
            "cancel_remaining",
            "detach_remaining",
            "keep_bound",
        ):
            raise ValidationError(code="join_wait_satisfied_policy_invalid")
        if self.late_handoff_policy not in ("ignore", "surface", "add_to_context"):
            raise ValidationError(code="join_wait_handoff_policy_invalid")
        if self.mode is DelegationJoinMode.QUORUM:
            if (
                not isinstance(self.quorum, int)
                or isinstance(self.quorum, bool)
                or not 1 <= self.quorum <= len(targets)
            ):
                raise ValidationError(code="join_wait_quorum_invalid")
        elif self.quorum not in (MISSING, None):
            raise ValidationError(code="join_wait_quorum_forbidden")
        object.__setattr__(self, "reason", _optional_text(self.reason, "join_wait_reason_invalid"))


@final
@dataclass(frozen=True, slots=True, kw_only=True)
class ReconciliationWaitCreatedPayload:
    wait_id: WaitId
    action_id: ActionId | MissingType | None = MISSING
    reason: str | MissingType | None = MISSING
    kind: Literal[WaitKind.RECONCILIATION] = WaitKind.RECONCILIATION

    def __post_init__(self) -> None:
        if self.kind is not WaitKind.RECONCILIATION:
            raise ValidationError(code="wait_payload_kind_invalid")
        if not isinstance(self.wait_id, WaitId):
            raise ValidationError(code="wait_payload_id_invalid")
        object.__setattr__(
            self,
            "action_id",
            _optional_instance(self.action_id, ActionId, "reconciliation_wait_action_id_invalid"),
        )
        object.__setattr__(
            self,
            "reason",
            _optional_text(self.reason, "reconciliation_wait_reason_invalid"),
        )


@final
@dataclass(frozen=True, slots=True, kw_only=True)
class AggregateWaitResolvedPayload:
    resumed_from: str
    trigger_event_id: EventId
    kind: WaitKind | MissingType | None = MISSING

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "resumed_from",
            _required_text(self.resumed_from, "aggregate_wait_resumed_from_invalid"),
        )
        if not isinstance(self.trigger_event_id, EventId):
            raise ValidationError(code="aggregate_wait_trigger_event_id_invalid")
        if self.kind not in (MISSING, None) and not isinstance(self.kind, WaitKind):
            raise ValidationError(code="aggregate_wait_kind_invalid")


@final
@dataclass(frozen=True, slots=True, kw_only=True)
class ApprovalWaitResolvedPayload:
    wait_id: WaitId
    decision: Literal["approved", "denied", "cancelled", "expired", "resolved"]
    approved_input: JsonObject | MissingType | None = MISSING
    approved_input_validation: JsonObject | MissingType | None = MISSING
    note: Content | MissingType | None = MISSING
    resolved_by: str | MissingType | None = MISSING
    kind: Literal[WaitKind.APPROVAL] = WaitKind.APPROVAL

    def __post_init__(self) -> None:
        if self.kind is not WaitKind.APPROVAL:
            raise ValidationError(code="wait_payload_kind_invalid")
        if not isinstance(self.wait_id, WaitId):
            raise ValidationError(code="wait_payload_id_invalid")
        if self.decision not in (
            "approved",
            "denied",
            "cancelled",
            "expired",
            "resolved",
        ):
            raise ValidationError(code="approval_wait_decision_invalid")
        object.__setattr__(
            self,
            "approved_input",
            _optional_object(self.approved_input, "approval_wait_input_invalid"),
        )
        object.__setattr__(
            self,
            "approved_input_validation",
            _optional_object(
                self.approved_input_validation,
                "approval_wait_input_validation_invalid",
            ),
        )
        object.__setattr__(
            self,
            "note",
            _optional_instance(self.note, Content, "approval_wait_note_invalid"),
        )
        object.__setattr__(
            self,
            "resolved_by",
            _optional_text(self.resolved_by, "approval_wait_resolver_invalid"),
        )


@final
@dataclass(frozen=True, slots=True, kw_only=True)
class InteractionWaitResolvedPayload:
    wait_id: WaitId
    response: Content
    request_event_id: EventId | MissingType | None = MISSING
    responded_by: str | MissingType | None = MISSING
    kind: Literal[WaitKind.INTERACTION] = WaitKind.INTERACTION

    def __post_init__(self) -> None:
        if self.kind is not WaitKind.INTERACTION:
            raise ValidationError(code="wait_payload_kind_invalid")
        if not isinstance(self.wait_id, WaitId):
            raise ValidationError(code="wait_payload_id_invalid")
        if not isinstance(self.response, Content):
            raise ValidationError(code="interaction_wait_response_invalid")
        object.__setattr__(
            self,
            "request_event_id",
            _optional_instance(
                self.request_event_id,
                EventId,
                "interaction_wait_request_event_id_invalid",
            ),
        )
        object.__setattr__(
            self,
            "responded_by",
            _optional_text(self.responded_by, "interaction_wait_responder_invalid"),
        )


@final
@dataclass(frozen=True, slots=True, kw_only=True)
class TimerWaitResolvedPayload:
    wait_id: WaitId
    fired_at: Timestamp
    scheduled_for: Timestamp | MissingType | None = MISSING
    fired_by: str | MissingType | None = MISSING
    kind: Literal[WaitKind.TIMER] = WaitKind.TIMER

    def __post_init__(self) -> None:
        if self.kind is not WaitKind.TIMER:
            raise ValidationError(code="wait_payload_kind_invalid")
        if not isinstance(self.wait_id, WaitId):
            raise ValidationError(code="wait_payload_id_invalid")
        if not isinstance(self.fired_at, Timestamp):
            raise ValidationError(code="timer_wait_fired_at_invalid")
        object.__setattr__(
            self,
            "scheduled_for",
            _optional_instance(self.scheduled_for, Timestamp, "timer_wait_scheduled_for_invalid"),
        )
        object.__setattr__(
            self,
            "fired_by",
            _optional_text(self.fired_by, "timer_wait_fired_by_invalid"),
        )


@final
@dataclass(frozen=True, slots=True, kw_only=True)
class JoinWaitResolvedPayload:
    wait_id: WaitId
    target_run_ids: tuple[RunId, ...]
    mode: DelegationJoinMode
    completed_run_ids: tuple[RunId, ...]
    terminal_run_ids: tuple[RunId, ...] = ()
    quorum: int | MissingType | None = MISSING
    on_satisfied: (
        Literal["cancel_remaining", "detach_remaining", "keep_bound"] | MissingType | None
    ) = MISSING
    kind: Literal[WaitKind.JOIN] = WaitKind.JOIN

    def __post_init__(self) -> None:
        if self.kind is not WaitKind.JOIN:
            raise ValidationError(code="wait_payload_kind_invalid")
        if not isinstance(self.wait_id, WaitId):
            raise ValidationError(code="wait_payload_id_invalid")
        targets = _typed_tuple(self.target_run_ids, RunId, "join_wait_target_ids_invalid")
        completed = _typed_tuple(self.completed_run_ids, RunId, "join_wait_completed_ids_invalid")
        terminal = _typed_tuple(self.terminal_run_ids, RunId, "join_wait_terminal_ids_invalid")
        if not targets or any(item not in targets for item in completed + terminal):
            raise ValidationError(code="join_wait_result_ids_invalid")
        object.__setattr__(self, "target_run_ids", targets)
        object.__setattr__(self, "completed_run_ids", completed)
        object.__setattr__(self, "terminal_run_ids", terminal)
        if not isinstance(self.mode, DelegationJoinMode):
            raise ValidationError(code="join_wait_mode_invalid")
        if self.quorum not in (MISSING, None):
            _safe_position(self.quorum, "join_wait_quorum_invalid", minimum=1)
        if self.on_satisfied not in (
            MISSING,
            None,
            "cancel_remaining",
            "detach_remaining",
            "keep_bound",
        ):
            raise ValidationError(code="join_wait_satisfied_policy_invalid")


@final
@dataclass(frozen=True, slots=True, kw_only=True)
class ReconciliationWaitResolvedPayload:
    wait_id: WaitId
    outcome: str
    kind: Literal[WaitKind.RECONCILIATION] = WaitKind.RECONCILIATION

    def __post_init__(self) -> None:
        if self.kind is not WaitKind.RECONCILIATION:
            raise ValidationError(code="wait_payload_kind_invalid")
        if not isinstance(self.wait_id, WaitId):
            raise ValidationError(code="wait_payload_id_invalid")
        object.__setattr__(
            self,
            "outcome",
            _required_text(self.outcome, "reconciliation_wait_outcome_invalid"),
        )


def _validate_wait_end(
    wait_id: object,
    kind: object,
    expected_kind: WaitKind,
    reason: object,
) -> str | MissingType | None:
    if not isinstance(wait_id, WaitId):
        raise ValidationError(code="wait_payload_id_invalid")
    if kind is not expected_kind:
        raise ValidationError(code="wait_payload_kind_invalid")
    return _optional_text(reason, "wait_end_reason_invalid")


@final
@dataclass(frozen=True, slots=True, kw_only=True)
class ApprovalWaitCancelledPayload:
    wait_id: WaitId
    reason: str | MissingType | None = MISSING
    request_event_id: EventId | MissingType | None = MISSING
    kind: Literal[WaitKind.APPROVAL] = WaitKind.APPROVAL

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "reason",
            _validate_wait_end(self.wait_id, self.kind, WaitKind.APPROVAL, self.reason),
        )
        object.__setattr__(
            self,
            "request_event_id",
            _optional_instance(self.request_event_id, EventId, "wait_request_event_id_invalid"),
        )


@final
@dataclass(frozen=True, slots=True, kw_only=True)
class InteractionWaitCancelledPayload:
    wait_id: WaitId
    reason: str | MissingType | None = MISSING
    request_event_id: EventId | MissingType | None = MISSING
    kind: Literal[WaitKind.INTERACTION] = WaitKind.INTERACTION

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "reason",
            _validate_wait_end(self.wait_id, self.kind, WaitKind.INTERACTION, self.reason),
        )
        object.__setattr__(
            self,
            "request_event_id",
            _optional_instance(self.request_event_id, EventId, "wait_request_event_id_invalid"),
        )


@final
@dataclass(frozen=True, slots=True, kw_only=True)
class TimerWaitCancelledPayload:
    wait_id: WaitId
    reason: str | MissingType | None = MISSING
    kind: Literal[WaitKind.TIMER] = WaitKind.TIMER

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "reason",
            _validate_wait_end(self.wait_id, self.kind, WaitKind.TIMER, self.reason),
        )


@final
@dataclass(frozen=True, slots=True, kw_only=True)
class JoinWaitCancelledPayload:
    wait_id: WaitId
    target_run_ids: tuple[RunId, ...] = ()
    reason: str | MissingType | None = MISSING
    kind: Literal[WaitKind.JOIN] = WaitKind.JOIN

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "reason",
            _validate_wait_end(self.wait_id, self.kind, WaitKind.JOIN, self.reason),
        )
        object.__setattr__(
            self,
            "target_run_ids",
            _typed_tuple(self.target_run_ids, RunId, "wait_cancelled_target_ids_invalid"),
        )


@final
@dataclass(frozen=True, slots=True, kw_only=True)
class ReconciliationWaitCancelledPayload:
    wait_id: WaitId
    reason: str | MissingType | None = MISSING
    kind: Literal[WaitKind.RECONCILIATION] = WaitKind.RECONCILIATION

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "reason",
            _validate_wait_end(self.wait_id, self.kind, WaitKind.RECONCILIATION, self.reason),
        )


def _validate_wait_expired(
    wait_id: object,
    kind: object,
    expected_kind: WaitKind,
    expired_at: object,
    reason: object,
) -> tuple[Timestamp | MissingType | None, str | MissingType | None]:
    if not isinstance(wait_id, WaitId):
        raise ValidationError(code="wait_payload_id_invalid")
    if kind is not expected_kind:
        raise ValidationError(code="wait_payload_kind_invalid")
    return (
        _optional_instance(expired_at, Timestamp, "wait_expired_at_invalid"),
        _optional_text(reason, "wait_end_reason_invalid"),
    )


@final
@dataclass(frozen=True, slots=True, kw_only=True)
class ApprovalWaitExpiredPayload:
    wait_id: WaitId
    expired_at: Timestamp | MissingType | None = MISSING
    reason: str | MissingType | None = MISSING
    kind: Literal[WaitKind.APPROVAL] = WaitKind.APPROVAL

    def __post_init__(self) -> None:
        expired_at, reason = _validate_wait_expired(
            self.wait_id, self.kind, WaitKind.APPROVAL, self.expired_at, self.reason
        )
        object.__setattr__(self, "expired_at", expired_at)
        object.__setattr__(self, "reason", reason)


@final
@dataclass(frozen=True, slots=True, kw_only=True)
class InteractionWaitExpiredPayload:
    wait_id: WaitId
    expired_at: Timestamp | MissingType | None = MISSING
    reason: str | MissingType | None = MISSING
    kind: Literal[WaitKind.INTERACTION] = WaitKind.INTERACTION

    def __post_init__(self) -> None:
        expired_at, reason = _validate_wait_expired(
            self.wait_id,
            self.kind,
            WaitKind.INTERACTION,
            self.expired_at,
            self.reason,
        )
        object.__setattr__(self, "expired_at", expired_at)
        object.__setattr__(self, "reason", reason)


@final
@dataclass(frozen=True, slots=True, kw_only=True)
class TimerWaitExpiredPayload:
    wait_id: WaitId
    expired_at: Timestamp | MissingType | None = MISSING
    reason: str | MissingType | None = MISSING
    kind: Literal[WaitKind.TIMER] = WaitKind.TIMER

    def __post_init__(self) -> None:
        expired_at, reason = _validate_wait_expired(
            self.wait_id, self.kind, WaitKind.TIMER, self.expired_at, self.reason
        )
        object.__setattr__(self, "expired_at", expired_at)
        object.__setattr__(self, "reason", reason)


@final
@dataclass(frozen=True, slots=True, kw_only=True)
class JoinWaitExpiredPayload:
    wait_id: WaitId
    expired_at: Timestamp | MissingType | None = MISSING
    reason: str | MissingType | None = MISSING
    kind: Literal[WaitKind.JOIN] = WaitKind.JOIN

    def __post_init__(self) -> None:
        expired_at, reason = _validate_wait_expired(
            self.wait_id, self.kind, WaitKind.JOIN, self.expired_at, self.reason
        )
        object.__setattr__(self, "expired_at", expired_at)
        object.__setattr__(self, "reason", reason)


@final
@dataclass(frozen=True, slots=True, kw_only=True)
class ReconciliationWaitExpiredPayload:
    wait_id: WaitId
    expired_at: Timestamp | MissingType | None = MISSING
    reason: str | MissingType | None = MISSING
    kind: Literal[WaitKind.RECONCILIATION] = WaitKind.RECONCILIATION

    def __post_init__(self) -> None:
        expired_at, reason = _validate_wait_expired(
            self.wait_id,
            self.kind,
            WaitKind.RECONCILIATION,
            self.expired_at,
            self.reason,
        )
        object.__setattr__(self, "expired_at", expired_at)
        object.__setattr__(self, "reason", reason)


@final
@dataclass(frozen=True, slots=True, kw_only=True)
class DelegationContractCreatedPayload:
    delegated_run_id: RunId
    contract: DelegationContract
    input: DelegationInput
    delegation_id: DelegationId | MissingType | None = MISSING
    contract_preview: Content | MissingType | None = MISSING
    metadata: JsonObject | MissingType | None = MISSING

    def __post_init__(self) -> None:
        if not isinstance(self.delegated_run_id, RunId):
            raise ValidationError(code="delegation_created_run_id_invalid")
        if not isinstance(self.contract, DelegationContract):
            raise ValidationError(code="delegation_created_contract_invalid")
        if not isinstance(self.input, DelegationInput):
            raise ValidationError(code="delegation_created_input_invalid")
        object.__setattr__(
            self,
            "delegation_id",
            _optional_instance(
                self.delegation_id,
                DelegationId,
                "delegation_created_id_invalid",
            ),
        )
        object.__setattr__(
            self,
            "contract_preview",
            _optional_instance(
                self.contract_preview,
                Content,
                "delegation_created_preview_invalid",
            ),
        )
        object.__setattr__(
            self,
            "metadata",
            _optional_object(self.metadata, "delegation_created_metadata_invalid"),
        )


@final
@dataclass(frozen=True, slots=True, kw_only=True)
class DelegationHandoffCreatedPayload:
    delegated_run_id: RunId
    parent_spawn_event_id: EventId
    delegated_run_first_position: int
    delegation_id: DelegationId | MissingType | None = MISSING
    metadata: JsonObject | MissingType | None = MISSING

    def __post_init__(self) -> None:
        if not isinstance(self.delegated_run_id, RunId):
            raise ValidationError(code="delegation_created_run_id_invalid")
        if not isinstance(self.parent_spawn_event_id, EventId):
            raise ValidationError(code="delegation_handoff_parent_event_id_invalid")
        object.__setattr__(
            self,
            "delegated_run_first_position",
            _safe_position(
                self.delegated_run_first_position,
                "delegation_handoff_position_invalid",
                minimum=1,
            ),
        )
        object.__setattr__(
            self,
            "delegation_id",
            _optional_instance(
                self.delegation_id,
                DelegationId,
                "delegation_created_id_invalid",
            ),
        )
        object.__setattr__(
            self,
            "metadata",
            _optional_object(self.metadata, "delegation_created_metadata_invalid"),
        )


@final
@dataclass(frozen=True, slots=True, kw_only=True)
class DelegationCompletedPayload:
    delegated_run_id: RunId
    delegation_id: DelegationId | MissingType | None = MISSING
    result: RunResult | MissingType | None = MISSING
    note: Content | MissingType | None = MISSING

    def __post_init__(self) -> None:
        if not isinstance(self.delegated_run_id, RunId):
            raise ValidationError(code="delegation_completed_run_id_invalid")
        object.__setattr__(
            self,
            "delegation_id",
            _optional_instance(
                self.delegation_id,
                DelegationId,
                "delegation_completed_id_invalid",
            ),
        )
        object.__setattr__(
            self,
            "result",
            _optional_instance(self.result, RunResult, "delegation_completed_result_invalid"),
        )
        object.__setattr__(
            self,
            "note",
            _optional_instance(self.note, Content, "delegation_completed_note_invalid"),
        )


@final
@dataclass(frozen=True, slots=True, kw_only=True)
class DelegationFailedPayload:
    delegated_run_id: RunId
    message: str
    delegation_id: DelegationId | MissingType | None = MISSING
    evidence: Content | MissingType | None = MISSING

    def __post_init__(self) -> None:
        if not isinstance(self.delegated_run_id, RunId):
            raise ValidationError(code="delegation_failed_run_id_invalid")
        object.__setattr__(
            self,
            "message",
            _required_text(self.message, "delegation_failed_message_invalid"),
        )
        object.__setattr__(
            self,
            "delegation_id",
            _optional_instance(self.delegation_id, DelegationId, "delegation_failed_id_invalid"),
        )
        object.__setattr__(
            self,
            "evidence",
            _optional_instance(self.evidence, Content, "delegation_failed_evidence_invalid"),
        )


@final
@dataclass(frozen=True, slots=True, kw_only=True)
class DelegationCancelledPayload:
    delegated_run_id: RunId
    delegation_id: DelegationId | MissingType | None = MISSING
    reason: str | MissingType | None = MISSING

    def __post_init__(self) -> None:
        if not isinstance(self.delegated_run_id, RunId):
            raise ValidationError(code="delegation_cancelled_run_id_invalid")
        object.__setattr__(
            self,
            "delegation_id",
            _optional_instance(
                self.delegation_id,
                DelegationId,
                "delegation_cancelled_id_invalid",
            ),
        )
        object.__setattr__(
            self,
            "reason",
            _optional_text(self.reason, "delegation_cancelled_reason_invalid"),
        )


@final
@dataclass(frozen=True, slots=True, kw_only=True)
class CheckRecordedReportPayload:
    check_id: CheckId
    subject: str
    rule: str
    status: CheckStatus
    validator: str
    summary: str
    check_count: int
    result: Content
    message: str | MissingType | None = MISSING
    evidence: Content | MissingType | None = MISSING

    def __post_init__(self) -> None:
        if not isinstance(self.check_id, CheckId):
            raise ValidationError(code="check_recorded_id_invalid")
        for name in ("subject", "rule", "validator", "summary"):
            object.__setattr__(
                self,
                name,
                _required_text(getattr(self, name), f"check_recorded_{name}_invalid"),
            )
        if not isinstance(self.status, CheckStatus):
            raise ValidationError(code="check_recorded_status_invalid")
        object.__setattr__(
            self,
            "check_count",
            _safe_position(self.check_count, "check_recorded_count_invalid", minimum=0),
        )
        if not isinstance(self.result, Content):
            raise ValidationError(code="check_recorded_result_invalid")
        object.__setattr__(
            self,
            "message",
            _optional_text(self.message, "check_recorded_message_invalid"),
        )
        object.__setattr__(
            self,
            "evidence",
            _optional_instance(self.evidence, Content, "check_recorded_evidence_invalid"),
        )


@dataclass(frozen=True, slots=True, kw_only=True)
class _CheckpointCreatedPayload:
    checkpoint_id: CheckpointId
    from_position: int
    to_position: int
    source: Literal["model", "runtime", "operator"]
    summary: str | MissingType | None = MISSING
    retained_context: JsonObject | MissingType | None = MISSING
    protected_event_types: tuple[CoreEventType, ...] = ()
    artifact_ids: tuple[ArtifactId, ...] = ()
    failure_behavior: (
        Literal["fail_command", "record_annotation", "request_operator_intervention"]
        | MissingType
        | None
    ) = MISSING

    def __post_init__(self) -> None:
        if not isinstance(self.checkpoint_id, CheckpointId):
            raise ValidationError(code="checkpoint_created_id_invalid")
        start = _safe_position(self.from_position, "checkpoint_created_range_invalid", minimum=0)
        end = _safe_position(self.to_position, "checkpoint_created_range_invalid", minimum=0)
        if end < start:
            raise ValidationError(code="checkpoint_created_range_invalid")
        if self.source not in ("model", "runtime", "operator"):
            raise ValidationError(code="checkpoint_created_source_invalid")
        object.__setattr__(
            self,
            "summary",
            _optional_text(self.summary, "checkpoint_created_summary_invalid"),
        )
        object.__setattr__(
            self,
            "retained_context",
            _optional_object(self.retained_context, "checkpoint_created_context_invalid"),
        )
        object.__setattr__(
            self,
            "protected_event_types",
            _typed_tuple(
                self.protected_event_types,
                CoreEventType,
                "checkpoint_created_event_types_invalid",
            ),
        )
        object.__setattr__(
            self,
            "artifact_ids",
            _typed_tuple(
                self.artifact_ids,
                ArtifactId,
                "checkpoint_created_artifact_ids_invalid",
            ),
        )
        if self.failure_behavior not in (
            MISSING,
            None,
            "fail_command",
            "record_annotation",
            "request_operator_intervention",
        ):
            raise ValidationError(code="checkpoint_created_failure_behavior_invalid")


@final
@dataclass(frozen=True, slots=True, kw_only=True)
class CheckpointRangeCreatedPayload(_CheckpointCreatedPayload):
    variant: Literal["range"] = "range"

    def __post_init__(self) -> None:
        super(CheckpointRangeCreatedPayload, self).__post_init__()
        if self.variant != "range":
            raise ValidationError(code="checkpoint_created_variant_invalid")


@final
@dataclass(frozen=True, slots=True, kw_only=True)
class CheckpointCorrection:
    corrects_checkpoint_id: CheckpointId
    reason: str | MissingType | None = MISSING

    def __post_init__(self) -> None:
        if not isinstance(self.corrects_checkpoint_id, CheckpointId):
            raise ValidationError(code="checkpoint_correction_id_invalid")
        object.__setattr__(
            self,
            "reason",
            _optional_text(self.reason, "checkpoint_correction_reason_invalid"),
        )


@final
@dataclass(frozen=True, slots=True, kw_only=True)
class CheckpointCorrectionCreatedPayload(_CheckpointCreatedPayload):
    correction: CheckpointCorrection
    variant: Literal["correction"] = "correction"

    def __post_init__(self) -> None:
        super(CheckpointCorrectionCreatedPayload, self).__post_init__()
        if self.variant != "correction":
            raise ValidationError(code="checkpoint_created_variant_invalid")
        if not isinstance(self.correction, CheckpointCorrection):
            raise ValidationError(code="checkpoint_created_correction_invalid")


@final
@dataclass(frozen=True, slots=True, kw_only=True)
class ArtifactMetadataCreatedPayload:
    artifact_id: ArtifactId
    kind: str
    metadata: JsonObject
    uri: str | MissingType | None = MISSING
    hash: str | MissingType | None = MISSING

    def __post_init__(self) -> None:
        if not isinstance(self.artifact_id, ArtifactId):
            raise ValidationError(code="artifact_created_id_invalid")
        object.__setattr__(self, "kind", _required_text(self.kind, "artifact_created_kind_invalid"))
        object.__setattr__(
            self,
            "metadata",
            _required_object(self.metadata, "artifact_created_metadata_invalid"),
        )
        object.__setattr__(self, "uri", _optional_text(self.uri, "artifact_created_uri_invalid"))
        object.__setattr__(self, "hash", _optional_text(self.hash, "artifact_created_hash_invalid"))


@final
@dataclass(frozen=True, slots=True, kw_only=True)
class ArtifactPreviewCreatedPayload:
    artifact_id: ArtifactId
    kind: str
    metadata: JsonObject
    content_preview: str
    uri: str | MissingType | None = MISSING
    hash: str | MissingType | None = MISSING

    def __post_init__(self) -> None:
        if not isinstance(self.artifact_id, ArtifactId):
            raise ValidationError(code="artifact_created_id_invalid")
        object.__setattr__(self, "kind", _required_text(self.kind, "artifact_created_kind_invalid"))
        object.__setattr__(
            self,
            "metadata",
            _required_object(self.metadata, "artifact_created_metadata_invalid"),
        )
        if not isinstance(self.content_preview, str):
            raise ValidationError(code="artifact_created_preview_invalid")
        object.__setattr__(self, "uri", _optional_text(self.uri, "artifact_created_uri_invalid"))
        object.__setattr__(self, "hash", _optional_text(self.hash, "artifact_created_hash_invalid"))


@final
@dataclass(frozen=True, slots=True, kw_only=True)
class ArtifactUnavailablePayload:
    artifact_id: ArtifactId
    reason: str

    def __post_init__(self) -> None:
        if not isinstance(self.artifact_id, ArtifactId):
            raise ValidationError(code="artifact_unavailable_id_invalid")
        object.__setattr__(
            self,
            "reason",
            _required_text(self.reason, "artifact_unavailable_reason_invalid"),
        )


@final
@dataclass(frozen=True, slots=True, kw_only=True)
class CapabilityAuthorityGrantedPayload:
    capability_id: CapabilityId
    authority_id: AuthorityId | MissingType | None = MISSING
    constraints: JsonObject | MissingType | None = MISSING
    granted_by: str | MissingType | None = MISSING
    metadata: JsonObject | MissingType | None = MISSING

    def __post_init__(self) -> None:
        if not isinstance(self.capability_id, CapabilityId):
            raise ValidationError(code="authority_capability_id_invalid")
        object.__setattr__(
            self,
            "authority_id",
            _optional_instance(self.authority_id, AuthorityId, "authority_id_invalid"),
        )
        object.__setattr__(
            self,
            "constraints",
            _optional_object(self.constraints, "authority_constraints_invalid"),
        )
        object.__setattr__(
            self,
            "granted_by",
            _optional_text(self.granted_by, "authority_granted_by_invalid"),
        )
        object.__setattr__(
            self,
            "metadata",
            _optional_object(self.metadata, "authority_metadata_invalid"),
        )


@final
@dataclass(frozen=True, slots=True, kw_only=True)
class PolicyAuthorityGrantedPayload:
    rule_id: PolicyRuleId
    rule: JsonObject
    authority_id: AuthorityId | MissingType | None = MISSING
    constraints: JsonObject | MissingType | None = MISSING
    granted_by: str | MissingType | None = MISSING

    def __post_init__(self) -> None:
        if not isinstance(self.rule_id, PolicyRuleId):
            raise ValidationError(code="authority_rule_id_invalid")
        object.__setattr__(self, "rule", _required_object(self.rule, "authority_rule_invalid"))
        object.__setattr__(
            self,
            "authority_id",
            _optional_instance(self.authority_id, AuthorityId, "authority_id_invalid"),
        )
        object.__setattr__(
            self,
            "constraints",
            _optional_object(self.constraints, "authority_constraints_invalid"),
        )
        object.__setattr__(
            self,
            "granted_by",
            _optional_text(self.granted_by, "authority_granted_by_invalid"),
        )


@final
@dataclass(frozen=True, slots=True, kw_only=True)
class CapabilityAuthorityRevokedPayload:
    capability_id: CapabilityId
    authority_id: AuthorityId | MissingType | None = MISSING
    reason: str | MissingType | None = MISSING

    def __post_init__(self) -> None:
        if not isinstance(self.capability_id, CapabilityId):
            raise ValidationError(code="authority_capability_id_invalid")
        object.__setattr__(
            self,
            "authority_id",
            _optional_instance(self.authority_id, AuthorityId, "authority_id_invalid"),
        )
        object.__setattr__(self, "reason", _optional_text(self.reason, "authority_reason_invalid"))


@final
@dataclass(frozen=True, slots=True, kw_only=True)
class PolicyAuthorityRevokedPayload:
    rule_id: PolicyRuleId
    authority_id: AuthorityId | MissingType | None = MISSING
    reason: str | MissingType | None = MISSING

    def __post_init__(self) -> None:
        if not isinstance(self.rule_id, PolicyRuleId):
            raise ValidationError(code="authority_rule_id_invalid")
        object.__setattr__(
            self,
            "authority_id",
            _optional_instance(self.authority_id, AuthorityId, "authority_id_invalid"),
        )
        object.__setattr__(self, "reason", _optional_text(self.reason, "authority_reason_invalid"))


@final
@dataclass(frozen=True, slots=True, kw_only=True)
class LeaseAcquiredPayload:
    lease_id: LeaseId
    owner_id: str
    expires_at: Timestamp

    def __post_init__(self) -> None:
        if not isinstance(self.lease_id, LeaseId):
            raise ValidationError(code="lease_acquired_id_invalid")
        object.__setattr__(
            self, "owner_id", _required_text(self.owner_id, "lease_owner_id_invalid")
        )
        if not isinstance(self.expires_at, Timestamp):
            raise ValidationError(code="lease_expires_at_invalid")


@final
@dataclass(frozen=True, slots=True, kw_only=True)
class LeaseReleasedPayload:
    lease_id: LeaseId
    owner_id: str

    def __post_init__(self) -> None:
        if not isinstance(self.lease_id, LeaseId):
            raise ValidationError(code="lease_released_id_invalid")
        object.__setattr__(
            self, "owner_id", _required_text(self.owner_id, "lease_owner_id_invalid")
        )


@final
@dataclass(frozen=True, slots=True, kw_only=True)
class LeaseExpiredPayload:
    lease_id: LeaseId
    owner_id: str | MissingType | None = MISSING

    def __post_init__(self) -> None:
        if not isinstance(self.lease_id, LeaseId):
            raise ValidationError(code="lease_expired_id_invalid")
        object.__setattr__(
            self,
            "owner_id",
            _optional_text(self.owner_id, "lease_owner_id_invalid"),
        )


type EventPayload = (
    RunCreatedPayload
    | RunStartedPayload
    | RunCompletedPayload
    | RunFailedPayload
    | RunCancelledPayload
    | ModelCommandRecordedPayload
    | RuntimeCommandRecordedPayload
    | CanonicalMessageAddedPayload
    | LegacyPreviewMessageAddedPayload
    | MessageDeltaPayload
    | CanonicalAnnotationRecordedPayload
    | LegacyPreviewAnnotationRecordedPayload
    | ModelCallStartedPayload
    | ModelCallCompletedPayload
    | ModelCallFailedPayload
    | ModelCallCancelledPayload
    | ActionCreatedPayload
    | ActionStartedPayload
    | ActionCompletedPayload
    | ActionFailedPayload
    | ActionCancelledPayload
    | ActionUnknownPayload
    | ActionReconciledCompletedPayload
    | ActionReconciledFailedPayload
    | ActionReconciledCancelledPayload
    | AggregateWaitCreatedPayload
    | ApprovalWaitCreatedPayload
    | InteractionWaitCreatedPayload
    | TimerWaitCreatedPayload
    | JoinWaitCreatedPayload
    | ReconciliationWaitCreatedPayload
    | AggregateWaitResolvedPayload
    | ApprovalWaitResolvedPayload
    | InteractionWaitResolvedPayload
    | TimerWaitResolvedPayload
    | JoinWaitResolvedPayload
    | ReconciliationWaitResolvedPayload
    | ApprovalWaitCancelledPayload
    | InteractionWaitCancelledPayload
    | TimerWaitCancelledPayload
    | JoinWaitCancelledPayload
    | ReconciliationWaitCancelledPayload
    | ApprovalWaitExpiredPayload
    | InteractionWaitExpiredPayload
    | TimerWaitExpiredPayload
    | JoinWaitExpiredPayload
    | ReconciliationWaitExpiredPayload
    | DelegationContractCreatedPayload
    | DelegationHandoffCreatedPayload
    | DelegationCompletedPayload
    | DelegationFailedPayload
    | DelegationCancelledPayload
    | CheckRecordedReportPayload
    | CheckpointRangeCreatedPayload
    | CheckpointCorrectionCreatedPayload
    | ArtifactMetadataCreatedPayload
    | ArtifactPreviewCreatedPayload
    | ArtifactUnavailablePayload
    | CapabilityAuthorityGrantedPayload
    | PolicyAuthorityGrantedPayload
    | CapabilityAuthorityRevokedPayload
    | PolicyAuthorityRevokedPayload
    | LeaseAcquiredPayload
    | LeaseReleasedPayload
    | LeaseExpiredPayload
)


@final
@dataclass(frozen=True, slots=True, kw_only=True)
class EventAssociation:
    event_type: CoreEventType
    version: Literal[1]
    variant: str
    payload_type: type[EventPayload]
    decode_only: bool = False

    def __post_init__(self) -> None:
        if not isinstance(self.event_type, CoreEventType):
            raise ValidationError(code="event_association_type_invalid")
        if self.version != 1:
            raise ValidationError(code="event_association_version_invalid")
        object.__setattr__(
            self,
            "variant",
            _required_text(self.variant, "event_association_variant_invalid"),
        )
        if not isinstance(self.payload_type, type):
            raise ValidationError(code="event_association_payload_type_invalid")
        if not isinstance(self.decode_only, bool):
            raise ValidationError(code="event_association_decode_only_invalid")


def _association(
    event_type: CoreEventType,
    variant: str,
    payload_type: type[EventPayload],
    *,
    decode_only: bool = False,
) -> EventAssociation:
    return EventAssociation(
        event_type=event_type,
        version=1,
        variant=variant,
        payload_type=payload_type,
        decode_only=decode_only,
    )


_EVENT_ASSOCIATIONS: tuple[EventAssociation, ...] = (
    _association(CoreEventType.RUN_CREATED, "canonical", RunCreatedPayload),
    _association(CoreEventType.RUN_STARTED, "canonical", RunStartedPayload),
    _association(CoreEventType.RUN_COMPLETED, "canonical", RunCompletedPayload),
    _association(CoreEventType.RUN_FAILED, "canonical", RunFailedPayload),
    _association(CoreEventType.RUN_CANCELLED, "canonical", RunCancelledPayload),
    _association(CoreEventType.COMMAND_RECORDED, "model", ModelCommandRecordedPayload),
    _association(CoreEventType.COMMAND_RECORDED, "runtime", RuntimeCommandRecordedPayload),
    _association(
        CoreEventType.MESSAGE_ADDED,
        "content",
        LegacyPreviewMessageAddedPayload,
        decode_only=True,
    ),
    _association(CoreEventType.MESSAGE_ADDED, "legacy-preview", CanonicalMessageAddedPayload),
    _association(CoreEventType.MESSAGE_DELTA, "canonical", MessageDeltaPayload),
    _association(
        CoreEventType.ANNOTATION_RECORDED,
        "content",
        LegacyPreviewAnnotationRecordedPayload,
        decode_only=True,
    ),
    _association(
        CoreEventType.ANNOTATION_RECORDED,
        "legacy-preview",
        CanonicalAnnotationRecordedPayload,
    ),
    _association(CoreEventType.MODEL_CALL_STARTED, "canonical", ModelCallStartedPayload),
    _association(CoreEventType.MODEL_CALL_COMPLETED, "canonical", ModelCallCompletedPayload),
    _association(CoreEventType.MODEL_CALL_FAILED, "canonical", ModelCallFailedPayload),
    _association(CoreEventType.MODEL_CALL_CANCELLED, "canonical", ModelCallCancelledPayload),
    _association(CoreEventType.ACTION_CREATED, "canonical", ActionCreatedPayload),
    _association(CoreEventType.ACTION_STARTED, "canonical", ActionStartedPayload),
    _association(CoreEventType.ACTION_COMPLETED, "canonical", ActionCompletedPayload),
    _association(CoreEventType.ACTION_FAILED, "structured-error", ActionFailedPayload),
    _association(CoreEventType.ACTION_CANCELLED, "canonical", ActionCancelledPayload),
    _association(CoreEventType.ACTION_UNKNOWN, "canonical", ActionUnknownPayload),
    _association(
        CoreEventType.ACTION_RECONCILED,
        "completed",
        ActionReconciledCompletedPayload,
    ),
    _association(CoreEventType.ACTION_RECONCILED, "failed", ActionReconciledFailedPayload),
    _association(
        CoreEventType.ACTION_RECONCILED,
        "cancelled",
        ActionReconciledCancelledPayload,
    ),
    _association(CoreEventType.WAIT_CREATED, "aggregate", AggregateWaitCreatedPayload),
    _association(CoreEventType.WAIT_CREATED, "approval", ApprovalWaitCreatedPayload),
    _association(CoreEventType.WAIT_CREATED, "interaction", InteractionWaitCreatedPayload),
    _association(CoreEventType.WAIT_CREATED, "timer", TimerWaitCreatedPayload),
    _association(CoreEventType.WAIT_CREATED, "join", JoinWaitCreatedPayload),
    _association(
        CoreEventType.WAIT_CREATED,
        "reconciliation",
        ReconciliationWaitCreatedPayload,
    ),
    _association(CoreEventType.WAIT_RESOLVED, "aggregate", AggregateWaitResolvedPayload),
    _association(CoreEventType.WAIT_RESOLVED, "approval", ApprovalWaitResolvedPayload),
    _association(
        CoreEventType.WAIT_RESOLVED,
        "interaction",
        InteractionWaitResolvedPayload,
    ),
    _association(CoreEventType.WAIT_RESOLVED, "timer", TimerWaitResolvedPayload),
    _association(CoreEventType.WAIT_RESOLVED, "join", JoinWaitResolvedPayload),
    _association(
        CoreEventType.WAIT_RESOLVED,
        "reconciliation",
        ReconciliationWaitResolvedPayload,
    ),
    _association(CoreEventType.WAIT_CANCELLED, "approval", ApprovalWaitCancelledPayload),
    _association(
        CoreEventType.WAIT_CANCELLED,
        "interaction",
        InteractionWaitCancelledPayload,
    ),
    _association(CoreEventType.WAIT_CANCELLED, "timer", TimerWaitCancelledPayload),
    _association(CoreEventType.WAIT_CANCELLED, "join", JoinWaitCancelledPayload),
    _association(
        CoreEventType.WAIT_CANCELLED,
        "reconciliation",
        ReconciliationWaitCancelledPayload,
    ),
    _association(CoreEventType.WAIT_EXPIRED, "approval", ApprovalWaitExpiredPayload),
    _association(CoreEventType.WAIT_EXPIRED, "interaction", InteractionWaitExpiredPayload),
    _association(CoreEventType.WAIT_EXPIRED, "timer", TimerWaitExpiredPayload),
    _association(CoreEventType.WAIT_EXPIRED, "join", JoinWaitExpiredPayload),
    _association(
        CoreEventType.WAIT_EXPIRED,
        "reconciliation",
        ReconciliationWaitExpiredPayload,
    ),
    _association(
        CoreEventType.DELEGATION_CREATED,
        "contract",
        DelegationContractCreatedPayload,
    ),
    _association(
        CoreEventType.DELEGATION_CREATED,
        "handoff",
        DelegationHandoffCreatedPayload,
    ),
    _association(
        CoreEventType.DELEGATION_COMPLETED,
        "canonical",
        DelegationCompletedPayload,
    ),
    _association(CoreEventType.DELEGATION_FAILED, "canonical", DelegationFailedPayload),
    _association(
        CoreEventType.DELEGATION_CANCELLED,
        "canonical",
        DelegationCancelledPayload,
    ),
    _association(CoreEventType.CHECK_RECORDED, "report", CheckRecordedReportPayload),
    _association(
        CoreEventType.CHECKPOINT_CREATED,
        "range",
        CheckpointRangeCreatedPayload,
    ),
    _association(
        CoreEventType.CHECKPOINT_CREATED,
        "correction",
        CheckpointCorrectionCreatedPayload,
    ),
    _association(CoreEventType.ARTIFACT_CREATED, "metadata", ArtifactMetadataCreatedPayload),
    _association(CoreEventType.ARTIFACT_CREATED, "preview", ArtifactPreviewCreatedPayload),
    _association(
        CoreEventType.ARTIFACT_UNAVAILABLE,
        "canonical",
        ArtifactUnavailablePayload,
    ),
    _association(
        CoreEventType.AUTHORITY_GRANTED,
        "capability",
        CapabilityAuthorityGrantedPayload,
    ),
    _association(
        CoreEventType.AUTHORITY_GRANTED,
        "policy-rule",
        PolicyAuthorityGrantedPayload,
    ),
    _association(
        CoreEventType.AUTHORITY_REVOKED,
        "capability",
        CapabilityAuthorityRevokedPayload,
    ),
    _association(
        CoreEventType.AUTHORITY_REVOKED,
        "policy-rule",
        PolicyAuthorityRevokedPayload,
    ),
    _association(CoreEventType.LEASE_ACQUIRED, "canonical", LeaseAcquiredPayload),
    _association(CoreEventType.LEASE_RELEASED, "canonical", LeaseReleasedPayload),
    _association(CoreEventType.LEASE_EXPIRED, "canonical", LeaseExpiredPayload),
)

_catalog: dict[tuple[CoreEventType, int, str], EventAssociation] = {
    (association.event_type, association.version, association.variant): association
    for association in _EVENT_ASSOCIATIONS
}
if len(_catalog) != len(_EVENT_ASSOCIATIONS):
    raise RuntimeError("event_association_key_duplicate")

EVENT_PAYLOAD_CATALOG: Mapping[tuple[CoreEventType, int, str], EventAssociation] = MappingProxyType(
    _catalog
)
PAYLOAD_TYPES: tuple[type[EventPayload], ...] = tuple(
    association.payload_type for association in _EVENT_ASSOCIATIONS
)


@final
@dataclass(frozen=True, slots=True, kw_only=True)
class Event[TEventType: CoreEventType, TPayload: EventPayload]:
    event_id: EventId
    run_id: RunId
    position: int
    event_type: TEventType
    timestamp: Timestamp
    actor: EventActor
    payload: TPayload
    version: Literal[1] = 1
    causation_id: EventId | MissingType = MISSING
    correlation_id: CorrelationId | MissingType = MISSING
    command_id: CommandId | MissingType = MISSING
    association: EventAssociation = field(init=False, repr=False, compare=False)

    def __post_init__(self) -> None:
        if not isinstance(self.event_id, EventId):
            raise ValidationError(code="event_id_invalid")
        if not isinstance(self.run_id, RunId):
            raise ValidationError(code="event_run_id_invalid")
        object.__setattr__(
            self,
            "position",
            _safe_position(self.position, "event_position_invalid", minimum=1),
        )
        if not isinstance(self.event_type, CoreEventType):
            raise ValidationError(code="event_type_invalid")
        if self.version != 1 or isinstance(self.version, bool):
            code = "event_version_invalid" if self.version == 0 else "event_version_unsupported"
            raise ValidationError(code=code)
        if not isinstance(self.timestamp, Timestamp):
            raise ValidationError(code="event_timestamp_invalid")
        if not isinstance(self.actor, EventActor):
            raise ValidationError(code="event_actor_invalid")
        matches = tuple(
            association
            for association in _EVENT_ASSOCIATIONS
            if association.event_type is self.event_type
            and isinstance(self.payload, association.payload_type)
        )
        if len(matches) != 1:
            raise ValidationError(code="event_payload_type_invalid")
        object.__setattr__(self, "association", matches[0])
        if self.causation_id is not MISSING and not isinstance(self.causation_id, EventId):
            raise ValidationError(code="event_causation_id_invalid")
        if self.correlation_id is not MISSING and not isinstance(
            self.correlation_id, CorrelationId
        ):
            raise ValidationError(code="event_correlation_id_invalid")
        if self.command_id is not MISSING and not isinstance(self.command_id, CommandId):
            raise ValidationError(code="event_command_id_invalid")


type RuntimeEvent = Event[CoreEventType, EventPayload]
