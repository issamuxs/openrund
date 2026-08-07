"""Explicit validated Capability definitions and live transport bindings."""

from __future__ import annotations

from dataclasses import dataclass
from typing import final

from openrund.contracts.capabilities import (
    Capability,
    CapabilityAction,
    CapabilityReliability,
    CapabilityResult,
)
from openrund.contracts.ids import CapabilityId
from openrund.contracts.json import JsonArray, JsonObject, JsonValue, MissingType
from openrund.engine._governance import schema_violations
from openrund.errors import CapabilityProtocolError, ValidationError
from openrund.ports.capabilities import CapabilityInvocation, CapabilityTransport

_SCHEMA_KEYS = frozenset(
    {
        "$schema",
        "title",
        "description",
        "type",
        "required",
        "properties",
        "additionalProperties",
        "items",
        "enum",
        "minLength",
        "maxLength",
        "minimum",
        "maximum",
        "minItems",
        "maxItems",
    }
)
_SCHEMA_TYPES = frozenset({"object", "array", "string", "number", "integer", "boolean", "null"})


def _schema_definition_errors(schema: JsonObject, pointer: str = "$") -> tuple[str, ...]:
    errors: list[str] = []
    errors.extend(f"{pointer}:unsupported:{key}" for key in schema if key not in _SCHEMA_KEYS)
    declared = schema.get("type")
    types: tuple[str, ...]
    if isinstance(declared, str):
        types = (declared,)
    elif isinstance(declared, JsonArray) and all(isinstance(item, str) for item in declared):
        types = tuple(item for item in declared if isinstance(item, str))
    else:
        types = ()
        errors.append(f"{pointer}:type_invalid")
    if (
        not types
        or len(set(types)) != len(types)
        or any(item not in _SCHEMA_TYPES for item in types)
    ):
        errors.append(f"{pointer}:type_invalid")

    required = schema.get("required")
    if required is not None and (
        not isinstance(required, JsonArray)
        or any(not isinstance(item, str) or item == "" for item in required)
        or len(set(required)) != len(required)
    ):
        errors.append(f"{pointer}:required_invalid")
    properties = schema.get("properties")
    if properties is not None:
        if not isinstance(properties, JsonObject):
            errors.append(f"{pointer}:properties_invalid")
        else:
            for name, child in properties.entries:
                if not isinstance(child, JsonObject):
                    errors.append(f"{pointer}.{name}:schema_invalid")
                else:
                    errors.extend(_schema_definition_errors(child, f"{pointer}.{name}"))
    additional = schema.get("additionalProperties")
    if additional not in (None, True, False):
        if not isinstance(additional, JsonObject):
            errors.append(f"{pointer}:additional_properties_invalid")
        else:
            errors.extend(_schema_definition_errors(additional, f"{pointer}.*"))
    items = schema.get("items")
    if items is not None:
        if not isinstance(items, JsonObject):
            errors.append(f"{pointer}:items_invalid")
        else:
            errors.extend(_schema_definition_errors(items, f"{pointer}[]"))
    enum = schema.get("enum")
    if enum is not None and (not isinstance(enum, JsonArray) or len(enum) == 0):
        errors.append(f"{pointer}:enum_invalid")
    for name in ("minLength", "maxLength", "minItems", "maxItems"):
        value = schema.get(name)
        if value is not None and (
            isinstance(value, bool) or not isinstance(value, int) or value < 0
        ):
            errors.append(f"{pointer}:{name}_invalid")
    for name in ("minimum", "maximum"):
        value = schema.get(name)
        if value is not None and (isinstance(value, bool) or not isinstance(value, (int, float))):
            errors.append(f"{pointer}:{name}_invalid")
    return tuple(dict.fromkeys(errors))


def _validate_action_definition(action: CapabilityAction) -> None:
    if _schema_definition_errors(action.input_schema):
        raise ValidationError(code="capability_input_schema_unsupported")
    if isinstance(action.output_schema, JsonObject) and _schema_definition_errors(
        action.output_schema
    ):
        raise ValidationError(code="capability_output_schema_unsupported")
    if action.transport is None or isinstance(action.transport, MissingType):
        raise ValidationError(code="capability_action_transport_required")
    if (
        action.reliability is CapabilityReliability.INTERRUPTIBLE
        and not action.cancellation.supported
    ):
        raise ValidationError(code="capability_interruptible_cancellation_required")
    if (
        action.cancellation.supported
        and action.reliability is not CapabilityReliability.INTERRUPTIBLE
    ):
        raise ValidationError(code="capability_cancellation_reliability_mismatch")


@final
@dataclass(frozen=True, slots=True, kw_only=True)
class ActionTransportBinding:
    action_name: str
    transport: CapabilityTransport

    def __post_init__(self) -> None:
        if not isinstance(self.action_name, str) or self.action_name == "":
            raise ValidationError(code="capability_binding_action_invalid")
        if not callable(getattr(self.transport, "invoke", None)):
            raise ValidationError(code="capability_binding_transport_invalid")


@final
@dataclass(frozen=True, slots=True, kw_only=True)
class RegisteredCapability:
    definition: Capability
    bindings: tuple[ActionTransportBinding, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.definition, Capability):
            raise ValidationError(code="registered_capability_definition_invalid")
        if not self.definition.actions:
            raise ValidationError(code="registered_capability_actions_empty")
        try:
            bindings = tuple(self.bindings)
        except TypeError as error:
            raise ValidationError(code="registered_capability_bindings_invalid") from error
        if any(not isinstance(item, ActionTransportBinding) for item in bindings):
            raise ValidationError(code="registered_capability_bindings_invalid")
        names = tuple(item.action_name for item in bindings)
        expected = tuple(item.name for item in self.definition.actions)
        if len(set(names)) != len(names):
            raise ValidationError(code="capability_binding_duplicate")
        if set(names) != set(expected):
            raise ValidationError(code="capability_binding_incomplete")
        for action in self.definition.actions:
            _validate_action_definition(action)
            binding = next(item for item in bindings if item.action_name == action.name)
            transport_kind = getattr(binding.transport, "kind", None)
            assert action.transport is not None and not isinstance(action.transport, MissingType)
            if transport_kind is not action.transport.kind:
                raise ValidationError(code="capability_binding_kind_mismatch")
        object.__setattr__(self, "bindings", bindings)


@final
@dataclass(frozen=True, slots=True, kw_only=True)
class CapabilityRoute:
    definition: Capability
    action: CapabilityAction
    transport: CapabilityTransport

    def validate_input(self, value: JsonValue, /) -> None:
        if schema_violations(value, self.action.input_schema):
            raise CapabilityProtocolError(code="capability_input_schema_violation")

    def validate_result(self, result: CapabilityResult, /) -> CapabilityResult:
        if not isinstance(result, CapabilityResult):
            raise CapabilityProtocolError(code="capability_result_type_invalid")
        if isinstance(self.action.output_schema, JsonObject):
            output: JsonValue = None if isinstance(result.output, MissingType) else result.output
            if schema_violations(output, self.action.output_schema):
                raise CapabilityProtocolError(code="capability_output_schema_violation")
        declared = {item.kind for item in self.action.artifacts}
        actual = {item.kind for item in result.inline_artifacts}
        if not actual <= declared:
            raise CapabilityProtocolError(code="capability_artifact_kind_undeclared")
        required = {item.kind for item in self.action.artifacts if item.required}
        if not required <= actual:
            raise CapabilityProtocolError(code="capability_artifact_required_missing")
        return result


@final
class CapabilityRegistry:
    __slots__ = ("_registered",)

    def __init__(self, capabilities: tuple[RegisteredCapability, ...] = ()) -> None:
        try:
            registered = tuple(capabilities)
        except TypeError as error:
            raise ValidationError(code="capability_registry_invalid") from error
        if any(not isinstance(item, RegisteredCapability) for item in registered):
            raise ValidationError(code="capability_registry_invalid")
        ids = tuple(item.definition.capability_id for item in registered)
        if len(set(ids)) != len(ids):
            raise ValidationError(code="capability_registry_duplicate")
        self._registered = registered

    @property
    def definitions(self) -> tuple[Capability, ...]:
        return tuple(item.definition for item in self._registered)

    def resolve(self, capability_id: CapabilityId, action_name: str, /) -> CapabilityRoute:
        if not isinstance(capability_id, CapabilityId) or not isinstance(action_name, str):
            raise ValidationError(code="capability_route_invalid")
        registered = next(
            (item for item in self._registered if item.definition.capability_id == capability_id),
            None,
        )
        if registered is None:
            raise CapabilityProtocolError(code="capability_not_registered")
        action = next(
            (item for item in registered.definition.actions if item.name == action_name), None
        )
        if action is None:
            raise CapabilityProtocolError(code="capability_action_not_registered")
        binding = next(item for item in registered.bindings if item.action_name == action_name)
        return CapabilityRoute(
            definition=registered.definition,
            action=action,
            transport=binding.transport,
        )

    async def invoke(self, invocation: CapabilityInvocation, /) -> CapabilityResult:
        if not isinstance(invocation, CapabilityInvocation):
            raise ValidationError(code="capability_registry_invocation_invalid")
        route = self.resolve(invocation.capability_id, invocation.action_name)
        route.validate_input(
            invocation.input.data if isinstance(invocation.input.data, JsonObject) else None
        )
        return route.validate_result(await route.transport.invoke(invocation))
