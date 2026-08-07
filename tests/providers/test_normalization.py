from __future__ import annotations

import pytest

from openrund.contracts.commands import (
    AddMessageOperation,
    CreateActionOperation,
    OperationBatch,
)
from openrund.contracts.ids import ActionId, CapabilityId, ModelCallId
from openrund.contracts.json import JsonObject
from openrund.errors import ProviderProtocolError, ProviderToolArgumentsError, ValidationError
from openrund.providers import (
    ProviderTool,
    ProviderToolCall,
    normalize_provider_output,
    parse_provider_tool_arguments,
    split_provider_qualified_name,
)


def test_provider_tool_is_frozen_and_validated() -> None:
    source = {"type": "object", "properties": {"path": {"type": "string"}}}
    tool = ProviderTool(name="filesystem.read", description="Read a file", input_schema=source)  # type: ignore[arg-type]
    source["type"] = "array"

    assert tool.input_schema["type"] == "object"
    with pytest.raises(ValidationError, match="provider_tool_name_invalid"):
        ProviderTool(name="", description="Read", input_schema={})  # type: ignore[arg-type]


@pytest.mark.parametrize("value", [None, ""])
def test_absent_or_empty_tool_arguments_are_explicit_empty_input(value: str | None) -> None:
    parsed = parse_provider_tool_arguments(value)

    assert isinstance(parsed, JsonObject)
    assert len(parsed) == 0


def test_tool_arguments_preserve_order_and_nested_json() -> None:
    parsed = parse_provider_tool_arguments('{"path":"README.md","flags":[true,null]}')

    assert tuple(parsed) == ("path", "flags")
    assert parsed["path"] == "README.md"


@pytest.mark.parametrize(
    ("value", "classification"),
    [
        ("{broken", "malformed_json"),
        ("[]", "non_object"),
        ("null", "non_object"),
        ('"secret"', "non_object"),
    ],
)
def test_invalid_tool_arguments_fail_closed_without_raw_body(
    value: str,
    classification: str,
) -> None:
    with pytest.raises(ProviderToolArgumentsError) as raised:
        parse_provider_tool_arguments(value)

    assert raised.value.code == "provider_tool_arguments_invalid"
    assert raised.value.input_classification == classification
    assert value not in str(raised.value)


def test_qualified_name_splits_only_at_first_dot() -> None:
    assert split_provider_qualified_name("documents.markdown.replace_heading") == (
        "documents",
        "markdown.replace_heading",
    )
    assert split_provider_qualified_name("read") == ("unknown", "read")
    with pytest.raises(ProviderProtocolError, match="provider_tool_name_invalid"):
        split_provider_qualified_name("filesystem.")


def test_text_normalizes_to_request_bound_message_proposal() -> None:
    proposal = normalize_provider_output(
        model_call_id=ModelCallId(value="call-local"),
        provider="local-openai-compatible",
        text="  assistant answer  ",
    )

    assert proposal.model_call_id == ModelCallId(value="call-local")
    assert proposal.provider == "local-openai-compatible"
    assert proposal.response.preview == "assistant answer"
    assert isinstance(proposal.operation, AddMessageOperation)
    assert proposal.operation.message.preview == "assistant answer"


@pytest.mark.parametrize("text", [None, "", "  "])
def test_empty_text_has_deterministic_fallback(text: str | None) -> None:
    proposal = normalize_provider_output(
        model_call_id=ModelCallId(value="call-empty"),
        provider="openai",
        text=text,
    )

    assert isinstance(proposal.operation, AddMessageOperation)
    assert proposal.operation.message.preview == "No assistant text returned"


def test_single_tool_call_normalizes_to_action_with_supplied_identity() -> None:
    proposal = normalize_provider_output(
        model_call_id=ModelCallId(value="call-openai"),
        provider="openai",
        tool_calls=(
            ProviderToolCall(
                name="filesystem.read",
                call_id="provider-action",
                arguments=parse_provider_tool_arguments('{"path":"README.md"}'),
            ),
        ),
    )

    operation = proposal.operation
    assert proposal.model_call_id == ModelCallId(value="call-openai")
    assert isinstance(operation, CreateActionOperation)
    assert operation.action_id == ActionId(value="provider-action")
    assert operation.capability_id == CapabilityId(value="filesystem")
    assert operation.action_name == "read"
    assert operation.input.data["path"] == "README.md"  # type: ignore[index]


def test_multiple_tool_calls_normalize_to_ordered_batch_with_fallback_ids() -> None:
    empty = parse_provider_tool_arguments(None)
    proposal = normalize_provider_output(
        model_call_id=ModelCallId(value="call-batch"),
        provider="anthropic",
        tool_calls=(
            ProviderToolCall(name="filesystem.read", arguments=empty),
            ProviderToolCall(
                name="documents.markdown.replace_heading",
                call_id="tool-two",
                arguments=empty,
            ),
        ),
        metadata={"model": "fixed"},  # type: ignore[arg-type]
    )

    operation = proposal.operation
    assert isinstance(operation, OperationBatch)
    assert tuple(item.action_id.value for item in operation.actions) == (
        "call-batch_action_1",
        "tool-two",
    )
    assert operation.actions[1].capability_id == CapabilityId(value="documents")
    assert operation.actions[1].action_name == "markdown.replace_heading"
    assert proposal.metadata["model"] == "fixed"  # type: ignore[index]


def test_invalid_provider_tool_call_identity_is_rejected_at_boundary() -> None:
    with pytest.raises(ValidationError, match="provider_tool_call_id_invalid"):
        ProviderToolCall(
            name="filesystem.read",
            call_id="",
            arguments=parse_provider_tool_arguments(None),
        )
