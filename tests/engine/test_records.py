from __future__ import annotations

import hashlib

import pytest

from openrund.codec import (
    canonical_content_bytes,
    canonical_content_hash,
    encode_command_decision,
)
from openrund.contracts.commands import (
    AcceptedCommandDecision,
    AddMessageOperation,
    Command,
    CommandDecisionTraceEntry,
    CommandOrigin,
    DeferredCommandDecision,
    LegalityCriterion,
    LegalityCriterionResult,
    RejectedCommandDecision,
    SupersededCommandDecision,
    SupersededDecisionRecord,
)
from openrund.contracts.content import ArtifactReference, Content
from openrund.contracts.events import ModelCommandRecordedPayload, RuntimeCommandRecordedPayload
from openrund.contracts.ids import ArtifactId, CommandId, EventId, RunId, WaitId
from openrund.contracts.json import MISSING, JsonObject
from openrund.contracts.runs import WaitKind
from openrund.engine._records import build_command_recorded_payload, build_decision_record
from openrund.errors import EncodeError


def test_canonical_empty_content_has_one_stable_commitment() -> None:
    content = Content()

    assert canonical_content_bytes(content) == b"{}"
    assert canonical_content_hash(content) == hashlib.sha256(b"{}").hexdigest()


def test_canonical_content_uses_v1_aliases_omission_and_utf16_key_order() -> None:
    content = Content(
        preview="é",
        data={"\ue000": -0.0, "𐀀": 1},  # type: ignore[arg-type]
        artifact_refs=(
            ArtifactReference(
                artifact_id=ArtifactId(value="artifact_1"),
                kind=None,
                preview="p",
            ),
        ),
        artifact_ids=(ArtifactId(value="artifact_2"),),
        metadata={"z": True, "a": None},  # type: ignore[arg-type]
    )

    encoded = canonical_content_bytes(content)

    assert encoded == (
        b'{"artifactIDs":["artifact_2"],"artifactRefs":'
        b'[{"artifactID":"artifact_1","kind":null,"preview":"p"}],'
        b'"data":{"\xf0\x90\x80\x80":1,"\xee\x80\x80":0},'
        b'"metadata":{"a":null,"z":true},"preview":"\xc3\xa9"}'
    )
    assert canonical_content_hash(content) == hashlib.sha256(encoded).hexdigest()
    assert content.artifact_refs[0].metadata is MISSING


def test_canonical_content_rejects_non_content() -> None:
    with pytest.raises(EncodeError, match="content_type_invalid"):
        canonical_content_bytes(object())  # type: ignore[arg-type]


def _command(origin: CommandOrigin = CommandOrigin.SYSTEM) -> Command:
    return Command(
        command_id=CommandId(value="command_1"),
        run_id=RunId(value="run_1"),
        origin=origin,
        actor="provider" if origin is CommandOrigin.MODEL else "runtime",
        operation=AddMessageOperation(message=Content(preview="hello")),
        content=Content(preview="hello"),
        idempotency_key="key_1",
    )


def _trace(result: LegalityCriterionResult) -> tuple[CommandDecisionTraceEntry, ...]:
    return (
        CommandDecisionTraceEntry(
            criterion=LegalityCriterion.RUN_LIFECYCLE,
            result=result,
            reason="checked",
        ),
    )


def test_all_runtime_decisions_map_to_exact_durable_branches() -> None:
    command = _command()
    event_id = EventId(value="event_1")
    wait_id = WaitId(value="wait_1")
    replacement = CommandId(value="command_0")
    decisions = (
        AcceptedCommandDecision(
            trace=_trace(LegalityCriterionResult.PASS),
            result_event_ids=(event_id,),
        ),
        RejectedCommandDecision(
            reason="illegal",
            trace=_trace(LegalityCriterionResult.FAIL),
        ),
        DeferredCommandDecision(
            reason="waiting",
            trace=_trace(LegalityCriterionResult.DEFER),
            wait_ids=(wait_id,),
        ),
        SupersededCommandDecision(
            reason="duplicate",
            trace=_trace(LegalityCriterionResult.PASS),
            superseded_by_command_id=replacement,
        ),
    )

    records = tuple(
        build_decision_record(
            command,
            decision,
            deferred_wait_kind=WaitKind.INTERACTION,
        )
        for decision in decisions
    )

    assert tuple(record.branch.decision for record in records) == (
        "accepted",
        "rejected",
        "deferred",
        "superseded",
    )
    assert b'"targetEvent":{"status":"present","eventID":"event_1"}' in (
        encode_command_decision(records[0])
    )
    with pytest.raises(EncodeError, match="declaration_only_writer"):
        encode_command_decision(records[3])
    assert isinstance(records[3].branch, SupersededDecisionRecord)
    assert records[3].branch.replacement_command_id == replacement


def test_command_payload_preserves_origin_and_canonical_content_evidence() -> None:
    decision = AcceptedCommandDecision(
        trace=_trace(LegalityCriterionResult.PASS),
        result_event_ids=(EventId(value="event_1"),),
    )
    runtime = build_command_recorded_payload(_command(), decision)
    model = build_command_recorded_payload(_command(CommandOrigin.MODEL), decision)

    assert isinstance(runtime, RuntimeCommandRecordedPayload)
    assert runtime.origin_actor == "runtime"
    assert runtime.content_hash == canonical_content_hash(Content(preview="hello"))
    assert isinstance(runtime.metadata, JsonObject)
    assert runtime.metadata["commandOrigin"] == "system"
    assert runtime.metadata["idempotencyKey"] == "key_1"
    assert isinstance(model, ModelCommandRecordedPayload)
    assert model.provider == "provider"
    assert isinstance(model.metadata, JsonObject)
    assert model.metadata["commandOrigin"] == "model"


def test_accepted_record_requires_target_ids_and_deferred_requires_wait_kind() -> None:
    with pytest.raises(Exception, match="accepted_result_event_ids_required"):
        build_decision_record(
            _command(),
            AcceptedCommandDecision(trace=_trace(LegalityCriterionResult.PASS)),
        )
    with pytest.raises(Exception, match="deferred_wait_kind_required"):
        build_decision_record(
            _command(),
            DeferredCommandDecision(
                reason="waiting",
                trace=_trace(LegalityCriterionResult.DEFER),
                wait_ids=(WaitId(value="wait_1"),),
            ),
        )
