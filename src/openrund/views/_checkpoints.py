"""Deterministic Checkpoint correction and active-summary Views."""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Literal, final

from openrund.contracts.events import (
    CheckpointCorrectionCreatedPayload,
    CheckpointRangeCreatedPayload,
    CoreEventType,
)
from openrund.contracts.ids import ArtifactId, CheckpointId
from openrund.contracts.json import JsonObject
from openrund.views._history import KnownHistory

_EMPTY_OBJECT = JsonObject(entries=())


@final
@dataclass(frozen=True, slots=True, kw_only=True)
class CheckpointEntry:
    checkpoint_id: CheckpointId
    from_position: int
    to_position: int
    source: Literal["model", "runtime", "operator"]
    summary: str | None
    retained_context: JsonObject
    protected_event_types: tuple[CoreEventType, ...]
    artifact_ids: tuple[ArtifactId, ...]
    obsolete: bool
    corrects_checkpoint_id: CheckpointId | None


@final
@dataclass(frozen=True, slots=True, kw_only=True)
class CheckpointView:
    checkpoints: tuple[CheckpointEntry, ...]
    active_checkpoints: tuple[CheckpointEntry, ...]


def reduce_checkpoints(history: KnownHistory) -> CheckpointView:
    """Retain all Checkpoints and mark corrected entries obsolete."""

    entries: list[CheckpointEntry] = []
    obsolete_ids: set[CheckpointId] = set()
    for event in history.events:
        payload = event.payload
        if not isinstance(
            payload,
            (CheckpointRangeCreatedPayload, CheckpointCorrectionCreatedPayload),
        ):
            continue
        corrects = (
            payload.correction.corrects_checkpoint_id
            if isinstance(payload, CheckpointCorrectionCreatedPayload)
            else None
        )
        if corrects is not None:
            obsolete_ids.add(corrects)
        entries.append(
            CheckpointEntry(
                checkpoint_id=payload.checkpoint_id,
                from_position=payload.from_position,
                to_position=payload.to_position,
                source=payload.source,
                summary=payload.summary if isinstance(payload.summary, str) else None,
                retained_context=(
                    payload.retained_context
                    if isinstance(payload.retained_context, JsonObject)
                    else _EMPTY_OBJECT
                ),
                protected_event_types=payload.protected_event_types,
                artifact_ids=payload.artifact_ids,
                obsolete=False,
                corrects_checkpoint_id=corrects,
            )
        )

    complete = tuple(
        replace(entry, obsolete=True) if entry.checkpoint_id in obsolete_ids else entry
        for entry in entries
    )
    return CheckpointView(
        checkpoints=complete,
        active_checkpoints=tuple(entry for entry in complete if not entry.obsolete),
    )
