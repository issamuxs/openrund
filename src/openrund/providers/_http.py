"""Bounded dependency-free async HTTP/1.1 and server-sent event transport."""

from __future__ import annotations

import asyncio
import re
import ssl
from contextlib import suppress
from dataclasses import dataclass
from typing import Final, Protocol, Self, final
from urllib.parse import SplitResult, urlsplit

from openrund.errors import ProviderProtocolError, ProviderTransportError, ValidationError

_HEADER_NAME: Final = re.compile(r"^[!#$%&'*+\-.^_`|~0-9A-Za-z]+$")
_MAX_HEADER_LINE: Final = 8 * 1024
_MAX_HEADERS: Final = 100
_RESERVED_REQUEST_HEADERS: Final = frozenset(
    {"connection", "content-length", "host", "transfer-encoding"}
)


def _positive_integer(value: object, code: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        raise ValidationError(code=code)
    return value


def _header_pairs(value: object) -> tuple[tuple[str, str], ...]:
    try:
        pairs: tuple[object, ...] = tuple(value)  # type: ignore[arg-type]
    except TypeError as error:
        raise ValidationError(code="provider_http_headers_invalid") from error
    normalized: list[tuple[str, str]] = []
    seen: set[str] = set()
    for pair in pairs:
        if not isinstance(pair, tuple) or len(pair) != 2:
            raise ValidationError(code="provider_http_headers_invalid")
        name, header_value = pair
        if (
            not isinstance(name, str)
            or not _HEADER_NAME.fullmatch(name)
            or not isinstance(header_value, str)
            or "\r" in header_value
            or "\n" in header_value
            or "\x00" in header_value
        ):
            raise ValidationError(code="provider_http_headers_invalid")
        lowered = name.lower()
        if lowered in seen or lowered in _RESERVED_REQUEST_HEADERS:
            raise ValidationError(code="provider_http_headers_invalid")
        seen.add(lowered)
        normalized.append((lowered, header_value))
    return tuple(normalized)


def _url(value: object) -> str:
    if not isinstance(value, str) or value == "":
        raise ValidationError(code="provider_http_url_invalid")
    try:
        parsed = urlsplit(value)
        _endpoint(parsed)
    except (ValueError, TypeError):
        raise ValidationError(code="provider_http_url_invalid") from None
    return value


def _endpoint(parsed: SplitResult) -> tuple[str, int, bool, str]:
    if (
        parsed.scheme not in {"http", "https"}
        or parsed.hostname is None
        or parsed.username is not None
        or parsed.password is not None
        or parsed.fragment != ""
    ):
        raise ValueError("invalid endpoint")
    host = parsed.hostname
    if "\x00" in host or "\r" in host or "\n" in host:
        raise ValueError("invalid host")
    secure = parsed.scheme == "https"
    port = parsed.port or (443 if secure else 80)
    target = parsed.path or "/"
    if parsed.query:
        target += f"?{parsed.query}"
    if any(character in target for character in "\r\n\x00"):
        raise ValueError("invalid target")
    return host, port, secure, target


@final
@dataclass(frozen=True, slots=True, kw_only=True)
class HttpRequest:
    url: str
    body: bytes
    headers: tuple[tuple[str, str], ...] = ()
    timeout_ms: int = 60_000
    max_response_bytes: int = 8 * 1024 * 1024

    def __post_init__(self) -> None:
        object.__setattr__(self, "url", _url(self.url))
        if not isinstance(self.body, bytes):
            raise ValidationError(code="provider_http_body_invalid")
        object.__setattr__(self, "headers", _header_pairs(self.headers))
        object.__setattr__(
            self,
            "timeout_ms",
            _positive_integer(self.timeout_ms, "provider_http_timeout_invalid"),
        )
        object.__setattr__(
            self,
            "max_response_bytes",
            _positive_integer(
                self.max_response_bytes,
                "provider_http_response_limit_invalid",
            ),
        )


@final
@dataclass(frozen=True, slots=True, kw_only=True)
class ServerSentEvent:
    data: str
    event: str | None = None
    event_id: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.data, str):
            raise ValidationError(code="provider_sse_data_invalid")
        for name in ("event", "event_id"):
            value = getattr(self, name)
            if value is not None and not isinstance(value, str):
                raise ValidationError(code="provider_sse_field_invalid")


@final
@dataclass(frozen=True, slots=True, kw_only=True)
class HttpResponse:
    status: int
    headers: tuple[tuple[str, str], ...]
    body: bytes
    events: tuple[ServerSentEvent, ...] = ()

    def __post_init__(self) -> None:
        if isinstance(self.status, bool) or not isinstance(self.status, int):
            raise ValidationError(code="provider_http_status_invalid")
        object.__setattr__(self, "headers", _header_pairs_response(self.headers))
        if not isinstance(self.body, bytes):
            raise ValidationError(code="provider_http_response_body_invalid")
        events = tuple(self.events)
        if any(not isinstance(item, ServerSentEvent) for item in events):
            raise ValidationError(code="provider_sse_events_invalid")
        object.__setattr__(self, "events", events)

    def header(self, name: str, /) -> str | None:
        lowered = name.lower()
        values = tuple(value for candidate, value in self.headers if candidate == lowered)
        return None if not values else ", ".join(values)


class AsyncHttpTransport(Protocol):
    async def request(self, request: HttpRequest, /) -> HttpResponse: ...


def _header_pairs_response(value: object) -> tuple[tuple[str, str], ...]:
    try:
        pairs: tuple[object, ...] = tuple(value)  # type: ignore[arg-type]
    except TypeError as error:
        raise ValidationError(code="provider_http_response_headers_invalid") from error
    normalized: list[tuple[str, str]] = []
    for pair in pairs:
        if not isinstance(pair, tuple) or len(pair) != 2:
            raise ValidationError(code="provider_http_response_headers_invalid")
        name, header_value = pair
        if not isinstance(name, str) or not isinstance(header_value, str):
            raise ValidationError(code="provider_http_response_headers_invalid")
        normalized.append((name.lower(), header_value))
    return tuple(normalized)


async def _line(reader: asyncio.StreamReader, code: str) -> bytes:
    try:
        line = await reader.readline()
    except (OSError, ValueError, asyncio.LimitOverrunError):
        raise ProviderTransportError(code="provider_http_read_failed") from None
    if not line or len(line) > _MAX_HEADER_LINE or not line.endswith(b"\n"):
        raise ProviderProtocolError(code=code)
    return line


async def _headers(reader: asyncio.StreamReader) -> tuple[tuple[str, str], ...]:
    headers: list[tuple[str, str]] = []
    while True:
        line = await _line(reader, "provider_http_headers_invalid")
        if line in {b"\r\n", b"\n"}:
            return tuple(headers)
        if len(headers) >= _MAX_HEADERS or line[:1] in {b" ", b"\t"} or b":" not in line:
            raise ProviderProtocolError(code="provider_http_headers_invalid")
        raw_name, raw_value = line.rstrip(b"\r\n").split(b":", 1)
        try:
            name = raw_name.decode("ascii").lower()
            value = raw_value.strip(b" \t").decode("latin-1")
        except UnicodeError:
            raise ProviderProtocolError(code="provider_http_headers_invalid") from None
        if not _HEADER_NAME.fullmatch(name) or "\x00" in value:
            raise ProviderProtocolError(code="provider_http_headers_invalid")
        headers.append((name, value))


def _header_values(headers: tuple[tuple[str, str], ...], name: str) -> tuple[str, ...]:
    return tuple(value for candidate, value in headers if candidate == name)


async def _read_exact(reader: asyncio.StreamReader, size: int, code: str) -> bytes:
    try:
        return await reader.readexactly(size)
    except (asyncio.IncompleteReadError, OSError, ValueError):
        raise ProviderProtocolError(code=code) from None


async def _chunked(
    reader: asyncio.StreamReader,
    limit: int,
) -> bytes:
    chunks: list[bytes] = []
    size = 0
    while True:
        line = await _line(reader, "provider_http_chunk_invalid")
        token = line.rstrip(b"\r\n").split(b";", 1)[0]
        try:
            chunk_size = int(token, 16)
        except ValueError:
            raise ProviderProtocolError(code="provider_http_chunk_invalid") from None
        if chunk_size < 0 or size + chunk_size > limit:
            raise ProviderProtocolError(code="provider_http_response_too_large")
        if chunk_size == 0:
            await _headers(reader)
            return b"".join(chunks)
        chunk = await _read_exact(reader, chunk_size, "provider_http_body_truncated")
        if await _read_exact(reader, 2, "provider_http_chunk_invalid") != b"\r\n":
            raise ProviderProtocolError(code="provider_http_chunk_invalid")
        chunks.append(chunk)
        size += chunk_size


async def _to_eof(reader: asyncio.StreamReader, limit: int) -> bytes:
    chunks: list[bytes] = []
    size = 0
    while True:
        try:
            chunk = await reader.read(min(65_536, limit + 1 - size))
        except (OSError, ValueError):
            raise ProviderTransportError(code="provider_http_read_failed") from None
        if not chunk:
            return b"".join(chunks)
        size += len(chunk)
        if size > limit:
            raise ProviderProtocolError(code="provider_http_response_too_large")
        chunks.append(chunk)


async def _body(
    reader: asyncio.StreamReader,
    headers: tuple[tuple[str, str], ...],
    limit: int,
) -> bytes:
    encodings = _header_values(headers, "transfer-encoding")
    lengths = _header_values(headers, "content-length")
    if encodings and lengths:
        raise ProviderProtocolError(code="provider_http_body_framing_invalid")
    if encodings:
        if len(encodings) != 1 or encodings[0].lower() != "chunked":
            raise ProviderProtocolError(code="provider_http_transfer_encoding_invalid")
        return await _chunked(reader, limit)
    if lengths:
        if len(lengths) != 1:
            raise ProviderProtocolError(code="provider_http_content_length_invalid")
        try:
            size = int(lengths[0], 10)
        except ValueError:
            raise ProviderProtocolError(code="provider_http_content_length_invalid") from None
        if size < 0 or size > limit:
            raise ProviderProtocolError(code="provider_http_response_too_large")
        return await _read_exact(reader, size, "provider_http_body_truncated")
    return await _to_eof(reader, limit)


def parse_server_sent_events(
    body: bytes, /, *, max_events: int = 10_000
) -> tuple[ServerSentEvent, ...]:
    _positive_integer(max_events, "provider_sse_event_limit_invalid")
    try:
        text = body.decode("utf-8", errors="strict").replace("\r\n", "\n").replace("\r", "\n")
    except UnicodeDecodeError:
        raise ProviderProtocolError(code="provider_sse_utf8_invalid") from None
    events: list[ServerSentEvent] = []
    data: list[str] = []
    event: str | None = None
    event_id: str | None = None

    def flush() -> None:
        nonlocal data, event, event_id
        if not data:
            event = None
            event_id = None
            return
        if len(events) >= max_events:
            raise ProviderProtocolError(code="provider_sse_events_too_many")
        events.append(ServerSentEvent(data="\n".join(data), event=event, event_id=event_id))
        data = []
        event = None
        event_id = None

    for line in text.split("\n"):
        if line == "":
            flush()
            continue
        if line.startswith(":"):
            continue
        name, separator, value = line.partition(":")
        if separator and value.startswith(" "):
            value = value[1:]
        if name == "data":
            data.append(value)
        elif name == "event":
            event = value
        elif name == "id":
            if "\x00" in value:
                raise ProviderProtocolError(code="provider_sse_id_invalid")
            event_id = value
        elif name == "retry" and not value.isdigit():
            raise ProviderProtocolError(code="provider_sse_retry_invalid")
    flush()
    return tuple(events)


@final
class StdlibHttpTransport:
    """One-request-per-connection transport with explicit task and socket lifetime."""

    __slots__ = ("_active", "_closed")

    def __init__(self) -> None:
        self._active: set[asyncio.Task[HttpResponse]] = set()
        self._closed = False

    async def __aenter__(self) -> Self:
        if self._closed:
            raise ProviderTransportError(code="provider_http_transport_closed")
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
        active = tuple(self._active)
        for task in active:
            task.cancel()
        if active:
            await asyncio.gather(*active, return_exceptions=True)
        self._active.clear()

    async def request(self, request: HttpRequest, /) -> HttpResponse:
        if self._closed:
            raise ProviderTransportError(code="provider_http_transport_closed")
        if not isinstance(request, HttpRequest):
            raise ValidationError(code="provider_http_request_invalid")
        task = asyncio.create_task(self._perform(request))
        self._active.add(task)
        try:
            return await task
        finally:
            self._active.discard(task)

    async def _perform(self, request: HttpRequest) -> HttpResponse:
        parsed = urlsplit(request.url)
        host, port, secure, target = _endpoint(parsed)
        context = ssl.create_default_context() if secure else None
        writer: asyncio.StreamWriter | None = None
        try:
            async with asyncio.timeout(request.timeout_ms / 1_000):
                try:
                    reader, writer = await asyncio.open_connection(
                        host,
                        port,
                        ssl=context,
                        server_hostname=host if secure else None,
                    )
                except (OSError, ssl.SSLError):
                    raise ProviderTransportError(code="provider_http_connect_failed") from None
                authority = host if port in ({443} if secure else {80}) else f"{host}:{port}"
                lines = [
                    f"POST {target} HTTP/1.1\r\n",
                    f"Host: {authority}\r\n",
                    f"Content-Length: {len(request.body)}\r\n",
                    "Connection: close\r\n",
                    *(f"{name}: {value}\r\n" for name, value in request.headers),
                    "\r\n",
                ]
                try:
                    writer.write("".join(lines).encode("latin-1") + request.body)
                    await writer.drain()
                except (OSError, UnicodeError):
                    raise ProviderTransportError(code="provider_http_write_failed") from None
                status_line = await _line(reader, "provider_http_status_invalid")
                try:
                    version, raw_status, _reason = status_line.rstrip(b"\r\n").split(b" ", 2)
                    status = int(raw_status)
                except (ValueError, UnicodeError):
                    raise ProviderProtocolError(code="provider_http_status_invalid") from None
                if version not in {b"HTTP/1.0", b"HTTP/1.1"} or not 100 <= status <= 599:
                    raise ProviderProtocolError(code="provider_http_status_invalid")
                response_headers = await _headers(reader)
                response_body = await _body(
                    reader,
                    response_headers,
                    request.max_response_bytes,
                )
        except TimeoutError:
            raise ProviderTransportError(code="provider_http_timeout") from None
        finally:
            if writer is not None:
                writer.close()
                with suppress(OSError, ConnectionError):
                    await writer.wait_closed()
        content_types = _header_values(response_headers, "content-type")
        events = (
            parse_server_sent_events(response_body)
            if any(value.lower().startswith("text/event-stream") for value in content_types)
            else ()
        )
        return HttpResponse(
            status=status,
            headers=response_headers,
            body=response_body,
            events=events,
        )
