"""Domain-valued Artifact storage contracts without custody behavior."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Protocol, final

from openrund.contracts.ids import ArtifactId
from openrund.contracts.json import MISSING, JsonObject, MissingType, freeze_json
from openrund.contracts.time import Timestamp
from openrund.errors import ValidationError


def _optional_text(value: object, code: str) -> str | MissingType | None:
    if value is MISSING or value is None:
        return value
    if not isinstance(value, str) or value == "":
        raise ValidationError(code=code)
    return value


@final
@dataclass(frozen=True, slots=True, kw_only=True)
class ArtifactEntry:
    artifact_id: ArtifactId
    kind: str
    created_at: Timestamp
    content_type: str | MissingType | None = MISSING
    byte_length: int | MissingType | None = MISSING
    sha256: str | MissingType | None = MISSING
    metadata: JsonObject | MissingType | None = MISSING
    unavailable_at: Timestamp | MissingType | None = MISSING

    def __post_init__(self) -> None:
        if not isinstance(self.artifact_id, ArtifactId):
            raise ValidationError(code="artifact_entry_id_invalid")
        if not isinstance(self.kind, str) or self.kind == "":
            raise ValidationError(code="artifact_entry_kind_invalid")
        if not isinstance(self.created_at, Timestamp):
            raise ValidationError(code="artifact_entry_created_at_invalid")
        object.__setattr__(
            self,
            "content_type",
            _optional_text(self.content_type, "artifact_entry_content_type_invalid"),
        )
        if self.byte_length not in (MISSING, None) and (
            isinstance(self.byte_length, bool)
            or not isinstance(self.byte_length, int)
            or self.byte_length < 0
        ):
            raise ValidationError(code="artifact_entry_byte_length_invalid")
        if self.sha256 not in (MISSING, None) and (
            not isinstance(self.sha256, str) or re.fullmatch(r"[0-9a-f]{64}", self.sha256) is None
        ):
            raise ValidationError(code="artifact_entry_sha256_invalid")
        if self.sha256 not in (MISSING, None) and self.byte_length in (MISSING, None):
            raise ValidationError(code="artifact_entry_sha256_without_length")
        if self.metadata not in (MISSING, None):
            metadata = freeze_json(self.metadata)
            if not isinstance(metadata, JsonObject):
                raise ValidationError(code="artifact_entry_metadata_invalid")
            object.__setattr__(self, "metadata", metadata)
        if self.unavailable_at not in (MISSING, None) and not isinstance(
            self.unavailable_at, Timestamp
        ):
            raise ValidationError(code="artifact_entry_unavailable_at_invalid")


@final
@dataclass(frozen=True, slots=True, kw_only=True)
class ArtifactBlob:
    content: bytes
    content_type: str | MissingType | None = MISSING

    def __post_init__(self) -> None:
        if not isinstance(self.content, bytes):
            raise ValidationError(code="artifact_blob_content_invalid")
        if self.content_type not in (MISSING, None) and not isinstance(self.content_type, str):
            raise ValidationError(code="artifact_blob_content_type_invalid")


class ArtifactStore(Protocol):
    async def put(
        self, artifact: ArtifactEntry, /, *, blob: ArtifactBlob | None = None
    ) -> None: ...

    async def get(self, artifact_id: ArtifactId, /) -> ArtifactEntry | None: ...

    async def get_blob(self, artifact_id: ArtifactId, /) -> ArtifactBlob | None: ...

    async def mark_unavailable(
        self, artifact_id: ArtifactId, unavailable_at: Timestamp, /
    ) -> None: ...
