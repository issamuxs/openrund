from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable

import pytest

from openrund.errors import ProviderProtocolError, ProviderTransportError, ValidationError
from openrund.providers import (
    HttpRequest,
    StdlibHttpTransport,
    parse_server_sent_events,
)

type Handler = Callable[[asyncio.StreamReader, asyncio.StreamWriter], Awaitable[None]]


async def _with_server[T](handler: Handler, action: Callable[[str], Awaitable[T]]) -> T:
    server = await asyncio.start_server(handler, "127.0.0.1", 0)
    socket = server.sockets[0]
    host, port = socket.getsockname()[:2]
    try:
        return await action(f"http://{host}:{port}")
    finally:
        server.close()
        await server.wait_closed()


async def _request_head(reader: asyncio.StreamReader) -> tuple[bytes, bytes]:
    head = await reader.readuntil(b"\r\n\r\n")
    length = 0
    for line in head.split(b"\r\n"):
        if line.lower().startswith(b"content-length:"):
            length = int(line.split(b":", 1)[1])
    return head, await reader.readexactly(length)


def test_http_request_validates_url_headers_and_bounds() -> None:
    with pytest.raises(ValidationError, match="provider_http_url_invalid"):
        HttpRequest(url="https://user:secret@example.com/v1", body=b"{}")
    with pytest.raises(ValidationError, match="provider_http_headers_invalid"):
        HttpRequest(url="https://example.com/v1", body=b"{}", headers=(("Host", "evil"),))
    with pytest.raises(ValidationError, match="provider_http_headers_invalid"):
        HttpRequest(url="https://example.com/v1", body=b"{}", headers=(("x", "a\r\nb"),))
    with pytest.raises(ValidationError, match="provider_http_timeout_invalid"):
        HttpRequest(url="https://example.com/v1", body=b"{}", timeout_ms=0)


def test_content_length_response_and_exact_post_request() -> None:
    observed: list[tuple[bytes, bytes]] = []

    async def scenario() -> None:
        async def handler(reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
            observed.append(await _request_head(reader))
            writer.write(
                b"HTTP/1.1 200 OK\r\n"
                b"Content-Type: application/json\r\n"
                b"Content-Length: 11\r\n\r\n"
                b'{"ok":true}'
            )
            await writer.drain()
            writer.close()
            await writer.wait_closed()

        async def call(base_url: str) -> None:
            async with StdlibHttpTransport() as transport:
                response = await transport.request(
                    HttpRequest(
                        url=f"{base_url}/v1/responses?mode=test",
                        body=b'{"input":1}',
                        headers=(("content-type", "application/json"), ("x-test", "fixed")),
                    )
                )
            assert response.status == 200
            assert response.body == b'{"ok":true}'
            assert response.header("Content-Type") == "application/json"
            assert response.events == ()

        await _with_server(handler, call)

    asyncio.run(scenario())
    head, body = observed[0]
    assert head.startswith(b"POST /v1/responses?mode=test HTTP/1.1\r\n")
    assert b"connection: close\r\n" in head.lower()
    assert b"x-test: fixed\r\n" in head.lower()
    assert body == b'{"input":1}'


def test_fragmented_chunked_sse_is_bounded_and_parsed() -> None:
    async def scenario() -> None:
        async def handler(reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
            await _request_head(reader)
            fragments = (
                b"HTTP/1.1 200 OK\r\nContent-Type: text/event-stream\r\n",
                b"Transfer-Encoding: chunked\r\n\r\n",
                b"1A;kind=event\r\nevent: response.completed\n\r\n",
                b'10\r\ndata: {"id":1}\n\n\r\n',
                b"0\r\nX-Trailer: done\r\n\r\n",
            )
            for fragment in fragments:
                writer.write(fragment)
                await writer.drain()
                await asyncio.sleep(0)
            writer.close()
            await writer.wait_closed()

        async def call(base_url: str) -> None:
            async with StdlibHttpTransport() as transport:
                response = await transport.request(HttpRequest(url=base_url, body=b"{}"))
            assert len(response.events) == 1
            assert response.events[0].event == "response.completed"
            assert response.events[0].data == '{"id":1}'

        await _with_server(handler, call)

    asyncio.run(scenario())


def test_sse_parser_handles_comments_multiline_and_strict_fields() -> None:
    events = parse_server_sent_events(
        b": keepalive\r\nevent: message\r\nid: one\r\ndata: first\r\ndata: second\r\n\r\n"
    )

    assert events[0].event == "message"
    assert events[0].event_id == "one"
    assert events[0].data == "first\nsecond"
    with pytest.raises(ProviderProtocolError, match="provider_sse_retry_invalid"):
        parse_server_sent_events(b"retry: soon\n\ndata: value\n\n")
    with pytest.raises(ProviderProtocolError, match="provider_sse_events_too_many"):
        parse_server_sent_events(b"data: one\n\ndata: two\n\n", max_events=1)


@pytest.mark.parametrize(
    ("response", "code"),
    [
        (
            b"HTTP/1.1 200 OK\r\nContent-Length: 10\r\n\r\nshort",
            "provider_http_body_truncated",
        ),
        (
            b"HTTP/1.1 200 OK\r\nContent-Length: 10\r\nTransfer-Encoding: chunked\r\n\r\n",
            "provider_http_body_framing_invalid",
        ),
        (
            b"HTTP/1.1 200 OK\r\nTransfer-Encoding: gzip\r\n\r\n",
            "provider_http_transfer_encoding_invalid",
        ),
    ],
)
def test_malformed_or_truncated_http_fails_with_stable_code(response: bytes, code: str) -> None:
    async def scenario() -> None:
        async def handler(reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
            await _request_head(reader)
            writer.write(response)
            await writer.drain()
            writer.close()
            await writer.wait_closed()

        async def call(base_url: str) -> None:
            async with StdlibHttpTransport() as transport:
                with pytest.raises(ProviderProtocolError) as raised:
                    await transport.request(HttpRequest(url=base_url, body=b"{}"))
            assert raised.value.code == code

        await _with_server(handler, call)

    asyncio.run(scenario())


def test_response_limit_fails_before_unbounded_read() -> None:
    async def scenario() -> None:
        async def handler(reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
            await _request_head(reader)
            writer.write(b"HTTP/1.1 200 OK\r\nContent-Length: 100\r\n\r\n")
            await writer.drain()
            writer.close()
            await writer.wait_closed()

        async def call(base_url: str) -> None:
            async with StdlibHttpTransport() as transport:
                with pytest.raises(
                    ProviderProtocolError,
                    match="provider_http_response_too_large",
                ):
                    await transport.request(
                        HttpRequest(url=base_url, body=b"{}", max_response_bytes=8)
                    )

        await _with_server(handler, call)

    asyncio.run(scenario())


def test_timeout_and_context_exit_cancel_active_request_without_orphan_task() -> None:
    handler_started = asyncio.Event()

    async def scenario() -> None:
        async def handler(reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
            await _request_head(reader)
            handler_started.set()
            try:
                await reader.read()
            finally:
                writer.close()
                await writer.wait_closed()

        async def call(base_url: str) -> None:
            transport = StdlibHttpTransport()
            request = HttpRequest(url=base_url, body=b"{}", timeout_ms=10_000)
            task = asyncio.create_task(transport.request(request))
            await handler_started.wait()
            await transport.aclose()
            with pytest.raises(asyncio.CancelledError):
                await task
            with pytest.raises(ProviderTransportError, match="provider_http_transport_closed"):
                await transport.request(request)

        await _with_server(handler, call)

    asyncio.run(scenario())


def test_timeout_uses_safe_transport_error() -> None:
    async def scenario() -> None:
        async def handler(reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
            await _request_head(reader)
            await asyncio.sleep(1)
            writer.close()
            await writer.wait_closed()

        async def call(base_url: str) -> None:
            async with StdlibHttpTransport() as transport:
                with pytest.raises(ProviderTransportError) as raised:
                    await transport.request(HttpRequest(url=base_url, body=b"{}", timeout_ms=10))
            assert raised.value.code == "provider_http_timeout"
            assert base_url not in str(raised.value)

        await _with_server(handler, call)

    asyncio.run(scenario())
