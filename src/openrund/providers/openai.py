"""OpenAI Responses and local OpenAI-compatible providers over direct async HTTP."""

from __future__ import annotations

import json
from dataclasses import dataclass
from enum import StrEnum
from typing import Self, final

from openrund.codec import encode_json_value
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
    parse_provider_tool_arguments,
)


def _text(value: object, code: str) -> str:
    if not isinstance(value, str) or value == "" or "\x00" in value:
        raise ValidationError(code=code)
    return value


def _decode_object(data: bytes | str) -> JsonObject:
    try:
        text = data.decode("utf-8", errors="strict") if isinstance(data, bytes) else data
        value = json.loads(
            text,
            object_pairs_hook=_unique_object,
            parse_constant=_reject_constant,
        )
        frozen = freeze_json(value)
    except (UnicodeError, ValueError, TypeError, RecursionError, ValidationError):
        raise ProviderProtocolError(code="provider_response_json_invalid") from None
    if not isinstance(frozen, JsonObject):
        raise ProviderProtocolError(code="provider_response_object_required")
    return frozen


def _unique_object(pairs: list[tuple[str, object]]) -> dict[str, object]:
    value: dict[str, object] = {}
    for key, item in pairs:
        if key in value:
            raise ValueError("duplicate key")
        value[key] = item
    return value


def _reject_constant(_value: str) -> object:
    raise ValueError("non-finite number")


def _wire(value: object) -> bytes:
    return encode_json_value(freeze_json(value))[:-1]


def _content_context(request: ModelRequest) -> JsonObject:
    context = request.context
    value: dict[str, object] = {
        "runId": request.run_id.value,
        "remainingRequests": request.remaining_requests,
    }
    if isinstance(context.preview, str):
        value["preview"] = context.preview
    if isinstance(context.data, JsonObject):
        value["data"] = context.data
    if context.artifact_ids:
        value["artifactIds"] = [item.value for item in context.artifact_ids]
    if isinstance(context.metadata, JsonObject):
        value["metadata"] = context.metadata
    frozen = freeze_json(value)
    assert isinstance(frozen, JsonObject)
    return frozen


def _tools(tools: tuple[ProviderTool, ...]) -> list[dict[str, object]]:
    return [
        {
            "type": "function",
            "name": tool.name,
            "description": tool.description,
            "parameters": tool.input_schema,
            "strict": True,
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
        for name in ("input_tokens", "output_tokens", "total_tokens"):
            token_count = usage.get(name)
            if (
                isinstance(token_count, int)
                and not isinstance(token_count, bool)
                and token_count >= 0
            ):
                compact[name] = token_count
        if compact:
            value["usage"] = compact
    frozen = freeze_json(value)
    assert isinstance(frozen, JsonObject)
    return frozen


def _final_payload(response: HttpResponse) -> tuple[JsonObject, bool]:
    if not 200 <= response.status <= 299:
        raise ProviderResponseError(status=response.status)
    if not response.events:
        return _decode_object(response.body), False
    final: JsonObject | None = None
    for event in response.events:
        if event.data == "[DONE]":
            continue
        item = _decode_object(event.data)
        kind = item.get("type")
        if event.event in {"response.completed", "response.done"} or kind in {
            "response.completed",
            "response.done",
        }:
            nested = item.get("response")
            final = nested if isinstance(nested, JsonObject) else item
    if final is None:
        raise ProviderProtocolError(code="openai_stream_completion_missing")
    return final, True


def normalize_openai_response(
    payload: JsonObject,
    *,
    request: ModelRequest,
    provider: str,
    model: str,
    streamed: bool = False,
) -> ModelProposal:
    """Normalize one complete Responses payload with request-owned identity."""

    output = payload.get("output")
    if output is None:
        raise ProviderProtocolError(code="openai_output_missing")
    if not isinstance(output, JsonArray):
        raise ProviderProtocolError(code="openai_output_invalid")
    calls: list[ProviderToolCall] = []
    texts: list[str] = []
    for item in output:
        if not isinstance(item, JsonObject):
            raise ProviderProtocolError(code="openai_output_item_invalid")
        item_type = item.get("type")
        if item_type == "function_call":
            name = item.get("name")
            arguments = item.get("arguments")
            call_id = item.get("call_id", MISSING)
            if not isinstance(name, str) or not isinstance(arguments, str):
                raise ProviderProtocolError(code="openai_function_call_invalid")
            if call_id not in (MISSING, None) and not isinstance(call_id, str):
                raise ProviderProtocolError(code="openai_function_call_invalid")
            calls.append(
                ProviderToolCall(
                    name=name,
                    arguments=parse_provider_tool_arguments(arguments),
                    call_id=call_id,
                )
            )
        elif item_type == "message":
            content = item.get("content")
            if not isinstance(content, JsonArray):
                raise ProviderProtocolError(code="openai_message_content_invalid")
            for part in content:
                if not isinstance(part, JsonObject):
                    raise ProviderProtocolError(code="openai_message_part_invalid")
                if part.get("type") == "output_text":
                    text = part.get("text")
                    if not isinstance(text, str):
                        raise ProviderProtocolError(code="openai_message_text_invalid")
                    texts.append(text)
    return normalize_provider_output(
        model_call_id=request.model_call_id,
        provider=provider,
        text="\n".join(texts),
        tool_calls=tuple(calls),
        metadata=_metadata(payload, model, streamed=streamed),
    )


@final
@dataclass(frozen=True, slots=True, kw_only=True)
class LocalModelDescription:
    profile: str
    default_model: str
    target_hardware: str
    model: str


class LocalModelProfile(StrEnum):
    STRONG = "strong"
    FALLBACK = "fallback"


_LOCAL_PROFILES = {
    LocalModelProfile.STRONG: ("mistral-small-3.1", "32GB-class laptop"),
    LocalModelProfile.FALLBACK: ("llama-3.2-3b", "8GB-16GB laptop"),
}


class _ResponsesProvider:
    _api_key: str | None

    __slots__ = (
        "_api_key",
        "_base_url",
        "_closed",
        "_model",
        "_owned_transport",
        "_stream",
        "_timeout_ms",
        "_tools",
        "_transport",
        "provider",
    )

    def __init__(
        self,
        *,
        provider: str,
        model: str,
        base_url: str,
        api_key: str | None,
        tools: tuple[ProviderTool, ...],
        transport: AsyncHttpTransport | None,
        stream: bool,
        timeout_ms: int,
    ) -> None:
        self.provider = _text(provider, "provider_name_invalid")
        self._model = _text(model, "provider_model_invalid")
        self._base_url = _text(base_url, "provider_base_url_invalid").rstrip("/")
        if api_key is not None:
            self._api_key = _text(api_key, "provider_api_key_invalid")
        else:
            self._api_key = None
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
        HttpRequest(url=f"{self._base_url}/responses", body=b"{}")

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
            "input": [
                {
                    "role": "user",
                    "content": [{"type": "input_text", "text": _wire(context).decode("utf-8")}],
                }
            ],
            "stream": self._stream,
        }
        if self._tools:
            body["tools"] = _tools(self._tools)
        headers: list[tuple[str, str]] = [
            ("content-type", "application/json"),
            ("accept", "text/event-stream" if self._stream else "application/json"),
        ]
        if self._api_key is not None:
            headers.append(("authorization", f"Bearer {self._api_key}"))
        response = await self._transport.request(
            HttpRequest(
                url=f"{self._base_url}/responses",
                body=_wire(body),
                headers=tuple(headers),
                timeout_ms=self._timeout_ms,
            )
        )
        payload, streamed = _final_payload(response)
        return normalize_openai_response(
            payload,
            request=request,
            provider=self.provider,
            model=self._model,
            streamed=streamed,
        )


@final
class OpenAIResponsesProvider(_ResponsesProvider):
    """Direct OpenAI Responses provider with explicit credentials."""

    def __init__(
        self,
        *,
        api_key: str,
        model: str,
        base_url: str = "https://api.openai.com/v1",
        tools: tuple[ProviderTool, ...] = (),
        transport: AsyncHttpTransport | None = None,
        stream: bool = True,
        timeout_ms: int = 60_000,
    ) -> None:
        super().__init__(
            provider="openai",
            model=model,
            base_url=base_url,
            api_key=api_key,
            tools=tools,
            transport=transport,
            stream=stream,
            timeout_ms=timeout_ms,
        )


@final
class LocalOpenAICompatibleProvider(_ResponsesProvider):
    """Explicit local Responses-compatible provider with no ambient credentials."""

    __slots__ = ("_description",)

    def __init__(
        self,
        *,
        base_url: str,
        profile: LocalModelProfile,
        model: str | None = None,
        api_key: str | None = None,
        tools: tuple[ProviderTool, ...] = (),
        transport: AsyncHttpTransport | None = None,
        stream: bool = False,
        timeout_ms: int = 60_000,
    ) -> None:
        if not isinstance(profile, LocalModelProfile):
            raise ValidationError(code="local_provider_profile_invalid")
        default_model, target_hardware = _LOCAL_PROFILES[profile]
        selected = default_model if model is None else model
        super().__init__(
            provider="local-openai-compatible",
            model=selected,
            base_url=base_url,
            api_key=api_key,
            tools=tools,
            transport=transport,
            stream=stream,
            timeout_ms=timeout_ms,
        )
        self._description = LocalModelDescription(
            profile=profile.value,
            default_model=default_model,
            target_hardware=target_hardware,
            model=selected,
        )

    def describe_profile(self) -> LocalModelDescription:
        return self._description
