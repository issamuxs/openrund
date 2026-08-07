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
    HttpRequest,
    HttpResponse,
    LocalModelProfile,
    LocalOpenAICompatibleProvider,
    OpenAIResponsesProvider,
    ProviderTool,
    ServerSentEvent,
)


class _Transport:
    def __init__(self, responses: tuple[HttpResponse, ...]) -> None:
        self._responses = iter(responses)
        self.requests: list[HttpRequest] = []
        self.closed = False

    async def request(self, request: HttpRequest, /) -> HttpResponse:
        self.requests.append(request)
        return next(self._responses)

    async def aclose(self) -> None:
        self.closed = True


def _response(value: object, *, status: int = 200) -> HttpResponse:
    return HttpResponse(
        status=status,
        headers=(("content-type", "application/json"),),
        body=json.dumps(value, separators=(",", ":")).encode(),
    )


def _request(call_id: str = "model-local") -> ModelRequest:
    return ModelRequest(
        model_call_id=ModelCallId(value=call_id),
        run_id=RunId(value="run-one"),
        context=Content(preview="Inspect the workspace", data={"position": 4}),  # type: ignore[arg-type]
        remaining_requests=3,
        metadata={"attempt": 1},  # type: ignore[arg-type]
    )


def _tool() -> ProviderTool:
    return ProviderTool(
        name="filesystem.read",
        description="Read a workspace file",
        input_schema={  # type: ignore[arg-type]
            "type": "object",
            "required": ["path"],
            "properties": {"path": {"type": "string"}},
            "additionalProperties": False,
        },
    )


def test_openai_serializes_context_tools_and_explicit_credentials(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    transport = _Transport(
        (
            _response(
                {
                    "id": "remote-response",
                    "output": [
                        {
                            "type": "message",
                            "content": [{"type": "output_text", "text": "done"}],
                        }
                    ],
                    "usage": {"input_tokens": 10, "output_tokens": 2, "total_tokens": 12},
                }
            ),
        )
    )
    monkeypatch.setenv("OPENAI_API_KEY", "ambient-must-not-be-read")
    provider = OpenAIResponsesProvider(
        api_key="explicit-key",
        model="gpt-fixed",
        tools=(_tool(),),
        transport=transport,
        stream=False,
    )

    proposal = asyncio.run(provider.propose(_request()))
    sent = transport.requests[0]
    body = json.loads(sent.body)

    assert sent.url == "https://api.openai.com/v1/responses"
    assert ("authorization", "Bearer explicit-key") in sent.headers
    assert b"ambient-must-not-be-read" not in sent.body
    assert body["model"] == "gpt-fixed"
    assert body["stream"] is False
    assert body["tools"][0] == {
        "type": "function",
        "name": "filesystem.read",
        "description": "Read a workspace file",
        "parameters": {
            "type": "object",
            "required": ["path"],
            "properties": {"path": {"type": "string"}},
            "additionalProperties": False,
        },
        "strict": True,
    }
    serialized_context = json.loads(body["input"][0]["content"][0]["text"])
    assert serialized_context["runId"] == "run-one"
    assert serialized_context["preview"] == "Inspect the workspace"
    assert proposal.model_call_id == ModelCallId(value="model-local")
    assert isinstance(proposal.operation, AddMessageOperation)
    assert proposal.operation.message.preview == "done"
    assert proposal.metadata["remoteResponseId"] == "remote-response"  # type: ignore[index]
    usage = proposal.metadata["usage"]  # type: ignore[index]
    assert isinstance(usage, JsonObject)
    assert usage["total_tokens"] == 12


def test_openai_function_call_uses_request_identity_and_provider_action_identity() -> None:
    transport = _Transport(
        (
            _response(
                {
                    "id": "untrusted-remote-call-id",
                    "output": [
                        {
                            "type": "function_call",
                            "call_id": "action-provider",
                            "name": "filesystem.read",
                            "arguments": '{"path":"README.md"}',
                        }
                    ],
                }
            ),
        )
    )
    provider = OpenAIResponsesProvider(
        api_key="fixed",
        model="gpt-fixed",
        transport=transport,
        stream=False,
    )

    proposal = asyncio.run(provider.propose(_request("request-owned")))

    assert proposal.model_call_id == ModelCallId(value="request-owned")
    assert isinstance(proposal.operation, CreateActionOperation)
    assert proposal.operation.action_id.value == "action-provider"
    assert proposal.operation.input.data["path"] == "README.md"  # type: ignore[index]


def test_openai_multiple_calls_form_ordered_batch_with_fallback_ids() -> None:
    transport = _Transport(
        (
            _response(
                {
                    "output": [
                        {
                            "type": "function_call",
                            "name": "filesystem.read",
                            "arguments": "{}",
                        },
                        {
                            "type": "function_call",
                            "name": "documents.markdown.replace_heading",
                            "arguments": "{}",
                        },
                    ]
                }
            ),
        )
    )
    provider = OpenAIResponsesProvider(
        api_key="fixed", model="gpt-fixed", transport=transport, stream=False
    )

    proposal = asyncio.run(provider.propose(_request("batch-call")))

    assert isinstance(proposal.operation, OperationBatch)
    assert tuple(item.action_id.value for item in proposal.operation.actions) == (
        "batch-call_action_1",
        "batch-call_action_2",
    )
    assert proposal.operation.actions[1].action_name == "markdown.replace_heading"


def test_openai_sse_uses_only_completed_response() -> None:
    transport = _Transport(
        (
            HttpResponse(
                status=200,
                headers=(("content-type", "text/event-stream"),),
                body=b"",
                events=(
                    ServerSentEvent(
                        event="response.created",
                        data='{"type":"response.created","response":{"output":[]}}',
                    ),
                    ServerSentEvent(
                        event="response.completed",
                        data=(
                            '{"type":"response.completed","response":'
                            '{"id":"remote","output":[{"type":"message","content":'
                            '[{"type":"output_text","text":"stream done"}]}]}}'
                        ),
                    ),
                    ServerSentEvent(data="[DONE]"),
                ),
            ),
        )
    )
    provider = OpenAIResponsesProvider(
        api_key="fixed", model="gpt-fixed", transport=transport, stream=True
    )

    proposal = asyncio.run(provider.propose(_request()))

    assert isinstance(proposal.operation, AddMessageOperation)
    assert proposal.operation.message.preview == "stream done"
    assert proposal.metadata["streamed"] is True  # type: ignore[index]


@pytest.mark.parametrize(
    "body",
    [
        b"not-json",
        b'{"output":[],"output":[]}',
        b"[]",
        b'{"output":"wrong"}',
        b'{"output":[{"type":"function_call","name":"filesystem.read","arguments":"[1]"}]}',
    ],
)
def test_openai_malformed_output_is_safe_protocol_failure(body: bytes) -> None:
    transport = _Transport(
        (HttpResponse(status=200, headers=(("content-type", "application/json"),), body=body),)
    )
    provider = OpenAIResponsesProvider(
        api_key="fixed", model="gpt-fixed", transport=transport, stream=False
    )

    with pytest.raises(ProviderProtocolError) as raised:
        asyncio.run(provider.propose(_request()))

    assert body.decode(errors="ignore") not in str(raised.value)


def test_http_failure_discards_remote_body_and_classifies_retryability() -> None:
    secret = b'{"authorization":"Bearer secret","error":"offline"}'
    transport = _Transport(
        (HttpResponse(status=503, headers=(("content-type", "application/json"),), body=secret),)
    )
    provider = OpenAIResponsesProvider(
        api_key="fixed", model="gpt-fixed", transport=transport, stream=False
    )

    with pytest.raises(ProviderResponseError) as raised:
        asyncio.run(provider.propose(_request()))

    assert raised.value.status == 503
    assert raised.value.retryable is True
    assert "secret" not in str(raised.value)
    assert "offline" not in str(raised.value)


def test_local_profile_default_and_no_ambient_authorization() -> None:
    transport = _Transport((_response({"output": []}),))
    provider = LocalOpenAICompatibleProvider(
        base_url="http://127.0.0.1:11434/v1",
        profile=LocalModelProfile.FALLBACK,
        transport=transport,
    )

    proposal = asyncio.run(provider.propose(_request()))
    description = provider.describe_profile()
    sent = transport.requests[0]

    assert description.default_model == "llama-3.2-3b"
    assert description.model == "llama-3.2-3b"
    assert description.target_hardware == "8GB-16GB laptop"
    assert sent.url == "http://127.0.0.1:11434/v1/responses"
    assert all(name != "authorization" for name, _value in sent.headers)
    assert proposal.provider == "local-openai-compatible"


def test_injected_transport_is_not_owned_and_closed_provider_rejects_use() -> None:
    transport = _Transport((_response({"output": []}),))
    provider = OpenAIResponsesProvider(
        api_key="fixed", model="gpt-fixed", transport=transport, stream=False
    )

    asyncio.run(provider.aclose())

    assert transport.closed is False
    with pytest.raises(ProviderTransportError, match="provider_closed"):
        asyncio.run(provider.propose(_request()))
