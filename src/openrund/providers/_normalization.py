"""Strict provider-neutral tool declarations and proposal normalization."""

from __future__ import annotations

from dataclasses import dataclass
from typing import final

from openrund.codec import decode_json_value
from openrund.contracts.commands import (
    AddMessageOperation,
    CreateActionOperation,
    ModelOperation,
    OperationBatch,
)
from openrund.contracts.content import Content
from openrund.contracts.ids import ActionId, CapabilityId, ModelCallId
from openrund.contracts.json import MISSING, JsonObject, MissingType, freeze_json
from openrund.errors import (
    OpenRundError,
    ProviderProtocolError,
    ProviderToolArgumentsError,
    ValidationError,
)
from openrund.ports.providers import ModelProposal

_EMPTY_TEXT_FALLBACK = "No assistant text returned"


def _text(value: object, code: str) -> str:
    if not isinstance(value, str) or value == "":
        raise ValidationError(code=code)
    return value


@final
@dataclass(frozen=True, slots=True, kw_only=True)
class ProviderTool:
    """Provider-neutral declaration derived from one registered Capability action."""

    name: str
    description: str
    input_schema: JsonObject

    def __post_init__(self) -> None:
        object.__setattr__(self, "name", _text(self.name, "provider_tool_name_invalid"))
        object.__setattr__(
            self,
            "description",
            _text(self.description, "provider_tool_description_invalid"),
        )
        schema = freeze_json(self.input_schema)
        if not isinstance(schema, JsonObject):
            raise ValidationError(code="provider_tool_schema_invalid")
        object.__setattr__(self, "input_schema", schema)


@final
@dataclass(frozen=True, slots=True, kw_only=True)
class ProviderToolCall:
    """Normalized untrusted tool call before it becomes an Action proposal."""

    name: str
    arguments: JsonObject
    call_id: str | MissingType | None = MISSING

    def __post_init__(self) -> None:
        object.__setattr__(self, "name", _text(self.name, "provider_tool_call_name_invalid"))
        arguments = freeze_json(self.arguments)
        if not isinstance(arguments, JsonObject):
            raise ValidationError(code="provider_tool_call_arguments_invalid")
        object.__setattr__(self, "arguments", arguments)
        if self.call_id not in (MISSING, None) and (
            not isinstance(self.call_id, str) or self.call_id == ""
        ):
            raise ValidationError(code="provider_tool_call_id_invalid")


def split_provider_qualified_name(name: str, /) -> tuple[str, str]:
    """Split `capability.action` at the first dot with a deterministic fallback."""

    validated = _text(name, "provider_tool_call_name_invalid")
    capability, separator, action = validated.partition(".")
    if not separator:
        return "unknown", validated
    if capability == "" or action == "":
        raise ProviderProtocolError(code="provider_tool_name_invalid")
    return capability, action


def parse_provider_tool_arguments(value: str | None, /) -> JsonObject:
    """Decode a present provider argument string as exactly one JSON object."""

    if value is None or value == "":
        return JsonObject(entries=())
    if not isinstance(value, str):
        raise ProviderToolArgumentsError(input_classification="malformed_json")
    try:
        parsed = decode_json_value(value + "\n")
    except OpenRundError:
        raise ProviderToolArgumentsError(input_classification="malformed_json") from None
    if not isinstance(parsed, JsonObject):
        raise ProviderToolArgumentsError(input_classification="non_object")
    return parsed


def _action(
    call: ProviderToolCall,
    *,
    fallback_action_id: str,
) -> CreateActionOperation:
    capability, action_name = split_provider_qualified_name(call.name)
    call_id = call.call_id if isinstance(call.call_id, str) else fallback_action_id
    try:
        return CreateActionOperation(
            action_id=ActionId(value=call_id),
            capability_id=CapabilityId(value=capability),
            action_name=action_name,
            input=Content(data=call.arguments),
        )
    except ValidationError:
        raise ProviderProtocolError(code="provider_tool_call_invalid") from None


def normalize_provider_output(
    *,
    model_call_id: ModelCallId,
    provider: str,
    text: str | None = None,
    tool_calls: tuple[ProviderToolCall, ...] = (),
    metadata: JsonObject | MissingType | None = MISSING,
) -> ModelProposal:
    """Normalize text or tool calls into one inert request-bound proposal."""

    if not isinstance(model_call_id, ModelCallId):
        raise ValidationError(code="provider_model_call_id_invalid")
    validated_provider = _text(provider, "provider_name_invalid")
    try:
        calls = tuple(tool_calls)
    except TypeError as error:
        raise ValidationError(code="provider_tool_calls_invalid") from error
    if any(not isinstance(item, ProviderToolCall) for item in calls):
        raise ValidationError(code="provider_tool_calls_invalid")
    if calls:
        actions = tuple(
            _action(call, fallback_action_id=f"{model_call_id.value}_action_{index}")
            for index, call in enumerate(calls, start=1)
        )
        operation: ModelOperation = (
            actions[0] if len(actions) == 1 else OperationBatch(actions=actions)
        )
        response = Content(
            preview=(
                f"Provider proposed {len(actions)} actions"
                if len(actions) != 1
                else "Provider proposed an action"
            )
        )
    else:
        preview = text.strip() if isinstance(text, str) else ""
        if preview == "":
            preview = _EMPTY_TEXT_FALLBACK
        response = Content(preview=preview)
        operation = AddMessageOperation(message=response)
    return ModelProposal(
        model_call_id=model_call_id,
        operation=operation,
        response=response,
        provider=validated_provider,
        metadata=metadata,
    )
