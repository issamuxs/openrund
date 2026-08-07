"""Exact v1 Event envelope and payload decoding."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import MISSING as DATACLASS_MISSING
from dataclasses import dataclass, fields
from types import MappingProxyType
from typing import Any, Final, cast, final

from openrund.codec._aliases import EVENT_ENVELOPE_ALIASES, PAYLOAD_ALIASES
from openrund.codec._decisions import (
    _child_pointer,
    _decode_command_decision_object,
    _decode_dataclass,
    _decode_typed_value,
    _encode_command_decision_entries,
    _encode_dataclass_value,
    _encode_semantic_value,
    _exact_fields,
    _expect_object,
    _expect_string,
)
from openrund.codec._json import decode_json_value, encode_json_value
from openrund.contracts.content import Content
from openrund.contracts.events import (
    EVENT_PAYLOAD_CATALOG,
    CoreEventType,
    Event,
    EventActor,
    EventPayload,
    ModelCommandRecordedPayload,
    RuntimeCommandRecordedPayload,
    RuntimeEvent,
)
from openrund.contracts.ids import CommandId, CorrelationId, EventId, ModelCallId, RunId
from openrund.contracts.json import MISSING, JsonObject
from openrund.contracts.time import Timestamp
from openrund.errors import DecodeError, EncodeError, UnsupportedVersionError, ValidationError

_REQUIRED_ENVELOPE_FIELDS: Final = frozenset(
    {"id", "runID", "position", "type", "version", "timestamp", "actor", "payload"}
)
_OPTIONAL_ENVELOPE_FIELDS: Final = frozenset({"causationID", "correlationID", "commandID"})


@final
@dataclass(frozen=True, slots=True, kw_only=True)
class EventCodecSpec:
    event_type: CoreEventType
    version: int
    variant: str
    payload_type: type[object]
    required_fields: frozenset[str]
    optional_fields: frozenset[str]


def _payload_field_sets(
    event_type: CoreEventType, variant: str, payload_type: type[object]
) -> tuple[frozenset[str], frozenset[str]]:
    if event_type is CoreEventType.COMMAND_RECORDED:
        command_required = frozenset(
            {
                "commandID",
                "decision",
                "decisionTrace",
                "resultEventIDs",
                "targetEvent",
                "origin",
                "operation",
                "contentHash",
                "content",
            }
        )
        return command_required, frozenset(
            {
                "rejection",
                "wait",
                "declarationOnly",
                "replacementCommandID",
                "metadata",
            }
        )

    payload_fields = tuple(
        field for field in fields(cast(Any, payload_type)) if field.init and field.name != "variant"
    )
    aliases: dict[str, str] = {}
    for field in payload_fields:
        alias = PAYLOAD_ALIASES.get(field.name)
        if alias is None:
            raise RuntimeError(f"codec_alias_missing:{payload_type.__name__}.{field.name}")
        aliases[field.name] = alias.wire_name
    required: set[str] = {
        aliases[field.name]
        for field in payload_fields
        if field.default is DATACLASS_MISSING and field.default_factory is DATACLASS_MISSING
    }
    if event_type is CoreEventType.ACTION_RECONCILED:
        required.add("outcome")
    if (
        event_type
        in {
            CoreEventType.WAIT_CREATED,
            CoreEventType.WAIT_RESOLVED,
            CoreEventType.WAIT_CANCELLED,
            CoreEventType.WAIT_EXPIRED,
        }
        and variant != "aggregate"
    ):
        required.add("kind")
    allowed = set(aliases.values())
    return frozenset(required), frozenset(allowed - required)


_codec_registry: dict[tuple[CoreEventType, int, str], EventCodecSpec] = {}
for key, association in EVENT_PAYLOAD_CATALOG.items():
    event_type, version, variant = key
    required_fields, optional_fields = _payload_field_sets(
        event_type, variant, association.payload_type
    )
    _codec_registry[key] = EventCodecSpec(
        event_type=event_type,
        version=version,
        variant=variant,
        payload_type=cast(type[object], association.payload_type),
        required_fields=required_fields,
        optional_fields=optional_fields,
    )

EVENT_CODEC_REGISTRY: Mapping[tuple[CoreEventType, int, str], EventCodecSpec] = MappingProxyType(
    _codec_registry
)


def _exclusive_variant(
    payload: JsonObject,
    *,
    left_field: str,
    left_variant: str,
    right_field: str,
    right_variant: str,
) -> str:
    left = left_field in payload
    right = right_field in payload
    if left == right:
        raise DecodeError(code="event_payload_variant_invalid", pointer="/payload")
    return left_variant if left else right_variant


def _kind_variant(payload: JsonObject) -> str:
    if "kind" not in payload:
        raise DecodeError(code="payload_field_missing", pointer="/payload/kind")
    return _expect_string(payload["kind"], "/payload/kind")


def _select_variant(event_type: CoreEventType, payload: JsonObject) -> str:
    if event_type is CoreEventType.COMMAND_RECORDED:
        origin = _expect_object(payload.get("origin"), "/payload/origin")
        return _expect_string(origin.get("type"), "/payload/origin/type")
    if event_type in {CoreEventType.MESSAGE_ADDED, CoreEventType.ANNOTATION_RECORDED}:
        return _exclusive_variant(
            payload,
            left_field="content",
            left_variant="content",
            right_field="contentPreview",
            right_variant="legacy-preview",
        )
    if event_type is CoreEventType.ACTION_RECONCILED:
        if "outcome" not in payload:
            raise DecodeError(code="payload_field_missing", pointer="/payload/outcome")
        return _expect_string(payload["outcome"], "/payload/outcome")
    if event_type is CoreEventType.WAIT_CREATED:
        return "aggregate" if "waitingOn" in payload else _kind_variant(payload)
    if event_type is CoreEventType.WAIT_RESOLVED:
        return "aggregate" if "resumedFrom" in payload else _kind_variant(payload)
    if event_type in {CoreEventType.WAIT_CANCELLED, CoreEventType.WAIT_EXPIRED}:
        return _kind_variant(payload)
    if event_type is CoreEventType.DELEGATION_CREATED:
        return _exclusive_variant(
            payload,
            left_field="contract",
            left_variant="contract",
            right_field="parentSpawnEventID",
            right_variant="handoff",
        )
    if event_type is CoreEventType.CHECKPOINT_CREATED:
        return "correction" if "correction" in payload else "range"
    if event_type is CoreEventType.ARTIFACT_CREATED:
        return "preview" if "contentPreview" in payload else "metadata"
    if event_type in {CoreEventType.AUTHORITY_GRANTED, CoreEventType.AUTHORITY_REVOKED}:
        return _exclusive_variant(
            payload,
            left_field="capabilityID",
            left_variant="capability",
            right_field="ruleID",
            right_variant="policy-rule",
        )
    candidates = tuple(
        spec for key, spec in EVENT_CODEC_REGISTRY.items() if key[0] is event_type and key[1] == 1
    )
    if len(candidates) != 1:
        raise DecodeError(code="event_payload_variant_invalid", pointer="/payload")
    return candidates[0].variant


def _decode_command_recorded(
    payload: JsonObject, spec: EventCodecSpec
) -> ModelCommandRecordedPayload | RuntimeCommandRecordedPayload:
    _exact_fields(
        payload,
        required=spec.required_fields,
        optional=spec.optional_fields,
        pointer="/payload",
        missing_code="payload_field_missing",
        unknown_code="payload_field_unknown",
    )
    decision_record = _decode_command_decision_object(
        payload,
        pointer="/payload",
        extra_required=frozenset({"origin", "operation", "contentHash", "content"}),
        extra_optional=frozenset({"metadata"}),
    )
    origin = _expect_object(payload["origin"], "/payload/origin")
    _exact_fields(
        origin,
        required=frozenset({"type"}),
        optional=frozenset({"actor", "provider", "modelCallID"}),
        pointer="/payload/origin",
        missing_code="payload_field_missing",
        unknown_code="payload_field_unknown",
    )
    origin_type = _expect_string(origin["type"], "/payload/origin/type")
    if origin_type != spec.variant:
        raise DecodeError(code="event_payload_variant_invalid", pointer="/payload/origin/type")
    command_id = cast(
        CommandId,
        _decode_typed_value(payload["commandID"], CommandId, "/payload/commandID"),
    )
    kwargs: dict[str, object] = {
        "command_id": command_id,
        "decision_record": decision_record,
        "operation": _expect_string(payload["operation"], "/payload/operation"),
        "content_hash": _expect_string(payload["contentHash"], "/payload/contentHash"),
        "content": cast(
            Content, _decode_typed_value(payload["content"], Content, "/payload/content")
        ),
    }
    if "actor" in origin:
        kwargs["origin_actor"] = _decode_typed_value(
            origin["actor"], str | None, "/payload/origin/actor"
        )
    if "provider" in origin:
        kwargs["provider"] = _decode_typed_value(
            origin["provider"], str | None, "/payload/origin/provider"
        )
    if "modelCallID" in origin:
        kwargs["model_call_id"] = _decode_typed_value(
            origin["modelCallID"], ModelCallId | None, "/payload/origin/modelCallID"
        )
    if "metadata" in payload:
        kwargs["metadata"] = _decode_typed_value(
            payload["metadata"], JsonObject | None, "/payload/metadata"
        )
    payload_type = (
        ModelCommandRecordedPayload if origin_type == "model" else RuntimeCommandRecordedPayload
    )
    try:
        return payload_type(**cast(Any, kwargs))
    except ValidationError as error:
        raise DecodeError(
            code="payload_value_invalid", pointer="/payload", safe_detail=error.code
        ) from None


def _decode_payload(event_type: CoreEventType, payload: JsonObject) -> EventPayload:
    variant = _select_variant(event_type, payload)
    spec = EVENT_CODEC_REGISTRY.get((event_type, 1, variant))
    if spec is None:
        raise DecodeError(code="event_payload_variant_invalid", pointer="/payload")
    if event_type is CoreEventType.COMMAND_RECORDED:
        return _decode_command_recorded(payload, spec)
    _exact_fields(
        payload,
        required=spec.required_fields,
        optional=spec.optional_fields,
        pointer="/payload",
        missing_code="payload_field_missing",
        unknown_code="payload_field_unknown",
    )
    decoded = _decode_dataclass(
        payload,
        spec.payload_type,
        "/payload",
        ignored_fields=frozenset({"variant"}),
    )
    return cast(EventPayload, decoded)


def _envelope_value(envelope: JsonObject, semantic_name: str) -> object:
    return envelope[EVENT_ENVELOPE_ALIASES[semantic_name].wire_name]


def decode_event(data: bytes | str) -> RuntimeEvent:
    """Decode exactly one bounded v1 Event frame into semantic values."""

    envelope = _expect_object(decode_json_value(data), "")
    _exact_fields(
        envelope,
        required=_REQUIRED_ENVELOPE_FIELDS,
        optional=_OPTIONAL_ENVELOPE_FIELDS,
        pointer="",
        missing_code="event_envelope_field_missing",
        unknown_code="event_envelope_field_unknown",
    )
    raw_version = _envelope_value(envelope, "version")
    if isinstance(raw_version, bool) or not isinstance(raw_version, int):
        raise DecodeError(code="event_version_invalid", pointer="/version")
    if raw_version != 1:
        raise UnsupportedVersionError(version=raw_version, pointer="/version")

    raw_type = _expect_string(_envelope_value(envelope, "event_type"), "/type")
    try:
        event_type = CoreEventType(raw_type)
    except ValueError:
        raise DecodeError(code="event_type_unknown", pointer="/type") from None
    payload_object = _expect_object(_envelope_value(envelope, "payload"), "/payload")
    payload = _decode_payload(event_type, payload_object)

    kwargs: dict[str, object] = {
        "event_id": _decode_typed_value(_envelope_value(envelope, "event_id"), EventId, "/id"),
        "run_id": _decode_typed_value(_envelope_value(envelope, "run_id"), RunId, "/runID"),
        "position": _decode_typed_value(_envelope_value(envelope, "position"), int, "/position"),
        "event_type": event_type,
        "version": raw_version,
        "timestamp": _decode_typed_value(
            _envelope_value(envelope, "timestamp"), Timestamp, "/timestamp"
        ),
        "actor": _decode_typed_value(_envelope_value(envelope, "actor"), EventActor, "/actor"),
        "payload": payload,
    }
    for semantic_name, target in (
        ("causation_id", EventId),
        ("correlation_id", CorrelationId),
        ("command_id", CommandId),
    ):
        wire_name = EVENT_ENVELOPE_ALIASES[semantic_name].wire_name
        if wire_name in envelope:
            kwargs[semantic_name] = _decode_typed_value(
                envelope[wire_name], target, _child_pointer("", wire_name)
            )
        else:
            kwargs[semantic_name] = MISSING
    try:
        return Event(**cast(Any, kwargs))
    except ValidationError as error:
        raise DecodeError(code="event_invalid", safe_detail=error.code) from None


_ALWAYS_EMIT_EMPTY_PAYLOAD_FIELDS: Final = {
    "CanonicalMessageAddedPayload": frozenset({"artifact_ids"}),
    "ActionCompletedPayload": frozenset({"artifact_ids"}),
}


def _encode_command_recorded_payload(
    payload: ModelCommandRecordedPayload | RuntimeCommandRecordedPayload,
) -> JsonObject:
    entries = list(
        _encode_command_decision_entries(
            payload.decision_record,
            allow_superseded=True,
        )
    )
    origin_entries: list[tuple[str, object]] = [("type", payload.origin_type)]
    for field_name, wire_name in (
        ("origin_actor", "actor"),
        ("provider", "provider"),
        ("model_call_id", "modelCallID"),
    ):
        value = getattr(payload, field_name)
        if value is not MISSING:
            origin_entries.append((wire_name, _encode_semantic_value(value)))
    origin = JsonObject(entries=cast(Any, tuple(origin_entries)))
    entries.extend(
        [
            ("origin", origin),
            ("operation", payload.operation),
            ("contentHash", payload.content_hash),
            ("content", _encode_semantic_value(payload.content)),
        ]
    )
    if payload.metadata is not MISSING:
        entries.append(("metadata", cast(Any, payload.metadata)))
    return JsonObject(entries=tuple(entries))


def _encode_payload(event: RuntimeEvent) -> JsonObject:
    if event.association.decode_only:
        raise EncodeError(code="legacy_payload_writer")
    payload = event.payload
    if isinstance(payload, (ModelCommandRecordedPayload, RuntimeCommandRecordedPayload)):
        return _encode_command_recorded_payload(payload)
    always_emit = _ALWAYS_EMIT_EMPTY_PAYLOAD_FIELDS.get(type(payload).__name__, frozenset())
    return _encode_dataclass_value(payload, always_emit=always_emit)


def encode_event(event: RuntimeEvent) -> bytes:
    """Encode one writer-eligible semantic Event as exact v1 JSONL."""

    if not isinstance(event, Event):
        raise EncodeError(code="event_type_invalid")
    entries: list[tuple[str, object]] = [
        (EVENT_ENVELOPE_ALIASES["event_id"].wire_name, event.event_id.value),
        (EVENT_ENVELOPE_ALIASES["run_id"].wire_name, event.run_id.value),
        (EVENT_ENVELOPE_ALIASES["position"].wire_name, event.position),
        (EVENT_ENVELOPE_ALIASES["event_type"].wire_name, event.event_type.value),
        (EVENT_ENVELOPE_ALIASES["version"].wire_name, event.version),
        (EVENT_ENVELOPE_ALIASES["timestamp"].wire_name, event.timestamp.value),
        (EVENT_ENVELOPE_ALIASES["actor"].wire_name, event.actor.value),
    ]
    for semantic_name in ("causation_id", "correlation_id", "command_id"):
        value = getattr(event, semantic_name)
        if value is not MISSING:
            entries.append(
                (
                    EVENT_ENVELOPE_ALIASES[semantic_name].wire_name,
                    _encode_semantic_value(value),
                )
            )
    entries.append((EVENT_ENVELOPE_ALIASES["payload"].wire_name, _encode_payload(event)))
    return encode_json_value(JsonObject(entries=cast(Any, tuple(entries))))
