"""Derived non-authoritative Check Reports."""

from __future__ import annotations

from dataclasses import dataclass
from typing import final

from openrund.contracts.content import Content
from openrund.contracts.events import CheckRecordedReportPayload
from openrund.contracts.ids import ArtifactId, CheckId, EventId
from openrund.contracts.runs import CheckStatus
from openrund.contracts.time import Timestamp
from openrund.views._history import KnownHistory


@final
@dataclass(frozen=True, slots=True, kw_only=True)
class CheckReport:
    event_id: EventId
    check_id: CheckId
    timestamp: Timestamp
    source_watermark: int
    subject: str
    rule: str
    status: CheckStatus
    validator: str
    summary: str
    check_count: int
    result: Content
    message: str | None
    evidence: Content | None
    artifact_ids: tuple[ArtifactId, ...]


def _artifact_ids(*contents: Content | None) -> tuple[ArtifactId, ...]:
    values: dict[ArtifactId, None] = {}
    for content in contents:
        if content is None:
            continue
        for artifact_id in content.artifact_ids:
            values[artifact_id] = None
        for reference in content.artifact_refs:
            values[reference.artifact_id] = None
    return tuple(values)


def reduce_reports(history: KnownHistory) -> tuple[CheckReport, ...]:
    """Build replayable Reports without changing Check or Artifact state."""

    reports: list[CheckReport] = []
    for event in history.events:
        payload = event.payload
        if not isinstance(payload, CheckRecordedReportPayload):
            continue
        evidence = payload.evidence if isinstance(payload.evidence, Content) else None
        reports.append(
            CheckReport(
                event_id=event.event_id,
                check_id=payload.check_id,
                timestamp=event.timestamp,
                source_watermark=history.watermark,
                subject=payload.subject,
                rule=payload.rule,
                status=payload.status,
                validator=payload.validator,
                summary=payload.summary,
                check_count=payload.check_count,
                result=payload.result,
                message=payload.message if isinstance(payload.message, str) else None,
                evidence=evidence,
                artifact_ids=_artifact_ids(payload.result, evidence),
            )
        )
    return tuple(reports)
