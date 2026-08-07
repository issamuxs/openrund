from __future__ import annotations

import asyncio
import json

import pytest

from openrund.contracts.commands import AddMessageOperation, CreateActionOperation, OperationBatch
from openrund.contracts.content import Content
from openrund.contracts.ids import ModelCallId, RunId
from openrund.contracts.json import JsonObject
from openrund.errors import ProviderProtocolError, ProviderResponseError, ProviderTransportError
from openrund.ports.providers import ModelRequest
from openrund.providers import (
    AnthropicMessagesProvider,
    HttpRequest,
    HttpResponse,
    ProviderTool,
    ServerSentEvent,
)


class _Transport:
    def __init__(self, response: HttpResponse) -> None:
        self.response = response
        self.requests: list[HttpRequest] = []
        self.closed = False

    async def request(self, request: HttpRequest, /) -> HttpResponse:
        self.requests.append(request)
        return self.response

    async def aclose(self) -> None:
        self.closed = True


def _response(value: object, *, status: int = 200) -> HttpResponse:
    return HttpResponse(
        status=status,
        headers=(("content-type", "application/json"),),
        body=json.dumps(value, separators=(",", ":")).encode(),
    )


def _request(call_id: str = "anthropic-request") -> ModelRequest:
    return ModelRequest(
        model_call_id=ModelCallId(value=call_id),
        run_id=RunId(value="run-anthropic"),
        context=Content(preview="Inspect the workspace"),
        remaining_requests=2,
    )


def _tool() -> ProviderTool:
    return ProviderTool(
        name="filesystem.read",
        description="Read a workspace file",
        input_schema={  # type: ignore[arg-type]
            "type": "object",
            "properties": {"path": {"type": "string"}},
        },
    )


def test_anthropic_serializes_messages_tools_and_explicit_headers(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    transport = _Transport(
        _response(
            {
                "id": "message-remote",
                "content": [{"type": "text", "text": "done"}],
                "usage": {"input_tokens": 8, "output_tokens": 2},
            }
        )
    )
    monkeypatch.setenv("ANTHROPIC_API_KEY", "ambient-must-not-be-read")
    provider = AnthropicMessagesProvider(
        api_key="explicit-anthropic-key",
        model="claude-fixed",
        tools=(_tool(),),
        transport=transport,
        stream=False,
    )

    proposal = asyncio.run(provider.propose(_request()))
    sent = transport.requests[0]
    body = json.loads(sent.body)

    assert sent.url == "https://api.anthropic.com/v1/messages"
    assert ("x-api-key", "explicit-anthropic-key") in sent.headers
    assert ("anthropic-version", "2023-06-01") in sent.headers
    assert b"ambient-must-not-be-read" not in sent.body
    assert body["model"] == "claude-fixed"
    assert body["max_tokens"] == 1024
    assert body["tools"][0] == {
        "name": "filesystem.read",
        "description": "Read a workspace file",
        "input_schema": {
            "type": "object",
            "properties": {"path": {"type": "string"}},
        },
    }
    assert json.loads(body["messages"][0]["content"])["runId"] == "run-anthropic"
    assert proposal.model_call_id == ModelCallId(value="anthropic-request")
    assert isinstance(proposal.operation, AddMessageOperation)
    assert proposal.operation.message.preview == "done"
    usage = proposal.metadata["usage"]  # type: ignore[index]
    assert isinstance(usage, JsonObject)
    assert usage["output_tokens"] == 2


def test_anthropic_tool_use_is_request_bound_action() -> None:
    transport = _Transport(
        _response(
            {
                "id": "untrusted-remote-id",
                "content": [
                    {
                        "type": "tool_use",
                        "id": "tool-one",
                        "name": "filesystem.read",
                        "input": {"path": "README.md"},
                    }
                ],
            }
        )
    )
    provider = AnthropicMessagesProvider(
        api_key="fixed",
        model="claude-fixed",
        transport=transport,
        stream=False,
    )

    proposal = asyncio.run(provider.propose(_request("request-owned")))

    assert proposal.model_call_id == ModelCallId(value="request-owned")
    assert isinstance(proposal.operation, CreateActionOperation)
    assert proposal.operation.action_id.value == "tool-one"
    assert proposal.operation.input.data["path"] == "README.md"  # type: ignore[index]


def test_anthropic_multiple_tool_uses_form_ordered_batch() -> None:
    transport = _Transport(
        _response(
            {
                "content": [
                    {"type": "tool_use", "name": "filesystem.read", "input": {}},
                    {
                        "type": "tool_use",
                        "name": "documents.markdown.replace_heading",
                        "input": {},
                    },
                ]
            }
        )
    )
    provider = AnthropicMessagesProvider(
        api_key="fixed",
        model="claude-fixed",
        transport=transport,
        stream=False,
    )

    proposal = asyncio.run(provider.propose(_request("batch-anthropic")))

    assert isinstance(proposal.operation, OperationBatch)
    assert tuple(item.action_id.value for item in proposal.operation.actions) == (
        "batch-anthropic_action_1",
        "batch-anthropic_action_2",
    )
    assert proposal.operation.actions[1].action_name == "markdown.replace_heading"


def test_anthropic_sse_reconstructs_text_and_tool_input() -> None:
    response = HttpResponse(
        status=200,
        headers=(("content-type", "text/event-stream"),),
        body=b"",
        events=(
            ServerSentEvent(
                event="message_start",
                data=(
                    '{"type":"message_start","message":{"id":"remote-stream",'
                    '"usage":{"input_tokens":5}}}'
                ),
            ),
            ServerSentEvent(
                event="content_block_start",
                data=(
                    '{"type":"content_block_start","index":0,"content_block":'
                    '{"type":"tool_use","id":"tool-stream","name":"filesystem.read"}}'
                ),
            ),
            ServerSentEvent(
                event="content_block_delta",
                data=(
                    '{"type":"content_block_delta","index":0,"delta":'
                    '{"type":"input_json_delta","partial_json":"{\\"path\\":"}}'
                ),
            ),
            ServerSentEvent(
                event="content_block_delta",
                data=(
                    '{"type":"content_block_delta","index":0,"delta":'
                    '{"type":"input_json_delta","partial_json":"\\"README.md\\"}"}}'
                ),
            ),
            ServerSentEvent(
                event="message_delta",
                data='{"type":"message_delta","usage":{"output_tokens":3}}',
            ),
            ServerSentEvent(event="message_stop", data='{"type":"message_stop"}'),
        ),
    )
    provider = AnthropicMessagesProvider(
        api_key="fixed",
        model="claude-fixed",
        transport=_Transport(response),
        stream=True,
    )

    proposal = asyncio.run(provider.propose(_request()))

    assert isinstance(proposal.operation, CreateActionOperation)
    assert proposal.operation.input.data["path"] == "README.md"  # type: ignore[index]
    assert proposal.metadata["streamed"] is True  # type: ignore[index]


def test_anthropic_sse_reconstructs_text_deltas() -> None:
    response = HttpResponse(
        status=200,
        headers=(("content-type", "text/event-stream"),),
        body=b"",
        events=(
            ServerSentEvent(data=('{"type":"message_start","message":{"id":"remote","usage":{}}}')),
            ServerSentEvent(
                data=(
                    '{"type":"content_block_start","index":0,'
                    '"content_block":{"type":"text","text":""}}'
                )
            ),
            ServerSentEvent(
                data=(
                    '{"type":"content_block_delta","index":0,'
                    '"delta":{"type":"text_delta","text":"hello "}}'
                )
            ),
            ServerSentEvent(
                data=(
                    '{"type":"content_block_delta","index":0,'
                    '"delta":{"type":"text_delta","text":"world"}}'
                )
            ),
            ServerSentEvent(data='{"type":"message_stop"}'),
        ),
    )
    provider = AnthropicMessagesProvider(
        api_key="fixed",
        model="claude-fixed",
        transport=_Transport(response),
        stream=True,
    )

    proposal = asyncio.run(provider.propose(_request()))

    assert isinstance(proposal.operation, AddMessageOperation)
    assert proposal.operation.message.preview == "hello world"


@pytest.mark.parametrize(
    "value",
    [
        {"content": "wrong"},
        {"content": [{"type": "tool_use", "name": "filesystem.read", "input": []}]},
        {"content": [{"type": "text", "text": 1}]},
    ],
)
def test_anthropic_malformed_content_is_safe_protocol_failure(value: object) -> None:
    raw = json.dumps(value).encode()
    provider = AnthropicMessagesProvider(
        api_key="fixed",
        model="claude-fixed",
        transport=_Transport(
            HttpResponse(status=200, headers=(("content-type", "application/json"),), body=raw)
        ),
        stream=False,
    )

    with pytest.raises(ProviderProtocolError) as raised:
        asyncio.run(provider.propose(_request()))

    assert raw.decode() not in str(raised.value)


def test_anthropic_http_failure_is_body_blind() -> None:
    secret = b'{"x-api-key":"secret","error":"offline"}'
    provider = AnthropicMessagesProvider(
        api_key="fixed",
        model="claude-fixed",
        transport=_Transport(
            HttpResponse(status=429, headers=(("content-type", "application/json"),), body=secret)
        ),
        stream=False,
    )

    with pytest.raises(ProviderResponseError) as raised:
        asyncio.run(provider.propose(_request()))

    assert raised.value.status == 429
    assert raised.value.retryable is True
    assert "secret" not in str(raised.value)


def test_injected_transport_is_not_owned_and_closed_provider_rejects_use() -> None:
    transport = _Transport(_response({"content": []}))
    provider = AnthropicMessagesProvider(
        api_key="fixed",
        model="claude-fixed",
        transport=transport,
        stream=False,
    )

    asyncio.run(provider.aclose())

    assert transport.closed is False
    with pytest.raises(ProviderTransportError, match="provider_closed"):
        asyncio.run(provider.propose(_request()))
