from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import NoReturn

from pytest import MonkeyPatch

from openrund.codec import decode_event
from openrund.contracts.events import RuntimeEvent
from openrund.views import (
    CompleteViewReplay,
    IncompleteViewReplay,
    RunViewBundle,
    rebuild_views,
)
from openrund.views._history import KnownHistory

_PROJECT_ROOT = Path(__file__).parents[2]
_SOURCE_ROOT = _PROJECT_ROOT / "src"
_EVIDENCE = Path(__file__).parents[1] / "fixtures" / "compatibility" / "v1" / "evidence"


def _events(name: str) -> tuple[RuntimeEvent, ...]:
    decoded: object = json.loads((_EVIDENCE / name).read_bytes())
    assert isinstance(decoded, dict)
    stream = decoded["stream"]
    assert isinstance(stream, list)
    return tuple(decode_event(json.dumps(value, separators=(",", ":")) + "\n") for value in stream)


def _complete(events: tuple[RuntimeEvent, ...]) -> CompleteViewReplay[RunViewBundle]:
    replay = rebuild_views(events, watermark=len(events))
    assert isinstance(replay, CompleteViewReplay)
    return replay


def test_repeated_replay_is_value_and_representation_stable() -> None:
    events = _events("view-action-receipts-completed.jsonl")

    first = _complete(events)
    second = _complete(tuple(events))

    assert first == second
    assert repr(first) == repr(second)
    assert (
        hashlib.sha256(repr(first).encode()).digest()
        == hashlib.sha256(repr(second).encode()).digest()
    )


def test_prefix_replay_matches_an_independently_reconstructed_prefix() -> None:
    events = _events("view-action-receipts-completed.jsonl")

    first_prefix = _complete(events[:2])
    _complete(events)
    second_prefix = _complete(tuple(event for event in events if event.position <= 2))

    assert first_prefix == second_prefix
    assert len(first_prefix.views.timeline) == 2


def test_unrelated_replays_cannot_change_result_state() -> None:
    events = _events("view-action-receipts-completed.jsonl")
    unrelated = _events("view-timeline-explicit-summary.jsonl")

    before = _complete(events)
    _complete(unrelated)
    _complete(unrelated)
    after = _complete(events)

    assert before == after


def test_fresh_processes_produce_the_same_replay_fingerprint() -> None:
    path = _EVIDENCE / "view-action-receipts-completed.jsonl"
    script = """
import hashlib, json, sys
from openrund.codec import decode_event
from openrund.views import rebuild_views
value = json.loads(open(sys.argv[1], 'rb').read())
events = tuple(
    decode_event(json.dumps(item, separators=(',', ':')) + '\\n')
    for item in value['stream']
)
result = rebuild_views(events, watermark=value['watermark'])
print(hashlib.sha256(repr(result).encode()).hexdigest())
"""
    environment = dict(os.environ)
    environment["PYTHONPATH"] = str(_SOURCE_ROOT)

    outputs = tuple(
        subprocess.run(
            (sys.executable, "-c", script, str(path)),
            cwd=_PROJECT_ROOT,
            env=environment,
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
        for _ in range(2)
    )

    assert outputs[0] == outputs[1]
    assert len(outputs[0]) == 64


def test_aggregate_returns_only_immutable_collections() -> None:
    replay = _complete(_events("view-action-receipts-completed.jsonl"))
    bundle = replay.views

    assert isinstance(bundle.timeline, tuple)
    assert type(bundle.action_status).__name__ == "mappingproxy"
    assert type(bundle.action_receipts).__name__ == "mappingproxy"
    assert type(bundle.artifact_index).__name__ == "mappingproxy"
    assert isinstance(bundle.reports, tuple)


def test_incomplete_history_returns_before_any_reducer(monkeypatch: MonkeyPatch) -> None:
    from openrund.views import _rebuild

    events = _events("view-action-receipts-completed.jsonl")

    def fail_if_called(_: KnownHistory) -> NoReturn:
        raise AssertionError("reducer_called_before_validation")

    monkeypatch.setattr(_rebuild, "reduce_actions", fail_if_called)

    replay = rebuild_views(events[:1], watermark=2)

    assert isinstance(replay, IncompleteViewReplay)
    assert not hasattr(replay, "views")
