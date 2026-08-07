"""One-request stdio JSON-RPC entry point for root-bound Markdown work."""

from __future__ import annotations

import asyncio
import os
import sys

from openrund.capabilities._transports import (
    decode_invocation,
    encode_capability_result,
)
from openrund.capabilities.documents import (
    MarkdownDocumentsHandler,
    mounts_from_worker_environment,
)
from openrund.codec import decode_json_value, encode_json_value
from openrund.contracts.json import JsonObject, JsonValue, freeze_json
from openrund.errors import CapabilityExecutionError, OpenRundError

_MAX_REQUEST_BYTES = 8 * 1024 * 1024


def _request(value: JsonValue) -> tuple[JsonValue, JsonObject]:
    if not isinstance(value, JsonObject) or set(value) != {
        "jsonrpc",
        "id",
        "method",
        "params",
    }:
        raise CapabilityExecutionError(code="documents_worker_request_invalid")
    identifier = value.get("id")
    params = value.get("params")
    if (
        value.get("jsonrpc") != "2.0"
        or value.get("method") != "capability.invoke"
        or not isinstance(identifier, (str, int))
        or isinstance(identifier, bool)
        or not isinstance(params, JsonObject)
    ):
        raise CapabilityExecutionError(code="documents_worker_request_invalid")
    return identifier, params


def _response(identifier: JsonValue, result: JsonObject) -> bytes:
    value = freeze_json({"jsonrpc": "2.0", "id": identifier, "result": result})
    return encode_json_value(value)


def _error(identifier: JsonValue, code: str) -> bytes:
    value = freeze_json(
        {
            "jsonrpc": "2.0",
            "id": identifier,
            "error": {
                "code": -32000,
                "message": "Capability rejected",
                "data": {"code": code},
            },
        }
    )
    return encode_json_value(value)


def main() -> int:
    raw = sys.stdin.buffer.read(_MAX_REQUEST_BYTES + 1)
    identifier: JsonValue = "openrund-capability-1"
    if len(raw) > _MAX_REQUEST_BYTES:
        sys.stdout.buffer.write(_error(identifier, "documents_worker_request_too_large"))
        return 0
    try:
        value = decode_json_value(raw)
        identifier, params = _request(value)
        invocation = decode_invocation(params)
        roots = os.environ.get("OPENRUND_DOCUMENT_ROOTS")
        if roots is None:
            raise CapabilityExecutionError(code="documents_worker_roots_missing")
        try:
            max_bytes = int(os.environ.get("OPENRUND_DOCUMENT_MAX_BYTES", "8388608"))
            max_diff = int(os.environ.get("OPENRUND_DOCUMENT_MAX_DIFF_BYTES", "2097152"))
        except ValueError:
            raise CapabilityExecutionError(code="documents_worker_limits_invalid") from None
        handler = MarkdownDocumentsHandler(
            mounts=mounts_from_worker_environment(roots),
            max_document_bytes=max_bytes,
            max_diff_bytes=max_diff,
        )
        result = asyncio.run(handler(invocation))
        sys.stdout.buffer.write(_response(identifier, encode_capability_result(result)))
        return 0
    except CapabilityExecutionError as error:
        sys.stdout.buffer.write(_error(identifier, error.code))
        return 0
    except OpenRundError:
        sys.stdout.buffer.write(_error(identifier, "documents_worker_protocol_invalid"))
        return 0
    except Exception:
        sys.stdout.buffer.write(_error(identifier, "documents_worker_internal_error"))
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
