from __future__ import annotations

import asyncio
import sys
from pathlib import Path

import pytest

from openrund.capabilities import InProcessTransport, StdioJsonRpcConfig, StdioJsonRpcTransport
from openrund.capabilities._transports import decode_capability_result, encode_capability_result
from openrund.contracts.capabilities import CapabilityInlineArtifact, CapabilityResult
from openrund.contracts.content import Content, EffectEntry, EvidenceEntry
from openrund.contracts.ids import ActionId, ArtifactId, CapabilityId
from openrund.contracts.json import freeze_json
from openrund.errors import (
    CapabilityExecutionError,
    CapabilityProtocolError,
    CapabilityTransportError,
    ValidationError,
)
from openrund.ports.capabilities import CapabilityInvocation


def _invocation() -> CapabilityInvocation:
    return CapabilityInvocation(
        action_id=ActionId(value="action-1"),
        capability_id=CapabilityId(value="cap.test"),
        action_name="inspect",
        input=Content(data={"value": "safe"}),  # type: ignore[arg-type]
    )


def _write_worker(path: Path, body: str) -> Path:
    path.write_text(body, encoding="utf-8")
    return path


def _transport(worker: Path, **overrides: object) -> StdioJsonRpcTransport:
    values: dict[str, object] = {
        "command": (sys.executable, str(worker)),
        "timeout_ms": 2_000,
        "max_response_bytes": 32_768,
        "max_stderr_bytes": 1_024,
    }
    values.update(overrides)
    return StdioJsonRpcTransport(StdioJsonRpcConfig(**values))  # type: ignore[arg-type]


def test_capability_result_wire_codec_round_trips_exact_values() -> None:
    result = CapabilityResult(
        output={"ok": True},  # type: ignore[arg-type]
        preview="done",
        effects=(EffectEntry(kind="read", summary="safe"),),
        evidence=(EvidenceEntry(description="checked"),),
        artifact_ids=(ArtifactId(value="existing"),),
        inline_artifacts=(
            CapabilityInlineArtifact(
                kind="receipt",
                content=b"\x00bytes",
                content_type="application/octet-stream",
                metadata={"safe": True},  # type: ignore[arg-type]
            ),
        ),
        metadata={"worker": "test"},  # type: ignore[arg-type]
    )

    decoded = decode_capability_result(encode_capability_result(result))

    assert decoded == result


def test_stdio_transport_invokes_one_strict_json_rpc_request(tmp_path: Path) -> None:
    worker = _write_worker(
        tmp_path / "worker.py",
        """import base64, json, sys
request = json.loads(sys.stdin.readline())
assert request['jsonrpc'] == '2.0'
assert request['method'] == 'capability.invoke'
assert request['params']['input']['data'] == {'value': 'safe'}
response = {
  'jsonrpc': '2.0',
  'id': request['id'],
  'result': {
    'output': {'ok': True},
    'inlineArtifacts': [{
      'kind': 'receipt',
      'contentBase64': base64.b64encode(b'evidence').decode('ascii')
    }]
  }
}
sys.stdout.write(json.dumps(response, separators=(',', ':')) + '\\n')
""",
    )

    result = asyncio.run(_transport(worker).invoke(_invocation()))

    assert result.output == freeze_json({"ok": True})
    assert result.inline_artifacts[0].content == b"evidence"


@pytest.mark.parametrize(
    "response",
    [
        {"jsonrpc": "2.0", "id": "wrong", "result": {}},
        {"jsonrpc": "2.0", "id": "openrund-capability-1", "result": {}, "extra": True},
        {
            "jsonrpc": "2.0",
            "id": "openrund-capability-1",
            "result": {"events": []},
        },
        {
            "jsonrpc": "2.0",
            "id": "openrund-capability-1",
            "result": {},
            "error": {"code": -1, "message": "both"},
        },
    ],
)
def test_stdio_transport_rejects_mismatched_or_authoritative_results(
    tmp_path: Path, response: object
) -> None:
    worker = _write_worker(
        tmp_path / "worker.py",
        "import json, sys\nsys.stdin.readline()\nsys.stdout.write(json.dumps("
        + repr(response)
        + ", separators=(',', ':')) + '\\n')\n",
    )

    with pytest.raises(CapabilityProtocolError):
        asyncio.run(_transport(worker).invoke(_invocation()))


def test_stdio_transport_distinguishes_error_timeout_stderr_and_oversize(tmp_path: Path) -> None:
    rejected = _write_worker(
        tmp_path / "rejected.py",
        """import json, sys
request = json.loads(sys.stdin.readline())
response = {
  'jsonrpc': '2.0',
  'id': request['id'],
  'error': {'code': -32000, 'message': 'no'}
}
sys.stdout.write(json.dumps(response) + '\\n')
""",
    )
    with pytest.raises(CapabilityExecutionError, match="capability_worker_rejected"):
        asyncio.run(_transport(rejected).invoke(_invocation()))

    noisy = _write_worker(
        tmp_path / "noisy.py",
        """import json, sys
request = json.loads(sys.stdin.readline())
sys.stderr.write('noise')
response = {'jsonrpc': '2.0', 'id': request['id'], 'result': {}}
sys.stdout.write(json.dumps(response) + '\\n')
""",
    )
    with pytest.raises(CapabilityProtocolError, match="capability_worker_stderr_forbidden"):
        asyncio.run(_transport(noisy).invoke(_invocation()))

    slow = _write_worker(
        tmp_path / "slow.py",
        "import sys, time\nsys.stdin.readline()\ntime.sleep(5)\n",
    )
    with pytest.raises(CapabilityTransportError, match="capability_worker_timeout"):
        asyncio.run(_transport(slow, timeout_ms=20).invoke(_invocation()))

    large = _write_worker(
        tmp_path / "large.py",
        "import sys\nsys.stdin.readline()\nsys.stdout.write('x' * 10000)\n",
    )
    with pytest.raises(CapabilityProtocolError, match="capability_worker_response_too_large"):
        asyncio.run(_transport(large, max_response_bytes=32).invoke(_invocation()))


def test_in_process_transport_preserves_cancel_and_wraps_handler_failure() -> None:
    async def valid(_invocation: CapabilityInvocation) -> CapabilityResult:
        return CapabilityResult(output={"ok": True})  # type: ignore[arg-type]

    async def invalid(_invocation: CapabilityInvocation) -> CapabilityResult:
        raise RuntimeError("secret detail")

    result = asyncio.run(InProcessTransport(valid).invoke(_invocation()))
    assert result.output == freeze_json({"ok": True})
    with pytest.raises(CapabilityTransportError, match="capability_handler_failed") as captured:
        asyncio.run(InProcessTransport(invalid).invoke(_invocation()))
    assert "secret detail" not in str(captured.value)


def test_stdio_config_requires_absolute_executable_and_explicit_safe_environment() -> None:
    with pytest.raises(ValidationError, match="stdio_transport_executable_not_absolute"):
        StdioJsonRpcConfig(command=("python", "worker.py"))
    with pytest.raises(ValidationError, match="stdio_transport_environment_duplicate"):
        StdioJsonRpcConfig(
            command=(sys.executable, "worker.py"),
            environment=(("SAFE", "1"), ("SAFE", "2")),
        )
