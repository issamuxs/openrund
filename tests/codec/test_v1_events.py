from __future__ import annotations

from dataclasses import replace

import pytest
from tests.conftest import CorpusEntry, read_corpus_entry

from openrund.codec import decode_command_decision, decode_event, encode_event
from openrund.contracts.events import ModelCommandRecordedPayload, RunCreatedPayload
from openrund.contracts.ids import RunId
from openrund.errors import EncodeError


def test_every_writer_eligible_event_round_trips_exact_frozen_bytes(
    phase28_entries: tuple[CorpusEntry, ...],
) -> None:
    entries = tuple(entry for entry in phase28_entries if entry.category == "event")
    encoded = 0
    rejected = 0
    for entry in entries:
        wire = read_corpus_entry(entry)
        event = decode_event(wire)
        if event.association.decode_only:
            with pytest.raises(EncodeError, match="legacy_payload_writer"):
                encode_event(event)
            rejected += 1
            continue
        assert encode_event(event) == wire, entry.key
        encoded += 1

    assert encoded == 63
    assert rejected == 2


def test_event_encoder_preserves_missing_null_and_present_values() -> None:
    base = (
        b'{"id":"e1","runID":"r1","position":1,"type":"run.created","version":1,'
        b'"timestamp":"2026-01-02T03:04:05.678Z","actor":"system",'
        b'"payload":{"rootID":"r1","initialStatus":"created","parentRunID":null}}\n'
    )
    event = decode_event(base)

    assert isinstance(event.payload, RunCreatedPayload)
    assert event.payload.parent_run_id is None
    assert encode_event(event) == base

    present_wire = base.replace(b"null", b'"r0"')
    present = decode_event(present_wire)
    assert isinstance(present.payload, RunCreatedPayload)
    assert present.payload.parent_run_id == RunId(value="r0")
    assert encode_event(present) == present_wire


def test_command_recorded_superseded_branch_is_writer_eligible_only_in_event_context(
    phase28_entries: tuple[CorpusEntry, ...],
) -> None:
    command_entry = next(entry for entry in phase28_entries if entry.key == "command:superseded")
    model_event_entry = next(
        entry for entry in phase28_entries if entry.key == "event:command.recorded:1:model"
    )
    record = decode_command_decision(read_corpus_entry(command_entry))
    event = decode_event(read_corpus_entry(model_event_entry))
    assert isinstance(event.payload, ModelCommandRecordedPayload)
    linked_record = replace(record, command_id=event.payload.command_id)
    superseded_payload = replace(event.payload, decision_record=linked_record)
    superseded_event = replace(event, payload=superseded_payload)

    encoded = encode_event(superseded_event)

    assert b'"decision":"superseded"' in encoded
    assert b'"declarationOnly":true' in encoded
    assert b'"replacementCommandID"' in encoded
    assert decode_event(encoded) == superseded_event
