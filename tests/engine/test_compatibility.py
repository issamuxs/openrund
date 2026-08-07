from __future__ import annotations

import pytest

from openrund.codec import decode_command_decision, decode_event, encode_event
from openrund.contracts.commands import SupersededDecisionRecord
from openrund.contracts.events import ModelCommandRecordedPayload, RuntimeCommandRecordedPayload
from openrund.errors import EncodeError
from tests.conftest import CorpusEntry, read_corpus_entry

_PHASE31_EVENT_KEYS = (
    "event:run.created:1:canonical",
    "event:run.started:1:canonical",
    "event:run.completed:1:canonical",
    "event:run.failed:1:canonical",
    "event:run.cancelled:1:canonical",
    "event:command.recorded:1:model",
    "event:command.recorded:1:runtime",
    "event:message.added:1:legacy-preview",
    "event:message.delta:1:canonical",
    "event:model_call.started:1:canonical",
    "event:model_call.completed:1:canonical",
    "event:model_call.failed:1:canonical",
    "event:model_call.cancelled:1:canonical",
)
_PHASE31_COMMAND_KEYS = (
    "command:accepted",
    "command:rejected",
    "command:deferred",
    "command:superseded",
)


def _by_key(entries: tuple[CorpusEntry, ...]) -> dict[str, CorpusEntry]:
    selected = {
        entry.key: entry
        for entry in entries
        if entry.key in {*_PHASE31_EVENT_KEYS, *_PHASE31_COMMAND_KEYS}
    }
    all_keys = (*_PHASE31_EVENT_KEYS, *_PHASE31_COMMAND_KEYS)
    assert tuple(key for key in all_keys if key in selected) == (
        *_PHASE31_EVENT_KEYS,
        *_PHASE31_COMMAND_KEYS,
    )
    assert len(selected) == len(_PHASE31_EVENT_KEYS) + len(_PHASE31_COMMAND_KEYS)
    return selected


def test_phase31_writer_events_round_trip_exact_authenticated_bytes(
    phase28_entries: tuple[CorpusEntry, ...],
) -> None:
    selected = _by_key(phase28_entries)

    for key in _PHASE31_EVENT_KEYS:
        wire = read_corpus_entry(selected[key])
        event = decode_event(wire)
        assert encode_event(event) == wire, key

    model = decode_event(read_corpus_entry(selected["event:command.recorded:1:model"]))
    runtime = decode_event(read_corpus_entry(selected["event:command.recorded:1:runtime"]))
    assert isinstance(model.payload, ModelCommandRecordedPayload)
    assert isinstance(runtime.payload, RuntimeCommandRecordedPayload)


def test_phase31_decision_evidence_preserves_all_frozen_branches(
    phase28_entries: tuple[CorpusEntry, ...],
) -> None:
    selected = _by_key(phase28_entries)
    records = tuple(
        decode_command_decision(read_corpus_entry(selected[key])) for key in _PHASE31_COMMAND_KEYS
    )

    assert tuple(record.branch.decision for record in records) == (
        "accepted",
        "rejected",
        "deferred",
        "superseded",
    )
    assert isinstance(records[-1].branch, SupersededDecisionRecord)
    with pytest.raises(EncodeError, match="declaration_only_writer"):
        from openrund.codec import encode_command_decision

        encode_command_decision(records[-1])


def test_phase31_compatibility_selection_is_explicit_and_closed(
    phase28_entries: tuple[CorpusEntry, ...],
) -> None:
    selected = _by_key(phase28_entries)

    assert set(selected) == {*_PHASE31_EVENT_KEYS, *_PHASE31_COMMAND_KEYS}
    assert not any("action." in key or "wait." in key for key in selected)
