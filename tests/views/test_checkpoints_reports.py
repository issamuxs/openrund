from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path

from openrund.codec import decode_event
from openrund.contracts.events import CheckpointCorrectionCreatedPayload, RuntimeEvent
from openrund.contracts.ids import CheckpointId
from openrund.views import prepare_history
from openrund.views._checkpoints import reduce_checkpoints
from openrund.views._history import KnownHistory
from openrund.views._reports import reduce_reports
from tests.conftest import CorpusEntry
from tests.views.conftest import read_view_entry


def _entry(entries: tuple[CorpusEntry, ...], key: str) -> CorpusEntry:
    return next(entry for entry in entries if entry.key == key)


def _history(entry: CorpusEntry) -> KnownHistory:
    decoded: object = json.loads(read_view_entry(entry))
    assert isinstance(decoded, dict)
    stream = decoded["stream"]
    watermark = decoded["watermark"]
    assert isinstance(stream, list)
    assert isinstance(watermark, int)
    events: tuple[RuntimeEvent, ...] = tuple(
        decode_event(json.dumps(value, separators=(",", ":")) + "\n") for value in stream
    )
    history = prepare_history(events, watermark=watermark)
    assert isinstance(history, KnownHistory)
    return history


def test_checkpoint_ranges_and_corrections_match_frozen_cases(
    view_entries: tuple[CorpusEntry, ...],
) -> None:
    default = reduce_checkpoints(
        _history(_entry(view_entries, "view:checkpoints:default-range"))
    ).checkpoints[0]
    explicit = reduce_checkpoints(
        _history(_entry(view_entries, "view:checkpoints:explicit-range"))
    ).checkpoints[0]
    correction = reduce_checkpoints(
        _history(_entry(view_entries, "view:checkpoints:correction"))
    ).checkpoints[0]

    assert (default.from_position, default.to_position) == (0, 2)
    assert (explicit.from_position, explicit.to_position) == (1, 2)
    assert correction.corrects_checkpoint_id == CheckpointId(value="ckp_previous")
    assert correction.obsolete is False


def test_correction_marks_an_existing_checkpoint_obsolete(
    view_entries: tuple[CorpusEntry, ...],
) -> None:
    first = _history(_entry(view_entries, "view:checkpoints:explicit-range")).events[0]
    correction = _history(_entry(view_entries, "view:checkpoints:correction")).events[0]
    payload = correction.payload
    assert isinstance(payload, CheckpointCorrectionCreatedPayload)
    correction = replace(
        correction,
        run_id=first.run_id,
        position=2,
        payload=replace(
            payload,
            checkpoint_id=CheckpointId(value="ckp_correction"),
            correction=replace(
                payload.correction,
                corrects_checkpoint_id=CheckpointId(value="ckp_oracle"),
            ),
        ),
    )
    history = prepare_history((first, correction), watermark=2)
    assert isinstance(history, KnownHistory)

    result = reduce_checkpoints(history)

    assert result.checkpoints[0].obsolete is True
    assert result.active_checkpoints == (result.checkpoints[1],)


def test_check_events_produce_non_authoritative_reports() -> None:
    event_path = (
        Path(__file__).parents[1]
        / "fixtures"
        / "compatibility"
        / "v1"
        / "evidence"
        / "event-check.recorded-1-report.jsonl"
    )
    event = replace(decode_event(event_path.read_bytes()), position=1)
    history = prepare_history((event,), watermark=1)
    assert isinstance(history, KnownHistory)

    reports = reduce_reports(history)

    assert len(reports) == 1
    assert reports[0].summary
    assert reports[0].source_watermark == history.watermark
    assert not hasattr(reports[0], "append_event")
    assert not hasattr(reports[0], "decide_legality")
