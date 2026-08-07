"""Fail-closed validation for known-watermark View input."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from itertools import pairwise
from typing import final

from openrund.contracts.events import Event, RuntimeEvent
from openrund.contracts.ids import RunId
from openrund.contracts.runs import Artifact
from openrund.views._model import IncompleteViewReplay, ReplayIssue, ReplayIssueCode


@final
@dataclass(frozen=True, slots=True, kw_only=True)
class KnownHistory:
    """Private source history proven complete at one exact watermark."""

    events: tuple[RuntimeEvent, ...]
    artifacts: tuple[Artifact, ...]
    watermark: int
    run_id: RunId | None


def _append_issue(
    issues: list[ReplayIssue],
    code: ReplayIssueCode,
    *,
    position: int | None = None,
) -> None:
    issue = ReplayIssue(code=code, position=position)
    if issue not in issues:
        issues.append(issue)


def _incomplete(
    watermark: int | None,
    positions: tuple[int, ...],
    issues: list[ReplayIssue],
) -> IncompleteViewReplay:
    return IncompleteViewReplay(
        declared_watermark=watermark,
        observed_positions=positions,
        issues=tuple(issues),
    )


def prepare_history(
    events: Iterable[RuntimeEvent],
    *,
    watermark: int | None,
    artifacts: Iterable[Artifact] = (),
) -> KnownHistory | IncompleteViewReplay:
    """Prove exact completeness before exposing input to any reducer."""

    if watermark is None:
        return _incomplete(
            None,
            (),
            [ReplayIssue(code=ReplayIssueCode.WATERMARK_UNKNOWN)],
        )
    if not isinstance(watermark, int) or isinstance(watermark, bool) or watermark < 0:
        return _incomplete(
            None,
            (),
            [ReplayIssue(code=ReplayIssueCode.WATERMARK_INVALID)],
        )

    issues: list[ReplayIssue] = []
    try:
        event_values: tuple[object, ...] = tuple(events)
    except TypeError:
        return _incomplete(
            watermark,
            (),
            [ReplayIssue(code=ReplayIssueCode.HISTORY_INPUT_INVALID)],
        )
    if any(not isinstance(event, Event) for event in event_values):
        return _incomplete(
            watermark,
            (),
            [ReplayIssue(code=ReplayIssueCode.HISTORY_EVENT_INVALID)],
        )
    typed_events = event_values  # statically narrowed below after the runtime boundary
    event_tuple: tuple[RuntimeEvent, ...] = tuple(typed_events)  # type: ignore[arg-type]
    positions = tuple(event.position for event in event_tuple)

    run_ids = tuple(dict.fromkeys(event.run_id for event in event_tuple))
    if len(run_ids) > 1:
        _append_issue(issues, ReplayIssueCode.HISTORY_MIXED_RUN)
    if len(set(positions)) != len(positions):
        duplicate = next(
            position for index, position in enumerate(positions) if position in positions[:index]
        )
        _append_issue(
            issues,
            ReplayIssueCode.HISTORY_POSITION_DUPLICATE,
            position=duplicate,
        )
    if any(right <= left for left, right in pairwise(positions)):
        _append_issue(issues, ReplayIssueCode.HISTORY_OUT_OF_ORDER)
    beyond = next((position for position in positions if position > watermark), None)
    if beyond is not None:
        _append_issue(
            issues,
            ReplayIssueCode.HISTORY_BEYOND_WATERMARK,
            position=beyond,
        )
    if positions != tuple(range(1, watermark + 1)):
        _append_issue(issues, ReplayIssueCode.HISTORY_INCOMPLETE)

    try:
        artifact_values: tuple[object, ...] = tuple(artifacts)
    except TypeError:
        _append_issue(issues, ReplayIssueCode.ARTIFACT_INPUT_INVALID)
        artifact_values = ()
    if any(not isinstance(artifact, Artifact) for artifact in artifact_values):
        _append_issue(issues, ReplayIssueCode.ARTIFACT_INPUT_INVALID)
        artifact_values = ()
    artifact_tuple: tuple[Artifact, ...] = tuple(artifact_values)  # type: ignore[arg-type]
    unique_artifacts: dict[object, Artifact] = {}
    for artifact in artifact_tuple:
        existing = unique_artifacts.get(artifact.artifact_id)
        if existing is not None and existing != artifact:
            _append_issue(issues, ReplayIssueCode.ARTIFACT_CONFLICT)
        else:
            unique_artifacts[artifact.artifact_id] = artifact

    run_id = run_ids[0] if len(run_ids) == 1 else None
    if run_id is not None and any(
        artifact.run_id != run_id for artifact in unique_artifacts.values()
    ):
        _append_issue(issues, ReplayIssueCode.ARTIFACT_MIXED_RUN)

    if issues:
        return _incomplete(watermark, positions, issues)
    return KnownHistory(
        events=event_tuple,
        artifacts=tuple(unique_artifacts.values()),
        watermark=watermark,
        run_id=run_id,
    )
