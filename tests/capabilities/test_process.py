from __future__ import annotations

import asyncio
import hashlib
import json
import os
import signal
import sys
from pathlib import Path

import pytest

from openrund.capabilities import (
    CapabilityRegistry,
    FilesystemMount,
    ProcessBinding,
    ProcessCapability,
    ProcessEnvironmentRule,
)
from openrund.contracts.capabilities import CapabilityAccessMode, CapabilityResult
from openrund.contracts.content import Content
from openrund.contracts.ids import ActionId, CapabilityId
from openrund.contracts.json import JsonObject
from openrund.errors import CapabilityExecutionError, CapabilityProtocolError
from openrund.ports.capabilities import CapabilityInvocation


def _capability(
    root: Path,
    *,
    max_arguments: int = 32,
    max_argument_chars: int = 8_192,
    max_stdin_bytes: int = 4_096,
    max_output_bytes: int = 4_096,
    default_timeout_ms: int = 2_000,
    max_timeout_ms: int = 5_000,
    terminate_grace_ms: int = 100,
) -> ProcessCapability:
    return ProcessCapability(
        mounts=(
            FilesystemMount(
                name="workspace",
                root=root,
                access=CapabilityAccessMode.READ_WRITE,
            ),
        ),
        bindings=(
            ProcessBinding(
                name="python",
                executable=Path(sys.executable).resolve(),
                environment=(("PYTHONUTF8", "1"),),
                allowed_environment=(
                    ProcessEnvironmentRule(name="OPENRUND_MODE", allowed_values=("safe",)),
                ),
            ),
        ),
        max_arguments=max_arguments,
        max_argument_chars=max_argument_chars,
        max_stdin_bytes=max_stdin_bytes,
        max_output_bytes=max_output_bytes,
        default_timeout_ms=default_timeout_ms,
        max_timeout_ms=max_timeout_ms,
        terminate_grace_ms=terminate_grace_ms,
    )


def _invocation(data: dict[str, object]) -> CapabilityInvocation:
    return CapabilityInvocation(
        action_id=ActionId(value="action-process"),
        capability_id=CapabilityId(value="process"),
        action_name="run",
        input=Content(data=data),  # type: ignore[arg-type]
    )


def _invoke(capability: ProcessCapability, data: dict[str, object]) -> CapabilityResult:
    registry = CapabilityRegistry((capability.registered(),))
    return asyncio.run(registry.invoke(_invocation(data)))


def _output(result: CapabilityResult) -> JsonObject:
    assert isinstance(result.output, JsonObject)
    return result.output


def _alive(process_id: int) -> bool:
    try:
        os.kill(process_id, 0)
    except ProcessLookupError:
        return False
    return True


def test_process_runs_bound_executable_with_cwd_stdin_and_artifacts(tmp_path: Path) -> None:
    work = tmp_path / "work"
    work.mkdir()
    capability = _capability(tmp_path)
    result = _invoke(
        capability,
        {
            "executable": "python",
            "args": [
                "-c",
                "import os,sys; print(os.getcwd()); print(sys.stdin.read())",
            ],
            "cwdMount": "workspace",
            "cwdPath": "work",
            "stdin": "input text",
        },
    )

    stdout = result.inline_artifacts[0].content
    output = _output(result)
    assert output["exitCode"] == 0
    assert output["signal"] is None
    assert output["timedOut"] is False
    assert output["stdoutSha256"] == hashlib.sha256(stdout).hexdigest()
    assert str(work) in stdout.decode()
    assert "input text" in stdout.decode()
    assert [artifact.kind for artifact in result.inline_artifacts] == [
        "process.stdout",
        "process.stderr",
    ]
    assert result.effects[0].kind == "process.exited"


def test_process_bounds_and_hashes_complete_stdout_and_stderr(tmp_path: Path) -> None:
    capability = _capability(tmp_path, max_output_bytes=64)
    result = _invoke(
        capability,
        {
            "executable": "python",
            "args": [
                "-c",
                "import sys; sys.stdout.write('x'*5000); sys.stderr.write('y'*3000)",
            ],
            "cwdMount": "workspace",
        },
    )

    output = _output(result)
    assert output["stdoutBytes"] == 5_000
    assert output["stderrBytes"] == 3_000
    assert output["stdoutTruncated"] is True
    assert output["stderrTruncated"] is True
    assert output["stdoutSha256"] == hashlib.sha256(b"x" * 5_000).hexdigest()
    assert output["stderrSha256"] == hashlib.sha256(b"y" * 3_000).hexdigest()
    assert result.inline_artifacts[0].content == b"x" * 64
    assert result.inline_artifacts[1].content == b"y" * 64


def test_process_security_environment_is_explicit_and_value_allowlisted(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "must-not-leak")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "must-not-leak")
    capability = _capability(tmp_path)
    script = (
        "import json,os; print(json.dumps({"
        "'path': os.getenv('PATH'),"
        "'openai': os.getenv('OPENAI_API_KEY'),"
        "'aws': os.getenv('AWS_SECRET_ACCESS_KEY'),"
        "'mode': os.getenv('OPENRUND_MODE'),"
        "'utf8': os.getenv('PYTHONUTF8')}))"
    )
    result = _invoke(
        capability,
        {
            "executable": "python",
            "args": ["-c", script],
            "cwdMount": "workspace",
            "env": {"OPENRUND_MODE": "safe"},
        },
    )
    observed = json.loads(result.inline_artifacts[0].content)
    assert observed == {
        "path": None,
        "openai": None,
        "aws": None,
        "mode": "safe",
        "utf8": "1",
    }

    with pytest.raises(CapabilityExecutionError, match="process_environment_forbidden"):
        _invoke(
            capability,
            {
                "executable": "python",
                "args": ["-c", "pass"],
                "cwdMount": "workspace",
                "env": {"SECRET": "no"},
            },
        )
    with pytest.raises(CapabilityExecutionError, match="process_environment_value_forbidden"):
        _invoke(
            capability,
            {
                "executable": "python",
                "args": ["-c", "pass"],
                "cwdMount": "workspace",
                "env": {"OPENRUND_MODE": "unsafe"},
            },
        )


def test_process_security_shell_metacharacters_are_inert_arguments(tmp_path: Path) -> None:
    capability = _capability(tmp_path)
    target = tmp_path / "must-not-exist"
    literal = f"; touch {target}"
    result = _invoke(
        capability,
        {
            "executable": "python",
            "args": ["-c", "import sys; print(sys.argv[1])", literal],
            "cwdMount": "workspace",
        },
    )
    assert result.inline_artifacts[0].content.decode().strip() == literal
    assert not target.exists()

    registry = CapabilityRegistry((capability.registered(),))
    with pytest.raises(CapabilityProtocolError, match="capability_input_schema_violation"):
        asyncio.run(
            registry.invoke(
                _invocation(
                    {
                        "executable": "python",
                        "cwdMount": "workspace",
                        "shell": True,
                    }
                )
            )
        )


def test_process_security_rejects_unbound_network_tools_and_bad_arguments(
    tmp_path: Path,
) -> None:
    capability = _capability(tmp_path, max_arguments=2, max_argument_chars=8)
    registry = CapabilityRegistry((capability.registered(),))
    invalid_inputs: tuple[dict[str, object], ...] = (
        {"executable": "curl", "cwdMount": "workspace"},
        {"executable": "python", "args": ["1", "2", "3"], "cwdMount": "workspace"},
        {"executable": "python", "args": ["too-long-value"], "cwdMount": "workspace"},
    )
    for data in invalid_inputs:
        with pytest.raises(CapabilityProtocolError, match="capability_input_schema_violation"):
            asyncio.run(registry.invoke(_invocation(data)))

    with pytest.raises(CapabilityExecutionError, match="process_argument_invalid"):
        _invoke(
            _capability(tmp_path),
            {
                "executable": "python",
                "args": ["nul\x00argument"],
                "cwdMount": "workspace",
            },
        )


def test_process_security_rejects_cwd_escape_symlink_and_read_only_mount(
    tmp_path: Path,
) -> None:
    root = tmp_path / "root"
    root.mkdir()
    outside = tmp_path / "outside"
    outside.mkdir()
    (root / "linked").symlink_to(outside, target_is_directory=True)
    capability = _capability(root)

    with pytest.raises(CapabilityExecutionError, match="filesystem_path_invalid"):
        _invoke(
            capability,
            {"executable": "python", "cwdMount": "workspace", "cwdPath": "../outside"},
        )
    with pytest.raises(CapabilityExecutionError, match="filesystem_symlink_forbidden"):
        _invoke(
            capability,
            {"executable": "python", "cwdMount": "workspace", "cwdPath": "linked"},
        )

    read_only = ProcessCapability(
        mounts=(FilesystemMount(name="workspace", root=root, access=CapabilityAccessMode.READ),),
        bindings=(ProcessBinding(name="python", executable=Path(sys.executable).resolve()),),
    )
    with pytest.raises(CapabilityExecutionError, match="filesystem_mount_read_only"):
        _invoke(read_only, {"executable": "python", "cwdMount": "workspace"})


def test_process_rejects_oversized_stdin_before_spawn(tmp_path: Path) -> None:
    capability = _capability(tmp_path, max_stdin_bytes=4)
    with pytest.raises(CapabilityExecutionError, match="process_stdin_too_large"):
        _invoke(
            capability,
            {
                "executable": "python",
                "args": ["-c", "import sys; sys.stdin.read()"],
                "cwdMount": "workspace",
                "stdin": "12345",
            },
        )


def test_process_timeout_escalates_to_kill_and_reaps_child(tmp_path: Path) -> None:
    pid_file = tmp_path / "timeout.pid"
    capability = _capability(
        tmp_path,
        default_timeout_ms=250,
        max_timeout_ms=1_000,
        terminate_grace_ms=50,
    )
    script = (
        "import os,pathlib,signal,time;"
        "signal.signal(signal.SIGTERM, signal.SIG_IGN);"
        "pathlib.Path('timeout.pid').write_text(str(os.getpid()));"
        "time.sleep(10)"
    )
    result = _invoke(
        capability,
        {
            "executable": "python",
            "args": ["-c", script],
            "cwdMount": "workspace",
            "timeoutMs": 250,
        },
    )

    process_id = int(pid_file.read_text(encoding="utf-8"))
    assert _output(result)["timedOut"] is True
    assert _output(result)["signal"] == signal.SIGKILL
    assert result.effects[0].kind == "process.timed_out"
    assert not _alive(process_id)


def test_process_cancel_terminates_and_reaps_child(tmp_path: Path) -> None:
    pid_file = tmp_path / "cancel.pid"
    capability = _capability(tmp_path, default_timeout_ms=5_000, terminate_grace_ms=50)
    registry = CapabilityRegistry((capability.registered(),))
    invocation = _invocation(
        {
            "executable": "python",
            "args": [
                "-c",
                "import os,pathlib,time; "
                "pathlib.Path('cancel.pid').write_text(str(os.getpid())); time.sleep(10)",
            ],
            "cwdMount": "workspace",
        }
    )

    async def cancel_after_start() -> None:
        task = asyncio.create_task(registry.invoke(invocation))
        for _attempt in range(200):
            if pid_file.exists():
                break
            await asyncio.sleep(0.005)
        assert pid_file.exists()
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task

    asyncio.run(cancel_after_start())
    process_id = int(pid_file.read_text(encoding="utf-8"))
    assert not _alive(process_id)


def test_process_reports_signal_exit(tmp_path: Path) -> None:
    capability = _capability(tmp_path)
    result = _invoke(
        capability,
        {
            "executable": "python",
            "args": [
                "-c",
                "import os,signal; os.kill(os.getpid(), signal.SIGTERM)",
            ],
            "cwdMount": "workspace",
        },
    )
    assert _output(result)["exitCode"] is None
    assert _output(result)["signal"] == signal.SIGTERM
    assert result.effects[0].kind == "process.signalled"


def test_process_spawn_failure_is_safe(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    capability = _capability(tmp_path)

    async def fail_spawn(*_args: object, **_kwargs: object) -> object:
        raise OSError("sensitive local failure")

    monkeypatch.setattr(asyncio, "create_subprocess_exec", fail_spawn)
    with pytest.raises(CapabilityExecutionError, match="process_spawn_failed") as captured:
        _invoke(capability, {"executable": "python", "cwdMount": "workspace"})
    assert "sensitive local failure" not in str(captured.value)
