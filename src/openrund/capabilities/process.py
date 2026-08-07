"""Allowlisted, root-bound, resource-bounded local process execution."""

from __future__ import annotations

import asyncio
import base64
import binascii
import contextlib
import hashlib
import os
import re
import stat
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import final

from openrund.capabilities._registry import ActionTransportBinding, RegisteredCapability
from openrund.capabilities._sandbox import FilesystemMount, RootSandbox
from openrund.capabilities._transports import InProcessTransport
from openrund.contracts.capabilities import (
    Capability,
    CapabilityAccessMode,
    CapabilityAction,
    CapabilityArtifact,
    CapabilityCancellation,
    CapabilityInlineArtifact,
    CapabilityReliability,
    CapabilityResult,
    CapabilityTransportKind,
    CapabilityTransportMetadata,
)
from openrund.contracts.content import EffectEntry, EvidenceEntry
from openrund.contracts.ids import CapabilityId
from openrund.contracts.json import JsonArray, JsonObject, freeze_json
from openrund.errors import CapabilityExecutionError, ValidationError
from openrund.paths import PathInput, normalize_local_path
from openrund.ports.capabilities import CapabilityInvocation

_BINDING_NAME = re.compile(r"^[a-z][a-z0-9._-]{0,63}$")
_ENVIRONMENT_NAME = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


def _schema(value: object) -> JsonObject:
    frozen = freeze_json(value)
    assert isinstance(frozen, JsonObject)
    return frozen


def _execution(code: str) -> CapabilityExecutionError:
    return CapabilityExecutionError(code=code)


@final
@dataclass(frozen=True, slots=True, kw_only=True)
class ProcessEnvironmentRule:
    """One input environment key and its complete allowlist of values."""

    name: str
    allowed_values: tuple[str, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.name, str) or _ENVIRONMENT_NAME.fullmatch(self.name) is None:
            raise ValidationError(code="process_environment_name_invalid")
        try:
            values = tuple(self.allowed_values)
        except TypeError as error:
            raise ValidationError(code="process_environment_values_invalid") from error
        if (
            not values
            or any(not isinstance(value, str) or "\x00" in value for value in values)
            or len(set(values)) != len(values)
        ):
            raise ValidationError(code="process_environment_values_invalid")
        object.__setattr__(self, "allowed_values", values)


@final
@dataclass(frozen=True, slots=True, kw_only=True)
class ProcessBinding:
    """A stable name bound to one absolute executable and narrow environment."""

    name: str
    executable: PathInput
    environment: tuple[tuple[str, str], ...] = ()
    allowed_environment: tuple[ProcessEnvironmentRule, ...] = ()
    resolved_executable: Path = field(init=False, repr=False, compare=False)
    executable_identity: tuple[int, int] = field(init=False, repr=False, compare=False)

    def __post_init__(self) -> None:
        if not isinstance(self.name, str) or _BINDING_NAME.fullmatch(self.name) is None:
            raise ValidationError(code="process_binding_name_invalid")
        local = normalize_local_path(self.executable)
        if not local.path.is_absolute() or ".." in local.path.parts:
            raise ValidationError(code="process_executable_invalid")
        try:
            status = local.path.lstat()
            resolved = local.path.resolve(strict=True)
        except OSError as error:
            raise ValidationError(code="process_executable_unavailable") from error
        if (
            stat.S_ISLNK(status.st_mode)
            or not stat.S_ISREG(status.st_mode)
            or not os.access(local.path, os.X_OK)
        ):
            raise ValidationError(code="process_executable_invalid")
        try:
            environment = tuple(self.environment)
            allowed = tuple(self.allowed_environment)
        except TypeError as error:
            raise ValidationError(code="process_binding_environment_invalid") from error
        if any(
            not isinstance(item, tuple)
            or len(item) != 2
            or not isinstance(item[0], str)
            or _ENVIRONMENT_NAME.fullmatch(item[0]) is None
            or not isinstance(item[1], str)
            or "\x00" in item[1]
            for item in environment
        ):
            raise ValidationError(code="process_binding_environment_invalid")
        if len({name for name, _value in environment}) != len(environment):
            raise ValidationError(code="process_binding_environment_duplicate")
        if any(not isinstance(item, ProcessEnvironmentRule) for item in allowed):
            raise ValidationError(code="process_environment_rules_invalid")
        allowed_names = tuple(item.name for item in allowed)
        if len(set(allowed_names)) != len(allowed_names):
            raise ValidationError(code="process_environment_rule_duplicate")
        if set(allowed_names) & {name for name, _value in environment}:
            raise ValidationError(code="process_environment_rule_conflict")
        object.__setattr__(self, "executable", local.raw)
        object.__setattr__(self, "environment", environment)
        object.__setattr__(self, "allowed_environment", allowed)
        object.__setattr__(self, "resolved_executable", resolved)
        object.__setattr__(self, "executable_identity", (status.st_dev, status.st_ino))

    def verify(self) -> Path:
        path = Path(self.executable)
        try:
            status = path.lstat()
            resolved = path.resolve(strict=True)
        except OSError:
            raise _execution("process_executable_changed") from None
        if (
            stat.S_ISLNK(status.st_mode)
            or not stat.S_ISREG(status.st_mode)
            or not os.access(path, os.X_OK)
            or resolved != self.resolved_executable
            or (status.st_dev, status.st_ino) != self.executable_identity
        ):
            raise _execution("process_executable_changed")
        return path

    def child_environment(self, requested: JsonObject | None) -> dict[str, str]:
        environment = dict(self.environment)
        rules = {item.name: item.allowed_values for item in self.allowed_environment}
        if requested is None:
            return environment
        for name, value in requested.entries:
            if not isinstance(value, str):
                raise _execution("process_environment_invalid")
            allowed = rules.get(name)
            if allowed is None:
                raise _execution("process_environment_forbidden")
            if value not in allowed:
                raise _execution("process_environment_value_forbidden")
            environment[name] = value
        return environment


@final
@dataclass(frozen=True, slots=True, kw_only=True)
class _CapturedOutput:
    content: bytes
    byte_length: int
    sha256: str
    truncated: bool


async def _capture_output(stream: asyncio.StreamReader | None, limit: int) -> _CapturedOutput:
    if stream is None:
        raise _execution("process_output_pipe_missing")
    retained = bytearray()
    digest = hashlib.sha256()
    total = 0
    while True:
        chunk = await stream.read(65_536)
        if not chunk:
            return _CapturedOutput(
                content=bytes(retained),
                byte_length=total,
                sha256=digest.hexdigest(),
                truncated=total > len(retained),
            )
        digest.update(chunk)
        total += len(chunk)
        remaining = limit - len(retained)
        if remaining > 0:
            retained.extend(chunk[:remaining])


async def _write_stdin(writer: asyncio.StreamWriter | None, content: bytes) -> None:
    if writer is None:
        raise _execution("process_stdin_pipe_missing")
    try:
        writer.write(content)
        await writer.drain()
    except (BrokenPipeError, ConnectionResetError):
        pass
    finally:
        writer.close()
        with contextlib.suppress(BrokenPipeError, ConnectionResetError):
            await writer.wait_closed()


async def _terminate_and_reap(process: asyncio.subprocess.Process, grace_seconds: float) -> None:
    if process.returncode is not None:
        await process.wait()
        return
    with contextlib.suppress(ProcessLookupError):
        process.terminate()
    try:
        await asyncio.wait_for(process.wait(), timeout=grace_seconds)
    except TimeoutError:
        with contextlib.suppress(ProcessLookupError):
            process.kill()
        await process.wait()


def _data(invocation: CapabilityInvocation) -> JsonObject:
    if not isinstance(invocation.input.data, JsonObject):
        raise _execution("process_input_invalid")
    return invocation.input.data


def _required_text(data: JsonObject, name: str) -> str:
    value = data.get(name)
    if not isinstance(value, str):
        raise _execution("process_input_invalid")
    return value


def _optional_text(data: JsonObject, name: str) -> str | None:
    value = data.get(name)
    if value is None:
        return None
    if not isinstance(value, str):
        raise _execution("process_input_invalid")
    return value


def _preview(content: bytes, limit: int) -> str:
    return content[:limit].decode("utf-8", errors="replace")


@final
@dataclass(frozen=True, slots=True, kw_only=True)
class ProcessCapability:
    mounts: tuple[FilesystemMount, ...]
    bindings: tuple[ProcessBinding, ...]
    max_arguments: int = 128
    max_argument_chars: int = 16_384
    max_stdin_bytes: int = 1024 * 1024
    max_output_bytes: int = 1024 * 1024
    default_timeout_ms: int = 30_000
    max_timeout_ms: int = 300_000
    terminate_grace_ms: int = 1_000
    preview_bytes: int = 512
    monotonic_ns: Callable[[], int] = time.monotonic_ns

    def __post_init__(self) -> None:
        try:
            mounts = tuple(self.mounts)
            bindings = tuple(self.bindings)
        except TypeError as error:
            raise ValidationError(code="process_configuration_invalid") from error
        RootSandbox(mounts)
        if not bindings or any(not isinstance(item, ProcessBinding) for item in bindings):
            raise ValidationError(code="process_bindings_invalid")
        if len({item.name for item in bindings}) != len(bindings):
            raise ValidationError(code="process_binding_duplicate")
        for name, value in (
            ("max_arguments", self.max_arguments),
            ("max_argument_chars", self.max_argument_chars),
            ("max_stdin_bytes", self.max_stdin_bytes),
            ("max_output_bytes", self.max_output_bytes),
            ("default_timeout_ms", self.default_timeout_ms),
            ("max_timeout_ms", self.max_timeout_ms),
            ("terminate_grace_ms", self.terminate_grace_ms),
            ("preview_bytes", self.preview_bytes),
        ):
            if isinstance(value, bool) or not isinstance(value, int) or value < 1:
                raise ValidationError(code=f"process_{name}_invalid")
        if self.default_timeout_ms > self.max_timeout_ms:
            raise ValidationError(code="process_timeout_bounds_invalid")
        if not callable(self.monotonic_ns):
            raise ValidationError(code="process_monotonic_clock_invalid")
        object.__setattr__(self, "mounts", mounts)
        object.__setattr__(self, "bindings", bindings)

    @property
    def sandbox(self) -> RootSandbox:
        return RootSandbox(self.mounts)

    def action(self) -> CapabilityAction:
        input_schema = _schema(
            {
                "type": "object",
                "required": ["executable", "cwdMount"],
                "properties": {
                    "executable": {
                        "type": "string",
                        "enum": [item.name for item in self.bindings],
                    },
                    "args": {
                        "type": "array",
                        "maxItems": self.max_arguments,
                        "items": {"type": "string", "maxLength": self.max_argument_chars},
                    },
                    "cwdMount": {"type": "string", "minLength": 1},
                    "cwdPath": {"type": "string", "minLength": 1},
                    "stdin": {"type": "string"},
                    "stdinBase64": {"type": "string"},
                    "timeoutMs": {
                        "type": "integer",
                        "minimum": 1,
                        "maximum": self.max_timeout_ms,
                    },
                    "env": {
                        "type": "object",
                        "additionalProperties": {
                            "type": "string",
                            "maxLength": self.max_argument_chars,
                        },
                    },
                },
                "additionalProperties": False,
            }
        )
        return CapabilityAction(
            name="run",
            description="Run one explicitly bound local executable with bounded resources",
            posture=CapabilityAccessMode.WRITE,
            reliability=CapabilityReliability.INTERRUPTIBLE,
            cancellation=CapabilityCancellation(supported=True),
            input_schema=input_schema,
            output_schema=_schema({"type": "object", "additionalProperties": True}),
            artifacts=(
                CapabilityArtifact(
                    kind="process.stdout",
                    content_type="application/octet-stream",
                    required=True,
                ),
                CapabilityArtifact(
                    kind="process.stderr",
                    content_type="application/octet-stream",
                    required=True,
                ),
            ),
            transport=CapabilityTransportMetadata(kind=CapabilityTransportKind.IN_PROCESS),
        )

    def _binding(self, name: str) -> ProcessBinding:
        binding = next((item for item in self.bindings if item.name == name), None)
        if binding is None:
            raise _execution("process_executable_not_bound")
        return binding

    def _arguments(self, data: JsonObject) -> tuple[str, ...]:
        value = data.get("args")
        if value is None:
            return ()
        if not isinstance(value, JsonArray):
            raise _execution("process_arguments_invalid")
        arguments: list[str] = []
        for argument in value:
            if (
                not isinstance(argument, str)
                or "\x00" in argument
                or len(argument) > self.max_argument_chars
            ):
                raise _execution("process_argument_invalid")
            arguments.append(argument)
        if len(arguments) > self.max_arguments:
            raise _execution("process_arguments_too_many")
        return tuple(arguments)

    def _stdin(self, data: JsonObject) -> bytes:
        value = data.get("stdin")
        encoded_value = data.get("stdinBase64")
        if value is None and encoded_value is None:
            return b""
        if (isinstance(value, str)) == (isinstance(encoded_value, str)):
            raise _execution("process_stdin_branch_invalid")
        if isinstance(value, str):
            try:
                content = value.encode("utf-8", errors="strict")
            except UnicodeEncodeError:
                raise _execution("process_stdin_utf8_invalid") from None
        elif isinstance(encoded_value, str):
            try:
                content = base64.b64decode(encoded_value.encode("ascii"), validate=True)
            except (UnicodeEncodeError, binascii.Error, ValueError):
                raise _execution("process_stdin_base64_invalid") from None
        else:
            raise _execution("process_stdin_invalid")
        if len(content) > self.max_stdin_bytes:
            raise _execution("process_stdin_too_large")
        return content

    def _timeout(self, data: JsonObject) -> int:
        value = data.get("timeoutMs")
        if value is None:
            return self.default_timeout_ms
        if (
            isinstance(value, bool)
            or not isinstance(value, int)
            or value < 1
            or value > self.max_timeout_ms
        ):
            raise _execution("process_timeout_invalid")
        return value

    async def __call__(self, invocation: CapabilityInvocation, /) -> CapabilityResult:
        if invocation.action_name != "run":
            raise _execution("process_action_unsupported")
        data = _data(invocation)
        binding = self._binding(_required_text(data, "executable"))
        executable = binding.verify()
        arguments = self._arguments(data)
        stdin = self._stdin(data)
        timeout_ms = self._timeout(data)
        cwd_mount = _required_text(data, "cwdMount")
        cwd_path = _optional_text(data, "cwdPath")
        cwd = self.sandbox.resolve(cwd_mount, cwd_path, write=True)
        try:
            cwd_status = cwd.path.lstat()
        except OSError:
            raise _execution("process_cwd_unavailable") from None
        if stat.S_ISLNK(cwd_status.st_mode) or not stat.S_ISDIR(cwd_status.st_mode):
            raise _execution("process_cwd_not_directory")
        requested_environment = data.get("env")
        if requested_environment is not None and not isinstance(requested_environment, JsonObject):
            raise _execution("process_environment_invalid")
        environment = binding.child_environment(requested_environment)

        started = self.monotonic_ns()
        try:
            child = await asyncio.create_subprocess_exec(
                str(executable),
                *arguments,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=cwd.path,
                env=environment,
            )
        except (OSError, ValueError):
            raise _execution("process_spawn_failed") from None
        stdout_task = asyncio.create_task(_capture_output(child.stdout, self.max_output_bytes))
        stderr_task = asyncio.create_task(_capture_output(child.stderr, self.max_output_bytes))
        stdin_task = asyncio.create_task(_write_stdin(child.stdin, stdin))
        timed_out = False
        try:
            try:
                async with asyncio.timeout(timeout_ms / 1000):
                    await child.wait()
            except TimeoutError:
                timed_out = True
                await _terminate_and_reap(child, self.terminate_grace_ms / 1000)
            await stdin_task
            stdout, stderr = await asyncio.gather(stdout_task, stderr_task)
        except asyncio.CancelledError:
            await _terminate_and_reap(child, self.terminate_grace_ms / 1000)
            stdin_task.cancel()
            await asyncio.gather(stdin_task, stdout_task, stderr_task, return_exceptions=True)
            raise
        except BaseException:
            await _terminate_and_reap(child, self.terminate_grace_ms / 1000)
            stdin_task.cancel()
            await asyncio.gather(stdin_task, stdout_task, stderr_task, return_exceptions=True)
            raise

        returncode = child.returncode
        exit_code = returncode if returncode is not None and returncode >= 0 else None
        signal_number = -returncode if returncode is not None and returncode < 0 else None
        duration_ms = max(0, (self.monotonic_ns() - started) // 1_000_000)
        output = {
            "executable": binding.name,
            "args": arguments,
            "cwdMount": cwd_mount,
            "cwdPath": cwd_path,
            "exitCode": exit_code,
            "signal": signal_number,
            "timedOut": timed_out,
            "durationMs": duration_ms,
            "stdoutSha256": stdout.sha256,
            "stderrSha256": stderr.sha256,
            "stdoutBytes": stdout.byte_length,
            "stderrBytes": stderr.byte_length,
            "stdoutTruncated": stdout.truncated,
            "stderrTruncated": stderr.truncated,
        }
        effect_kind = (
            "process.timed_out"
            if timed_out
            else "process.signalled"
            if signal_number is not None
            else "process.exited"
        )
        combined_preview = _preview(stdout.content or stderr.content, self.preview_bytes)
        return CapabilityResult(
            output=output,  # type: ignore[arg-type]
            preview=combined_preview,
            effects=(EffectEntry(kind=effect_kind, summary=f"{binding.name}@{cwd_mount}"),),
            evidence=(
                EvidenceEntry(description=f"stdout-sha256:{stdout.sha256}"),
                EvidenceEntry(description=f"stderr-sha256:{stderr.sha256}"),
            ),
            inline_artifacts=(
                CapabilityInlineArtifact(
                    kind="process.stdout",
                    content=stdout.content,
                    content_type="application/octet-stream",
                    preview=_preview(stdout.content, self.preview_bytes),
                    metadata={
                        "sha256": stdout.sha256,
                        "byteLength": stdout.byte_length,
                        "truncated": stdout.truncated,
                    },  # type: ignore[arg-type]
                ),
                CapabilityInlineArtifact(
                    kind="process.stderr",
                    content=stderr.content,
                    content_type="application/octet-stream",
                    preview=_preview(stderr.content, self.preview_bytes),
                    metadata={
                        "sha256": stderr.sha256,
                        "byteLength": stderr.byte_length,
                        "truncated": stderr.truncated,
                    },  # type: ignore[arg-type]
                ),
            ),
        )

    def registered(self, *, capability_id: CapabilityId | None = None) -> RegisteredCapability:
        identifier = CapabilityId(value="process") if capability_id is None else capability_id
        action = self.action()
        return RegisteredCapability(
            definition=Capability(capability_id=identifier, version="1", actions=(action,)),
            bindings=(
                ActionTransportBinding(action_name=action.name, transport=InProcessTransport(self)),
            ),
        )
