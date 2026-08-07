"""Inert Capability, Action, and worker-result semantic values."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import final

from openrund.contracts.content import Content, EffectEntry, EvidenceEntry, Mutation
from openrund.contracts.ids import ActionId, ArtifactId, CapabilityId
from openrund.contracts.json import MISSING, JsonObject, JsonValue, MissingType, freeze_json
from openrund.errors import ValidationError


def _text(value: object, code: str) -> str:
    if not isinstance(value, str) or value == "":
        raise ValidationError(code=code)
    return value


def _metadata(value: object, code: str) -> JsonObject | MissingType | None:
    if value is MISSING or value is None:
        return value
    frozen = freeze_json(value)
    if not isinstance(frozen, JsonObject):
        raise ValidationError(code=code)
    return frozen


class CapabilityAccessMode(StrEnum):
    READ = "read"
    WRITE = "write"
    READ_WRITE = "read_write"


class CapabilityReliability(StrEnum):
    PURE = "pure"
    READ_ONLY = "read_only"
    IDEMPOTENT_MUTATION = "idempotent_mutation"
    EXTERNALLY_TRANSACTIONAL = "externally_transactional"
    COMPENSATABLE = "compensatable"
    IRREVERSIBLE = "irreversible"
    INTERRUPTIBLE = "interruptible"


class CapabilityTransportKind(StrEnum):
    IN_PROCESS = "in_process"
    STDIO_JSON_RPC = "stdio_json_rpc"


@final
@dataclass(frozen=True, slots=True, kw_only=True)
class CapabilityBatching:
    eligible: bool = False
    max_size: int = 1

    def __post_init__(self) -> None:
        if not isinstance(self.eligible, bool):
            raise ValidationError(code="capability_batching_eligible_invalid")
        if (
            isinstance(self.max_size, bool)
            or not isinstance(self.max_size, int)
            or self.max_size < 1
        ):
            raise ValidationError(code="capability_batching_size_invalid")
        if not self.eligible and self.max_size != 1:
            raise ValidationError(code="capability_batching_size_forbidden")


@final
@dataclass(frozen=True, slots=True, kw_only=True)
class CapabilityCancellation:
    supported: bool = False

    def __post_init__(self) -> None:
        if not isinstance(self.supported, bool):
            raise ValidationError(code="capability_cancellation_supported_invalid")


@final
@dataclass(frozen=True, slots=True, kw_only=True)
class CapabilityArtifact:
    kind: str
    content_type: str | MissingType | None = MISSING
    required: bool = False

    def __post_init__(self) -> None:
        object.__setattr__(self, "kind", _text(self.kind, "capability_artifact_kind_invalid"))
        if self.content_type not in (MISSING, None) and (
            not isinstance(self.content_type, str) or self.content_type == ""
        ):
            raise ValidationError(code="capability_artifact_content_type_invalid")
        if not isinstance(self.required, bool):
            raise ValidationError(code="capability_artifact_required_invalid")


@final
@dataclass(frozen=True, slots=True, kw_only=True)
class CapabilityTransportMetadata:
    kind: CapabilityTransportKind
    timeout_ms: int = 30_000
    max_response_bytes: int = 8 * 1024 * 1024

    def __post_init__(self) -> None:
        if not isinstance(self.kind, CapabilityTransportKind):
            raise ValidationError(code="capability_transport_kind_invalid")
        for name, value in (
            ("timeout_ms", self.timeout_ms),
            ("max_response_bytes", self.max_response_bytes),
        ):
            if isinstance(value, bool) or not isinstance(value, int) or value < 1:
                raise ValidationError(code=f"capability_transport_{name}_invalid")


class ActionOutcome(StrEnum):
    PROPOSED = "proposed"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    UNKNOWN = "unknown"


class ActionReliability(StrEnum):
    PURE = "pure"
    READ_ONLY = "read_only"
    IDEMPOTENT_MUTATION = "idempotent_mutation"
    EXTERNALLY_TRANSACTIONAL = "externally_transactional"
    COMPENSATABLE = "compensatable"
    IRREVERSIBLE = "irreversible"
    INTERRUPTIBLE = "interruptible"
    STARTED_NOT_CONFIRMED = "started_not_confirmed"
    TRANSPORT_LOST = "transport_lost"
    TIMEOUT_AFTER_DISPATCH = "timeout_after_dispatch"
    PARTIAL_EVIDENCE = "partial_evidence"
    WORKER_CRASH = "worker_crash"
    UNKNOWN = "unknown"


@final
@dataclass(frozen=True, slots=True, kw_only=True)
class ActionFailure:
    message: str
    code: str | MissingType | None = MISSING
    retryable: bool | MissingType | None = MISSING

    def __post_init__(self) -> None:
        object.__setattr__(self, "message", _text(self.message, "action_failure_message_invalid"))
        if self.code not in (MISSING, None) and not isinstance(self.code, str):
            raise ValidationError(code="action_failure_code_invalid")
        if self.retryable not in (MISSING, None) and not isinstance(self.retryable, bool):
            raise ValidationError(code="action_failure_retryable_invalid")


@final
@dataclass(frozen=True, slots=True, kw_only=True)
class CapabilityAction:
    name: str
    description: str
    posture: CapabilityAccessMode
    reliability: CapabilityReliability
    input_schema: JsonObject
    output_schema: JsonObject | MissingType | None = MISSING
    batching: CapabilityBatching = CapabilityBatching()
    cancellation: CapabilityCancellation = CapabilityCancellation()
    artifacts: tuple[CapabilityArtifact, ...] = ()
    transport: CapabilityTransportMetadata | MissingType | None = MISSING
    metadata: JsonObject | MissingType | None = MISSING

    def __post_init__(self) -> None:
        object.__setattr__(self, "name", _text(self.name, "capability_action_name_invalid"))
        object.__setattr__(
            self,
            "description",
            _text(self.description, "capability_action_description_invalid"),
        )
        if not isinstance(self.posture, CapabilityAccessMode):
            raise ValidationError(code="capability_action_posture_invalid")
        if not isinstance(self.reliability, CapabilityReliability):
            raise ValidationError(code="capability_action_reliability_invalid")
        input_schema = freeze_json(self.input_schema)
        if not isinstance(input_schema, JsonObject):
            raise ValidationError(code="capability_action_input_schema_invalid")
        object.__setattr__(self, "input_schema", input_schema)
        object.__setattr__(
            self,
            "output_schema",
            _metadata(self.output_schema, "capability_action_output_schema_invalid"),
        )
        if not isinstance(self.batching, CapabilityBatching):
            raise ValidationError(code="capability_action_batching_invalid")
        if not isinstance(self.cancellation, CapabilityCancellation):
            raise ValidationError(code="capability_action_cancellation_invalid")
        try:
            artifacts = tuple(self.artifacts)
        except TypeError as error:
            raise ValidationError(code="capability_action_artifacts_invalid") from error
        if any(not isinstance(item, CapabilityArtifact) for item in artifacts):
            raise ValidationError(code="capability_action_artifacts_invalid")
        if len({item.kind for item in artifacts}) != len(artifacts):
            raise ValidationError(code="capability_action_artifact_kind_duplicate")
        object.__setattr__(self, "artifacts", artifacts)
        if self.transport not in (MISSING, None) and not isinstance(
            self.transport, CapabilityTransportMetadata
        ):
            raise ValidationError(code="capability_action_transport_invalid")
        object.__setattr__(
            self, "metadata", _metadata(self.metadata, "capability_action_metadata_invalid")
        )


@final
@dataclass(frozen=True, slots=True, kw_only=True)
class Capability:
    capability_id: CapabilityId
    version: str
    actions: tuple[CapabilityAction, ...]
    display_name: str | MissingType | None = MISSING
    description: str | MissingType | None = MISSING
    metadata: JsonObject | MissingType | None = MISSING

    def __post_init__(self) -> None:
        if not isinstance(self.capability_id, CapabilityId):
            raise ValidationError(code="capability_id_invalid")
        object.__setattr__(self, "version", _text(self.version, "capability_version_invalid"))
        try:
            actions = tuple(self.actions)
        except TypeError as error:
            raise ValidationError(code="capability_actions_invalid") from error
        if any(not isinstance(action, CapabilityAction) for action in actions):
            raise ValidationError(code="capability_actions_invalid")
        if len({action.name for action in actions}) != len(actions):
            raise ValidationError(code="capability_action_name_duplicate")
        object.__setattr__(self, "actions", actions)
        for field_name in ("display_name", "description"):
            value = getattr(self, field_name)
            if value is not MISSING and value is not None and not isinstance(value, str):
                raise ValidationError(code=f"capability_{field_name}_invalid")
        object.__setattr__(
            self, "metadata", _metadata(self.metadata, "capability_metadata_invalid")
        )


@final
@dataclass(frozen=True, slots=True, kw_only=True)
class CapabilityResult:
    output: JsonValue | MissingType = MISSING
    preview: str | MissingType | None = MISSING
    effects: tuple[EffectEntry, ...] = ()
    evidence: tuple[EvidenceEntry, ...] = ()
    artifact_ids: tuple[ArtifactId, ...] = ()
    inline_artifacts: tuple[CapabilityInlineArtifact, ...] = ()
    metadata: JsonObject | MissingType | None = MISSING

    def __post_init__(self) -> None:
        if self.output is not MISSING:
            object.__setattr__(self, "output", freeze_json(self.output))
        if (
            self.preview is not MISSING
            and self.preview is not None
            and not isinstance(self.preview, str)
        ):
            raise ValidationError(code="capability_result_preview_invalid")
        effects = tuple(self.effects)
        evidence = tuple(self.evidence)
        artifact_ids = tuple(self.artifact_ids)
        inline_artifacts = tuple(self.inline_artifacts)
        if any(not isinstance(item, EffectEntry) for item in effects):
            raise ValidationError(code="capability_result_effects_invalid")
        if any(not isinstance(item, EvidenceEntry) for item in evidence):
            raise ValidationError(code="capability_result_evidence_invalid")
        if any(not isinstance(item, ArtifactId) for item in artifact_ids):
            raise ValidationError(code="capability_result_artifact_ids_invalid")
        if any(not isinstance(item, CapabilityInlineArtifact) for item in inline_artifacts):
            raise ValidationError(code="capability_result_inline_artifacts_invalid")
        object.__setattr__(self, "effects", effects)
        object.__setattr__(self, "evidence", evidence)
        object.__setattr__(self, "artifact_ids", artifact_ids)
        object.__setattr__(self, "inline_artifacts", inline_artifacts)
        object.__setattr__(
            self, "metadata", _metadata(self.metadata, "capability_result_metadata_invalid")
        )


@final
@dataclass(frozen=True, slots=True, kw_only=True)
class CapabilityInlineArtifact:
    kind: str
    content: bytes
    content_type: str | MissingType | None = MISSING
    preview: str | MissingType | None = MISSING
    metadata: JsonObject | MissingType | None = MISSING

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "kind", _text(self.kind, "capability_inline_artifact_kind_invalid")
        )
        if not isinstance(self.content, bytes):
            raise ValidationError(code="capability_inline_artifact_content_invalid")
        for name in ("content_type", "preview"):
            value = getattr(self, name)
            if value not in (MISSING, None) and (
                not isinstance(value, str) or (name == "content_type" and value == "")
            ):
                raise ValidationError(code=f"capability_inline_artifact_{name}_invalid")
        object.__setattr__(
            self,
            "metadata",
            _metadata(self.metadata, "capability_inline_artifact_metadata_invalid"),
        )


@final
@dataclass(frozen=True, slots=True, kw_only=True)
class Action:
    action_id: ActionId
    capability_id: CapabilityId
    action_name: str
    input: Content
    mutation: Mutation | MissingType | None = MISSING
    outcome: ActionOutcome = ActionOutcome.PROPOSED
    reliability: ActionReliability | MissingType | None = MISSING
    result: CapabilityResult | MissingType | None = MISSING
    metadata: JsonObject | MissingType | None = MISSING

    def __post_init__(self) -> None:
        if not isinstance(self.action_id, ActionId):
            raise ValidationError(code="action_id_invalid")
        if not isinstance(self.capability_id, CapabilityId):
            raise ValidationError(code="action_capability_id_invalid")
        object.__setattr__(self, "action_name", _text(self.action_name, "action_name_invalid"))
        if not isinstance(self.input, Content):
            raise ValidationError(code="action_input_invalid")
        if (
            self.mutation is not MISSING
            and self.mutation is not None
            and not isinstance(self.mutation, Mutation)
        ):
            raise ValidationError(code="action_mutation_invalid")
        if not isinstance(self.outcome, ActionOutcome):
            raise ValidationError(code="action_outcome_invalid")
        if (
            self.reliability is not MISSING
            and self.reliability is not None
            and not isinstance(self.reliability, ActionReliability)
        ):
            raise ValidationError(code="action_reliability_invalid")
        if (
            self.result is not MISSING
            and self.result is not None
            and not isinstance(self.result, CapabilityResult)
        ):
            raise ValidationError(code="action_result_invalid")
        if self.outcome is ActionOutcome.UNKNOWN and self.reliability in (MISSING, None):
            raise ValidationError(code="action_unknown_reliability_required")
        if self.outcome is ActionOutcome.COMPLETED and self.result in (MISSING, None):
            raise ValidationError(code="action_completed_result_required")
        object.__setattr__(self, "metadata", _metadata(self.metadata, "action_metadata_invalid"))
