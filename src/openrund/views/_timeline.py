"""Deterministic chronological Event summaries."""

from __future__ import annotations

from dataclasses import dataclass
from typing import final

from openrund.contracts.content import RunResult
from openrund.contracts.events import (
    ActionCreatedPayload,
    ActionReconciledCancelledPayload,
    ActionReconciledCompletedPayload,
    ActionReconciledFailedPayload,
    ActionUnknownPayload,
    ArtifactMetadataCreatedPayload,
    ArtifactPreviewCreatedPayload,
    CanonicalMessageAddedPayload,
    CheckRecordedReportPayload,
    CoreEventType,
    LegacyPreviewMessageAddedPayload,
    RunCompletedPayload,
    RunCreatedPayload,
    RunFailedPayload,
    RunStartedPayload,
    RuntimeEvent,
)
from openrund.contracts.ids import EventId
from openrund.contracts.json import MISSING
from openrund.contracts.time import Timestamp
from openrund.views._history import KnownHistory


@final
@dataclass(frozen=True, slots=True, kw_only=True)
class TimelineEntry:
    event_id: EventId
    event_type: CoreEventType
    timestamp: Timestamp
    summary: str | None


def _summary(event: RuntimeEvent) -> str | None:
    payload = event.payload
    if isinstance(payload, RunCreatedPayload):
        return "Run created"
    if isinstance(payload, RunStartedPayload):
        return payload.reason if isinstance(payload.reason, str) else "Run started"
    if isinstance(payload, RunCompletedPayload):
        if isinstance(payload.result, RunResult) and isinstance(payload.result.summary, str):
            return payload.result.summary
        return "Run completed"
    if isinstance(payload, RunFailedPayload):
        return payload.message
    if isinstance(payload, CanonicalMessageAddedPayload):
        return payload.content_preview
    if isinstance(payload, LegacyPreviewMessageAddedPayload):
        return payload.content.preview if isinstance(payload.content.preview, str) else None
    if isinstance(payload, ActionCreatedPayload):
        return f"{payload.capability_id.value}.{payload.action_name}"
    if isinstance(payload, ActionUnknownPayload):
        return f"Action outcome unknown: {payload.action_id.value}"
    if isinstance(
        payload,
        (
            ActionReconciledCompletedPayload,
            ActionReconciledFailedPayload,
            ActionReconciledCancelledPayload,
        ),
    ):
        return f"Action outcome reconciled: {payload.outcome}"
    if isinstance(payload, CheckRecordedReportPayload):
        return f"Check {payload.status.value}: {payload.summary}"
    if isinstance(payload, ArtifactPreviewCreatedPayload):
        return payload.content_preview
    if isinstance(payload, ArtifactMetadataCreatedPayload):
        return payload.kind
    if event.event_type is CoreEventType.WAIT_CREATED:
        reason = getattr(payload, "reason", MISSING)
        return reason if isinstance(reason, str) else "Run waiting"
    if event.event_type is CoreEventType.WAIT_RESOLVED:
        return "Run resumed"
    return None


def reduce_timeline(history: KnownHistory) -> tuple[TimelineEntry, ...]:
    """Return one immutable entry per source Event in exact history order."""

    return tuple(
        TimelineEntry(
            event_id=event.event_id,
            event_type=event.event_type,
            timestamp=event.timestamp,
            summary=_summary(event),
        )
        for event in history.events
    )
