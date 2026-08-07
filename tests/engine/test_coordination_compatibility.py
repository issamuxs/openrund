from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import replace

import pytest

from openrund.codec import decode_event, encode_event
from openrund.errors import EncodeError
from tests.conftest import (
    CorpusEntry,
    CorpusIntegrityError,
    FrozenJson,
    read_corpus_entry,
)

_PAYLOAD_TYPES_BY_KEY = {
    "event:annotation.recorded:1:content": "LegacyPreviewAnnotationRecordedPayload",
    "event:annotation.recorded:1:legacy-preview": "CanonicalAnnotationRecordedPayload",
    "event:action.unknown:1:canonical": "ActionUnknownPayload",
    "event:action.reconciled:1:completed": "ActionReconciledCompletedPayload",
    "event:action.reconciled:1:failed": "ActionReconciledFailedPayload",
    "event:action.reconciled:1:cancelled": "ActionReconciledCancelledPayload",
    "event:wait.created:1:aggregate": "AggregateWaitCreatedPayload",
    "event:wait.created:1:approval": "ApprovalWaitCreatedPayload",
    "event:wait.created:1:interaction": "InteractionWaitCreatedPayload",
    "event:wait.created:1:timer": "TimerWaitCreatedPayload",
    "event:wait.created:1:join": "JoinWaitCreatedPayload",
    "event:wait.created:1:reconciliation": "ReconciliationWaitCreatedPayload",
    "event:wait.resolved:1:aggregate": "AggregateWaitResolvedPayload",
    "event:wait.resolved:1:approval": "ApprovalWaitResolvedPayload",
    "event:wait.resolved:1:interaction": "InteractionWaitResolvedPayload",
    "event:wait.resolved:1:timer": "TimerWaitResolvedPayload",
    "event:wait.resolved:1:join": "JoinWaitResolvedPayload",
    "event:wait.resolved:1:reconciliation": "ReconciliationWaitResolvedPayload",
    "event:wait.cancelled:1:approval": "ApprovalWaitCancelledPayload",
    "event:wait.cancelled:1:interaction": "InteractionWaitCancelledPayload",
    "event:wait.cancelled:1:timer": "TimerWaitCancelledPayload",
    "event:wait.cancelled:1:join": "JoinWaitCancelledPayload",
    "event:wait.cancelled:1:reconciliation": "ReconciliationWaitCancelledPayload",
    "event:wait.expired:1:approval": "ApprovalWaitExpiredPayload",
    "event:wait.expired:1:interaction": "InteractionWaitExpiredPayload",
    "event:wait.expired:1:timer": "TimerWaitExpiredPayload",
    "event:wait.expired:1:join": "JoinWaitExpiredPayload",
    "event:wait.expired:1:reconciliation": "ReconciliationWaitExpiredPayload",
    "event:delegation.created:1:contract": "DelegationContractCreatedPayload",
    "event:delegation.created:1:handoff": "DelegationHandoffCreatedPayload",
    "event:delegation.completed:1:canonical": "DelegationCompletedPayload",
    "event:delegation.failed:1:canonical": "DelegationFailedPayload",
    "event:delegation.cancelled:1:canonical": "DelegationCancelledPayload",
    "event:check.recorded:1:report": "CheckRecordedReportPayload",
    "event:checkpoint.created:1:range": "CheckpointRangeCreatedPayload",
    "event:checkpoint.created:1:correction": "CheckpointCorrectionCreatedPayload",
    "event:authority.granted:1:capability": "CapabilityAuthorityGrantedPayload",
    "event:authority.granted:1:policy-rule": "PolicyAuthorityGrantedPayload",
    "event:authority.revoked:1:capability": "CapabilityAuthorityRevokedPayload",
    "event:authority.revoked:1:policy-rule": "PolicyAuthorityRevokedPayload",
}
_PHASE32_EVENT_KEYS = tuple(_PAYLOAD_TYPES_BY_KEY)
_READ_ONLY_KEYS = frozenset({"event:annotation.recorded:1:content"})


def _by_key(entries: tuple[CorpusEntry, ...]) -> dict[str, CorpusEntry]:
    selected = {entry.key: entry for entry in entries if entry.key in _PAYLOAD_TYPES_BY_KEY}
    assert tuple(key for key in _PHASE32_EVENT_KEYS if key in selected) == _PHASE32_EVENT_KEYS
    assert len(selected) == len(_PHASE32_EVENT_KEYS)
    return selected


def _at_pointer(value: object, pointer: str) -> object:
    if pointer == "":
        return value
    current = value
    for encoded_part in pointer.removeprefix("/").split("/"):
        part = encoded_part.replace("~1", "/").replace("~0", "~")
        if isinstance(current, dict):
            current = current[part]
        elif isinstance(current, list):
            current = current[int(part)]
        else:
            raise KeyError(pointer)
    return current


def _links(entry: CorpusEntry) -> tuple[Mapping[str, FrozenJson], ...]:
    value = entry.manifest_entry.get("links")
    assert isinstance(value, tuple)
    assert all(isinstance(item, Mapping) for item in value)
    return tuple(item for item in value if isinstance(item, Mapping))


def test_phase32_event_selection_is_explicit_complete_and_closed(
    phase28_entries: tuple[CorpusEntry, ...],
) -> None:
    selected = _by_key(phase28_entries)

    assert len(selected) == 40
    assert set(selected) == set(_PHASE32_EVENT_KEYS)
    assert not any(
        key.startswith(("event:artifact.", "event:lease.", "event:model_call.")) for key in selected
    )


def test_phase32_events_preserve_authenticated_bytes_and_semantic_branches(
    phase28_entries: tuple[CorpusEntry, ...],
) -> None:
    selected = _by_key(phase28_entries)

    for key, payload_type in _PAYLOAD_TYPES_BY_KEY.items():
        wire = read_corpus_entry(selected[key])
        event = decode_event(wire)
        assert type(event.payload).__name__ == payload_type, key
        if key in _READ_ONLY_KEYS:
            with pytest.raises(EncodeError, match="legacy_payload_writer"):
                encode_event(event)
        else:
            assert encode_event(event) == wire, key


def test_phase32_evidence_preserves_presence_null_and_causal_links(
    phase28_entries: tuple[CorpusEntry, ...],
) -> None:
    selected = _by_key(phase28_entries)

    for key, entry in selected.items():
        decoded = json.loads(read_corpus_entry(entry))
        for pointer in entry.required_pointers:
            _at_pointer(decoded, pointer)
        for pointer in entry.absent_pointers:
            with pytest.raises(KeyError):
                _at_pointer(decoded, pointer)
        for pointer in entry.null_pointers:
            assert _at_pointer(decoded, pointer) is None, (key, pointer)
        for link in _links(entry):
            field = link.get("field")
            target = link.get("target")
            assert isinstance(field, str)
            assert isinstance(target, str)
            assert decoded[field] == target, key


def test_phase32_evidence_authentication_fails_closed(
    phase28_entries: tuple[CorpusEntry, ...],
) -> None:
    selected = _by_key(phase28_entries)
    entry = selected["event:wait.created:1:approval"]

    with pytest.raises(CorpusIntegrityError, match="corpus_entry_sha256_mismatch"):
        read_corpus_entry(replace(entry, sha256="0" * 64))
