from __future__ import annotations

import json
from collections.abc import Mapping

from openrund.codec import decode_event
from openrund.contracts.events import RuntimeEvent
from openrund.contracts.ids import ArtifactId
from openrund.views import prepare_history
from openrund.views._artifacts import reduce_artifact_index
from openrund.views._history import KnownHistory
from openrund.views._timeline import reduce_timeline
from tests.conftest import CorpusEntry
from tests.views.conftest import read_view_entry


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


def _entry(entries: tuple[CorpusEntry, ...], key: str) -> CorpusEntry:
    return next(entry for entry in entries if entry.key == key)


def test_timeline_explicit_fallback_and_absent_summaries(
    view_entries: tuple[CorpusEntry, ...],
) -> None:
    explicit = reduce_timeline(_history(_entry(view_entries, "view:timeline:explicit-summary")))
    fallback = reduce_timeline(_history(_entry(view_entries, "view:timeline:fallback-summary")))
    absent = reduce_timeline(_history(_entry(view_entries, "view:timeline:undefined-summary")))

    assert explicit[0].summary == "explicit oracle summary"
    assert fallback[0].summary == "Run started"
    assert absent[0].summary is None
    assert explicit[0].event_type.value == "run.started"


def test_timeline_preserves_event_order(view_entries: tuple[CorpusEntry, ...]) -> None:
    history = _history(_entry(view_entries, "view:artifact-index:unavailable"))

    timeline = reduce_timeline(history)

    assert tuple(item.event_id for item in timeline) == tuple(
        event.event_id for event in history.events
    )


def test_artifact_index_matches_all_frozen_states(
    view_entries: tuple[CorpusEntry, ...],
) -> None:
    cases: Mapping[str, tuple[bool, str | None]] = {
        "view:artifact-index:available-preview": (True, "oracle preview"),
        "view:artifact-index:available-no-preview": (True, None),
        "view:artifact-index:unavailable": (False, None),
    }
    for key, (available, preview) in cases.items():
        index = reduce_artifact_index(_history(_entry(view_entries, key)))
        item = index[ArtifactId(value="art_oracle")]
        assert item.available is available
        assert item.content_preview == preview
        assert item.kind == "oracle"
        assert dict(item.metadata) == {}


def test_artifact_index_mapping_is_immutable(view_entries: tuple[CorpusEntry, ...]) -> None:
    index = reduce_artifact_index(
        _history(_entry(view_entries, "view:artifact-index:available-preview"))
    )

    assert type(index).__name__ == "mappingproxy"
