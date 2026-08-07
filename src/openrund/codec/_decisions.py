"""Strict decoding for frozen v1 command-decision evidence."""

from __future__ import annotations

import types
from collections.abc import Callable, Mapping
from dataclasses import MISSING as DATACLASS_MISSING
from dataclasses import dataclass, fields, is_dataclass
from enum import StrEnum
from types import MappingProxyType
from typing import Any, Final, Literal, Union, cast, final, get_args, get_origin, get_type_hints

from openrund.codec._aliases import PAYLOAD_ALIASES
from openrund.codec._json import decode_json_value, encode_json_value
from openrund.contracts.commands import (
    AcceptedDecisionRecord,
    CommandDecisionRecord,
    CommandDecisionRecordBranch,
    CommandDecisionTraceEntry,
    CommandRejectionRecord,
    CommandWaitRecord,
    DeferredDecisionRecord,
    RejectedDecisionRecord,
    SupersededDecisionRecord,
    TargetEventAbsent,
    TargetEventPresent,
)
from openrund.contracts.ids import (
    ActionId,
    AnnotationId,
    ArtifactId,
    AuthorityId,
    CapabilityId,
    CheckId,
    CheckpointId,
    CommandId,
    CorrelationId,
    DelegationId,
    EventId,
    LeaseId,
    MessageId,
    ModelCallId,
    PolicyRuleId,
    RunId,
    WaitId,
)
from openrund.contracts.json import MISSING, JsonArray, JsonObject, JsonValue, MissingType
from openrund.contracts.runs import (
    AuthorityGrant,
    DelegationBudget,
    DelegationContract,
    WaitKind,
)
from openrund.contracts.time import Timestamp
from openrund.errors import DecodeError, EncodeError, ValidationError

_ID_TYPES: Final = (
    RunId,
    EventId,
    CommandId,
    ModelCallId,
    WaitId,
    DelegationId,
    CheckId,
    CheckpointId,
    MessageId,
    AnnotationId,
    AuthorityId,
    ActionId,
    ArtifactId,
    LeaseId,
    CapabilityId,
    PolicyRuleId,
    CorrelationId,
)


def _child_pointer(pointer: str, token: str | int) -> str:
    escaped = str(token).replace("~", "~0").replace("/", "~1")
    return f"{pointer}/{escaped}" if pointer else f"/{escaped}"


def _expect_object(value: object, pointer: str) -> JsonObject:
    if not isinstance(value, JsonObject):
        raise DecodeError(code="field_object_required", pointer=pointer)
    return value


def _expect_array(value: object, pointer: str) -> JsonArray:
    if not isinstance(value, JsonArray):
        raise DecodeError(code="field_array_required", pointer=pointer)
    return value


def _expect_string(value: object, pointer: str) -> str:
    if not isinstance(value, str):
        raise DecodeError(code="field_string_required", pointer=pointer)
    return value


def _expect_bool(value: object, pointer: str) -> bool:
    if not isinstance(value, bool):
        raise DecodeError(code="field_boolean_required", pointer=pointer)
    return value


def _expect_integer(value: object, pointer: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise DecodeError(code="field_integer_required", pointer=pointer)
    return value


def _exact_fields(
    value: JsonObject,
    *,
    required: frozenset[str],
    optional: frozenset[str] = frozenset(),
    pointer: str,
    missing_code: str = "field_required",
    unknown_code: str = "field_unknown",
) -> None:
    actual = frozenset(value)
    missing = sorted(required - actual)
    if missing:
        raise DecodeError(
            code=missing_code,
            pointer=_child_pointer(pointer, missing[0]),
        )
    unknown = sorted(actual - required - optional)
    if unknown:
        raise DecodeError(
            code=unknown_code,
            pointer=_child_pointer(pointer, unknown[0]),
        )


def _decode_literal(value: object, annotation: object, pointer: str) -> object:
    choices = get_args(annotation)
    for choice in choices:
        expected = choice.value if isinstance(choice, StrEnum) else choice
        if type(value) is type(expected) and value == expected:
            return choice
    raise DecodeError(code="field_literal_invalid", pointer=pointer)


def _decode_delegation_contract(value: object, pointer: str) -> DelegationContract:
    obj = _expect_object(value, pointer)
    required = frozenset(
        {"version", "runKind", "objective", "authority", "budgets", "resultSchema", "policies"}
    )
    optional = frozenset({"requiredArtifactKinds", "lateHandoff", "metadata"})
    _exact_fields(obj, required=required, optional=optional, pointer=pointer)

    authority_pointer = _child_pointer(pointer, "authority")
    authority = _expect_object(obj["authority"], authority_pointer)
    _exact_fields(
        authority,
        required=frozenset({"grants", "drift"}),
        pointer=authority_pointer,
    )
    grants = cast(
        tuple[AuthorityGrant, ...],
        _decode_typed_value(
            authority["grants"],
            tuple[AuthorityGrant, ...],
            _child_pointer(authority_pointer, "grants"),
        ),
    )

    budgets_pointer = _child_pointer(pointer, "budgets")
    budget = cast(
        DelegationBudget,
        _decode_typed_value(obj["budgets"], DelegationBudget, budgets_pointer),
    )

    schema_pointer = _child_pointer(pointer, "resultSchema")
    result_schema = _expect_object(obj["resultSchema"], schema_pointer)
    _exact_fields(result_schema, required=frozenset({"kind"}), pointer=schema_pointer)

    policies_pointer = _child_pointer(pointer, "policies")
    policies = _expect_object(obj["policies"], policies_pointer)
    _exact_fields(
        policies,
        required=frozenset({"allowNestedDelegation", "onParentCancel"}),
        pointer=policies_pointer,
    )

    kwargs: dict[str, object] = {
        "version": _expect_integer(obj["version"], _child_pointer(pointer, "version")),
        "run_kind": _decode_typed_value(
            obj["runKind"],
            get_type_hints(DelegationContract)["run_kind"],
            _child_pointer(pointer, "runKind"),
        ),
        "objective": _expect_string(obj["objective"], _child_pointer(pointer, "objective")),
        "authority_grants": grants,
        "authority_drift": _expect_string(
            authority["drift"], _child_pointer(authority_pointer, "drift")
        ),
        "budget": budget,
        "result_kind": _expect_string(
            result_schema["kind"], _child_pointer(schema_pointer, "kind")
        ),
        "allow_nested_delegation": _expect_bool(
            policies["allowNestedDelegation"],
            _child_pointer(policies_pointer, "allowNestedDelegation"),
        ),
        "on_parent_cancel": _expect_string(
            policies["onParentCancel"], _child_pointer(policies_pointer, "onParentCancel")
        ),
    }
    hints = get_type_hints(DelegationContract)
    for semantic, wire in (
        ("required_artifact_kinds", "requiredArtifactKinds"),
        ("late_handoff", "lateHandoff"),
        ("metadata", "metadata"),
    ):
        if wire in obj:
            kwargs[semantic] = _decode_typed_value(
                obj[wire], hints[semantic], _child_pointer(pointer, wire)
            )
    try:
        return DelegationContract(**cast(Any, kwargs))
    except (TypeError, ValueError, ValidationError) as error:
        detail = error.code if isinstance(error, ValidationError) else "delegation_contract_invalid"
        raise DecodeError(code="field_value_invalid", pointer=pointer, safe_detail=detail) from None


def _decode_dataclass(
    value: object,
    target: type[object],
    pointer: str,
    *,
    ignored_fields: frozenset[str] = frozenset(),
) -> object:
    if target is DelegationContract:
        return _decode_delegation_contract(value, pointer)
    obj = _expect_object(value, pointer)
    target_fields = tuple(
        field
        for field in fields(cast(Any, target))
        if field.init and field.name not in ignored_fields
    )
    aliases: dict[str, str] = {}
    for field in target_fields:
        alias = PAYLOAD_ALIASES.get(field.name)
        if alias is None:
            raise RuntimeError(f"codec_alias_missing:{target.__name__}.{field.name}")
        aliases[field.name] = alias.wire_name
    required = frozenset(
        aliases[field.name]
        for field in target_fields
        if field.default is DATACLASS_MISSING and field.default_factory is DATACLASS_MISSING
    )
    allowed = frozenset(aliases.values())
    _exact_fields(
        obj,
        required=required,
        optional=allowed - required,
        pointer=pointer,
        missing_code="payload_field_missing",
        unknown_code="payload_field_unknown",
    )
    hints = get_type_hints(target)
    kwargs: dict[str, object] = {}
    for field in target_fields:
        wire_name = aliases[field.name]
        if wire_name in obj:
            kwargs[field.name] = _decode_typed_value(
                obj[wire_name], hints[field.name], _child_pointer(pointer, wire_name)
            )
    try:
        constructor = cast(Callable[..., object], target)
        return constructor(**kwargs)
    except DecodeError:
        raise
    except (TypeError, ValueError, ValidationError) as error:
        detail = error.code if isinstance(error, ValidationError) else "semantic_value_invalid"
        raise DecodeError(code="field_value_invalid", pointer=pointer, safe_detail=detail) from None


def _decode_typed_value(value: object, annotation: object, pointer: str) -> object:
    origin = get_origin(annotation)
    if origin in (types.UnionType, Union):
        arguments = get_args(annotation)
        if value is None and type(None) in arguments:
            return None
        concrete = tuple(
            argument for argument in arguments if argument not in (type(None), MissingType)
        )
        if len(concrete) != 1:
            raise DecodeError(code="codec_union_unsupported", pointer=pointer)
        return _decode_typed_value(value, concrete[0], pointer)
    if origin is Literal:
        return _decode_literal(value, annotation, pointer)
    if origin is tuple:
        array = _expect_array(value, pointer)
        arguments = get_args(annotation)
        if len(arguments) != 2 or arguments[1] is not Ellipsis:
            raise DecodeError(code="codec_tuple_unsupported", pointer=pointer)
        return tuple(
            _decode_typed_value(item, arguments[0], _child_pointer(pointer, index))
            for index, item in enumerate(array)
        )
    if annotation is JsonObject:
        return _expect_object(value, pointer)
    if annotation is JsonArray:
        return _expect_array(value, pointer)
    if annotation is str:
        return _expect_string(value, pointer)
    if annotation is bool:
        return _expect_bool(value, pointer)
    if annotation is int:
        return _expect_integer(value, pointer)
    if annotation is float:
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise DecodeError(code="field_number_required", pointer=pointer)
        return float(value)
    if annotation is type(None):
        if value is not None:
            raise DecodeError(code="field_null_required", pointer=pointer)
        return None
    if annotation is Timestamp:
        raw = _expect_string(value, pointer)
        try:
            return Timestamp(value=raw)
        except ValidationError as error:
            raise DecodeError(
                code="field_value_invalid", pointer=pointer, safe_detail=error.code
            ) from None
    if isinstance(annotation, type) and annotation in _ID_TYPES:
        raw = _expect_string(value, pointer)
        try:
            constructor = cast(Callable[..., object], annotation)
            return constructor(value=raw)
        except (TypeError, ValueError) as error:
            raise DecodeError(
                code="field_value_invalid", pointer=pointer, safe_detail=type(error).__name__
            ) from None
    if isinstance(annotation, type) and issubclass(annotation, StrEnum):
        raw = _expect_string(value, pointer)
        try:
            return annotation(raw)
        except ValueError:
            raise DecodeError(code="field_enum_invalid", pointer=pointer) from None
    if isinstance(annotation, type) and is_dataclass(annotation):
        return _decode_dataclass(value, annotation, pointer)
    raise DecodeError(code="codec_type_unsupported", pointer=pointer)


@final
@dataclass(frozen=True, slots=True, kw_only=True)
class CommandDecisionCodecSpec:
    decision: Literal["accepted", "rejected", "deferred", "superseded"]
    required_fields: frozenset[str]
    optional_fields: frozenset[str] = frozenset()


_BASE_DECISION_FIELDS: Final = frozenset(
    {"commandID", "decision", "decisionTrace", "resultEventIDs", "targetEvent"}
)

COMMAND_DECISION_CODEC_REGISTRY: Mapping[str, CommandDecisionCodecSpec] = MappingProxyType(
    {
        "accepted": CommandDecisionCodecSpec(
            decision="accepted",
            required_fields=_BASE_DECISION_FIELDS,
        ),
        "rejected": CommandDecisionCodecSpec(
            decision="rejected",
            required_fields=_BASE_DECISION_FIELDS | {"rejection"},
        ),
        "deferred": CommandDecisionCodecSpec(
            decision="deferred",
            required_fields=_BASE_DECISION_FIELDS | {"wait"},
        ),
        "superseded": CommandDecisionCodecSpec(
            decision="superseded",
            required_fields=_BASE_DECISION_FIELDS | {"declarationOnly", "replacementCommandID"},
        ),
    }
)


def _decode_trace(value: object, pointer: str) -> tuple[CommandDecisionTraceEntry, ...]:
    array = _expect_array(value, pointer)
    return tuple(
        cast(
            CommandDecisionTraceEntry,
            _decode_typed_value(item, CommandDecisionTraceEntry, _child_pointer(pointer, index)),
        )
        for index, item in enumerate(array)
    )


def _decode_event_ids(value: object, pointer: str) -> tuple[EventId, ...]:
    array = _expect_array(value, pointer)
    return tuple(
        cast(EventId, _decode_typed_value(item, EventId, _child_pointer(pointer, index)))
        for index, item in enumerate(array)
    )


def _decode_target(value: object, pointer: str) -> TargetEventPresent | TargetEventAbsent:
    obj = _expect_object(value, pointer)
    status_pointer = _child_pointer(pointer, "status")
    if "status" not in obj:
        raise DecodeError(code="field_required", pointer=status_pointer)
    status = _expect_string(obj["status"], status_pointer)
    if status == "present":
        _exact_fields(obj, required=frozenset({"status", "eventID"}), pointer=pointer)
        return TargetEventPresent(
            event_id=cast(
                EventId,
                _decode_typed_value(obj["eventID"], EventId, _child_pointer(pointer, "eventID")),
            )
        )
    if status == "absent":
        _exact_fields(obj, required=frozenset({"status"}), pointer=pointer)
        return TargetEventAbsent()
    raise DecodeError(code="target_event_status_invalid", pointer=status_pointer)


def _decode_command_decision_object(
    value: object,
    *,
    pointer: str = "",
    extra_required: frozenset[str] = frozenset(),
    extra_optional: frozenset[str] = frozenset(),
) -> CommandDecisionRecord:
    obj = _expect_object(value, pointer)
    if "decision" not in obj:
        raise DecodeError(code="field_required", pointer=_child_pointer(pointer, "decision"))
    decision = _expect_string(obj["decision"], _child_pointer(pointer, "decision"))
    spec = COMMAND_DECISION_CODEC_REGISTRY.get(decision)
    if spec is None:
        raise DecodeError(
            code="command_decision_unknown", pointer=_child_pointer(pointer, "decision")
        )
    _exact_fields(
        obj,
        required=spec.required_fields | extra_required,
        optional=spec.optional_fields | extra_optional,
        pointer=pointer,
        missing_code="field_required",
        unknown_code="field_unknown",
    )
    command_id = cast(
        CommandId,
        _decode_typed_value(obj["commandID"], CommandId, _child_pointer(pointer, "commandID")),
    )
    trace = _decode_trace(obj["decisionTrace"], _child_pointer(pointer, "decisionTrace"))
    results = _decode_event_ids(obj["resultEventIDs"], _child_pointer(pointer, "resultEventIDs"))
    target = _decode_target(obj["targetEvent"], _child_pointer(pointer, "targetEvent"))

    if decision == "accepted":
        branch: CommandDecisionRecordBranch = AcceptedDecisionRecord(
            decision_trace=trace, result_event_ids=results
        )
    elif decision == "rejected":
        rejection_pointer = _child_pointer(pointer, "rejection")
        rejection_obj = _expect_object(obj["rejection"], rejection_pointer)
        _exact_fields(rejection_obj, required=frozenset({"code"}), pointer=rejection_pointer)
        branch = RejectedDecisionRecord(
            decision_trace=trace,
            result_event_ids=results,
            rejection=CommandRejectionRecord(
                code=_expect_string(
                    rejection_obj["code"], _child_pointer(rejection_pointer, "code")
                )
            ),
        )
    elif decision == "deferred":
        wait_pointer = _child_pointer(pointer, "wait")
        wait_obj = _expect_object(obj["wait"], wait_pointer)
        _exact_fields(wait_obj, required=frozenset({"waitID", "kind"}), pointer=wait_pointer)
        branch = DeferredDecisionRecord(
            decision_trace=trace,
            result_event_ids=results,
            wait=CommandWaitRecord(
                wait_id=cast(
                    WaitId,
                    _decode_typed_value(
                        wait_obj["waitID"], WaitId, _child_pointer(wait_pointer, "waitID")
                    ),
                ),
                kind=cast(
                    WaitKind,
                    _decode_typed_value(
                        wait_obj["kind"], WaitKind, _child_pointer(wait_pointer, "kind")
                    ),
                ),
            ),
        )
    else:
        declaration_only = _expect_bool(
            obj["declarationOnly"], _child_pointer(pointer, "declarationOnly")
        )
        branch = SupersededDecisionRecord(
            decision_trace=trace,
            result_event_ids=results,
            declaration_only=declaration_only,
            replacement_command_id=cast(
                CommandId,
                _decode_typed_value(
                    obj["replacementCommandID"],
                    CommandId,
                    _child_pointer(pointer, "replacementCommandID"),
                ),
            ),
        )
    try:
        return CommandDecisionRecord(command_id=command_id, branch=branch, target_event=target)
    except ValidationError as error:
        raise DecodeError(
            code="command_decision_invalid", pointer=pointer, safe_detail=error.code
        ) from None


def decode_command_decision(data: bytes | str) -> CommandDecisionRecord:
    """Decode one exact v1 standalone decision record."""

    return _decode_command_decision_object(decode_json_value(data))


def _json_object(entries: list[tuple[str, JsonValue]]) -> JsonObject:
    return JsonObject(entries=tuple(entries))


def _encode_delegation_contract(value: DelegationContract) -> JsonObject:
    authority = _json_object(
        [
            (
                "grants",
                JsonArray(
                    values=tuple(_encode_semantic_value(grant) for grant in value.authority_grants)
                ),
            ),
            ("drift", value.authority_drift),
        ]
    )
    budgets = _json_object(
        [
            ("maxRequests", value.budget.max_requests),
            ("wallClockTimeoutMs", value.budget.wall_clock_timeout_ms),
            ("onBudgetExpired", value.budget.on_budget_expired),
        ]
    )
    policies = _json_object(
        [
            ("allowNestedDelegation", value.allow_nested_delegation),
            ("onParentCancel", value.on_parent_cancel),
        ]
    )
    entries: list[tuple[str, JsonValue]] = [
        ("version", value.version),
        ("runKind", value.run_kind.value),
        ("objective", value.objective),
        ("authority", authority),
        ("budgets", budgets),
        ("resultSchema", _json_object([("kind", value.result_kind)])),
        ("policies", policies),
    ]
    if value.required_artifact_kinds:
        entries.append(("requiredArtifactKinds", JsonArray(values=value.required_artifact_kinds)))
    if value.late_handoff != "ignore":
        entries.append(("lateHandoff", value.late_handoff))
    if value.metadata is not MISSING:
        entries.append(("metadata", cast(JsonValue, value.metadata)))
    return _json_object(entries)


def _encode_dataclass_value(
    value: object, *, always_emit: frozenset[str] = frozenset()
) -> JsonObject:
    if isinstance(value, DelegationContract):
        return _encode_delegation_contract(value)
    entries: list[tuple[str, JsonValue]] = []
    value_fields = tuple(fields(cast(Any, value)))
    if type(value).__name__ == "RunResult":
        by_name = {field.name: field for field in value_fields}
        value_fields = tuple(
            by_name[name]
            for name in ("version", "kind", "summary", "data", "parts", "artifact_ids", "metadata")
        )
    elif type(value).__name__ == "ActionUnknownPayload":
        by_name = {field.name: field for field in value_fields}
        value_fields = tuple(
            by_name[name]
            for name in (
                "action_id",
                "reason",
                "reliability",
                "message",
                "note",
                "evidence",
            )
        )
    elif type(value).__name__ == "CheckRecordedReportPayload":
        by_name = {field.name: field for field in value_fields}
        value_fields = tuple(
            by_name[name]
            for name in (
                "check_id",
                "subject",
                "rule",
                "validator",
                "status",
                "summary",
                "check_count",
                "result",
                "message",
                "evidence",
            )
        )
    elif type(value).__name__ == "TimerWaitResolvedPayload":
        by_name = {field.name: field for field in value_fields}
        value_fields = tuple(
            by_name[name] for name in ("wait_id", "kind", "scheduled_for", "fired_at", "fired_by")
        )
    elif type(value).__name__.startswith("Wait") or "Wait" in type(value).__name__:
        by_name = {field.name: field for field in value_fields}
        if "kind" in by_name:
            names = [field.name for field in value_fields if field.name != "kind"]
            kind_index = 1 if names and names[0] == "wait_id" else 0
            names.insert(kind_index, "kind")
            value_fields = tuple(by_name[name] for name in names)
    for field in value_fields:
        if not field.init or field.name == "variant":
            continue
        item = getattr(value, field.name)
        if item is MISSING:
            continue
        if item == () and field.default == () and field.name not in always_emit:
            continue
        alias = PAYLOAD_ALIASES.get(field.name)
        if alias is None:
            raise EncodeError(code="codec_alias_missing", safe_detail=field.name)
        entries.append((alias.wire_name, _encode_semantic_value(item)))
    return _json_object(entries)


def _encode_semantic_value(value: object) -> JsonValue:
    if value is None or isinstance(value, (bool, int, float, str)):
        return value
    if isinstance(value, _ID_TYPES):
        return value.value
    if isinstance(value, Timestamp):
        return value.value
    if isinstance(value, StrEnum):
        return value.value
    if isinstance(value, (JsonArray, JsonObject)):
        return value
    if isinstance(value, tuple):
        return JsonArray(values=tuple(_encode_semantic_value(item) for item in value))
    if is_dataclass(value) and not isinstance(value, type):
        return _encode_dataclass_value(value)
    raise EncodeError(code="semantic_value_unsupported")


def _encode_trace(trace: tuple[CommandDecisionTraceEntry, ...]) -> JsonArray:
    return JsonArray(values=tuple(_encode_dataclass_value(entry) for entry in trace))


def _encode_command_decision_entries(
    record: CommandDecisionRecord,
    *,
    allow_superseded: bool = False,
) -> tuple[tuple[str, JsonValue], ...]:
    if isinstance(record.branch, SupersededDecisionRecord) and not allow_superseded:
        raise EncodeError(code="declaration_only_writer")
    entries: list[tuple[str, JsonValue]] = [
        ("commandID", record.command_id.value),
        ("decision", record.branch.decision),
        ("decisionTrace", _encode_trace(record.branch.decision_trace)),
        (
            "resultEventIDs",
            JsonArray(values=tuple(event_id.value for event_id in record.branch.result_event_ids)),
        ),
    ]
    if isinstance(record.target_event, TargetEventPresent):
        target = _json_object(
            [
                ("status", record.target_event.status),
                ("eventID", record.target_event.event_id.value),
            ]
        )
    else:
        target = _json_object([("status", record.target_event.status)])
    entries.append(("targetEvent", target))
    if isinstance(record.branch, RejectedDecisionRecord):
        entries.append(("rejection", _json_object([("code", record.branch.rejection.code)])))
    elif isinstance(record.branch, DeferredDecisionRecord):
        entries.append(
            (
                "wait",
                _json_object(
                    [
                        ("waitID", record.branch.wait.wait_id.value),
                        ("kind", record.branch.wait.kind.value),
                    ]
                ),
            )
        )
    elif isinstance(record.branch, SupersededDecisionRecord):
        entries.extend(
            [
                ("declarationOnly", record.branch.declaration_only),
                ("replacementCommandID", record.branch.replacement_command_id.value),
            ]
        )
    return tuple(entries)


def encode_command_decision(record: CommandDecisionRecord) -> bytes:
    """Encode one writer-eligible lossless v1 decision record."""

    if not isinstance(record, CommandDecisionRecord):
        raise EncodeError(code="command_decision_type_invalid")
    return encode_json_value(JsonObject(entries=_encode_command_decision_entries(record)))
