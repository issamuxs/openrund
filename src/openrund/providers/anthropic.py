"""Anthropic Messages provider over direct async HTTP and SSE."""

from __future__ import annotations

from typing import Self, final

from openrund.contracts.json import MISSING, JsonArray, JsonObject, freeze_json
from openrund.errors import (
    ProviderProtocolError,
    ProviderResponseError,
    ProviderTransportError,
    ValidationError,
)
from openrund.ports.providers import ModelProposal, ModelRequest
from openrund.providers._http import (
    AsyncHttpTransport,
    HttpRequest,
    HttpResponse,
    StdlibHttpTransport,
)
from openrund.providers._normalization import (
    ProviderTool,
    ProviderToolCall,
    normalize_provider_output,
)
from openrund.providers.openai import _content_context, _decode_object, _text, _wire


def _tools(tools: tuple[ProviderTool, ...]) -> list[dict[str, object]]:
    return [
        {
            "name": tool.name,
            "description": tool.description,
            "input_schema": tool.input_schema,
        }
        for tool in tools
    ]


def _metadata(payload: JsonObject, model: str, *, streamed: bool) -> JsonObject:
    value: dict[str, object] = {"model": model, "streamed": streamed}
    remote_id = payload.get("id")
    if isinstance(remote_id, str) and 0 < len(remote_id.encode("utf-8")) <= 256:
        value["remoteResponseId"] = remote_id
    usage = payload.get("usage")
    if isinstance(usage, JsonObject):
        compact: dict[str, object] = {}
        for name in ("input_tokens", "output_tokens"):
            count = usage.get(name)
            if isinstance(count, int) and not isinstance(count, bool) and count >= 0:
                compact[name] = count
        if compact:
            value["usage"] = compact
    frozen = freeze_json(value)
    assert isinstance(frozen, JsonObject)
    return frozen


def _index(value: object) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ProviderProtocolError(code="anthropic_stream_index_invalid")
    return value


def _stream_payload(response: HttpResponse) -> JsonObject:
    remote_id: str | None = None
    usage: dict[str, object] = {}
    blocks: dict[int, dict[str, object]] = {}
    stopped = False
    for event in response.events:
        item = _decode_object(event.data)
        kind = item.get("type")
        if kind == "message_start":
            message = item.get("message")
            if not isinstance(message, JsonObject):
                raise ProviderProtocolError(code="anthropic_stream_message_invalid")
            message_id = message.get("id")
            if isinstance(message_id, str):
                remote_id = message_id
            initial_usage = message.get("usage")
            if isinstance(initial_usage, JsonObject):
                usage.update(initial_usage)
        elif kind == "content_block_start":
            index = _index(item.get("index"))
            started_block = item.get("content_block")
            if not isinstance(started_block, JsonObject) or index in blocks:
                raise ProviderProtocolError(code="anthropic_stream_block_invalid")
            block_type = started_block.get("type")
            if block_type == "text":
                text = started_block.get("text", "")
                if not isinstance(text, str):
                    raise ProviderProtocolError(code="anthropic_stream_block_invalid")
                blocks[index] = {"type": "text", "text": text}
            elif block_type == "tool_use":
                name = started_block.get("name")
                tool_id = started_block.get("id", MISSING)
                if not isinstance(name, str) or (
                    tool_id not in (MISSING, None) and not isinstance(tool_id, str)
                ):
                    raise ProviderProtocolError(code="anthropic_stream_block_invalid")
                blocks[index] = {
                    "type": "tool_use",
                    "name": name,
                    **({"id": tool_id} if isinstance(tool_id, str) else {}),
                    "partial_input": "",
                }
            else:
                blocks[index] = {"type": "ignored"}
        elif kind == "content_block_delta":
            index = _index(item.get("index"))
            state = blocks.get(index)
            delta = item.get("delta")
            if state is None or not isinstance(delta, JsonObject):
                raise ProviderProtocolError(code="anthropic_stream_delta_invalid")
            delta_type = delta.get("type")
            if state.get("type") == "text" and delta_type == "text_delta":
                text = delta.get("text")
                if not isinstance(text, str):
                    raise ProviderProtocolError(code="anthropic_stream_delta_invalid")
                state["text"] = str(state["text"]) + text
            elif state.get("type") == "tool_use" and delta_type == "input_json_delta":
                partial = delta.get("partial_json")
                if not isinstance(partial, str):
                    raise ProviderProtocolError(code="anthropic_stream_delta_invalid")
                state["partial_input"] = str(state["partial_input"]) + partial
        elif kind == "message_delta":
            final_usage = item.get("usage")
            if isinstance(final_usage, JsonObject):
                usage.update(final_usage)
        elif kind == "error":
            raise ProviderProtocolError(code="anthropic_stream_error")
        elif kind == "message_stop":
            stopped = True
    if not stopped:
        raise ProviderProtocolError(code="anthropic_stream_completion_missing")
    content: list[dict[str, object]] = []
    for index in sorted(blocks):
        completed_block = blocks[index]
        if completed_block.get("type") == "text":
            content.append({"type": "text", "text": completed_block["text"]})
        elif completed_block.get("type") == "tool_use":
            completed_partial = completed_block.get("partial_input")
            parsed = _decode_object(
                completed_partial
                if isinstance(completed_partial, str) and completed_partial
                else "{}"
            )
            content.append(
                {
                    "type": "tool_use",
                    "name": completed_block["name"],
                    **({"id": completed_block["id"]} if "id" in completed_block else {}),
                    "input": parsed,
                }
            )
    value: dict[str, object] = {"content": content}
    if remote_id is not None:
        value["id"] = remote_id
    if usage:
        value["usage"] = usage
    frozen = freeze_json(value)
    assert isinstance(frozen, JsonObject)
    return frozen


def _final_payload(response: HttpResponse) -> tuple[JsonObject, bool]:
    if not 200 <= response.status <= 299:
        raise ProviderResponseError(status=response.status)
    if response.events:
        return _stream_payload(response), True
    return _decode_object(response.body), False


def normalize_anthropic_response(
    payload: JsonObject,
    *,
    request: ModelRequest,
    model: str,
    streamed: bool = False,
) -> ModelProposal:
    """Normalize one complete Messages payload with request-owned identity."""

    content = payload.get("content")
    if not isinstance(content, JsonArray):
        raise ProviderProtocolError(code="anthropic_content_invalid")
    calls: list[ProviderToolCall] = []
    texts: list[str] = []
    for item in content:
        if not isinstance(item, JsonObject):
            raise ProviderProtocolError(code="anthropic_content_item_invalid")
        item_type = item.get("type")
        if item_type == "tool_use":
            name = item.get("name")
            call_id = item.get("id", MISSING)
            arguments = item.get("input")
            if (
                not isinstance(name, str)
                or not isinstance(arguments, JsonObject)
                or (call_id not in (MISSING, None) and not isinstance(call_id, str))
            ):
                raise ProviderProtocolError(code="anthropic_tool_use_invalid")
            calls.append(ProviderToolCall(name=name, arguments=arguments, call_id=call_id))
        elif item_type == "text":
            text = item.get("text")
            if not isinstance(text, str):
                raise ProviderProtocolError(code="anthropic_text_invalid")
            texts.append(text)
    return normalize_provider_output(
        model_call_id=request.model_call_id,
        provider="anthropic",
        text="\n".join(texts),
        tool_calls=tuple(calls),
        metadata=_metadata(payload, model, streamed=streamed),
    )


@final
class AnthropicMessagesProvider:
    """Direct Anthropic Messages provider with explicit credentials and lifetime."""

    __slots__ = (
        "_api_key",
        "_base_url",
        "_closed",
        "_max_tokens",
        "_model",
        "_owned_transport",
        "_stream",
        "_timeout_ms",
        "_tools",
        "_transport",
    )
    provider = "anthropic"

    def __init__(
        self,
        *,
        api_key: str,
        model: str,
        base_url: str = "https://api.anthropic.com/v1",
        max_tokens: int = 1_024,
        tools: tuple[ProviderTool, ...] = (),
        transport: AsyncHttpTransport | None = None,
        stream: bool = True,
        timeout_ms: int = 60_000,
    ) -> None:
        self._api_key = _text(api_key, "provider_api_key_invalid")
        self._model = _text(model, "provider_model_invalid")
        self._base_url = _text(base_url, "provider_base_url_invalid").rstrip("/")
        if isinstance(max_tokens, bool) or not isinstance(max_tokens, int) or max_tokens < 1:
            raise ValidationError(code="anthropic_max_tokens_invalid")
        self._max_tokens = max_tokens
        try:
            self._tools = tuple(tools)
        except TypeError as error:
            raise ValidationError(code="provider_tools_invalid") from error
        if any(not isinstance(item, ProviderTool) for item in self._tools):
            raise ValidationError(code="provider_tools_invalid")
        if not isinstance(stream, bool):
            raise ValidationError(code="provider_stream_invalid")
        if isinstance(timeout_ms, bool) or not isinstance(timeout_ms, int) or timeout_ms < 1:
            raise ValidationError(code="provider_timeout_invalid")
        self._stream = stream
        self._timeout_ms = timeout_ms
        self._owned_transport = transport is None
        self._transport = StdlibHttpTransport() if transport is None else transport
        if not callable(getattr(self._transport, "request", None)):
            raise ValidationError(code="provider_transport_invalid")
        self._closed = False
        HttpRequest(url=f"{self._base_url}/messages", body=b"{}")

    async def __aenter__(self) -> Self:
        if self._closed:
            raise ProviderTransportError(code="provider_closed")
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: object | None,
    ) -> None:
        await self.aclose()

    async def aclose(self) -> None:
        if self._closed:
            return
        self._closed = True
        if self._owned_transport:
            close = getattr(self._transport, "aclose", None)
            if callable(close):
                await close()

    async def propose(self, request: ModelRequest, /) -> ModelProposal:
        if self._closed:
            raise ProviderTransportError(code="provider_closed")
        if not isinstance(request, ModelRequest):
            raise ValidationError(code="provider_request_invalid")
        context = _content_context(request)
        body: dict[str, object] = {
            "model": self._model,
            "max_tokens": self._max_tokens,
            "messages": [{"role": "user", "content": _wire(context).decode("utf-8")}],
            "stream": self._stream,
        }
        if self._tools:
            body["tools"] = _tools(self._tools)
        response = await self._transport.request(
            HttpRequest(
                url=f"{self._base_url}/messages",
                body=_wire(body),
                headers=(
                    ("content-type", "application/json"),
                    ("accept", "text/event-stream" if self._stream else "application/json"),
                    ("x-api-key", self._api_key),
                    ("anthropic-version", "2023-06-01"),
                ),
                timeout_ms=self._timeout_ms,
            )
        )
        payload, streamed = _final_payload(response)
        return normalize_anthropic_response(
            payload,
            request=request,
            model=self._model,
            streamed=streamed,
        )
