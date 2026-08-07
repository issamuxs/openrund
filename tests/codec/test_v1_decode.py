from __future__ import annotations

from collections.abc import Mapping

from tests.conftest import CorpusEntry, FrozenJson, read_corpus_entry

from openrund.codec import decode_command_decision, decode_event
from openrund.contracts.commands import (
    AcceptedDecisionRecord,
    DeferredDecisionRecord,
    RejectedDecisionRecord,
    SupersededDecisionRecord,
    TargetEventAbsent,
    TargetEventPresent,
)
from openrund.contracts.events import (
    ModelCommandRecordedPayload,
    RunCreatedPayload,
    RuntimeCommandRecordedPayload,
)
from openrund.contracts.ids import CommandId, CorrelationId, EventId, RunId
from openrund.contracts.json import MISSING


def _mapping(value: FrozenJson) -> Mapping[str, FrozenJson]:
    assert isinstance(value, Mapping)
    return value


def test_every_frozen_event_decodes_to_its_exact_catalog_association(
    phase28_entries: tuple[CorpusEntry, ...],
) -> None:
    entries = tuple(entry for entry in phase28_entries if entry.category == "event")
    assert len(entries) == 65

    for entry in entries:
        event = decode_event(read_corpus_entry(entry))
        event_meaning = _mapping(_mapping(entry.decoded_meaning)["event"])
        assert event.event_type.value == event_meaning["type"]
        assert event.version == event_meaning["version"]
        assert event.association.variant == entry.key.rsplit(":", 1)[1]
        assert isinstance(event.payload, event.association.payload_type)


def test_all_four_frozen_decision_branches_preserve_evidence(
    phase28_entries: tuple[CorpusEntry, ...],
) -> None:
    entries = tuple(entry for entry in phase28_entries if entry.category == "command-decision")
    assert len(entries) == 4
    records = {entry.key: decode_command_decision(read_corpus_entry(entry)) for entry in entries}

    accepted = records["command:accepted"]
    assert isinstance(accepted.branch, AcceptedDecisionRecord)
    assert isinstance(accepted.target_event, TargetEventPresent)
    assert accepted.target_event.event_id in accepted.branch.result_event_ids

    rejected = records["command:rejected"]
    assert isinstance(rejected.branch, RejectedDecisionRecord)
    assert rejected.branch.rejection.code == "command_rejected"
    assert isinstance(rejected.target_event, TargetEventAbsent)

    deferred = records["command:deferred"]
    assert isinstance(deferred.branch, DeferredDecisionRecord)
    assert deferred.branch.wait.wait_id.value == "w_oracle_deferred"
    assert deferred.branch.wait.kind.value == "approval"
    assert isinstance(deferred.target_event, TargetEventAbsent)

    superseded = records["command:superseded"]
    assert isinstance(superseded.branch, SupersededDecisionRecord)
    assert superseded.branch.declaration_only is True
    assert superseded.branch.replacement_command_id.value == "cmd_oracle_replacement"
    assert isinstance(superseded.target_event, TargetEventAbsent)


def test_command_recorded_reuses_typed_decision_linkage(
    phase28_entries: tuple[CorpusEntry, ...],
) -> None:
    entries = {
        entry.key: entry
        for entry in phase28_entries
        if entry.key.startswith("event:command.recorded:")
    }
    model = decode_event(read_corpus_entry(entries["event:command.recorded:1:model"]))
    runtime = decode_event(read_corpus_entry(entries["event:command.recorded:1:runtime"]))

    assert isinstance(model.payload, ModelCommandRecordedPayload)
    assert model.payload.command_id == model.payload.decision_record.command_id
    assert isinstance(model.payload.decision_record.branch, AcceptedDecisionRecord)
    assert isinstance(runtime.payload, RuntimeCommandRecordedPayload)
    assert runtime.payload.command_id == runtime.payload.decision_record.command_id


def test_optional_fields_preserve_missing_null_and_present_states() -> None:
    missing = decode_event(
        b'{"id":"e1","runID":"r1","position":1,"type":"run.created","version":1,'
        b'"timestamp":"2026-01-02T03:04:05.678Z","actor":"system",'
        b'"payload":{"rootID":"r1","initialStatus":"created"}}\n'
    )
    explicit_null = decode_event(
        b'{"id":"e2","runID":"r1","position":2,"type":"run.created","version":1,'
        b'"timestamp":"2026-01-02T03:04:05.678Z","actor":"system",'
        b'"payload":{"rootID":"r1","initialStatus":"created","parentRunID":null}}\n'
    )
    present = decode_event(
        b'{"id":"e3","runID":"r1","position":3,"type":"run.created","version":1,'
        b'"timestamp":"2026-01-02T03:04:05.678Z","actor":"system",'
        b'"payload":{"rootID":"r1","initialStatus":"created","parentRunID":"r0"}}\n'
    )

    assert isinstance(missing.payload, RunCreatedPayload)
    assert missing.payload.parent_run_id is MISSING
    assert isinstance(explicit_null.payload, RunCreatedPayload)
    assert explicit_null.payload.parent_run_id is None
    assert isinstance(present.payload, RunCreatedPayload)
    assert present.payload.parent_run_id == RunId(value="r0")
    assert missing.causation_id is MISSING


def test_aliases_are_explicitly_mapped_to_semantic_names() -> None:
    event = decode_event(
        b'{"id":"e1","runID":"r1","position":1,"type":"message.delta","version":1,'
        b'"timestamp":"2026-01-02T03:04:05.678Z","actor":"assistant",'
        b'"causationID":"e0","correlationID":"c1","commandID":"cmd1",'
        b'"payload":{"messageID":"m1","delta":"x"}}\n'
    )

    assert event.event_id.value == "e1"
    assert event.run_id.value == "r1"
    assert isinstance(event.causation_id, EventId)
    assert event.causation_id.value == "e0"
    assert isinstance(event.correlation_id, CorrelationId)
    assert event.correlation_id.value == "c1"
    assert isinstance(event.command_id, CommandId)
    assert event.command_id.value == "cmd1"
    assert event.payload.message_id.value == "m1"  # type: ignore[union-attr]
