from __future__ import annotations

import json
from dataclasses import FrozenInstanceError, fields, is_dataclass
from pathlib import Path
from typing import cast

import pytest

from openrund.contracts.content import Content
from openrund.contracts.events import (
    CORE_EVENT_TYPES,
    EVENT_PAYLOAD_CATALOG,
    PAYLOAD_TYPES,
    CanonicalAnnotationRecordedPayload,
    CanonicalMessageAddedPayload,
    CoreEventType,
    Event,
    EventActor,
    EventPayload,
    LegacyPreviewAnnotationRecordedPayload,
    LegacyPreviewMessageAddedPayload,
    RunCreatedPayload,
    RuntimeEvent,
)
from openrund.contracts.ids import (
    AnnotationId,
    CommandId,
    CorrelationId,
    EventId,
    MessageId,
    RunId,
)
from openrund.contracts.json import MISSING, JsonObject
from openrund.contracts.time import Timestamp
from openrund.errors import ValidationError

FIXTURE_MANIFEST = Path(__file__).parents[1] / "fixtures" / "compatibility" / "v1" / "manifest.json"

EXPECTED_PAYLOAD_NAMES = {
    "RunCreatedPayload",
    "RunStartedPayload",
    "RunCompletedPayload",
    "RunFailedPayload",
    "RunCancelledPayload",
    "ModelCommandRecordedPayload",
    "RuntimeCommandRecordedPayload",
    "CanonicalMessageAddedPayload",
    "LegacyPreviewMessageAddedPayload",
    "MessageDeltaPayload",
    "CanonicalAnnotationRecordedPayload",
    "LegacyPreviewAnnotationRecordedPayload",
    "ModelCallStartedPayload",
    "ModelCallCompletedPayload",
    "ModelCallFailedPayload",
    "ModelCallCancelledPayload",
    "ActionCreatedPayload",
    "ActionStartedPayload",
    "ActionCompletedPayload",
    "ActionFailedPayload",
    "ActionCancelledPayload",
    "ActionUnknownPayload",
    "ActionReconciledCompletedPayload",
    "ActionReconciledFailedPayload",
    "ActionReconciledCancelledPayload",
    "AggregateWaitCreatedPayload",
    "ApprovalWaitCreatedPayload",
    "InteractionWaitCreatedPayload",
    "TimerWaitCreatedPayload",
    "JoinWaitCreatedPayload",
    "ReconciliationWaitCreatedPayload",
    "AggregateWaitResolvedPayload",
    "ApprovalWaitResolvedPayload",
    "InteractionWaitResolvedPayload",
    "TimerWaitResolvedPayload",
    "JoinWaitResolvedPayload",
    "ReconciliationWaitResolvedPayload",
    "ApprovalWaitCancelledPayload",
    "InteractionWaitCancelledPayload",
    "TimerWaitCancelledPayload",
    "JoinWaitCancelledPayload",
    "ReconciliationWaitCancelledPayload",
    "ApprovalWaitExpiredPayload",
    "InteractionWaitExpiredPayload",
    "TimerWaitExpiredPayload",
    "JoinWaitExpiredPayload",
    "ReconciliationWaitExpiredPayload",
    "DelegationContractCreatedPayload",
    "DelegationHandoffCreatedPayload",
    "DelegationCompletedPayload",
    "DelegationFailedPayload",
    "DelegationCancelledPayload",
    "CheckRecordedReportPayload",
    "CheckpointRangeCreatedPayload",
    "CheckpointCorrectionCreatedPayload",
    "ArtifactMetadataCreatedPayload",
    "ArtifactPreviewCreatedPayload",
    "ArtifactUnavailablePayload",
    "CapabilityAuthorityGrantedPayload",
    "PolicyAuthorityGrantedPayload",
    "CapabilityAuthorityRevokedPayload",
    "PolicyAuthorityRevokedPayload",
    "LeaseAcquiredPayload",
    "LeaseReleasedPayload",
    "LeaseExpiredPayload",
}


def manifest_event_keys() -> set[tuple[CoreEventType, int, str]]:
    manifest = cast(dict[str, object], json.loads(FIXTURE_MANIFEST.read_text()))
    entries = cast(list[dict[str, object]], manifest["events"])
    keys: set[tuple[CoreEventType, int, str]] = set()
    for entry in entries:
        raw_key = cast(str, entry["key"])
        prefix, event_type, version, variant = raw_key.split(":", maxsplit=3)
        assert prefix == "event"
        keys.add((CoreEventType(event_type), int(version), variant))
    assert len(entries) == len(keys)
    return keys


def event_for(
    event_type: CoreEventType, payload: EventPayload, *, version: int = 1
) -> RuntimeEvent:
    return Event(
        event_id=EventId(value="evt_test"),
        run_id=RunId(value="run_test"),
        position=1,
        event_type=event_type,
        version=version,  # type: ignore[arg-type]
        timestamp=Timestamp(value="2026-08-04T12:00:00.000Z"),
        actor=EventActor.SYSTEM,
        payload=payload,
    )


def test_event_name_and_payload_catalog_are_manifest_bijective() -> None:
    catalog_keys = set(EVENT_PAYLOAD_CATALOG)

    assert len(CORE_EVENT_TYPES) == 37
    assert len(set(CORE_EVENT_TYPES)) == 37
    assert len(EVENT_PAYLOAD_CATALOG) == 65
    assert len(PAYLOAD_TYPES) == 65
    assert len(set(PAYLOAD_TYPES)) == 65
    assert catalog_keys == manifest_event_keys()
    assert {payload_type.__name__ for payload_type in PAYLOAD_TYPES} == EXPECTED_PAYLOAD_NAMES


def test_every_catalog_association_accepts_only_its_payload_class() -> None:
    for key, association in EVENT_PAYLOAD_CATALOG.items():
        payload = object.__new__(association.payload_type)
        event = event_for(key[0], payload)
        assert event.payload is payload
        assert event.association is association

        other = next(
            candidate
            for candidate in PAYLOAD_TYPES
            if candidate is not association.payload_type
            and not any(
                other_association.event_type is key[0]
                and other_association.payload_type is candidate
                for other_association in EVENT_PAYLOAD_CATALOG.values()
            )
        )
        with pytest.raises(ValidationError, match="event_payload_type_invalid"):
            event_for(key[0], object.__new__(other))


@pytest.mark.parametrize("version", [0, 2])
def test_event_rejects_unsupported_versions(version: int) -> None:
    payload = RunCreatedPayload(
        root_id=RunId(value="run_test"),
        initial_status="created",
    )
    with pytest.raises(ValidationError, match=r"event_version_(invalid|unsupported)"):
        event_for(CoreEventType.RUN_CREATED, payload, version=version)


def test_event_rejects_unknown_names_wrong_ids_and_invalid_positions() -> None:
    payload = RunCreatedPayload(
        root_id=RunId(value="run_test"),
        initial_status="created",
    )
    with pytest.raises(ValidationError, match="event_type_invalid"):
        Event(
            event_id=EventId(value="evt_test"),
            run_id=RunId(value="run_test"),
            position=1,
            event_type="unknown.event",  # type: ignore[type-var]
            timestamp=Timestamp(value="2026-08-04T12:00:00.000Z"),
            actor=EventActor.SYSTEM,
            payload=payload,
        )
    with pytest.raises(ValidationError, match="event_id_invalid"):
        Event(
            event_id=RunId(value="run_wrong"),  # type: ignore[arg-type]
            run_id=RunId(value="run_test"),
            position=1,
            event_type=CoreEventType.RUN_CREATED,
            timestamp=Timestamp(value="2026-08-04T12:00:00.000Z"),
            actor=EventActor.SYSTEM,
            payload=payload,
        )
    with pytest.raises(ValidationError, match="event_position_invalid"):
        Event(
            event_id=EventId(value="evt_test"),
            run_id=RunId(value="run_test"),
            position=0,
            event_type=CoreEventType.RUN_CREATED,
            timestamp=Timestamp(value="2026-08-04T12:00:00.000Z"),
            actor=EventActor.SYSTEM,
            payload=payload,
        )


def test_event_envelope_preserves_exact_optional_link_presence() -> None:
    payload = RunCreatedPayload(
        root_id=RunId(value="run_test"),
        initial_status="created",
    )
    event = Event(
        event_id=EventId(value="evt_test"),
        run_id=RunId(value="run_test"),
        position=1,
        event_type=CoreEventType.RUN_CREATED,
        timestamp=Timestamp(value="2026-08-04T12:00:00.000Z"),
        actor=EventActor.SYSTEM,
        payload=payload,
        causation_id=EventId(value="evt_cause"),
        correlation_id=CorrelationId(value="correlation_1"),
        command_id=CommandId(value="cmd_1"),
    )
    absent = event_for(CoreEventType.RUN_CREATED, payload)

    assert event.causation_id == EventId(value="evt_cause")
    assert event.correlation_id == CorrelationId(value="correlation_1")
    assert event.command_id == CommandId(value="cmd_1")
    assert absent.causation_id is MISSING
    assert absent.correlation_id is MISSING
    assert absent.command_id is MISSING
    with pytest.raises(ValidationError, match="event_causation_id_invalid"):
        Event(
            event_id=EventId(value="evt_test"),
            run_id=RunId(value="run_test"),
            position=1,
            event_type=CoreEventType.RUN_CREATED,
            timestamp=Timestamp(value="2026-08-04T12:00:00.000Z"),
            actor=EventActor.SYSTEM,
            payload=payload,
            causation_id=None,  # type: ignore[arg-type]
        )


def test_legacy_message_and_annotation_forms_are_explicitly_decode_only() -> None:
    message_legacy = EVENT_PAYLOAD_CATALOG[(CoreEventType.MESSAGE_ADDED, 1, "content")]
    message_canonical = EVENT_PAYLOAD_CATALOG[(CoreEventType.MESSAGE_ADDED, 1, "legacy-preview")]
    annotation_legacy = EVENT_PAYLOAD_CATALOG[(CoreEventType.ANNOTATION_RECORDED, 1, "content")]
    annotation_canonical = EVENT_PAYLOAD_CATALOG[
        (CoreEventType.ANNOTATION_RECORDED, 1, "legacy-preview")
    ]

    assert message_legacy.payload_type is LegacyPreviewMessageAddedPayload
    assert message_legacy.decode_only is True
    assert message_canonical.payload_type is CanonicalMessageAddedPayload
    assert message_canonical.decode_only is False
    assert annotation_legacy.payload_type is LegacyPreviewAnnotationRecordedPayload
    assert annotation_legacy.decode_only is True
    assert annotation_canonical.payload_type is CanonicalAnnotationRecordedPayload
    assert annotation_canonical.decode_only is False


def test_message_and_annotation_branches_have_distinct_required_fields() -> None:
    canonical_message = CanonicalMessageAddedPayload(
        message_id=MessageId(value="msg_1"),
        content_preview="hello",
        artifact_ids=(),
    )
    legacy_message = LegacyPreviewMessageAddedPayload(
        message_id=MessageId(value="msg_1"),
        direction="inbound",
        source="user",
        content=Content(preview="hello"),
    )
    canonical_annotation = CanonicalAnnotationRecordedPayload(
        annotation_id=AnnotationId(value="annotation_1"),
        content_preview="note",
        metadata={"kept": True},  # type: ignore[arg-type]
    )
    legacy_annotation = LegacyPreviewAnnotationRecordedPayload(
        annotation_id=AnnotationId(value="annotation_1"),
        content=Content(preview="note"),
    )

    assert canonical_message.content_preview == "hello"
    assert legacy_message.content == Content(preview="hello")
    assert isinstance(canonical_annotation.metadata, JsonObject)
    assert legacy_annotation.content == Content(preview="note")
    with pytest.raises(TypeError):
        CanonicalMessageAddedPayload(  # type: ignore[call-arg]
            message_id=MessageId(value="msg_1"),
            content_preview="hello",
            content=Content(preview="forbidden"),
        )


def test_all_payloads_and_events_are_final_frozen_slotted_and_annotated() -> None:
    assert all(is_dataclass(payload_type) for payload_type in PAYLOAD_TYPES)
    assert all(getattr(payload_type, "__final__", False) for payload_type in PAYLOAD_TYPES)
    assert all(payload_type.__annotations__ for payload_type in PAYLOAD_TYPES)
    assert all(
        field.type is not None for payload_type in PAYLOAD_TYPES for field in fields(payload_type)
    )

    payload = RunCreatedPayload(
        root_id=RunId(value="run_test"),
        initial_status="created",
        metadata={"nested": [1, 2]},  # type: ignore[arg-type]
    )
    event = event_for(CoreEventType.RUN_CREATED, payload)
    assert isinstance(payload.metadata, JsonObject)
    assert not hasattr(payload, "__dict__")
    assert not hasattr(event, "__dict__")
    with pytest.raises((FrozenInstanceError, AttributeError, TypeError)):
        payload.initial_status = "running"  # type: ignore[assignment, misc]


def test_payloads_expose_no_wire_alias_or_authority_methods() -> None:
    forbidden = {
        "from_dict",
        "to_dict",
        "asdict",
        "model_dump",
        "append",
        "execute",
        "grant",
        "reduce",
    }
    for payload_type in PAYLOAD_TYPES:
        assert forbidden.isdisjoint(dir(payload_type))
