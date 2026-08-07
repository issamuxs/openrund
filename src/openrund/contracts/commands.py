"""Typed command operations and legality decisions with no authority behavior."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Literal, cast, final

from openrund.contracts.capabilities import ActionFailure, ActionReliability
from openrund.contracts.content import ArtifactReference, Content, EffectEntry, Mutation, RunResult
from openrund.contracts.ids import (
    ActionId,
    AnnotationId,
    ArtifactId,
    AuthorityId,
    CapabilityId,
    CheckId,
    CheckpointId,
    CommandId,
    DelegationId,
    EventId,
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


def _optional_object(value: object, code: str) -> JsonObject | MissingType | None:
    if value is MISSING or value is None:
        return value
    frozen = freeze_json(value)
    if not isinstance(frozen, JsonObject):
        raise ValidationError(code=code)
    return frozen


def _typed_tuple[T](value: object, expected: type[T], code: str) -> tuple[T, ...]:
    try:
        items: tuple[object, ...] = tuple(value)  # type: ignore[arg-type]
    except TypeError as error:
        raise ValidationError(code=code) from error
    if any(not isinstance(item, expected) for item in items):
        raise ValidationError(code=code)
    return cast(tuple[T, ...], items)


def _text_tuple(value: object, code: str) -> tuple[str, ...]:
    items = _typed_tuple(value, str, code)
    if any(item == "" for item in items):
        raise ValidationError(code=code)
    return items


class ProviderOperationKind(StrEnum):
    ADD_MESSAGE = "add_message"
    CREATE_ACTION = "create_action"
    CREATE_DELEGATION = "create_delegation"
    OPEN_WAIT = "open_wait"
    CREATE_CHECKPOINT = "create_checkpoint"
    COMPLETE_RUN = "complete_run"
    FAIL_RUN = "fail_run"
    CANCEL_RUN = "cancel_run"


class RuntimeOperationKind(StrEnum):
    BOOTSTRAP_RUN = "bootstrap_run"
    START_RUN = "start_run"
    ADD_MESSAGE = "add_message"
    MESSAGE_DELTA = "message_delta"
    RESOLVE_WAIT = "resolve_wait"
    RECORD_CHECK = "record_check"
    START_MODEL_CALL = "start_model_call"
    COMPLETE_MODEL_CALL = "complete_model_call"
    FAIL_MODEL_CALL = "fail_model_call"
    CANCEL_MODEL_CALL = "cancel_model_call"
    RESOLVE_APPROVAL = "resolve_approval"
    RESUME_APPROVED_ACTION = "resume_approved_action"
    START_ACTION = "start_action"
    COMPLETE_ACTION = "complete_action"
    FAIL_ACTION = "fail_action"
    CANCEL_ACTION = "cancel_action"
    MARK_ACTION_UNKNOWN = "mark_action_unknown"
    RECONCILE_ACTION = "reconcile_action"
    COMPLETE_DELEGATION = "complete_delegation"
    FAIL_DELEGATION = "fail_delegation"
    CANCEL_DELEGATION = "cancel_delegation"
    GRANT_AUTHORITY = "grant_authority"
    REVOKE_AUTHORITY = "revoke_authority"
    AMEND_POLICY = "amend_policy"
    MARK_ARTIFACT_UNAVAILABLE = "mark_artifact_unavailable"
    RECORD_ANNOTATION = "record_annotation"


class ModelCallFailureClassification(StrEnum):
    PROVIDER = "provider"
    TRANSPORT = "transport"
    PARSE = "parse"


type CommandOperationKind = ProviderOperationKind | RuntimeOperationKind


class CommandOrigin(StrEnum):
    MODEL = "model"
    USER = "user"
    CLIENT = "client"
    EXTERNAL = "external"
    OPERATOR = "operator"
    TIMER = "timer"
    DELEGATED_RUN = "delegated_run"
    CAPABILITY = "capability"
    SYSTEM = "system"
    RECOVERY = "recovery"


class LegalityCriterion(StrEnum):
    RUN_LIFECYCLE = "run_lifecycle"
    OPERATION_SCHEMA = "operation_schema"
    AUTHORITY = "authority"
    CONTRACT = "contract"
    POLICY = "policy"
    CAPABILITY_METADATA = "capability_metadata"
    CAPABILITY_SCHEMA = "capability_schema"
    RESOURCE_SCOPE = "resource_scope"
    ARTIFACT_DISCIPLINE = "artifact_discipline"
    BUDGET = "budget"
    WAIT_STATE = "wait_state"
    REQUIRED_CHECKS = "required_checks"
    KNOWN_OUTCOMES = "known_outcomes"
    DELEGATION_LINEAGE = "delegation_lineage"
    TENANT_SCOPE = "tenant_scope"
    ORACLE_FIXTURE = "oracle_fixture"


class LegalityCriterionResult(StrEnum):
    PASS = "pass"
    FAIL = "fail"
    DEFER = "defer"


@final
@dataclass(frozen=True, slots=True, kw_only=True)
class CommandDecisionTraceEntry:
    criterion: LegalityCriterion
    result: LegalityCriterionResult
    reason: str | MissingType | None = MISSING
    evidence_refs: tuple[ArtifactReference, ...] = ()
    related_entity_ids: tuple[str, ...] = ()
    metadata: JsonObject | MissingType | None = MISSING

    def __post_init__(self) -> None:
        if not isinstance(self.criterion, LegalityCriterion):
            raise ValidationError(code="legality_criterion_invalid")
        if not isinstance(self.result, LegalityCriterionResult):
            raise ValidationError(code="legality_result_invalid")
        object.__setattr__(self, "reason", _optional_text(self.reason, "legality_reason_invalid"))
        object.__setattr__(
            self,
            "evidence_refs",
            _typed_tuple(self.evidence_refs, ArtifactReference, "legality_evidence_refs_invalid"),
        )
        object.__setattr__(
            self,
            "related_entity_ids",
            _text_tuple(self.related_entity_ids, "legality_related_ids_invalid"),
        )
        object.__setattr__(
            self, "metadata", _optional_object(self.metadata, "legality_metadata_invalid")
        )


def _trace(value: object) -> tuple[CommandDecisionTraceEntry, ...]:
    return _typed_tuple(value, CommandDecisionTraceEntry, "command_decision_trace_invalid")


@final
@dataclass(frozen=True, slots=True, kw_only=True)
class AcceptedCommandDecision:
    trace: tuple[CommandDecisionTraceEntry, ...]
    result_event_ids: tuple[EventId, ...] = ()
    kind: Literal["accepted"] = "accepted"

    def __post_init__(self) -> None:
        if self.kind != "accepted":
            raise ValidationError(code="command_decision_kind_invalid")
        object.__setattr__(self, "trace", _trace(self.trace))
        object.__setattr__(
            self,
            "result_event_ids",
            _typed_tuple(self.result_event_ids, EventId, "command_decision_event_ids_invalid"),
        )


def _validate_reasoned_decision(
    reason: object, trace: object
) -> tuple[str, tuple[CommandDecisionTraceEntry, ...]]:
    return (
        _required_text(reason, "command_decision_reason_invalid"),
        _trace(trace),
    )


@final
@dataclass(frozen=True, slots=True, kw_only=True)
class RejectedCommandDecision:
    reason: str
    trace: tuple[CommandDecisionTraceEntry, ...]
    kind: Literal["rejected"] = "rejected"

    def __post_init__(self) -> None:
        if self.kind != "rejected":
            raise ValidationError(code="command_decision_kind_invalid")
        reason, trace = _validate_reasoned_decision(self.reason, self.trace)
        object.__setattr__(self, "reason", reason)
        object.__setattr__(self, "trace", trace)


@final
@dataclass(frozen=True, slots=True, kw_only=True)
class DeferredCommandDecision:
    reason: str
    trace: tuple[CommandDecisionTraceEntry, ...]
    wait_ids: tuple[WaitId, ...]
    kind: Literal["deferred"] = "deferred"

    def __post_init__(self) -> None:
        if self.kind != "deferred":
            raise ValidationError(code="command_decision_kind_invalid")
        reason, trace = _validate_reasoned_decision(self.reason, self.trace)
        object.__setattr__(self, "reason", reason)
        object.__setattr__(self, "trace", trace)
        wait_ids = _typed_tuple(self.wait_ids, WaitId, "command_decision_wait_ids_invalid")
        if not wait_ids:
            raise ValidationError(code="command_decision_wait_ids_invalid")
        object.__setattr__(self, "wait_ids", wait_ids)


@final
@dataclass(frozen=True, slots=True, kw_only=True)
class SupersededCommandDecision:
    reason: str
    trace: tuple[CommandDecisionTraceEntry, ...]
    superseded_by_command_id: CommandId
    kind: Literal["superseded"] = "superseded"

    def __post_init__(self) -> None:
        if self.kind != "superseded":
            raise ValidationError(code="command_decision_kind_invalid")
        reason, trace = _validate_reasoned_decision(self.reason, self.trace)
        object.__setattr__(self, "reason", reason)
        object.__setattr__(self, "trace", trace)
        if not isinstance(self.superseded_by_command_id, CommandId):
            raise ValidationError(code="command_decision_replacement_id_invalid")


type CommandDecision = (
    AcceptedCommandDecision
    | RejectedCommandDecision
    | DeferredCommandDecision
    | SupersededCommandDecision
)


@final
@dataclass(frozen=True, slots=True, kw_only=True)
class TargetEventPresent:
    event_id: EventId
    status: Literal["present"] = "present"

    def __post_init__(self) -> None:
        if self.status != "present":
            raise ValidationError(code="target_event_status_invalid")
        if not isinstance(self.event_id, EventId):
            raise ValidationError(code="target_event_id_invalid")


@final
@dataclass(frozen=True, slots=True, kw_only=True)
class TargetEventAbsent:
    status: Literal["absent"] = "absent"

    def __post_init__(self) -> None:
        if self.status != "absent":
            raise ValidationError(code="target_event_status_invalid")


type TargetEventRecord = TargetEventPresent | TargetEventAbsent


@final
@dataclass(frozen=True, slots=True, kw_only=True)
class CommandRejectionRecord:
    code: str

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "code", _required_text(self.code, "command_rejection_code_invalid")
        )


@final
@dataclass(frozen=True, slots=True, kw_only=True)
class CommandWaitRecord:
    wait_id: WaitId
    kind: WaitKind

    def __post_init__(self) -> None:
        if not isinstance(self.wait_id, WaitId):
            raise ValidationError(code="command_wait_id_invalid")
        if not isinstance(self.kind, WaitKind):
            raise ValidationError(code="command_wait_kind_invalid")


def _record_trace_and_results(
    trace: object, result_event_ids: object
) -> tuple[tuple[CommandDecisionTraceEntry, ...], tuple[EventId, ...]]:
    return (
        _trace(trace),
        _typed_tuple(result_event_ids, EventId, "decision_record_result_event_ids_invalid"),
    )


@final
@dataclass(frozen=True, slots=True, kw_only=True)
class AcceptedDecisionRecord:
    decision_trace: tuple[CommandDecisionTraceEntry, ...]
    result_event_ids: tuple[EventId, ...]
    decision: Literal["accepted"] = "accepted"

    def __post_init__(self) -> None:
        if self.decision != "accepted":
            raise ValidationError(code="decision_record_kind_invalid")
        trace, results = _record_trace_and_results(self.decision_trace, self.result_event_ids)
        if not results:
            raise ValidationError(code="decision_record_results_required")
        object.__setattr__(self, "decision_trace", trace)
        object.__setattr__(self, "result_event_ids", results)


@final
@dataclass(frozen=True, slots=True, kw_only=True)
class RejectedDecisionRecord:
    decision_trace: tuple[CommandDecisionTraceEntry, ...]
    result_event_ids: tuple[EventId, ...]
    rejection: CommandRejectionRecord
    decision: Literal["rejected"] = "rejected"

    def __post_init__(self) -> None:
        if self.decision != "rejected":
            raise ValidationError(code="decision_record_kind_invalid")
        trace, results = _record_trace_and_results(self.decision_trace, self.result_event_ids)
        if results:
            raise ValidationError(code="decision_record_results_must_be_empty")
        if not isinstance(self.rejection, CommandRejectionRecord):
            raise ValidationError(code="decision_record_rejection_invalid")
        object.__setattr__(self, "decision_trace", trace)
        object.__setattr__(self, "result_event_ids", results)


@final
@dataclass(frozen=True, slots=True, kw_only=True)
class DeferredDecisionRecord:
    decision_trace: tuple[CommandDecisionTraceEntry, ...]
    result_event_ids: tuple[EventId, ...]
    wait: CommandWaitRecord
    decision: Literal["deferred"] = "deferred"

    def __post_init__(self) -> None:
        if self.decision != "deferred":
            raise ValidationError(code="decision_record_kind_invalid")
        trace, results = _record_trace_and_results(self.decision_trace, self.result_event_ids)
        if results:
            raise ValidationError(code="decision_record_results_must_be_empty")
        if not isinstance(self.wait, CommandWaitRecord):
            raise ValidationError(code="decision_record_wait_invalid")
        object.__setattr__(self, "decision_trace", trace)
        object.__setattr__(self, "result_event_ids", results)


@final
@dataclass(frozen=True, slots=True, kw_only=True)
class SupersededDecisionRecord:
    decision_trace: tuple[CommandDecisionTraceEntry, ...]
    result_event_ids: tuple[EventId, ...]
    declaration_only: bool
    replacement_command_id: CommandId
    decision: Literal["superseded"] = "superseded"

    def __post_init__(self) -> None:
        if self.decision != "superseded":
            raise ValidationError(code="decision_record_kind_invalid")
        trace, results = _record_trace_and_results(self.decision_trace, self.result_event_ids)
        if results:
            raise ValidationError(code="decision_record_results_must_be_empty")
        if self.declaration_only is not True:
            raise ValidationError(code="decision_record_declaration_only_invalid")
        if not isinstance(self.replacement_command_id, CommandId):
            raise ValidationError(code="decision_record_replacement_id_invalid")
        object.__setattr__(self, "decision_trace", trace)
        object.__setattr__(self, "result_event_ids", results)


type CommandDecisionRecordBranch = (
    AcceptedDecisionRecord
    | RejectedDecisionRecord
    | DeferredDecisionRecord
    | SupersededDecisionRecord
)


@final
@dataclass(frozen=True, slots=True, kw_only=True)
class CommandDecisionRecord:
    command_id: CommandId
    branch: CommandDecisionRecordBranch
    target_event: TargetEventRecord

    def __post_init__(self) -> None:
        if not isinstance(self.command_id, CommandId):
            raise ValidationError(code="command_record_id_invalid")
        if not isinstance(
            self.branch,
            (
                AcceptedDecisionRecord,
                RejectedDecisionRecord,
                DeferredDecisionRecord,
                SupersededDecisionRecord,
            ),
        ):
            raise ValidationError(code="command_record_branch_invalid")
        if isinstance(self.branch, AcceptedDecisionRecord):
            if not isinstance(self.target_event, TargetEventPresent):
                raise ValidationError(code="command_record_target_mismatch")
            if self.target_event.event_id not in self.branch.result_event_ids:
                raise ValidationError(code="command_record_result_event_mismatch")
        elif not isinstance(self.target_event, TargetEventAbsent):
            raise ValidationError(code="command_record_target_mismatch")


@final
@dataclass(frozen=True, slots=True, kw_only=True)
class AddMessageOperation:
    message: Content
    kind: Literal[ProviderOperationKind.ADD_MESSAGE] = ProviderOperationKind.ADD_MESSAGE

    def __post_init__(self) -> None:
        if self.kind is not ProviderOperationKind.ADD_MESSAGE:
            raise ValidationError(code="operation_kind_invalid")
        if not isinstance(self.message, Content):
            raise ValidationError(code="add_message_content_invalid")


@final
@dataclass(frozen=True, slots=True, kw_only=True)
class CreateActionOperation:
    action_id: ActionId
    capability_id: CapabilityId
    action_name: str
    input: Content
    mutation: Mutation | MissingType | None = MISSING
    kind: Literal[ProviderOperationKind.CREATE_ACTION] = ProviderOperationKind.CREATE_ACTION

    def __post_init__(self) -> None:
        if self.kind is not ProviderOperationKind.CREATE_ACTION:
            raise ValidationError(code="operation_kind_invalid")
        if not isinstance(self.action_id, ActionId):
            raise ValidationError(code="create_action_id_invalid")
        if not isinstance(self.capability_id, CapabilityId):
            raise ValidationError(code="create_action_capability_id_invalid")
        object.__setattr__(
            self, "action_name", _required_text(self.action_name, "create_action_name_invalid")
        )
        if not isinstance(self.input, Content):
            raise ValidationError(code="create_action_input_invalid")
        if self.mutation not in (MISSING, None) and not isinstance(self.mutation, Mutation):
            raise ValidationError(code="create_action_mutation_invalid")


@final
@dataclass(frozen=True, slots=True, kw_only=True)
class CreateDelegationOperation:
    contract: DelegationContract
    input: DelegationInput
    delegated_run_id: RunId | MissingType | None = MISSING
    kind: Literal[ProviderOperationKind.CREATE_DELEGATION] = ProviderOperationKind.CREATE_DELEGATION

    def __post_init__(self) -> None:
        if self.kind is not ProviderOperationKind.CREATE_DELEGATION:
            raise ValidationError(code="operation_kind_invalid")
        if not isinstance(self.contract, DelegationContract):
            raise ValidationError(code="create_delegation_contract_invalid")
        if not isinstance(self.input, DelegationInput):
            raise ValidationError(code="create_delegation_input_invalid")
        if self.delegated_run_id not in (MISSING, None) and not isinstance(
            self.delegated_run_id, RunId
        ):
            raise ValidationError(code="create_delegation_run_id_invalid")


def _optional_wait_id(value: object) -> None:
    if value not in (MISSING, None) and not isinstance(value, WaitId):
        raise ValidationError(code="open_wait_id_invalid")


@final
@dataclass(frozen=True, slots=True, kw_only=True)
class OpenApprovalWaitOperation:
    target: str
    reason: str
    wait_id: WaitId | MissingType | None = MISSING
    action_id: ActionId | MissingType | None = MISSING
    capability_id: CapabilityId | MissingType | None = MISSING
    action_name: str | MissingType | None = MISSING
    request_payload: Content | MissingType | None = MISSING
    policy_snapshot: Content | MissingType | None = MISSING
    deadline: Timestamp | MissingType | None = MISSING
    metadata: JsonObject | MissingType | None = MISSING
    wait_kind: Literal[WaitKind.APPROVAL] = WaitKind.APPROVAL
    kind: Literal[ProviderOperationKind.OPEN_WAIT] = ProviderOperationKind.OPEN_WAIT

    def __post_init__(self) -> None:
        if (
            self.kind is not ProviderOperationKind.OPEN_WAIT
            or self.wait_kind is not WaitKind.APPROVAL
        ):
            raise ValidationError(code="operation_kind_invalid")
        _optional_wait_id(self.wait_id)
        if self.action_id not in (MISSING, None) and not isinstance(self.action_id, ActionId):
            raise ValidationError(code="open_approval_action_id_invalid")
        if self.capability_id not in (MISSING, None) and not isinstance(
            self.capability_id, CapabilityId
        ):
            raise ValidationError(code="open_approval_capability_id_invalid")
        object.__setattr__(
            self,
            "action_name",
            _optional_text(self.action_name, "open_approval_action_name_invalid"),
        )
        for name in ("request_payload", "policy_snapshot"):
            value = getattr(self, name)
            if value not in (MISSING, None) and not isinstance(value, Content):
                raise ValidationError(code=f"open_approval_{name}_invalid")
        if self.deadline not in (MISSING, None) and not isinstance(self.deadline, Timestamp):
            raise ValidationError(code="open_approval_deadline_invalid")
        object.__setattr__(self, "target", _required_text(self.target, "open_wait_target_invalid"))
        object.__setattr__(self, "reason", _required_text(self.reason, "open_wait_reason_invalid"))
        object.__setattr__(
            self, "metadata", _optional_object(self.metadata, "open_wait_metadata_invalid")
        )


@final
@dataclass(frozen=True, slots=True, kw_only=True)
class OpenInteractionWaitOperation:
    prompt: str
    wait_id: WaitId | MissingType | None = MISSING
    deadline: Timestamp | MissingType | None = MISSING
    metadata: JsonObject | MissingType | None = MISSING
    wait_kind: Literal[WaitKind.INTERACTION] = WaitKind.INTERACTION
    kind: Literal[ProviderOperationKind.OPEN_WAIT] = ProviderOperationKind.OPEN_WAIT

    def __post_init__(self) -> None:
        if (
            self.kind is not ProviderOperationKind.OPEN_WAIT
            or self.wait_kind is not WaitKind.INTERACTION
        ):
            raise ValidationError(code="operation_kind_invalid")
        _optional_wait_id(self.wait_id)
        if self.deadline not in (MISSING, None) and not isinstance(self.deadline, Timestamp):
            raise ValidationError(code="open_interaction_deadline_invalid")
        object.__setattr__(self, "prompt", _required_text(self.prompt, "open_wait_prompt_invalid"))
        object.__setattr__(
            self, "metadata", _optional_object(self.metadata, "open_wait_metadata_invalid")
        )


@final
@dataclass(frozen=True, slots=True, kw_only=True)
class OpenTimerWaitOperation:
    fire_at: Timestamp
    wait_id: WaitId | MissingType | None = MISSING
    reason: str | MissingType | None = MISSING
    metadata: JsonObject | MissingType | None = MISSING
    wait_kind: Literal[WaitKind.TIMER] = WaitKind.TIMER
    kind: Literal[ProviderOperationKind.OPEN_WAIT] = ProviderOperationKind.OPEN_WAIT

    def __post_init__(self) -> None:
        if self.kind is not ProviderOperationKind.OPEN_WAIT or self.wait_kind is not WaitKind.TIMER:
            raise ValidationError(code="operation_kind_invalid")
        _optional_wait_id(self.wait_id)
        if not isinstance(self.fire_at, Timestamp):
            raise ValidationError(code="open_wait_fire_at_invalid")
        object.__setattr__(self, "reason", _optional_text(self.reason, "open_wait_reason_invalid"))
        object.__setattr__(
            self, "metadata", _optional_object(self.metadata, "open_wait_metadata_invalid")
        )


@final
@dataclass(frozen=True, slots=True, kw_only=True)
class OpenJoinWaitOperation:
    target_run_ids: tuple[RunId, ...]
    mode: DelegationJoinMode
    outcome_filter: Literal["completed_only", "terminal_any", "completed_or_failed"]
    failure_policy: Literal["fail_fast", "wait_for_all_terminal"]
    on_satisfied: Literal["cancel_remaining", "detach_remaining", "keep_bound"]
    late_handoff_policy: Literal["ignore", "surface", "add_to_context"]
    wait_id: WaitId | MissingType | None = MISSING
    quorum: int | MissingType | None = MISSING
    reason: str | MissingType | None = MISSING
    metadata: JsonObject | MissingType | None = MISSING
    wait_kind: Literal[WaitKind.JOIN] = WaitKind.JOIN
    kind: Literal[ProviderOperationKind.OPEN_WAIT] = ProviderOperationKind.OPEN_WAIT

    def __post_init__(self) -> None:
        if self.kind is not ProviderOperationKind.OPEN_WAIT or self.wait_kind is not WaitKind.JOIN:
            raise ValidationError(code="operation_kind_invalid")
        _optional_wait_id(self.wait_id)
        targets = _typed_tuple(self.target_run_ids, RunId, "open_join_target_ids_invalid")
        if not targets or len(set(targets)) != len(targets):
            raise ValidationError(code="open_join_target_ids_invalid")
        object.__setattr__(self, "target_run_ids", targets)
        if not isinstance(self.mode, DelegationJoinMode):
            raise ValidationError(code="open_join_mode_invalid")
        if self.outcome_filter not in (
            "completed_only",
            "terminal_any",
            "completed_or_failed",
        ):
            raise ValidationError(code="open_join_outcome_filter_invalid")
        if self.failure_policy not in ("fail_fast", "wait_for_all_terminal"):
            raise ValidationError(code="open_join_failure_policy_invalid")
        if self.on_satisfied not in (
            "cancel_remaining",
            "detach_remaining",
            "keep_bound",
        ):
            raise ValidationError(code="open_join_satisfied_policy_invalid")
        if self.late_handoff_policy not in ("ignore", "surface", "add_to_context"):
            raise ValidationError(code="open_join_late_handoff_invalid")
        if self.mode is DelegationJoinMode.QUORUM:
            if (
                not isinstance(self.quorum, int)
                or isinstance(self.quorum, bool)
                or not 1 <= self.quorum <= len(targets)
            ):
                raise ValidationError(code="open_join_quorum_required")
        elif self.quorum not in (MISSING, None):
            raise ValidationError(code="open_join_quorum_forbidden")
        object.__setattr__(self, "reason", _optional_text(self.reason, "open_wait_reason_invalid"))
        object.__setattr__(
            self, "metadata", _optional_object(self.metadata, "open_wait_metadata_invalid")
        )


@final
@dataclass(frozen=True, slots=True, kw_only=True)
class CreateCheckpointOperation:
    from_position: int
    to_position: int
    checkpoint_id: CheckpointId | MissingType | None = MISSING
    summary: str | MissingType | None = MISSING
    retained_context: JsonObject | MissingType | None = MISSING
    protected_event_types: tuple[str, ...] = ()
    artifact_ids: tuple[ArtifactId, ...] = ()
    kind: Literal[ProviderOperationKind.CREATE_CHECKPOINT] = ProviderOperationKind.CREATE_CHECKPOINT

    def __post_init__(self) -> None:
        if self.kind is not ProviderOperationKind.CREATE_CHECKPOINT:
            raise ValidationError(code="operation_kind_invalid")
        if (
            not isinstance(self.from_position, int)
            or isinstance(self.from_position, bool)
            or not isinstance(self.to_position, int)
            or isinstance(self.to_position, bool)
            or self.from_position < 0
            or self.to_position < self.from_position
        ):
            raise ValidationError(code="create_checkpoint_range_invalid")
        if self.checkpoint_id not in (MISSING, None) and not isinstance(
            self.checkpoint_id, CheckpointId
        ):
            raise ValidationError(code="create_checkpoint_id_invalid")
        object.__setattr__(
            self, "summary", _optional_text(self.summary, "create_checkpoint_summary_invalid")
        )
        object.__setattr__(
            self,
            "retained_context",
            _optional_object(self.retained_context, "create_checkpoint_context_invalid"),
        )
        object.__setattr__(
            self,
            "protected_event_types",
            _text_tuple(self.protected_event_types, "create_checkpoint_event_types_invalid"),
        )
        object.__setattr__(
            self,
            "artifact_ids",
            _typed_tuple(self.artifact_ids, ArtifactId, "create_checkpoint_artifact_ids_invalid"),
        )


@final
@dataclass(frozen=True, slots=True, kw_only=True)
class CompleteRunOperation:
    result: RunResult
    kind: Literal[ProviderOperationKind.COMPLETE_RUN] = ProviderOperationKind.COMPLETE_RUN

    def __post_init__(self) -> None:
        if self.kind is not ProviderOperationKind.COMPLETE_RUN:
            raise ValidationError(code="operation_kind_invalid")
        if not isinstance(self.result, RunResult):
            raise ValidationError(code="complete_run_result_invalid")


@final
@dataclass(frozen=True, slots=True, kw_only=True)
class FailRunOperation:
    message: str
    retryable: bool = False
    kind: Literal[ProviderOperationKind.FAIL_RUN] = ProviderOperationKind.FAIL_RUN

    def __post_init__(self) -> None:
        if self.kind is not ProviderOperationKind.FAIL_RUN:
            raise ValidationError(code="operation_kind_invalid")
        object.__setattr__(
            self, "message", _required_text(self.message, "fail_run_message_invalid")
        )
        if not isinstance(self.retryable, bool):
            raise ValidationError(code="fail_run_retryable_invalid")


@final
@dataclass(frozen=True, slots=True, kw_only=True)
class CancelRunOperation:
    reason: str | MissingType | None = MISSING
    kind: Literal[ProviderOperationKind.CANCEL_RUN] = ProviderOperationKind.CANCEL_RUN

    def __post_init__(self) -> None:
        if self.kind is not ProviderOperationKind.CANCEL_RUN:
            raise ValidationError(code="operation_kind_invalid")
        object.__setattr__(self, "reason", _optional_text(self.reason, "cancel_run_reason_invalid"))


@final
@dataclass(frozen=True, slots=True, kw_only=True)
class BootstrapRunOperation:
    root_id: RunId
    parent_run_id: RunId | MissingType | None = MISSING
    title: str | MissingType | None = MISSING
    objective: str | MissingType | None = MISSING
    metadata: JsonObject | MissingType | None = MISSING
    start_reason: str | MissingType | None = MISSING
    kind: Literal[RuntimeOperationKind.BOOTSTRAP_RUN] = RuntimeOperationKind.BOOTSTRAP_RUN

    def __post_init__(self) -> None:
        if self.kind is not RuntimeOperationKind.BOOTSTRAP_RUN:
            raise ValidationError(code="operation_kind_invalid")
        if not isinstance(self.root_id, RunId):
            raise ValidationError(code="bootstrap_run_root_id_invalid")
        if self.parent_run_id not in (MISSING, None) and not isinstance(self.parent_run_id, RunId):
            raise ValidationError(code="bootstrap_run_parent_id_invalid")
        object.__setattr__(self, "title", _optional_text(self.title, "bootstrap_run_title_invalid"))
        object.__setattr__(
            self,
            "objective",
            _optional_text(self.objective, "bootstrap_run_objective_invalid"),
        )
        object.__setattr__(
            self, "metadata", _optional_object(self.metadata, "bootstrap_run_metadata_invalid")
        )
        object.__setattr__(
            self,
            "start_reason",
            _optional_text(self.start_reason, "bootstrap_run_start_reason_invalid"),
        )


@final
@dataclass(frozen=True, slots=True, kw_only=True)
class StartRunOperation:
    reason: str | MissingType | None = MISSING
    kind: Literal[RuntimeOperationKind.START_RUN] = RuntimeOperationKind.START_RUN

    def __post_init__(self) -> None:
        if self.kind is not RuntimeOperationKind.START_RUN:
            raise ValidationError(code="operation_kind_invalid")
        object.__setattr__(self, "reason", _optional_text(self.reason, "start_run_reason_invalid"))


@final
@dataclass(frozen=True, slots=True, kw_only=True)
class MessageDeltaOperation:
    message_id: MessageId
    delta: str
    kind: Literal[RuntimeOperationKind.MESSAGE_DELTA] = RuntimeOperationKind.MESSAGE_DELTA

    def __post_init__(self) -> None:
        if self.kind is not RuntimeOperationKind.MESSAGE_DELTA:
            raise ValidationError(code="operation_kind_invalid")
        if not isinstance(self.message_id, MessageId):
            raise ValidationError(code="message_delta_id_invalid")
        if not isinstance(self.delta, str):
            raise ValidationError(code="message_delta_invalid")


@final
@dataclass(frozen=True, slots=True, kw_only=True)
class StartModelCallOperation:
    model_call_id: ModelCallId
    kind: Literal[RuntimeOperationKind.START_MODEL_CALL] = RuntimeOperationKind.START_MODEL_CALL

    def __post_init__(self) -> None:
        if self.kind is not RuntimeOperationKind.START_MODEL_CALL:
            raise ValidationError(code="operation_kind_invalid")
        if not isinstance(self.model_call_id, ModelCallId):
            raise ValidationError(code="start_model_call_id_invalid")


@final
@dataclass(frozen=True, slots=True, kw_only=True)
class CompleteModelCallOperation:
    model_call_id: ModelCallId
    outcome: str
    metadata: JsonObject | MissingType | None = MISSING
    kind: Literal[RuntimeOperationKind.COMPLETE_MODEL_CALL] = (
        RuntimeOperationKind.COMPLETE_MODEL_CALL
    )

    def __post_init__(self) -> None:
        if self.kind is not RuntimeOperationKind.COMPLETE_MODEL_CALL:
            raise ValidationError(code="operation_kind_invalid")
        if not isinstance(self.model_call_id, ModelCallId):
            raise ValidationError(code="complete_model_call_id_invalid")
        object.__setattr__(
            self, "outcome", _required_text(self.outcome, "complete_model_call_outcome_invalid")
        )
        object.__setattr__(
            self,
            "metadata",
            _optional_object(self.metadata, "complete_model_call_metadata_invalid"),
        )


@final
@dataclass(frozen=True, slots=True, kw_only=True)
class FailModelCallOperation:
    model_call_id: ModelCallId
    message: str
    classification: ModelCallFailureClassification | MissingType | None = MISSING
    retryable: bool | MissingType | None = MISSING
    evidence: Content | MissingType | None = MISSING
    kind: Literal[RuntimeOperationKind.FAIL_MODEL_CALL] = RuntimeOperationKind.FAIL_MODEL_CALL

    def __post_init__(self) -> None:
        if self.kind is not RuntimeOperationKind.FAIL_MODEL_CALL:
            raise ValidationError(code="operation_kind_invalid")
        if not isinstance(self.model_call_id, ModelCallId):
            raise ValidationError(code="fail_model_call_id_invalid")
        object.__setattr__(
            self, "message", _required_text(self.message, "fail_model_call_message_invalid")
        )
        if self.classification not in (MISSING, None) and not isinstance(
            self.classification, ModelCallFailureClassification
        ):
            raise ValidationError(code="fail_model_call_classification_invalid")
        if self.retryable not in (MISSING, None) and not isinstance(self.retryable, bool):
            raise ValidationError(code="fail_model_call_retryable_invalid")
        if self.evidence not in (MISSING, None) and not isinstance(self.evidence, Content):
            raise ValidationError(code="fail_model_call_evidence_invalid")


@final
@dataclass(frozen=True, slots=True, kw_only=True)
class CancelModelCallOperation:
    model_call_id: ModelCallId
    reason: str | MissingType | None = MISSING
    kind: Literal[RuntimeOperationKind.CANCEL_MODEL_CALL] = RuntimeOperationKind.CANCEL_MODEL_CALL

    def __post_init__(self) -> None:
        if self.kind is not RuntimeOperationKind.CANCEL_MODEL_CALL:
            raise ValidationError(code="operation_kind_invalid")
        if not isinstance(self.model_call_id, ModelCallId):
            raise ValidationError(code="cancel_model_call_id_invalid")
        object.__setattr__(
            self,
            "reason",
            _optional_text(self.reason, "cancel_model_call_reason_invalid"),
        )


@final
@dataclass(frozen=True, slots=True, kw_only=True)
class ResolveApprovalOperation:
    wait_id: WaitId
    decision: Literal["approved", "denied", "cancelled"]
    approved_input: JsonObject | MissingType | None = MISSING
    note: Content | MissingType | None = MISSING
    resolved_by: str | MissingType | None = MISSING
    kind: Literal[RuntimeOperationKind.RESOLVE_APPROVAL] = RuntimeOperationKind.RESOLVE_APPROVAL

    def __post_init__(self) -> None:
        if self.kind is not RuntimeOperationKind.RESOLVE_APPROVAL:
            raise ValidationError(code="operation_kind_invalid")
        if not isinstance(self.wait_id, WaitId):
            raise ValidationError(code="resolve_approval_wait_id_invalid")
        if self.decision not in ("approved", "denied", "cancelled"):
            raise ValidationError(code="resolve_approval_decision_invalid")
        approved_input = _optional_object(self.approved_input, "resolve_approval_input_invalid")
        if self.decision != "approved" and approved_input not in (MISSING, None):
            raise ValidationError(code="resolve_approval_input_forbidden")
        object.__setattr__(self, "approved_input", approved_input)
        if self.note not in (MISSING, None) and not isinstance(self.note, Content):
            raise ValidationError(code="resolve_approval_note_invalid")
        object.__setattr__(
            self,
            "resolved_by",
            _optional_text(self.resolved_by, "resolve_approval_actor_invalid"),
        )


@final
@dataclass(frozen=True, slots=True, kw_only=True)
class ResumeApprovedActionOperation:
    wait_id: WaitId
    kind: Literal[RuntimeOperationKind.RESUME_APPROVED_ACTION] = (
        RuntimeOperationKind.RESUME_APPROVED_ACTION
    )

    def __post_init__(self) -> None:
        if self.kind is not RuntimeOperationKind.RESUME_APPROVED_ACTION:
            raise ValidationError(code="operation_kind_invalid")
        if not isinstance(self.wait_id, WaitId):
            raise ValidationError(code="resume_approval_wait_id_invalid")


@final
@dataclass(frozen=True, slots=True, kw_only=True)
class ResolveInteractionWaitOperation:
    wait_id: WaitId
    response: Content
    request_event_id: EventId | MissingType | None = MISSING
    responded_by: str | MissingType | None = MISSING
    kind: Literal[RuntimeOperationKind.RESOLVE_WAIT] = RuntimeOperationKind.RESOLVE_WAIT

    def __post_init__(self) -> None:
        if self.kind is not RuntimeOperationKind.RESOLVE_WAIT:
            raise ValidationError(code="operation_kind_invalid")
        if not isinstance(self.wait_id, WaitId):
            raise ValidationError(code="resolve_wait_id_invalid")
        if not isinstance(self.response, Content):
            raise ValidationError(code="resolve_interaction_response_invalid")
        if self.request_event_id not in (MISSING, None) and not isinstance(
            self.request_event_id, EventId
        ):
            raise ValidationError(code="resolve_interaction_request_event_id_invalid")
        object.__setattr__(
            self,
            "responded_by",
            _optional_text(self.responded_by, "resolve_interaction_actor_invalid"),
        )


@final
@dataclass(frozen=True, slots=True, kw_only=True)
class FireTimerWaitOperation:
    wait_id: WaitId
    fired_by: str | MissingType | None = MISSING
    kind: Literal[RuntimeOperationKind.RESOLVE_WAIT] = RuntimeOperationKind.RESOLVE_WAIT

    def __post_init__(self) -> None:
        if self.kind is not RuntimeOperationKind.RESOLVE_WAIT:
            raise ValidationError(code="operation_kind_invalid")
        if not isinstance(self.wait_id, WaitId):
            raise ValidationError(code="resolve_wait_id_invalid")
        object.__setattr__(
            self,
            "fired_by",
            _optional_text(self.fired_by, "fire_timer_actor_invalid"),
        )


@final
@dataclass(frozen=True, slots=True, kw_only=True)
class ResolveJoinWaitOperation:
    wait_id: WaitId
    kind: Literal[RuntimeOperationKind.RESOLVE_WAIT] = RuntimeOperationKind.RESOLVE_WAIT

    def __post_init__(self) -> None:
        if self.kind is not RuntimeOperationKind.RESOLVE_WAIT:
            raise ValidationError(code="operation_kind_invalid")
        if not isinstance(self.wait_id, WaitId):
            raise ValidationError(code="resolve_wait_id_invalid")


@final
@dataclass(frozen=True, slots=True, kw_only=True)
class CancelWaitOperation:
    wait_id: WaitId
    wait_kind: WaitKind
    reason: str | MissingType | None = MISSING
    kind: Literal[RuntimeOperationKind.RESOLVE_WAIT] = RuntimeOperationKind.RESOLVE_WAIT

    def __post_init__(self) -> None:
        if self.kind is not RuntimeOperationKind.RESOLVE_WAIT:
            raise ValidationError(code="operation_kind_invalid")
        if not isinstance(self.wait_id, WaitId):
            raise ValidationError(code="cancel_wait_id_invalid")
        if not isinstance(self.wait_kind, WaitKind):
            raise ValidationError(code="cancel_wait_kind_invalid")
        object.__setattr__(
            self, "reason", _optional_text(self.reason, "cancel_wait_reason_invalid")
        )


@final
@dataclass(frozen=True, slots=True, kw_only=True)
class ExpireWaitOperation:
    wait_id: WaitId
    wait_kind: WaitKind
    reason: str | MissingType | None = MISSING
    kind: Literal[RuntimeOperationKind.RESOLVE_WAIT] = RuntimeOperationKind.RESOLVE_WAIT

    def __post_init__(self) -> None:
        if self.kind is not RuntimeOperationKind.RESOLVE_WAIT:
            raise ValidationError(code="operation_kind_invalid")
        if not isinstance(self.wait_id, WaitId):
            raise ValidationError(code="expire_wait_id_invalid")
        if not isinstance(self.wait_kind, WaitKind):
            raise ValidationError(code="expire_wait_kind_invalid")
        object.__setattr__(
            self, "reason", _optional_text(self.reason, "expire_wait_reason_invalid")
        )


@final
@dataclass(frozen=True, slots=True, kw_only=True)
class MarkActionUnknownOperation:
    action_id: ActionId
    reliability: ActionReliability
    reason: str
    message: str | MissingType | None = MISSING
    note: Content | MissingType | None = MISSING
    evidence: Content | MissingType | None = MISSING
    kind: Literal[RuntimeOperationKind.MARK_ACTION_UNKNOWN] = (
        RuntimeOperationKind.MARK_ACTION_UNKNOWN
    )

    def __post_init__(self) -> None:
        if self.kind is not RuntimeOperationKind.MARK_ACTION_UNKNOWN:
            raise ValidationError(code="operation_kind_invalid")
        if not isinstance(self.action_id, ActionId):
            raise ValidationError(code="mark_action_unknown_id_invalid")
        if not isinstance(self.reliability, ActionReliability):
            raise ValidationError(code="mark_action_unknown_reliability_invalid")
        object.__setattr__(
            self, "reason", _required_text(self.reason, "mark_action_unknown_reason_invalid")
        )
        object.__setattr__(
            self, "message", _optional_text(self.message, "mark_action_unknown_message_invalid")
        )
        for name in ("note", "evidence"):
            value = getattr(self, name)
            if value not in (MISSING, None) and not isinstance(value, Content):
                raise ValidationError(code=f"mark_action_unknown_{name}_invalid")


@final
@dataclass(frozen=True, slots=True, kw_only=True)
class ReconcileActionOperation:
    action_id: ActionId
    unknown_event_id: EventId
    outcome: Literal["completed", "failed", "cancelled"]
    evidence: Content
    note: Content | MissingType | None = MISSING
    reconciled_by: str | MissingType | None = MISSING
    kind: Literal[RuntimeOperationKind.RECONCILE_ACTION] = RuntimeOperationKind.RECONCILE_ACTION

    def __post_init__(self) -> None:
        if self.kind is not RuntimeOperationKind.RECONCILE_ACTION:
            raise ValidationError(code="operation_kind_invalid")
        if not isinstance(self.action_id, ActionId):
            raise ValidationError(code="reconcile_action_id_invalid")
        if not isinstance(self.unknown_event_id, EventId):
            raise ValidationError(code="reconcile_action_unknown_event_id_invalid")
        if self.outcome not in ("completed", "failed", "cancelled"):
            raise ValidationError(code="reconcile_action_outcome_invalid")
        if not isinstance(self.evidence, Content):
            raise ValidationError(code="reconcile_action_evidence_invalid")
        if self.note not in (MISSING, None) and not isinstance(self.note, Content):
            raise ValidationError(code="reconcile_action_note_invalid")
        object.__setattr__(
            self,
            "reconciled_by",
            _optional_text(self.reconciled_by, "reconcile_action_actor_invalid"),
        )


@final
@dataclass(frozen=True, slots=True, kw_only=True)
class StartActionOperation:
    action_id: ActionId
    capability_id: CapabilityId
    action_name: str
    input_hash: str
    kind: Literal[RuntimeOperationKind.START_ACTION] = RuntimeOperationKind.START_ACTION

    def __post_init__(self) -> None:
        if self.kind is not RuntimeOperationKind.START_ACTION:
            raise ValidationError(code="operation_kind_invalid")
        if not isinstance(self.action_id, ActionId):
            raise ValidationError(code="start_action_id_invalid")
        if not isinstance(self.capability_id, CapabilityId):
            raise ValidationError(code="start_action_capability_id_invalid")
        object.__setattr__(
            self, "action_name", _required_text(self.action_name, "start_action_name_invalid")
        )
        if (
            not isinstance(self.input_hash, str)
            or len(self.input_hash) != 64
            or any(character not in "0123456789abcdef" for character in self.input_hash)
        ):
            raise ValidationError(code="start_action_input_hash_invalid")


@final
@dataclass(frozen=True, slots=True, kw_only=True)
class ProducedArtifact:
    artifact_id: ArtifactId
    kind: str
    byte_length: int
    sha256: str
    content_type: str | MissingType | None = MISSING
    preview: str | MissingType | None = MISSING
    metadata: JsonObject | MissingType | None = MISSING

    def __post_init__(self) -> None:
        if not isinstance(self.artifact_id, ArtifactId):
            raise ValidationError(code="produced_artifact_id_invalid")
        object.__setattr__(
            self, "kind", _required_text(self.kind, "produced_artifact_kind_invalid")
        )
        if (
            isinstance(self.byte_length, bool)
            or not isinstance(self.byte_length, int)
            or self.byte_length < 0
        ):
            raise ValidationError(code="produced_artifact_length_invalid")
        if (
            not isinstance(self.sha256, str)
            or len(self.sha256) != 64
            or any(character not in "0123456789abcdef" for character in self.sha256)
        ):
            raise ValidationError(code="produced_artifact_sha256_invalid")
        for name in ("content_type", "preview"):
            object.__setattr__(
                self,
                name,
                _optional_text(getattr(self, name), f"produced_artifact_{name}_invalid"),
            )
        object.__setattr__(
            self,
            "metadata",
            _optional_object(self.metadata, "produced_artifact_metadata_invalid"),
        )


@final
@dataclass(frozen=True, slots=True, kw_only=True)
class CompleteActionOperation:
    action_id: ActionId
    result: Content | MissingType | None = MISSING
    effects: tuple[EffectEntry, ...] = ()
    artifact_ids: tuple[ArtifactId, ...] = ()
    produced_artifacts: tuple[ProducedArtifact, ...] = ()
    kind: Literal[RuntimeOperationKind.COMPLETE_ACTION] = RuntimeOperationKind.COMPLETE_ACTION

    def __post_init__(self) -> None:
        if self.kind is not RuntimeOperationKind.COMPLETE_ACTION:
            raise ValidationError(code="operation_kind_invalid")
        if not isinstance(self.action_id, ActionId):
            raise ValidationError(code="complete_action_id_invalid")
        if self.result not in (MISSING, None) and not isinstance(self.result, Content):
            raise ValidationError(code="complete_action_result_invalid")
        object.__setattr__(
            self,
            "effects",
            _typed_tuple(self.effects, EffectEntry, "complete_action_effects_invalid"),
        )
        object.__setattr__(
            self,
            "artifact_ids",
            _typed_tuple(self.artifact_ids, ArtifactId, "complete_action_artifact_ids_invalid"),
        )
        produced = _typed_tuple(
            self.produced_artifacts,
            ProducedArtifact,
            "complete_action_produced_artifacts_invalid",
        )
        if len({item.artifact_id for item in produced}) != len(produced):
            raise ValidationError(code="complete_action_produced_artifact_duplicate")
        produced_ids = {item.artifact_id for item in produced}
        if not produced_ids <= set(self.artifact_ids):
            raise ValidationError(code="complete_action_produced_artifact_unreferenced")
        object.__setattr__(self, "produced_artifacts", produced)


@final
@dataclass(frozen=True, slots=True, kw_only=True)
class FailActionOperation:
    action_id: ActionId
    error: ActionFailure
    effects: tuple[EffectEntry, ...] = ()
    evidence: Content | MissingType | None = MISSING
    kind: Literal[RuntimeOperationKind.FAIL_ACTION] = RuntimeOperationKind.FAIL_ACTION

    def __post_init__(self) -> None:
        if self.kind is not RuntimeOperationKind.FAIL_ACTION:
            raise ValidationError(code="operation_kind_invalid")
        if not isinstance(self.action_id, ActionId):
            raise ValidationError(code="fail_action_id_invalid")
        if not isinstance(self.error, ActionFailure):
            raise ValidationError(code="fail_action_error_invalid")
        object.__setattr__(
            self,
            "effects",
            _typed_tuple(self.effects, EffectEntry, "fail_action_effects_invalid"),
        )
        if self.evidence not in (MISSING, None) and not isinstance(self.evidence, Content):
            raise ValidationError(code="fail_action_evidence_invalid")


@final
@dataclass(frozen=True, slots=True, kw_only=True)
class CancelActionOperation:
    action_id: ActionId
    reason: str | MissingType | None = MISSING
    kind: Literal[RuntimeOperationKind.CANCEL_ACTION] = RuntimeOperationKind.CANCEL_ACTION

    def __post_init__(self) -> None:
        if self.kind is not RuntimeOperationKind.CANCEL_ACTION:
            raise ValidationError(code="operation_kind_invalid")
        if not isinstance(self.action_id, ActionId):
            raise ValidationError(code="cancel_action_id_invalid")
        object.__setattr__(
            self, "reason", _optional_text(self.reason, "cancel_action_reason_invalid")
        )


@final
@dataclass(frozen=True, slots=True, kw_only=True)
class RecordCheckOperation:
    subject: str
    rule: str
    status: CheckStatus
    validator: str
    summary: str
    check_count: int
    result: Content
    check_id: CheckId | MissingType | None = MISSING
    message: str | MissingType | None = MISSING
    evidence: Content | MissingType | None = MISSING
    kind: Literal[RuntimeOperationKind.RECORD_CHECK] = RuntimeOperationKind.RECORD_CHECK

    def __post_init__(self) -> None:
        if self.kind is not RuntimeOperationKind.RECORD_CHECK:
            raise ValidationError(code="operation_kind_invalid")
        for name in ("subject", "rule", "validator", "summary"):
            object.__setattr__(
                self, name, _required_text(getattr(self, name), f"record_check_{name}_invalid")
            )
        if not isinstance(self.status, CheckStatus):
            raise ValidationError(code="record_check_status_invalid")
        if (
            isinstance(self.check_count, bool)
            or not isinstance(self.check_count, int)
            or self.check_count < 0
        ):
            raise ValidationError(code="record_check_count_invalid")
        if not isinstance(self.result, Content):
            raise ValidationError(code="record_check_result_invalid")
        if self.check_id not in (MISSING, None) and not isinstance(self.check_id, CheckId):
            raise ValidationError(code="record_check_id_invalid")
        object.__setattr__(
            self, "message", _optional_text(self.message, "record_check_message_invalid")
        )
        if self.evidence not in (MISSING, None) and not isinstance(self.evidence, Content):
            raise ValidationError(code="record_check_evidence_invalid")


@final
@dataclass(frozen=True, slots=True, kw_only=True)
class RecordAnnotationOperation:
    content: Content
    annotation_id: AnnotationId | MissingType | None = MISSING
    metadata: JsonObject | MissingType | None = MISSING
    kind: Literal[RuntimeOperationKind.RECORD_ANNOTATION] = RuntimeOperationKind.RECORD_ANNOTATION

    def __post_init__(self) -> None:
        if self.kind is not RuntimeOperationKind.RECORD_ANNOTATION:
            raise ValidationError(code="operation_kind_invalid")
        if not isinstance(self.content, Content):
            raise ValidationError(code="record_annotation_content_invalid")
        if self.annotation_id not in (MISSING, None) and not isinstance(
            self.annotation_id, AnnotationId
        ):
            raise ValidationError(code="record_annotation_id_invalid")
        object.__setattr__(
            self, "metadata", _optional_object(self.metadata, "record_annotation_metadata_invalid")
        )


@final
@dataclass(frozen=True, slots=True, kw_only=True)
class CompleteDelegationOperation:
    delegated_run_id: RunId
    delegation_id: DelegationId | MissingType | None = MISSING
    result: RunResult | MissingType | None = MISSING
    note: Content | MissingType | None = MISSING
    kind: Literal[RuntimeOperationKind.COMPLETE_DELEGATION] = (
        RuntimeOperationKind.COMPLETE_DELEGATION
    )

    def __post_init__(self) -> None:
        if self.kind is not RuntimeOperationKind.COMPLETE_DELEGATION:
            raise ValidationError(code="operation_kind_invalid")
        if not isinstance(self.delegated_run_id, RunId):
            raise ValidationError(code="complete_delegation_run_id_invalid")
        if self.delegation_id not in (MISSING, None) and not isinstance(
            self.delegation_id, DelegationId
        ):
            raise ValidationError(code="complete_delegation_id_invalid")
        if self.result not in (MISSING, None) and not isinstance(self.result, RunResult):
            raise ValidationError(code="complete_delegation_result_invalid")
        if self.note not in (MISSING, None) and not isinstance(self.note, Content):
            raise ValidationError(code="complete_delegation_note_invalid")


@final
@dataclass(frozen=True, slots=True, kw_only=True)
class FailDelegationOperation:
    delegated_run_id: RunId
    message: str
    delegation_id: DelegationId | MissingType | None = MISSING
    evidence: Content | MissingType | None = MISSING
    kind: Literal[RuntimeOperationKind.FAIL_DELEGATION] = RuntimeOperationKind.FAIL_DELEGATION

    def __post_init__(self) -> None:
        if self.kind is not RuntimeOperationKind.FAIL_DELEGATION:
            raise ValidationError(code="operation_kind_invalid")
        if not isinstance(self.delegated_run_id, RunId):
            raise ValidationError(code="fail_delegation_run_id_invalid")
        object.__setattr__(
            self, "message", _required_text(self.message, "fail_delegation_message_invalid")
        )
        if self.delegation_id not in (MISSING, None) and not isinstance(
            self.delegation_id, DelegationId
        ):
            raise ValidationError(code="fail_delegation_id_invalid")
        if self.evidence not in (MISSING, None) and not isinstance(self.evidence, Content):
            raise ValidationError(code="fail_delegation_evidence_invalid")


@final
@dataclass(frozen=True, slots=True, kw_only=True)
class CancelDelegationOperation:
    delegated_run_id: RunId
    delegation_id: DelegationId | MissingType | None = MISSING
    reason: str | MissingType | None = MISSING
    kind: Literal[RuntimeOperationKind.CANCEL_DELEGATION] = RuntimeOperationKind.CANCEL_DELEGATION

    def __post_init__(self) -> None:
        if self.kind is not RuntimeOperationKind.CANCEL_DELEGATION:
            raise ValidationError(code="operation_kind_invalid")
        if not isinstance(self.delegated_run_id, RunId):
            raise ValidationError(code="cancel_delegation_run_id_invalid")
        if self.delegation_id not in (MISSING, None) and not isinstance(
            self.delegation_id, DelegationId
        ):
            raise ValidationError(code="cancel_delegation_id_invalid")
        object.__setattr__(
            self, "reason", _optional_text(self.reason, "cancel_delegation_reason_invalid")
        )


@final
@dataclass(frozen=True, slots=True, kw_only=True)
class GrantCapabilityAuthorityOperation:
    capability_id: CapabilityId
    authority_id: AuthorityId | MissingType | None = MISSING
    constraints: JsonObject | MissingType | None = MISSING
    granted_by: str | MissingType | None = MISSING
    metadata: JsonObject | MissingType | None = MISSING
    kind: Literal[RuntimeOperationKind.GRANT_AUTHORITY] = RuntimeOperationKind.GRANT_AUTHORITY

    def __post_init__(self) -> None:
        if self.kind is not RuntimeOperationKind.GRANT_AUTHORITY:
            raise ValidationError(code="operation_kind_invalid")
        if not isinstance(self.capability_id, CapabilityId):
            raise ValidationError(code="grant_authority_capability_id_invalid")
        if self.authority_id not in (MISSING, None) and not isinstance(
            self.authority_id, AuthorityId
        ):
            raise ValidationError(code="grant_authority_id_invalid")
        object.__setattr__(
            self,
            "constraints",
            _optional_object(self.constraints, "grant_authority_constraints_invalid"),
        )
        object.__setattr__(
            self, "granted_by", _optional_text(self.granted_by, "grant_authority_actor_invalid")
        )
        object.__setattr__(
            self, "metadata", _optional_object(self.metadata, "grant_authority_metadata_invalid")
        )


@final
@dataclass(frozen=True, slots=True, kw_only=True)
class GrantPolicyAuthorityOperation:
    rule_id: PolicyRuleId
    rule: JsonObject
    authority_id: AuthorityId | MissingType | None = MISSING
    constraints: JsonObject | MissingType | None = MISSING
    granted_by: str | MissingType | None = MISSING
    kind: Literal[RuntimeOperationKind.GRANT_AUTHORITY] = RuntimeOperationKind.GRANT_AUTHORITY

    def __post_init__(self) -> None:
        if self.kind is not RuntimeOperationKind.GRANT_AUTHORITY:
            raise ValidationError(code="operation_kind_invalid")
        if not isinstance(self.rule_id, PolicyRuleId):
            raise ValidationError(code="grant_policy_rule_id_invalid")
        rule = freeze_json(self.rule)
        if not isinstance(rule, JsonObject):
            raise ValidationError(code="grant_policy_rule_invalid")
        object.__setattr__(self, "rule", rule)
        if self.authority_id not in (MISSING, None) and not isinstance(
            self.authority_id, AuthorityId
        ):
            raise ValidationError(code="grant_authority_id_invalid")
        object.__setattr__(
            self,
            "constraints",
            _optional_object(self.constraints, "grant_authority_constraints_invalid"),
        )
        object.__setattr__(
            self, "granted_by", _optional_text(self.granted_by, "grant_authority_actor_invalid")
        )


@final
@dataclass(frozen=True, slots=True, kw_only=True)
class RevokeCapabilityAuthorityOperation:
    capability_id: CapabilityId
    authority_id: AuthorityId | MissingType | None = MISSING
    reason: str | MissingType | None = MISSING
    kind: Literal[RuntimeOperationKind.REVOKE_AUTHORITY] = RuntimeOperationKind.REVOKE_AUTHORITY

    def __post_init__(self) -> None:
        if self.kind is not RuntimeOperationKind.REVOKE_AUTHORITY:
            raise ValidationError(code="operation_kind_invalid")
        if not isinstance(self.capability_id, CapabilityId):
            raise ValidationError(code="revoke_authority_capability_id_invalid")
        if self.authority_id not in (MISSING, None) and not isinstance(
            self.authority_id, AuthorityId
        ):
            raise ValidationError(code="revoke_authority_id_invalid")
        object.__setattr__(
            self, "reason", _optional_text(self.reason, "revoke_authority_reason_invalid")
        )


@final
@dataclass(frozen=True, slots=True, kw_only=True)
class RevokePolicyAuthorityOperation:
    rule_id: PolicyRuleId
    authority_id: AuthorityId | MissingType | None = MISSING
    reason: str | MissingType | None = MISSING
    kind: Literal[RuntimeOperationKind.REVOKE_AUTHORITY] = RuntimeOperationKind.REVOKE_AUTHORITY

    def __post_init__(self) -> None:
        if self.kind is not RuntimeOperationKind.REVOKE_AUTHORITY:
            raise ValidationError(code="operation_kind_invalid")
        if not isinstance(self.rule_id, PolicyRuleId):
            raise ValidationError(code="revoke_policy_rule_id_invalid")
        if self.authority_id not in (MISSING, None) and not isinstance(
            self.authority_id, AuthorityId
        ):
            raise ValidationError(code="revoke_authority_id_invalid")
        object.__setattr__(
            self, "reason", _optional_text(self.reason, "revoke_authority_reason_invalid")
        )


@final
@dataclass(frozen=True, slots=True, kw_only=True)
class OperationBatch:
    actions: tuple[CreateActionOperation, ...]
    kind: Literal["operation_batch"] = "operation_batch"

    def __post_init__(self) -> None:
        if self.kind != "operation_batch":
            raise ValidationError(code="operation_kind_invalid")
        actions = _typed_tuple(
            self.actions, CreateActionOperation, "operation_batch_actions_invalid"
        )
        if not actions:
            raise ValidationError(code="operation_batch_actions_empty")
        object.__setattr__(self, "actions", actions)


type ModelOperation = (
    AddMessageOperation
    | CreateActionOperation
    | CreateDelegationOperation
    | OpenApprovalWaitOperation
    | OpenInteractionWaitOperation
    | OpenTimerWaitOperation
    | OpenJoinWaitOperation
    | CreateCheckpointOperation
    | CompleteRunOperation
    | FailRunOperation
    | CancelRunOperation
    | OperationBatch
)

type RuntimeOperation = (
    BootstrapRunOperation
    | StartRunOperation
    | MessageDeltaOperation
    | StartModelCallOperation
    | CompleteModelCallOperation
    | FailModelCallOperation
    | CancelModelCallOperation
    | ResolveApprovalOperation
    | ResumeApprovedActionOperation
    | StartActionOperation
    | CompleteActionOperation
    | FailActionOperation
    | CancelActionOperation
    | ResolveInteractionWaitOperation
    | FireTimerWaitOperation
    | ResolveJoinWaitOperation
    | CancelWaitOperation
    | ExpireWaitOperation
    | MarkActionUnknownOperation
    | ReconcileActionOperation
    | RecordCheckOperation
    | RecordAnnotationOperation
    | CompleteDelegationOperation
    | FailDelegationOperation
    | CancelDelegationOperation
    | GrantCapabilityAuthorityOperation
    | GrantPolicyAuthorityOperation
    | RevokeCapabilityAuthorityOperation
    | RevokePolicyAuthorityOperation
)

type CommandOperation = ModelOperation | RuntimeOperation

_COMMAND_OPERATION_TYPES = (
    AddMessageOperation,
    CreateActionOperation,
    CreateDelegationOperation,
    OpenApprovalWaitOperation,
    OpenInteractionWaitOperation,
    OpenTimerWaitOperation,
    OpenJoinWaitOperation,
    CreateCheckpointOperation,
    CompleteRunOperation,
    FailRunOperation,
    CancelRunOperation,
    OperationBatch,
    BootstrapRunOperation,
    StartRunOperation,
    MessageDeltaOperation,
    StartModelCallOperation,
    CompleteModelCallOperation,
    FailModelCallOperation,
    CancelModelCallOperation,
    ResolveApprovalOperation,
    ResumeApprovedActionOperation,
    StartActionOperation,
    CompleteActionOperation,
    FailActionOperation,
    CancelActionOperation,
    ResolveInteractionWaitOperation,
    FireTimerWaitOperation,
    ResolveJoinWaitOperation,
    CancelWaitOperation,
    ExpireWaitOperation,
    MarkActionUnknownOperation,
    ReconcileActionOperation,
    RecordCheckOperation,
    RecordAnnotationOperation,
    CompleteDelegationOperation,
    FailDelegationOperation,
    CancelDelegationOperation,
    GrantCapabilityAuthorityOperation,
    GrantPolicyAuthorityOperation,
    RevokeCapabilityAuthorityOperation,
    RevokePolicyAuthorityOperation,
)


@final
@dataclass(frozen=True, slots=True, kw_only=True)
class Command:
    command_id: CommandId
    run_id: RunId
    origin: CommandOrigin
    operation: CommandOperation
    content: Content | MissingType | None = MISSING
    actor: str | MissingType | None = MISSING
    model_call_id: ModelCallId | MissingType | None = MISSING
    idempotency_key: str | MissingType | None = MISSING
    created_at: Timestamp | MissingType | None = MISSING
    metadata: JsonObject | MissingType | None = MISSING

    def __post_init__(self) -> None:
        if not isinstance(self.command_id, CommandId):
            raise ValidationError(code="command_id_invalid")
        if not isinstance(self.run_id, RunId):
            raise ValidationError(code="command_run_id_invalid")
        if not isinstance(self.origin, CommandOrigin):
            raise ValidationError(code="command_origin_invalid")
        if not isinstance(self.operation, _COMMAND_OPERATION_TYPES):
            raise ValidationError(code="command_operation_invalid")
        if self.content not in (MISSING, None) and not isinstance(self.content, Content):
            raise ValidationError(code="command_content_invalid")
        object.__setattr__(self, "actor", _optional_text(self.actor, "command_actor_invalid"))
        if self.model_call_id not in (MISSING, None) and not isinstance(
            self.model_call_id, ModelCallId
        ):
            raise ValidationError(code="command_model_call_id_invalid")
        object.__setattr__(
            self,
            "idempotency_key",
            _optional_text(self.idempotency_key, "command_idempotency_key_invalid"),
        )
        if self.created_at not in (MISSING, None) and not isinstance(self.created_at, Timestamp):
            raise ValidationError(code="command_created_at_invalid")
        object.__setattr__(
            self, "metadata", _optional_object(self.metadata, "command_metadata_invalid")
        )


@final
@dataclass(frozen=True, slots=True, kw_only=True)
class CommandResult:
    command_id: CommandId
    decision: CommandDecision

    def __post_init__(self) -> None:
        if not isinstance(self.command_id, CommandId):
            raise ValidationError(code="command_result_id_invalid")
        if not isinstance(
            self.decision,
            (
                AcceptedCommandDecision,
                RejectedCommandDecision,
                DeferredCommandDecision,
                SupersededCommandDecision,
            ),
        ):
            raise ValidationError(code="command_result_decision_invalid")
