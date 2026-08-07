from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import pytest

from openrund.codec import decode_event
from openrund.contracts.events import RuntimeEvent
from openrund.contracts.ids import ArtifactId, EventId, RunId
from openrund.contracts.runs import Artifact
from openrund.views import IncompleteViewReplay, ReplayIssueCode, prepare_history
from openrund.views._history import KnownHistory

_EVENT_PATH = (
    Path(__file__).parents[1]
    / "fixtures"
    / "compatibility"
    / "v1"
    / "evidence"
    / "event-run.created-1-canonical.jsonl"
)


@pytest.fixture
def event() -> RuntimeEvent:
    return decode_event(_EVENT_PATH.read_bytes())


def _codes(result: IncompleteViewReplay) -> tuple[ReplayIssueCode, ...]:
    return tuple(issue.code for issue in result.issues)


def test_empty_history_is_complete_only_at_zero_watermark() -> None:
    complete = prepare_history((), watermark=0)
    incomplete = prepare_history((), watermark=1)

    assert isinstance(complete, KnownHistory)
    assert complete.watermark == 0
    assert complete.run_id is None
    assert isinstance(incomplete, IncompleteViewReplay)
    assert _codes(incomplete) == (ReplayIssueCode.HISTORY_INCOMPLETE,)


@pytest.mark.parametrize("watermark", [None, -1, True, "1"])
def test_unknown_and_invalid_watermarks_fail_closed(watermark: object) -> None:
    result = prepare_history((), watermark=watermark)  # type: ignore[arg-type]

    assert isinstance(result, IncompleteViewReplay)
    assert not hasattr(result, "views")
    expected = (
        ReplayIssueCode.WATERMARK_UNKNOWN
        if watermark is None
        else ReplayIssueCode.WATERMARK_INVALID
    )
    assert _codes(result) == (expected,)


def test_exact_single_run_history_is_known(event: RuntimeEvent) -> None:
    result = prepare_history((event,), watermark=1)

    assert isinstance(result, KnownHistory)
    assert result.events == (event,)
    assert result.run_id == event.run_id


def test_gap_duplicate_reorder_and_beyond_watermark_are_reported(event: RuntimeEvent) -> None:
    second = replace(event, event_id=EventId(value="event-second"), position=2)
    third = replace(event, event_id=EventId(value="event-third"), position=3)

    gap = prepare_history((event, third), watermark=3)
    duplicate = prepare_history((event, replace(second, position=1)), watermark=2)
    reorder = prepare_history((second, event), watermark=2)
    beyond = prepare_history((event, second), watermark=1)

    assert isinstance(gap, IncompleteViewReplay)
    assert ReplayIssueCode.HISTORY_INCOMPLETE in _codes(gap)
    assert isinstance(duplicate, IncompleteViewReplay)
    assert ReplayIssueCode.HISTORY_POSITION_DUPLICATE in _codes(duplicate)
    assert isinstance(reorder, IncompleteViewReplay)
    assert ReplayIssueCode.HISTORY_OUT_OF_ORDER in _codes(reorder)
    assert isinstance(beyond, IncompleteViewReplay)
    assert ReplayIssueCode.HISTORY_BEYOND_WATERMARK in _codes(beyond)


def test_mixed_runs_and_invalid_events_fail_closed(event: RuntimeEvent) -> None:
    other = replace(
        event,
        event_id=EventId(value="event-other"),
        run_id=RunId(value="run-other"),
        position=2,
    )
    mixed = prepare_history((event, other), watermark=2)
    invalid = prepare_history((event, object()), watermark=2)  # type: ignore[arg-type]

    assert isinstance(mixed, IncompleteViewReplay)
    assert ReplayIssueCode.HISTORY_MIXED_RUN in _codes(mixed)
    assert isinstance(invalid, IncompleteViewReplay)
    assert _codes(invalid) == (ReplayIssueCode.HISTORY_EVENT_INVALID,)


def _artifact(*, event: RuntimeEvent, artifact_id: str, kind: str = "report") -> Artifact:
    return Artifact(
        artifact_id=ArtifactId(value=artifact_id),
        run_id=event.run_id,
        kind=kind,
        byte_length=0,
        sha256="0" * 64,
    )


def test_identical_artifacts_dedupe_but_conflicts_fail_closed(event: RuntimeEvent) -> None:
    artifact = _artifact(event=event, artifact_id="artifact")
    deduped = prepare_history((event,), watermark=1, artifacts=(artifact, artifact))
    conflicting = prepare_history(
        (event,),
        watermark=1,
        artifacts=(artifact, _artifact(event=event, artifact_id="artifact", kind="other")),
    )

    assert isinstance(deduped, KnownHistory)
    assert deduped.artifacts == (artifact,)
    assert isinstance(conflicting, IncompleteViewReplay)
    assert _codes(conflicting) == (ReplayIssueCode.ARTIFACT_CONFLICT,)
