"""Inert Bundle and View semantic envelopes."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import final

from openrund.contracts.ids import ArtifactId, EventId, RunId
from openrund.contracts.json import MISSING, JsonObject, MissingType, freeze_json
from openrund.contracts.time import Timestamp
from openrund.errors import ValidationError
from openrund.paths import PortablePath


class BundleProfile(StrEnum):
    COMPLETE = "complete"
    AUDIT = "audit"
    REDACTED = "redacted"


@final
@dataclass(frozen=True, slots=True, kw_only=True)
class Bundle:
    run_id: RunId
    profile: BundleProfile
    exported_at: Timestamp
    event_ids: tuple[EventId, ...] = ()
    artifact_ids: tuple[ArtifactId, ...] = ()
    relative_paths: tuple[PortablePath, ...] = ()
    metadata: JsonObject | MissingType | None = MISSING

    def __post_init__(self) -> None:
        if not isinstance(self.run_id, RunId):
            raise ValidationError(code="bundle_run_id_invalid")
        if not isinstance(self.profile, BundleProfile):
            raise ValidationError(code="bundle_profile_invalid")
        if not isinstance(self.exported_at, Timestamp):
            raise ValidationError(code="bundle_exported_at_invalid")
        for field_name, kind, code in (
            ("event_ids", EventId, "bundle_event_ids_invalid"),
            ("artifact_ids", ArtifactId, "bundle_artifact_ids_invalid"),
            ("relative_paths", PortablePath, "bundle_relative_paths_invalid"),
        ):
            try:
                values = tuple(getattr(self, field_name))
            except TypeError as error:
                raise ValidationError(code=code) from error
            if any(not isinstance(item, kind) for item in values):
                raise ValidationError(code=code)
            object.__setattr__(self, field_name, values)
        if self.metadata is not MISSING and self.metadata is not None:
            metadata = freeze_json(self.metadata)
            if not isinstance(metadata, JsonObject):
                raise ValidationError(code="bundle_metadata_invalid")
            object.__setattr__(self, "metadata", metadata)


@final
@dataclass(frozen=True, slots=True, kw_only=True)
class ViewWatermark:
    run_id: RunId
    position: int

    def __post_init__(self) -> None:
        if not isinstance(self.run_id, RunId):
            raise ValidationError(code="view_watermark_run_id_invalid")
        if isinstance(self.position, bool) or not isinstance(self.position, int):
            raise ValidationError(code="view_watermark_position_type_invalid")
        if self.position < 0:
            raise ValidationError(code="view_watermark_position_invalid")


@final
@dataclass(frozen=True, slots=True, kw_only=True)
class View:
    name: str
    watermark: ViewWatermark
    value: JsonObject
    metadata: JsonObject | MissingType | None = MISSING

    def __post_init__(self) -> None:
        if not isinstance(self.name, str) or self.name == "":
            raise ValidationError(code="view_name_invalid")
        if not isinstance(self.watermark, ViewWatermark):
            raise ValidationError(code="view_watermark_invalid")
        value = freeze_json(self.value)
        if not isinstance(value, JsonObject):
            raise ValidationError(code="view_value_invalid")
        object.__setattr__(self, "value", value)
        if self.metadata is not MISSING and self.metadata is not None:
            metadata = freeze_json(self.metadata)
            if not isinstance(metadata, JsonObject):
                raise ValidationError(code="view_metadata_invalid")
            object.__setattr__(self, "metadata", metadata)
