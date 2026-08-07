"""Immutable root concepts for durable OpenRund runs."""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import StrEnum
from typing import Literal, cast, final

from openrund.contracts.content import Content, RunResult
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
    LeaseId,
    MessageId,
    ModelCallId,
    PolicyRuleId,
    RunId,
    WaitId,
)
from openrund.contracts.json import MISSING, JsonObject, MissingType, freeze_json
from openrund.contracts.time import Timestamp
from openrund.errors import ValidationError
from openrund.paths import LocalPath


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


def _text_tuple(value: object, code: str, *, allow_empty: bool = True) -> tuple[str, ...]:
    items = _typed_tuple(value, str, code)
    if not allow_empty and not items:
        raise ValidationError(code=code)
    if any(item == "" for item in items):
        raise ValidationError(code=code)
    return items


class RunStatus(StrEnum):
    CREATED = "created"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@final
@dataclass(frozen=True, slots=True, kw_only=True)
class Run:
    run_id: RunId
    root_id: RunId
    status: RunStatus
    parent_run_id: RunId | MissingType | None = MISSING
    title: str | MissingType | None = MISSING
    objective: str | MissingType | None = MISSING
    result: RunResult | MissingType | None = MISSING
    contract: RunContract | MissingType | None = MISSING
    metadata: JsonObject | MissingType | None = MISSING

    def __post_init__(self) -> None:
        if not isinstance(self.run_id, RunId):
            raise ValidationError(code="run_id_invalid")
        if not isinstance(self.root_id, RunId):
            raise ValidationError(code="run_root_id_invalid")
        if not isinstance(self.status, RunStatus):
            raise ValidationError(code="run_status_invalid")
        if self.parent_run_id not in (MISSING, None) and not isinstance(self.parent_run_id, RunId):
            raise ValidationError(code="run_parent_id_invalid")
        object.__setattr__(self, "title", _optional_text(self.title, "run_title_invalid"))
        object.__setattr__(
            self, "objective", _optional_text(self.objective, "run_objective_invalid")
        )
        if self.result not in (MISSING, None) and not isinstance(self.result, RunResult):
            raise ValidationError(code="run_result_invalid")
        if self.contract not in (MISSING, None) and not isinstance(self.contract, RunContract):
            raise ValidationError(code="run_contract_invalid")
        object.__setattr__(
            self, "metadata", _optional_object(self.metadata, "run_metadata_invalid")
        )


class MessageRole(StrEnum):
    USER = "user"
    CLIENT = "client"
    EXTERNAL = "external"
    ASSISTANT = "assistant"
    SYSTEM = "system"


@final
@dataclass(frozen=True, slots=True, kw_only=True)
class Message:
    message_id: MessageId
    run_id: RunId
    role: MessageRole
    content: Content
    model_call_id: ModelCallId | MissingType | None = MISSING
    timestamp: Timestamp | MissingType | None = MISSING
    metadata: JsonObject | MissingType | None = MISSING

    def __post_init__(self) -> None:
        if not isinstance(self.message_id, MessageId):
            raise ValidationError(code="message_id_invalid")
        if not isinstance(self.run_id, RunId):
            raise ValidationError(code="message_run_id_invalid")
        if not isinstance(self.role, MessageRole):
            raise ValidationError(code="message_role_invalid")
        if not isinstance(self.content, Content):
            raise ValidationError(code="message_content_invalid")
        if self.model_call_id not in (MISSING, None) and not isinstance(
            self.model_call_id, ModelCallId
        ):
            raise ValidationError(code="message_model_call_id_invalid")
        if self.timestamp not in (MISSING, None) and not isinstance(self.timestamp, Timestamp):
            raise ValidationError(code="message_timestamp_invalid")
        object.__setattr__(
            self, "metadata", _optional_object(self.metadata, "message_metadata_invalid")
        )


@final
@dataclass(frozen=True, slots=True, kw_only=True)
class ModelCall:
    model_call_id: ModelCallId
    run_id: RunId
    request: Content
    response: Content | MissingType | None = MISSING
    provider: str | MissingType | None = MISSING
    metadata: JsonObject | MissingType | None = MISSING

    def __post_init__(self) -> None:
        if not isinstance(self.model_call_id, ModelCallId):
            raise ValidationError(code="model_call_id_invalid")
        if not isinstance(self.run_id, RunId):
            raise ValidationError(code="model_call_run_id_invalid")
        if not isinstance(self.request, Content):
            raise ValidationError(code="model_call_request_invalid")
        if self.response not in (MISSING, None) and not isinstance(self.response, Content):
            raise ValidationError(code="model_call_response_invalid")
        object.__setattr__(
            self, "provider", _optional_text(self.provider, "model_call_provider_invalid")
        )
        object.__setattr__(
            self, "metadata", _optional_object(self.metadata, "model_call_metadata_invalid")
        )


class WaitKind(StrEnum):
    APPROVAL = "approval"
    INTERACTION = "interaction"
    TIMER = "timer"
    JOIN = "join"
    RECONCILIATION = "reconciliation"


def _validate_wait_common(
    wait_id: object,
    run_id: object,
    opened_by_command_id: object,
    metadata: object,
) -> JsonObject | MissingType | None:
    if not isinstance(wait_id, WaitId):
        raise ValidationError(code="wait_id_invalid")
    if not isinstance(run_id, RunId):
        raise ValidationError(code="wait_run_id_invalid")
    if not isinstance(opened_by_command_id, CommandId):
        raise ValidationError(code="wait_command_id_invalid")
    return _optional_object(metadata, "wait_metadata_invalid")


@final
@dataclass(frozen=True, slots=True, kw_only=True)
class ApprovalWait:
    wait_id: WaitId
    run_id: RunId
    opened_by_command_id: CommandId
    target: str
    reason: str
    metadata: JsonObject | MissingType | None = MISSING
    kind: Literal[WaitKind.APPROVAL] = WaitKind.APPROVAL

    def __post_init__(self) -> None:
        if self.kind is not WaitKind.APPROVAL:
            raise ValidationError(code="wait_kind_invalid")
        object.__setattr__(
            self,
            "metadata",
            _validate_wait_common(
                self.wait_id, self.run_id, self.opened_by_command_id, self.metadata
            ),
        )
        object.__setattr__(self, "target", _required_text(self.target, "wait_target_invalid"))
        object.__setattr__(self, "reason", _required_text(self.reason, "wait_reason_invalid"))


@final
@dataclass(frozen=True, slots=True, kw_only=True)
class InteractionWait:
    wait_id: WaitId
    run_id: RunId
    opened_by_command_id: CommandId
    prompt: str
    metadata: JsonObject | MissingType | None = MISSING
    kind: Literal[WaitKind.INTERACTION] = WaitKind.INTERACTION

    def __post_init__(self) -> None:
        if self.kind is not WaitKind.INTERACTION:
            raise ValidationError(code="wait_kind_invalid")
        object.__setattr__(
            self,
            "metadata",
            _validate_wait_common(
                self.wait_id, self.run_id, self.opened_by_command_id, self.metadata
            ),
        )
        object.__setattr__(self, "prompt", _required_text(self.prompt, "wait_prompt_invalid"))


@final
@dataclass(frozen=True, slots=True, kw_only=True)
class TimerWait:
    wait_id: WaitId
    run_id: RunId
    opened_by_command_id: CommandId
    fire_at: Timestamp
    reason: str | MissingType | None = MISSING
    metadata: JsonObject | MissingType | None = MISSING
    kind: Literal[WaitKind.TIMER] = WaitKind.TIMER

    def __post_init__(self) -> None:
        if self.kind is not WaitKind.TIMER:
            raise ValidationError(code="wait_kind_invalid")
        object.__setattr__(
            self,
            "metadata",
            _validate_wait_common(
                self.wait_id, self.run_id, self.opened_by_command_id, self.metadata
            ),
        )
        if not isinstance(self.fire_at, Timestamp):
            raise ValidationError(code="wait_fire_at_invalid")
        object.__setattr__(self, "reason", _optional_text(self.reason, "wait_reason_invalid"))


class DelegatedRunKind(StrEnum):
    WORKER = "worker"
    AGENT = "agent"


@final
@dataclass(frozen=True, slots=True, kw_only=True)
class DelegationBudget:
    max_requests: int
    wall_clock_timeout_ms: int
    on_budget_expired: Literal["cancel", "fail"] = "cancel"

    def __post_init__(self) -> None:
        if (
            not isinstance(self.max_requests, int)
            or isinstance(self.max_requests, bool)
            or self.max_requests <= 0
        ):
            raise ValidationError(code="delegation_budget_max_requests_invalid")
        if (
            not isinstance(self.wall_clock_timeout_ms, int)
            or isinstance(self.wall_clock_timeout_ms, bool)
            or self.wall_clock_timeout_ms <= 0
        ):
            raise ValidationError(code="delegation_budget_timeout_invalid")
        if self.on_budget_expired not in ("cancel", "fail"):
            raise ValidationError(code="delegation_budget_expiry_policy_invalid")


@final
@dataclass(frozen=True, slots=True, kw_only=True)
class AuthorityGrant:
    capability_id: CapabilityId
    actions: tuple[str, ...] = ()
    policy_rule_ids: tuple[PolicyRuleId, ...] = ()
    description: str | MissingType | None = MISSING
    metadata: JsonObject | MissingType | None = MISSING

    def __post_init__(self) -> None:
        if not isinstance(self.capability_id, CapabilityId):
            raise ValidationError(code="authority_grant_capability_id_invalid")
        object.__setattr__(self, "actions", _text_tuple(self.actions, "authority_actions_invalid"))
        object.__setattr__(
            self,
            "policy_rule_ids",
            _typed_tuple(self.policy_rule_ids, PolicyRuleId, "authority_policy_ids_invalid"),
        )
        object.__setattr__(
            self,
            "description",
            _optional_text(self.description, "authority_description_invalid"),
        )
        object.__setattr__(
            self, "metadata", _optional_object(self.metadata, "authority_metadata_invalid")
        )


@final
@dataclass(frozen=True, slots=True, kw_only=True)
class DelegationContract:
    run_kind: DelegatedRunKind
    objective: str
    authority_grants: tuple[AuthorityGrant, ...]
    authority_drift: Literal["snapshot", "live_revalidate"]
    budget: DelegationBudget
    result_kind: str
    allow_nested_delegation: bool
    on_parent_cancel: Literal["cancel", "detach", "allow_completion"]
    required_artifact_kinds: tuple[str, ...] = ()
    late_handoff: Literal["ignore", "surface", "add_to_context"] = "ignore"
    metadata: JsonObject | MissingType | None = MISSING
    version: Literal[1] = 1

    def __post_init__(self) -> None:
        if self.version != 1 or isinstance(self.version, bool):
            raise ValidationError(code="delegation_contract_version_invalid")
        if not isinstance(self.run_kind, DelegatedRunKind):
            raise ValidationError(code="delegation_run_kind_invalid")
        object.__setattr__(
            self, "objective", _required_text(self.objective, "delegation_objective_invalid")
        )
        object.__setattr__(
            self,
            "authority_grants",
            _typed_tuple(self.authority_grants, AuthorityGrant, "delegation_authority_invalid"),
        )
        if self.authority_drift not in ("snapshot", "live_revalidate"):
            raise ValidationError(code="delegation_authority_drift_invalid")
        if not isinstance(self.budget, DelegationBudget):
            raise ValidationError(code="delegation_budget_invalid")
        object.__setattr__(
            self, "result_kind", _required_text(self.result_kind, "delegation_result_kind_invalid")
        )
        object.__setattr__(
            self,
            "required_artifact_kinds",
            _text_tuple(self.required_artifact_kinds, "delegation_artifact_kinds_invalid"),
        )
        if not isinstance(self.allow_nested_delegation, bool):
            raise ValidationError(code="delegation_nested_policy_invalid")
        if self.on_parent_cancel not in ("cancel", "detach", "allow_completion"):
            raise ValidationError(code="delegation_parent_cancel_policy_invalid")
        if self.late_handoff not in ("ignore", "surface", "add_to_context"):
            raise ValidationError(code="delegation_late_handoff_invalid")
        object.__setattr__(
            self, "metadata", _optional_object(self.metadata, "delegation_metadata_invalid")
        )


@final
@dataclass(frozen=True, slots=True, kw_only=True)
class DelegationInput:
    artifact_ids: tuple[ArtifactId, ...] = ()
    parts: tuple[Content, ...] = ()
    data: JsonObject | MissingType | None = MISSING
    metadata: JsonObject | MissingType | None = MISSING

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "artifact_ids",
            _typed_tuple(self.artifact_ids, ArtifactId, "delegation_input_artifacts_invalid"),
        )
        object.__setattr__(
            self,
            "parts",
            _typed_tuple(self.parts, Content, "delegation_input_parts_invalid"),
        )
        object.__setattr__(
            self, "data", _optional_object(self.data, "delegation_input_data_invalid")
        )
        object.__setattr__(
            self, "metadata", _optional_object(self.metadata, "delegation_input_metadata_invalid")
        )


@final
@dataclass(frozen=True, slots=True, kw_only=True)
class DelegationLineage:
    parent_run_id: RunId
    delegated_run_id: RunId
    parent_delegation_event_id: EventId | MissingType | None = MISSING

    def __post_init__(self) -> None:
        if not isinstance(self.parent_run_id, RunId):
            raise ValidationError(code="delegation_parent_run_id_invalid")
        if not isinstance(self.delegated_run_id, RunId):
            raise ValidationError(code="delegation_run_id_invalid")
        if self.parent_run_id == self.delegated_run_id:
            raise ValidationError(code="delegation_lineage_cycle")
        if self.parent_delegation_event_id not in (MISSING, None) and not isinstance(
            self.parent_delegation_event_id, EventId
        ):
            raise ValidationError(code="delegation_parent_event_id_invalid")


class DelegationJoinMode(StrEnum):
    ALL = "all"
    ANY = "any"
    QUORUM = "quorum"


@final
@dataclass(frozen=True, slots=True, kw_only=True)
class DelegationJoinContract:
    wait_id: WaitId
    target_run_ids: tuple[RunId, ...]
    mode: DelegationJoinMode
    outcome_filter: Literal["completed_only", "terminal_any", "completed_or_failed"]
    failure_policy: Literal["fail_fast", "wait_for_all_terminal"]
    on_satisfied: Literal["cancel_remaining", "detach_remaining", "keep_bound"]
    late_handoff_policy: Literal["ignore", "surface", "add_to_context"]
    quorum: int | MissingType | None = MISSING

    def __post_init__(self) -> None:
        if not isinstance(self.wait_id, WaitId):
            raise ValidationError(code="delegation_join_wait_id_invalid")
        targets = _typed_tuple(self.target_run_ids, RunId, "delegation_join_target_ids_invalid")
        if not targets:
            raise ValidationError(code="delegation_join_target_ids_invalid")
        if len(set(targets)) != len(targets):
            raise ValidationError(code="delegation_join_target_ids_duplicate")
        object.__setattr__(self, "target_run_ids", targets)
        if not isinstance(self.mode, DelegationJoinMode):
            raise ValidationError(code="delegation_join_mode_invalid")
        if self.outcome_filter not in (
            "completed_only",
            "terminal_any",
            "completed_or_failed",
        ):
            raise ValidationError(code="delegation_join_outcome_filter_invalid")
        if self.failure_policy not in ("fail_fast", "wait_for_all_terminal"):
            raise ValidationError(code="delegation_join_failure_policy_invalid")
        if self.on_satisfied not in (
            "cancel_remaining",
            "detach_remaining",
            "keep_bound",
        ):
            raise ValidationError(code="delegation_join_satisfied_policy_invalid")
        if self.late_handoff_policy not in ("ignore", "surface", "add_to_context"):
            raise ValidationError(code="delegation_join_late_handoff_invalid")
        if self.mode is DelegationJoinMode.QUORUM:
            if (
                not isinstance(self.quorum, int)
                or isinstance(self.quorum, bool)
                or not 1 <= self.quorum <= len(targets)
            ):
                raise ValidationError(code="delegation_join_quorum_required")
        elif self.quorum not in (MISSING, None):
            raise ValidationError(code="delegation_join_quorum_forbidden")


@final
@dataclass(frozen=True, slots=True, kw_only=True)
class JoinWait:
    wait_id: WaitId
    run_id: RunId
    opened_by_command_id: CommandId
    contract: DelegationJoinContract
    reason: str | MissingType | None = MISSING
    metadata: JsonObject | MissingType | None = MISSING
    kind: Literal[WaitKind.JOIN] = WaitKind.JOIN

    def __post_init__(self) -> None:
        if self.kind is not WaitKind.JOIN:
            raise ValidationError(code="wait_kind_invalid")
        object.__setattr__(
            self,
            "metadata",
            _validate_wait_common(
                self.wait_id, self.run_id, self.opened_by_command_id, self.metadata
            ),
        )
        if not isinstance(self.contract, DelegationJoinContract):
            raise ValidationError(code="join_wait_contract_invalid")
        if self.contract.wait_id != self.wait_id:
            raise ValidationError(code="join_wait_id_mismatch")
        object.__setattr__(self, "reason", _optional_text(self.reason, "wait_reason_invalid"))


@final
@dataclass(frozen=True, slots=True, kw_only=True)
class ReconciliationWait:
    wait_id: WaitId
    run_id: RunId
    opened_by_command_id: CommandId
    action_id: ActionId
    reason: str
    metadata: JsonObject | MissingType | None = MISSING
    kind: Literal[WaitKind.RECONCILIATION] = WaitKind.RECONCILIATION

    def __post_init__(self) -> None:
        if self.kind is not WaitKind.RECONCILIATION:
            raise ValidationError(code="wait_kind_invalid")
        object.__setattr__(
            self,
            "metadata",
            _validate_wait_common(
                self.wait_id, self.run_id, self.opened_by_command_id, self.metadata
            ),
        )
        if not isinstance(self.action_id, ActionId):
            raise ValidationError(code="reconciliation_wait_action_id_invalid")
        object.__setattr__(self, "reason", _required_text(self.reason, "wait_reason_invalid"))


type Wait = ApprovalWait | InteractionWait | TimerWait | JoinWait | ReconciliationWait


@final
@dataclass(frozen=True, slots=True, kw_only=True)
class Delegation:
    delegation_id: DelegationId
    parent_run_id: RunId
    delegated_run_id: RunId
    contract: DelegationContract
    input: DelegationInput
    lineage: DelegationLineage
    join_contract: DelegationJoinContract | MissingType | None = MISSING
    metadata: JsonObject | MissingType | None = MISSING

    def __post_init__(self) -> None:
        if not isinstance(self.delegation_id, DelegationId):
            raise ValidationError(code="delegation_id_invalid")
        if not isinstance(self.parent_run_id, RunId):
            raise ValidationError(code="delegation_parent_run_id_invalid")
        if not isinstance(self.delegated_run_id, RunId):
            raise ValidationError(code="delegation_run_id_invalid")
        if not isinstance(self.contract, DelegationContract):
            raise ValidationError(code="delegation_contract_invalid")
        if not isinstance(self.input, DelegationInput):
            raise ValidationError(code="delegation_input_invalid")
        if not isinstance(self.lineage, DelegationLineage):
            raise ValidationError(code="delegation_lineage_invalid")
        if (
            self.lineage.parent_run_id != self.parent_run_id
            or self.lineage.delegated_run_id != self.delegated_run_id
        ):
            raise ValidationError(code="delegation_lineage_mismatch")
        if self.join_contract not in (MISSING, None) and not isinstance(
            self.join_contract, DelegationJoinContract
        ):
            raise ValidationError(code="delegation_join_contract_invalid")
        object.__setattr__(
            self, "metadata", _optional_object(self.metadata, "delegation_metadata_invalid")
        )


class CheckStatus(StrEnum):
    PASSED = "passed"
    FAILED = "failed"
    BLOCKED = "blocked"


@final
@dataclass(frozen=True, slots=True, kw_only=True)
class Check:
    check_id: CheckId
    run_id: RunId
    name: str
    status: CheckStatus
    report: Content
    artifact_ids: tuple[ArtifactId, ...] = ()
    metadata: JsonObject | MissingType | None = MISSING

    def __post_init__(self) -> None:
        if not isinstance(self.check_id, CheckId):
            raise ValidationError(code="check_id_invalid")
        if not isinstance(self.run_id, RunId):
            raise ValidationError(code="check_run_id_invalid")
        object.__setattr__(self, "name", _required_text(self.name, "check_name_invalid"))
        if not isinstance(self.status, CheckStatus):
            raise ValidationError(code="check_status_invalid")
        if not isinstance(self.report, Content):
            raise ValidationError(code="check_report_invalid")
        object.__setattr__(
            self,
            "artifact_ids",
            _typed_tuple(self.artifact_ids, ArtifactId, "check_artifact_ids_invalid"),
        )
        object.__setattr__(
            self, "metadata", _optional_object(self.metadata, "check_metadata_invalid")
        )


@final
@dataclass(frozen=True, slots=True, kw_only=True)
class Checkpoint:
    checkpoint_id: CheckpointId
    run_id: RunId
    from_position: int
    to_position: int
    summary: str | MissingType | None = MISSING
    retained_context: JsonObject | MissingType | None = MISSING
    protected_event_types: tuple[str, ...] = ()
    artifact_ids: tuple[ArtifactId, ...] = ()
    corrects_checkpoint_id: CheckpointId | MissingType | None = MISSING
    correction_reason: str | MissingType | None = MISSING
    metadata: JsonObject | MissingType | None = MISSING

    def __post_init__(self) -> None:
        if not isinstance(self.checkpoint_id, CheckpointId):
            raise ValidationError(code="checkpoint_id_invalid")
        if not isinstance(self.run_id, RunId):
            raise ValidationError(code="checkpoint_run_id_invalid")
        if (
            not isinstance(self.from_position, int)
            or isinstance(self.from_position, bool)
            or not isinstance(self.to_position, int)
            or isinstance(self.to_position, bool)
            or self.from_position < 0
            or self.to_position < self.from_position
        ):
            raise ValidationError(code="checkpoint_range_invalid")
        object.__setattr__(
            self, "summary", _optional_text(self.summary, "checkpoint_summary_invalid")
        )
        object.__setattr__(
            self,
            "retained_context",
            _optional_object(self.retained_context, "checkpoint_context_invalid"),
        )
        object.__setattr__(
            self,
            "protected_event_types",
            _text_tuple(self.protected_event_types, "checkpoint_event_types_invalid"),
        )
        object.__setattr__(
            self,
            "artifact_ids",
            _typed_tuple(self.artifact_ids, ArtifactId, "checkpoint_artifact_ids_invalid"),
        )
        if self.corrects_checkpoint_id not in (MISSING, None) and not isinstance(
            self.corrects_checkpoint_id, CheckpointId
        ):
            raise ValidationError(code="checkpoint_correction_id_invalid")
        object.__setattr__(
            self,
            "correction_reason",
            _optional_text(self.correction_reason, "checkpoint_correction_reason_invalid"),
        )
        if self.corrects_checkpoint_id in (MISSING, None) and self.correction_reason not in (
            MISSING,
            None,
        ):
            raise ValidationError(code="checkpoint_correction_reason_forbidden")
        object.__setattr__(
            self, "metadata", _optional_object(self.metadata, "checkpoint_metadata_invalid")
        )


@final
@dataclass(frozen=True, slots=True, kw_only=True)
class Annotation:
    annotation_id: AnnotationId
    run_id: RunId
    content: Content
    artifact_ids: tuple[ArtifactId, ...] = ()
    metadata: JsonObject | MissingType | None = MISSING

    def __post_init__(self) -> None:
        if not isinstance(self.annotation_id, AnnotationId):
            raise ValidationError(code="annotation_id_invalid")
        if not isinstance(self.run_id, RunId):
            raise ValidationError(code="annotation_run_id_invalid")
        if not isinstance(self.content, Content):
            raise ValidationError(code="annotation_content_invalid")
        object.__setattr__(
            self,
            "artifact_ids",
            _typed_tuple(self.artifact_ids, ArtifactId, "annotation_artifact_ids_invalid"),
        )
        object.__setattr__(
            self, "metadata", _optional_object(self.metadata, "annotation_metadata_invalid")
        )


@final
@dataclass(frozen=True, slots=True, kw_only=True)
class Artifact:
    artifact_id: ArtifactId
    run_id: RunId
    kind: str
    byte_length: int
    sha256: str
    preview: str | MissingType | None = MISSING
    metadata: JsonObject | MissingType | None = MISSING
    available: bool = True

    def __post_init__(self) -> None:
        if not isinstance(self.artifact_id, ArtifactId):
            raise ValidationError(code="artifact_id_invalid")
        if not isinstance(self.run_id, RunId):
            raise ValidationError(code="artifact_run_id_invalid")
        object.__setattr__(self, "kind", _required_text(self.kind, "artifact_kind_invalid"))
        if (
            not isinstance(self.byte_length, int)
            or isinstance(self.byte_length, bool)
            or self.byte_length < 0
        ):
            raise ValidationError(code="artifact_byte_length_invalid")
        if not isinstance(self.sha256, str) or re.fullmatch(r"[0-9a-f]{64}", self.sha256) is None:
            raise ValidationError(code="artifact_sha256_invalid")
        object.__setattr__(
            self, "preview", _optional_text(self.preview, "artifact_preview_invalid")
        )
        object.__setattr__(
            self, "metadata", _optional_object(self.metadata, "artifact_metadata_invalid")
        )
        if not isinstance(self.available, bool):
            raise ValidationError(code="artifact_availability_invalid")


@final
@dataclass(frozen=True, slots=True, kw_only=True)
class Authority:
    authority_id: AuthorityId
    run_id: RunId
    grants: tuple[AuthorityGrant, ...]
    metadata: JsonObject | MissingType | None = MISSING

    def __post_init__(self) -> None:
        if not isinstance(self.authority_id, AuthorityId):
            raise ValidationError(code="authority_id_invalid")
        if not isinstance(self.run_id, RunId):
            raise ValidationError(code="authority_run_id_invalid")
        object.__setattr__(
            self, "grants", _typed_tuple(self.grants, AuthorityGrant, "authority_grants_invalid")
        )
        object.__setattr__(
            self, "metadata", _optional_object(self.metadata, "authority_metadata_invalid")
        )


@final
@dataclass(frozen=True, slots=True, kw_only=True)
class Lease:
    lease_id: LeaseId
    run_id: RunId
    owner: str
    token: str
    acquired_at: Timestamp
    expires_at: Timestamp
    metadata: JsonObject | MissingType | None = MISSING

    def __post_init__(self) -> None:
        if not isinstance(self.lease_id, LeaseId):
            raise ValidationError(code="lease_id_invalid")
        if not isinstance(self.run_id, RunId):
            raise ValidationError(code="lease_run_id_invalid")
        object.__setattr__(self, "owner", _required_text(self.owner, "lease_owner_invalid"))
        object.__setattr__(self, "token", _required_text(self.token, "lease_token_invalid"))
        if not isinstance(self.acquired_at, Timestamp) or not isinstance(
            self.expires_at, Timestamp
        ):
            raise ValidationError(code="lease_timestamp_invalid")
        if self.expires_at.value <= self.acquired_at.value:
            raise ValidationError(code="lease_expiry_invalid")
        object.__setattr__(
            self, "metadata", _optional_object(self.metadata, "lease_metadata_invalid")
        )


@final
@dataclass(frozen=True, slots=True, kw_only=True)
class OutputArtifactRequirement:
    capability_id: CapabilityId
    format: str
    writable_root: LocalPath
    action_name: str | MissingType | None = MISSING
    artifact_kind: str | MissingType | None = MISSING
    metadata: JsonObject | MissingType | None = MISSING
    kind: Literal["output_artifact"] = "output_artifact"

    def __post_init__(self) -> None:
        if self.kind != "output_artifact":
            raise ValidationError(code="output_requirement_kind_invalid")
        if not isinstance(self.capability_id, CapabilityId):
            raise ValidationError(code="output_requirement_capability_id_invalid")
        object.__setattr__(
            self, "format", _required_text(self.format, "output_requirement_format_invalid")
        )
        if not isinstance(self.writable_root, LocalPath):
            raise ValidationError(code="output_requirement_root_invalid")
        object.__setattr__(
            self,
            "action_name",
            _optional_text(self.action_name, "output_requirement_action_invalid"),
        )
        object.__setattr__(
            self,
            "artifact_kind",
            _optional_text(self.artifact_kind, "output_requirement_artifact_kind_invalid"),
        )
        object.__setattr__(
            self,
            "metadata",
            _optional_object(self.metadata, "output_requirement_metadata_invalid"),
        )


@final
@dataclass(frozen=True, slots=True, kw_only=True)
class CheckRequirement:
    checks: tuple[str, ...]
    metadata: JsonObject | MissingType | None = MISSING
    kind: Literal["check"] = "check"

    def __post_init__(self) -> None:
        if self.kind != "check":
            raise ValidationError(code="check_requirement_kind_invalid")
        object.__setattr__(
            self,
            "checks",
            _text_tuple(self.checks, "check_requirement_checks_invalid", allow_empty=False),
        )
        object.__setattr__(
            self,
            "metadata",
            _optional_object(self.metadata, "check_requirement_metadata_invalid"),
        )


@final
@dataclass(frozen=True, slots=True, kw_only=True)
class SourceCoverageRequirement:
    metadata: JsonObject | MissingType | None = MISSING
    kind: Literal["source_coverage"] = "source_coverage"
    fanout: Literal["per_source"] = "per_source"
    source_coverage: Literal["all_sources"] = "all_sources"

    def __post_init__(self) -> None:
        if (
            self.kind != "source_coverage"
            or self.fanout != "per_source"
            or self.source_coverage != "all_sources"
        ):
            raise ValidationError(code="source_coverage_requirement_invalid")
        object.__setattr__(
            self,
            "metadata",
            _optional_object(self.metadata, "source_coverage_metadata_invalid"),
        )


@final
@dataclass(frozen=True, slots=True, kw_only=True)
class KnownActionOutcomesRequirement:
    kind: Literal["known_action_outcomes"] = "known_action_outcomes"

    def __post_init__(self) -> None:
        if self.kind != "known_action_outcomes":
            raise ValidationError(code="known_outcomes_requirement_invalid")


@final
@dataclass(frozen=True, slots=True, kw_only=True)
class RunContract:
    output: OutputArtifactRequirement | MissingType | None = MISSING
    check: CheckRequirement | MissingType | None = MISSING
    delegation: SourceCoverageRequirement | MissingType | None = MISSING
    completion: KnownActionOutcomesRequirement | MissingType | None = MISSING
    metadata: JsonObject | MissingType | None = MISSING
    version: Literal[1] = 1

    def __post_init__(self) -> None:
        if self.version != 1 or isinstance(self.version, bool):
            raise ValidationError(code="run_contract_version_invalid")
        if self.output not in (MISSING, None) and not isinstance(
            self.output, OutputArtifactRequirement
        ):
            raise ValidationError(code="run_contract_output_invalid")
        if self.check not in (MISSING, None) and not isinstance(self.check, CheckRequirement):
            raise ValidationError(code="run_contract_check_invalid")
        if self.delegation not in (MISSING, None) and not isinstance(
            self.delegation, SourceCoverageRequirement
        ):
            raise ValidationError(code="run_contract_delegation_invalid")
        if self.completion not in (MISSING, None) and not isinstance(
            self.completion, KnownActionOutcomesRequirement
        ):
            raise ValidationError(code="run_contract_completion_invalid")
        object.__setattr__(
            self, "metadata", _optional_object(self.metadata, "run_contract_metadata_invalid")
        )
