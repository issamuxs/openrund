"""Deterministic Artifact availability index."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, replace
from types import MappingProxyType
from typing import final

from openrund.contracts.events import (
    ArtifactMetadataCreatedPayload,
    ArtifactPreviewCreatedPayload,
    ArtifactUnavailablePayload,
)
from openrund.contracts.ids import ArtifactId
from openrund.contracts.json import JsonObject
from openrund.views._history import KnownHistory

_EMPTY_OBJECT = JsonObject(entries=())


@final
@dataclass(frozen=True, slots=True, kw_only=True)
class ArtifactIndexEntry:
    artifact_id: ArtifactId
    kind: str
    metadata: JsonObject
    content_preview: str | None
    available: bool


def reduce_artifact_index(history: KnownHistory) -> Mapping[ArtifactId, ArtifactIndexEntry]:
    """Index immutable Artifact facts without reading an Artifact store."""

    entries: dict[ArtifactId, ArtifactIndexEntry] = {}
    for event in history.events:
        payload = event.payload
        if isinstance(payload, (ArtifactMetadataCreatedPayload, ArtifactPreviewCreatedPayload)):
            preview = (
                payload.content_preview
                if isinstance(payload, ArtifactPreviewCreatedPayload)
                else None
            )
            entries[payload.artifact_id] = ArtifactIndexEntry(
                artifact_id=payload.artifact_id,
                kind=payload.kind,
                metadata=payload.metadata,
                content_preview=preview,
                available=True,
            )
        elif isinstance(payload, ArtifactUnavailablePayload):
            current = entries.get(payload.artifact_id)
            if current is not None:
                entries[payload.artifact_id] = replace(current, available=False)

    for artifact in history.artifacts:
        current = entries.get(artifact.artifact_id)
        if current is None:
            entries[artifact.artifact_id] = ArtifactIndexEntry(
                artifact_id=artifact.artifact_id,
                kind=artifact.kind,
                metadata=(
                    artifact.metadata
                    if isinstance(artifact.metadata, JsonObject)
                    else _EMPTY_OBJECT
                ),
                content_preview=artifact.preview if isinstance(artifact.preview, str) else None,
                available=artifact.available,
            )
        elif not artifact.available:
            entries[artifact.artifact_id] = replace(current, available=False)
        elif isinstance(artifact.preview, str) and current.content_preview is None:
            entries[artifact.artifact_id] = replace(
                current,
                content_preview=artifact.preview,
            )

    return MappingProxyType(entries)
