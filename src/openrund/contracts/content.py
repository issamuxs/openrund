"""Immutable content, result, effect, evidence, and artifact-reference values."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Literal, cast, final

from openrund.contracts.ids import ArtifactId
from openrund.contracts.json import MISSING, JsonObject, MissingType, freeze_json
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


def _id_tuple(value: object, code: str) -> tuple[ArtifactId, ...]:
    try:
        frozen: tuple[object, ...] = tuple(value)  # type: ignore[arg-type]
    except TypeError as error:
        raise ValidationError(code=code) from error
    if any(not isinstance(item, ArtifactId) for item in frozen):
        raise ValidationError(code=code)
    return cast(tuple[ArtifactId, ...], frozen)


def utf8_byte_length(text: str) -> int:
    """Return strict UTF-8 bytes without normalizing the input string."""

    if not isinstance(text, str):
        raise ValidationError(code="content_text_type_invalid")
    return len(text.encode("utf-8", errors="strict"))


@final
@dataclass(frozen=True, slots=True, kw_only=True)
class ArtifactReference:
    artifact_id: ArtifactId
    kind: str | MissingType | None = MISSING
    preview: str | MissingType | None = MISSING
    metadata: JsonObject | MissingType | None = MISSING

    def __post_init__(self) -> None:
        if not isinstance(self.artifact_id, ArtifactId):
            raise ValidationError(code="artifact_reference_id_invalid")
        object.__setattr__(
            self, "kind", _optional_text(self.kind, "artifact_reference_kind_invalid")
        )
        object.__setattr__(
            self, "preview", _optional_text(self.preview, "artifact_reference_preview_invalid")
        )
        object.__setattr__(
            self,
            "metadata",
            _optional_object(self.metadata, "artifact_reference_metadata_invalid"),
        )


@final
@dataclass(frozen=True, slots=True, kw_only=True)
class Content:
    preview: str | MissingType | None = MISSING
    data: JsonObject | MissingType | None = MISSING
    artifact_refs: tuple[ArtifactReference, ...] = ()
    artifact_ids: tuple[ArtifactId, ...] = ()
    metadata: JsonObject | MissingType | None = MISSING

    def __post_init__(self) -> None:
        object.__setattr__(self, "preview", _optional_text(self.preview, "content_preview_invalid"))
        object.__setattr__(self, "data", _optional_object(self.data, "content_data_invalid"))
        try:
            refs = tuple(self.artifact_refs)
        except TypeError as error:
            raise ValidationError(code="content_artifact_refs_invalid") from error
        if any(not isinstance(item, ArtifactReference) for item in refs):
            raise ValidationError(code="content_artifact_refs_invalid")
        object.__setattr__(self, "artifact_refs", refs)
        object.__setattr__(
            self, "artifact_ids", _id_tuple(self.artifact_ids, "content_artifact_ids_invalid")
        )
        object.__setattr__(
            self, "metadata", _optional_object(self.metadata, "content_metadata_invalid")
        )


class MutationOperationKind(StrEnum):
    CREATE = "create"
    UPDATE = "update"
    DELETE = "delete"
    MOVE = "move"
    PATCH = "patch"
    EXECUTE = "execute"
    INSPECT = "inspect"


class MutationReversibility(StrEnum):
    REVERSIBLE = "reversible"
    IRREVERSIBLE = "irreversible"
    UNKNOWN = "unknown"


@final
@dataclass(frozen=True, slots=True, kw_only=True)
class Mutation:
    affected_resources: tuple[JsonObject, ...]
    operation_kind: MutationOperationKind
    preview: Content | MissingType | None = MISSING
    reversibility: MutationReversibility | MissingType | None = MISSING
    check_plan: Content | MissingType | None = MISSING
    metadata: JsonObject | MissingType | None = MISSING

    def __post_init__(self) -> None:
        try:
            resources = tuple(self.affected_resources)
        except TypeError as error:
            raise ValidationError(code="mutation_resources_invalid") from error
        frozen_resources: list[JsonObject] = []
        for resource in resources:
            frozen = freeze_json(resource)
            if not isinstance(frozen, JsonObject):
                raise ValidationError(code="mutation_resource_invalid")
            frozen_resources.append(frozen)
        object.__setattr__(self, "affected_resources", tuple(frozen_resources))
        if not isinstance(self.operation_kind, MutationOperationKind):
            raise ValidationError(code="mutation_operation_kind_invalid")
        if (
            self.preview is not MISSING
            and self.preview is not None
            and not isinstance(self.preview, Content)
        ):
            raise ValidationError(code="mutation_preview_invalid")
        if (
            self.reversibility is not MISSING
            and self.reversibility is not None
            and not isinstance(self.reversibility, MutationReversibility)
        ):
            raise ValidationError(code="mutation_reversibility_invalid")
        if (
            self.check_plan is not MISSING
            and self.check_plan is not None
            and not isinstance(self.check_plan, Content)
        ):
            raise ValidationError(code="mutation_check_plan_invalid")
        object.__setattr__(
            self, "metadata", _optional_object(self.metadata, "mutation_metadata_invalid")
        )


@final
@dataclass(frozen=True, slots=True, kw_only=True)
class EffectEntry:
    kind: str
    summary: str | MissingType | None = MISSING
    artifact_ids: tuple[ArtifactId, ...] = ()
    metadata: JsonObject | MissingType | None = MISSING

    def __post_init__(self) -> None:
        object.__setattr__(self, "kind", _required_text(self.kind, "effect_kind_invalid"))
        object.__setattr__(self, "summary", _optional_text(self.summary, "effect_summary_invalid"))
        object.__setattr__(
            self, "artifact_ids", _id_tuple(self.artifact_ids, "effect_artifact_ids_invalid")
        )
        object.__setattr__(
            self, "metadata", _optional_object(self.metadata, "effect_metadata_invalid")
        )


@final
@dataclass(frozen=True, slots=True, kw_only=True)
class EvidenceEntry:
    artifact_id: ArtifactId | MissingType | None = MISSING
    description: str | MissingType | None = MISSING
    metadata: JsonObject | MissingType | None = MISSING

    def __post_init__(self) -> None:
        if (
            self.artifact_id is not MISSING
            and self.artifact_id is not None
            and not isinstance(self.artifact_id, ArtifactId)
        ):
            raise ValidationError(code="evidence_artifact_id_invalid")
        object.__setattr__(
            self,
            "description",
            _optional_text(self.description, "evidence_description_invalid"),
        )
        object.__setattr__(
            self, "metadata", _optional_object(self.metadata, "evidence_metadata_invalid")
        )


@final
@dataclass(frozen=True, slots=True, kw_only=True)
class ResultPart:
    kind: str
    text: str | MissingType | None = MISSING
    data: JsonObject | MissingType | None = MISSING
    artifact_id: ArtifactId | MissingType | None = MISSING
    metadata: JsonObject | MissingType | None = MISSING

    def __post_init__(self) -> None:
        object.__setattr__(self, "kind", _required_text(self.kind, "result_part_kind_invalid"))
        object.__setattr__(self, "text", _optional_text(self.text, "result_part_text_invalid"))
        object.__setattr__(self, "data", _optional_object(self.data, "result_part_data_invalid"))
        if (
            self.artifact_id is not MISSING
            and self.artifact_id is not None
            and not isinstance(self.artifact_id, ArtifactId)
        ):
            raise ValidationError(code="result_part_artifact_id_invalid")
        object.__setattr__(
            self, "metadata", _optional_object(self.metadata, "result_part_metadata_invalid")
        )


@final
@dataclass(frozen=True, slots=True, kw_only=True)
class RunResult:
    kind: str
    version: Literal[1] = 1
    summary: str | MissingType | None = MISSING
    data: JsonObject | MissingType | None = MISSING
    parts: tuple[ResultPart, ...] = ()
    artifact_ids: tuple[ArtifactId, ...] = ()
    metadata: JsonObject | MissingType | None = MISSING

    def __post_init__(self) -> None:
        if self.version != 1 or isinstance(self.version, bool):
            raise ValidationError(code="run_result_version_invalid")
        object.__setattr__(self, "kind", _required_text(self.kind, "run_result_kind_invalid"))
        object.__setattr__(
            self, "summary", _optional_text(self.summary, "run_result_summary_invalid")
        )
        object.__setattr__(self, "data", _optional_object(self.data, "run_result_data_invalid"))
        try:
            parts = tuple(self.parts)
        except TypeError as error:
            raise ValidationError(code="run_result_parts_invalid") from error
        if any(not isinstance(item, ResultPart) for item in parts):
            raise ValidationError(code="run_result_parts_invalid")
        object.__setattr__(self, "parts", parts)
        object.__setattr__(
            self,
            "artifact_ids",
            _id_tuple(self.artifact_ids, "run_result_artifact_ids_invalid"),
        )
        object.__setattr__(
            self, "metadata", _optional_object(self.metadata, "run_result_metadata_invalid")
        )
