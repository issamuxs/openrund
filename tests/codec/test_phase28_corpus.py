from __future__ import annotations

import hashlib
from collections import Counter
from dataclasses import replace

import pytest
from tests.conftest import CorpusEntry, read_corpus_entry

from openrund.codec import (
    canonical_json_bytes,
    decode_command_decision,
    decode_event,
    encode_command_decision,
    encode_event,
)
from openrund.contracts.commands import (
    AcceptedDecisionRecord,
    CommandDecisionRecord,
    DeferredDecisionRecord,
    RejectedCommandDecision,
    RejectedDecisionRecord,
    SupersededCommandDecision,
    SupersededDecisionRecord,
    TargetEventAbsent,
    TargetEventPresent,
)
from openrund.contracts.events import ModelCommandRecordedPayload
from openrund.contracts.json import freeze_json
from openrund.errors import EncodeError

_EXPECTED_COUNTS = {
    "event": 65,
    "command-decision": 4,
    "wire": 18,
    "number": 14,
    "field-policy": 6,
    "rejection": 19,
}


def _authenticated_snapshot(
    entries: tuple[CorpusEntry, ...],
) -> dict[str, tuple[int, str]]:
    return {
        entry.key: (len(evidence), hashlib.sha256(evidence).hexdigest())
        for entry in entries
        for evidence in (read_corpus_entry(entry),)
    }


def test_scoped_manifest_selection_is_an_exact_authenticated_bijection(
    phase28_entries: tuple[CorpusEntry, ...],
) -> None:
    counts = Counter(entry.category for entry in phase28_entries)

    assert counts == _EXPECTED_COUNTS
    assert len(phase28_entries) == sum(_EXPECTED_COUNTS.values()) == 126
    assert len({entry.key for entry in phase28_entries}) == len(phase28_entries)
    assert len({entry.relative_path for entry in phase28_entries}) == len(phase28_entries)
    for entry in phase28_entries:
        evidence = read_corpus_entry(entry)
        assert len(evidence) == entry.byte_length
        assert hashlib.sha256(evidence).hexdigest() == entry.sha256


def test_complete_event_matrix_decodes_hashes_and_applies_writer_policy(
    phase28_entries: tuple[CorpusEntry, ...],
) -> None:
    entries = tuple(entry for entry in phase28_entries if entry.category == "event")
    writer_count = 0
    decode_only_count = 0

    for entry in entries:
        wire = read_corpus_entry(entry)
        event = decode_event(wire)
        assert event.association.variant == entry.key.rsplit(":", 1)[1]
        expected_semantic_hash = entry.manifest_entry["semanticSha256"]
        assert isinstance(expected_semantic_hash, str)
        actual_semantic_hash = hashlib.sha256(
            canonical_json_bytes(freeze_json(entry.decoded_meaning))
        ).hexdigest()
        assert actual_semantic_hash == expected_semantic_hash
        if event.association.decode_only:
            with pytest.raises(EncodeError, match="legacy_payload_writer"):
                encode_event(event)
            decode_only_count += 1
        else:
            assert encode_event(event) == wire
            writer_count += 1

    assert writer_count == 63
    assert decode_only_count == 2


def test_four_decision_rows_preserve_every_branch_pointer_and_writer_rule(
    phase28_entries: tuple[CorpusEntry, ...],
) -> None:
    entries = {
        entry.key: entry for entry in phase28_entries if entry.category == "command-decision"
    }
    records: dict[str, CommandDecisionRecord] = {
        key: decode_command_decision(read_corpus_entry(entry)) for key, entry in entries.items()
    }

    accepted = records["command:accepted"]
    assert accepted.command_id.value == "cmd_oracle_accepted"
    assert isinstance(accepted.branch, AcceptedDecisionRecord)
    assert accepted.branch.decision == "accepted"
    assert len(accepted.branch.decision_trace) == 1
    assert accepted.branch.result_event_ids
    assert isinstance(accepted.target_event, TargetEventPresent)
    assert accepted.target_event.event_id in accepted.branch.result_event_ids

    rejected = records["command:rejected"]
    assert isinstance(rejected.branch, RejectedDecisionRecord)
    assert rejected.branch.decision == "rejected"
    assert rejected.branch.result_event_ids == ()
    assert rejected.branch.rejection.code == "command_rejected"
    assert isinstance(rejected.target_event, TargetEventAbsent)
    assert not hasattr(rejected.branch, "reason")

    deferred = records["command:deferred"]
    assert isinstance(deferred.branch, DeferredDecisionRecord)
    assert deferred.branch.decision == "deferred"
    assert deferred.branch.result_event_ids == ()
    assert deferred.branch.wait.wait_id.value == "w_oracle_deferred"
    assert deferred.branch.wait.kind.value == "approval"
    assert isinstance(deferred.target_event, TargetEventAbsent)
    assert not hasattr(deferred.branch, "reason")

    superseded = records["command:superseded"]
    assert isinstance(superseded.branch, SupersededDecisionRecord)
    assert superseded.branch.decision == "superseded"
    assert superseded.branch.declaration_only is True
    assert superseded.branch.replacement_command_id.value == "cmd_oracle_replacement"
    assert isinstance(superseded.target_event, TargetEventAbsent)
    assert not hasattr(superseded.branch, "reason")

    for key in ("command:accepted", "command:rejected", "command:deferred"):
        assert encode_command_decision(records[key]) == read_corpus_entry(entries[key])
    with pytest.raises(EncodeError, match="declaration_only_writer"):
        encode_command_decision(superseded)


def test_runtime_reasoned_decisions_remain_strict_and_normal_values() -> None:
    with pytest.raises(TypeError):
        RejectedCommandDecision(trace=())  # type: ignore[call-arg]
    with pytest.raises(TypeError):
        SupersededCommandDecision(trace=())  # type: ignore[call-arg]

    rejected = RejectedCommandDecision(reason="policy", trace=())
    assert rejected.kind == "rejected"
    assert rejected.reason == "policy"


def test_command_recorded_reuses_typed_record_and_phase31_supersession_path(
    phase28_entries: tuple[CorpusEntry, ...],
) -> None:
    model_entry = next(
        entry for entry in phase28_entries if entry.key == "event:command.recorded:1:model"
    )
    superseded_entry = next(entry for entry in phase28_entries if entry.key == "command:superseded")
    event = decode_event(read_corpus_entry(model_entry))
    assert isinstance(event.payload, ModelCommandRecordedPayload)
    assert event.payload.command_id == event.payload.decision_record.command_id
    assert isinstance(event.payload.decision_record.branch, AcceptedDecisionRecord)

    superseded = decode_command_decision(read_corpus_entry(superseded_entry))
    linked = replace(superseded, command_id=event.payload.command_id)
    changed_payload = replace(event.payload, decision_record=linked)
    changed_event = replace(event, payload=changed_payload)
    encoded = encode_event(changed_event)

    assert b'"decision":"superseded"' in encoded
    assert b'"declarationOnly":true' in encoded
    assert decode_event(encoded) == changed_event


def test_complete_gate_does_not_modify_authenticated_corpus(
    phase28_entries: tuple[CorpusEntry, ...],
) -> None:
    before = _authenticated_snapshot(phase28_entries)

    for entry in phase28_entries:
        read_corpus_entry(entry)

    assert _authenticated_snapshot(phase28_entries) == before
