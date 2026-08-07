"""In-process and strict one-request stdio JSON-RPC Capability transports."""

from __future__ import annotations

import asyncio
import base64
import binascii
from dataclasses import dataclass
from pathlib import Path
from typing import Final, Self, final

from openrund.codec import decode_json_value, encode_json_value
from openrund.contracts.capabilities import (
    CapabilityInlineArtifact,
    CapabilityResult,
    CapabilityTransportKind,
)
from openrund.contracts.content import (
    ArtifactReference,
    Content,
    EffectEntry,
    EvidenceEntry,
    Mutation,
    MutationOperationKind,
    MutationReversibility,
)
from openrund.contracts.ids import ActionId, ArtifactId, CapabilityId
from openrund.contracts.json import (
    MISSING,
    JsonArray,
    JsonObject,
    JsonValue,
    MissingType,
    freeze_json,
)
from openrund.errors import (
    CapabilityExecutionError,
    CapabilityProtocolError,
    CapabilityTransportError,
    OpenRundError,
    ResourceClosedError,
    ValidationError,
)
from openrund.paths import PathInput, normalize_local_path
from openrund.ports.capabilities import CapabilityHandler, CapabilityInvocation

_JSONRPC_VERSION: Final = "2.0"
_REQUEST_ID: Final = "openrund-capability-1"
_RESPONSE_KEYS: Final = frozenset({"jsonrpc", "id", "result", "error"})
_RESULT_KEYS: Final = frozenset(
    {"output", "preview", "effects", "evidence", "artifactIds", "inlineArtifacts", "metadata"}
)


def _content_wire(content: Content) -> JsonObject:
    values: dict[str, object] = {}
    if content.preview is not MISSING:
        values["preview"] = content.preview
    if content.data is not MISSING:
        values["data"] = content.data
    if content.artifact_refs:
        values["artifactRefs"] = [
            {
                "artifactId": item.artifact_id.value,
                **({"kind": item.kind} if isinstance(item.kind, str) else {}),
                **({"preview": item.preview} if isinstance(item.preview, str) else {}),
                **({"metadata": item.metadata} if isinstance(item.metadata, JsonObject) else {}),
            }
            for item in content.artifact_refs
        ]
    if content.artifact_ids:
        values["artifactIds"] = [item.value for item in content.artifact_ids]
    if content.metadata is not MISSING:
        values["metadata"] = content.metadata
    frozen = freeze_json(values)
    assert isinstance(frozen, JsonObject)
    return frozen


def _mutation_wire(mutation: Mutation) -> JsonObject:
    values: dict[str, object] = {
        "affectedResources": list(mutation.affected_resources),
        "operationKind": mutation.operation_kind.value,
    }
    if isinstance(mutation.preview, Content):
        values["preview"] = _content_wire(mutation.preview)
    if isinstance(mutation.reversibility, MutationReversibility):
        values["reversibility"] = mutation.reversibility.value
    if isinstance(mutation.check_plan, Content):
        values["checkPlan"] = _content_wire(mutation.check_plan)
    if isinstance(mutation.metadata, JsonObject):
        values["metadata"] = mutation.metadata
    frozen = freeze_json(values)
    assert isinstance(frozen, JsonObject)
    return frozen


def encode_invocation(invocation: CapabilityInvocation, /) -> JsonObject:
    values: dict[str, object] = {
        "actionId": invocation.action_id.value,
        "capabilityId": invocation.capability_id.value,
        "actionName": invocation.action_name,
        "input": _content_wire(invocation.input),
    }
    if isinstance(invocation.mutation, Mutation):
        values["mutation"] = _mutation_wire(invocation.mutation)
    if isinstance(invocation.idempotency_key, str):
        values["idempotencyKey"] = invocation.idempotency_key
    if isinstance(invocation.metadata, JsonObject):
        values["metadata"] = invocation.metadata
    frozen = freeze_json(values)
    assert isinstance(frozen, JsonObject)
    return frozen


def _decode_content(value: JsonValue) -> Content:
    item = _required_object(value, "capability_invocation_content_invalid")
    _exact_keys(
        item,
        frozenset({"preview", "data", "artifactRefs", "artifactIds", "metadata"}),
        "capability_invocation_content_invalid",
    )
    refs_value = item.get("artifactRefs")
    if refs_value is not None and not isinstance(refs_value, JsonArray):
        raise CapabilityProtocolError(code="capability_invocation_content_invalid")
    references: list[ArtifactReference] = []
    for value_item in refs_value or ():
        reference = _required_object(value_item, "capability_invocation_content_invalid")
        _exact_keys(
            reference,
            frozenset({"artifactId", "kind", "preview", "metadata"}),
            "capability_invocation_content_invalid",
        )
        artifact_id = reference.get("artifactId")
        if not isinstance(artifact_id, str):
            raise CapabilityProtocolError(code="capability_invocation_content_invalid")
        references.append(
            ArtifactReference(
                artifact_id=ArtifactId(value=artifact_id),
                kind=_optional_text(reference, "kind", "capability_invocation_content_invalid"),
                preview=_optional_text(
                    reference, "preview", "capability_invocation_content_invalid"
                ),
                metadata=_optional_object(
                    reference, "metadata", "capability_invocation_content_invalid"
                ),
            )
        )
    data = item.get("data", MISSING)
    if data not in (MISSING, None) and not isinstance(data, JsonObject):
        raise CapabilityProtocolError(code="capability_invocation_content_invalid")
    return Content(
        preview=_optional_text(item, "preview", "capability_invocation_content_invalid"),
        data=data,
        artifact_refs=tuple(references),
        artifact_ids=_decode_ids(item.get("artifactIds"), "capability_invocation_content_invalid"),
        metadata=_optional_object(item, "metadata", "capability_invocation_content_invalid"),
    )


def _decode_mutation(value: JsonValue) -> Mutation:
    item = _required_object(value, "capability_invocation_mutation_invalid")
    _exact_keys(
        item,
        frozenset(
            {
                "affectedResources",
                "operationKind",
                "preview",
                "reversibility",
                "checkPlan",
                "metadata",
            }
        ),
        "capability_invocation_mutation_invalid",
    )
    resources = item.get("affectedResources")
    operation_kind = item.get("operationKind")
    if (
        not isinstance(resources, JsonArray)
        or any(not isinstance(resource, JsonObject) for resource in resources)
        or not isinstance(operation_kind, str)
    ):
        raise CapabilityProtocolError(code="capability_invocation_mutation_invalid")
    preview_value = item.get("preview", MISSING)
    check_value = item.get("checkPlan", MISSING)
    reversibility_value = item.get("reversibility", MISSING)
    try:
        if isinstance(reversibility_value, str):
            reversibility: MutationReversibility | MissingType | None = MutationReversibility(
                reversibility_value
            )
        elif isinstance(reversibility_value, MissingType) or reversibility_value is None:
            reversibility = reversibility_value
        else:
            raise CapabilityProtocolError(code="capability_invocation_mutation_invalid")
        return Mutation(
            affected_resources=tuple(
                resource for resource in resources if isinstance(resource, JsonObject)
            ),
            operation_kind=MutationOperationKind(operation_kind),
            preview=(
                _decode_content(preview_value)
                if not isinstance(preview_value, MissingType) and preview_value is not None
                else preview_value
            ),
            reversibility=reversibility,
            check_plan=(
                _decode_content(check_value)
                if not isinstance(check_value, MissingType) and check_value is not None
                else check_value
            ),
            metadata=_optional_object(item, "metadata", "capability_invocation_mutation_invalid"),
        )
    except (OpenRundError, ValueError):
        raise CapabilityProtocolError(code="capability_invocation_mutation_invalid") from None


def decode_invocation(value: JsonValue, /) -> CapabilityInvocation:
    item = _required_object(value, "capability_invocation_object_required")
    _exact_keys(
        item,
        frozenset(
            {
                "actionId",
                "capabilityId",
                "actionName",
                "input",
                "mutation",
                "idempotencyKey",
                "metadata",
            }
        ),
        "capability_invocation_key_unsupported",
    )
    action_id = item.get("actionId")
    capability_id = item.get("capabilityId")
    action_name = item.get("actionName")
    input_value = item.get("input")
    if (
        not isinstance(action_id, str)
        or not isinstance(capability_id, str)
        or not isinstance(action_name, str)
        or input_value is None
    ):
        raise CapabilityProtocolError(code="capability_invocation_invalid")
    mutation_value = item.get("mutation", MISSING)
    try:
        return CapabilityInvocation(
            action_id=ActionId(value=action_id),
            capability_id=CapabilityId(value=capability_id),
            action_name=action_name,
            input=_decode_content(input_value),
            mutation=(
                _decode_mutation(mutation_value)
                if not isinstance(mutation_value, MissingType) and mutation_value is not None
                else mutation_value
            ),
            idempotency_key=_optional_text(item, "idempotencyKey", "capability_invocation_invalid"),
            metadata=_optional_object(item, "metadata", "capability_invocation_invalid"),
        )
    except CapabilityProtocolError:
        raise
    except (OpenRundError, TypeError, ValueError):
        raise CapabilityProtocolError(code="capability_invocation_invalid") from None


def _required_object(value: JsonValue | None, code: str) -> JsonObject:
    if not isinstance(value, JsonObject):
        raise CapabilityProtocolError(code=code)
    return value


def _exact_keys(value: JsonObject, allowed: frozenset[str], code: str) -> None:
    if any(key not in allowed for key in value):
        raise CapabilityProtocolError(code=code)


def _optional_text(value: JsonObject, name: str, code: str) -> str | MissingType | None:
    candidate = value.get(name, MISSING)
    if candidate is MISSING or candidate is None:
        return candidate
    if not isinstance(candidate, str):
        raise CapabilityProtocolError(code=code)
    return candidate


def _optional_object(value: JsonObject, name: str, code: str) -> JsonObject | MissingType | None:
    candidate = value.get(name, MISSING)
    if candidate is MISSING or candidate is None or isinstance(candidate, JsonObject):
        return candidate
    raise CapabilityProtocolError(code=code)


def _decode_ids(value: JsonValue | None, code: str) -> tuple[ArtifactId, ...]:
    if value is None:
        return ()
    if not isinstance(value, JsonArray) or any(not isinstance(item, str) for item in value):
        raise CapabilityProtocolError(code=code)
    try:
        return tuple(ArtifactId(value=item) for item in value if isinstance(item, str))
    except OpenRundError:
        raise CapabilityProtocolError(code=code) from None


def _decode_effect(value: JsonValue) -> EffectEntry:
    item = _required_object(value, "capability_result_effect_invalid")
    _exact_keys(
        item,
        frozenset({"kind", "summary", "artifactIds", "metadata"}),
        "capability_result_effect_invalid",
    )
    kind = item.get("kind")
    if not isinstance(kind, str) or kind == "":
        raise CapabilityProtocolError(code="capability_result_effect_invalid")
    try:
        return EffectEntry(
            kind=kind,
            summary=_optional_text(item, "summary", "capability_result_effect_invalid"),
            artifact_ids=_decode_ids(item.get("artifactIds"), "capability_result_effect_invalid"),
            metadata=_optional_object(item, "metadata", "capability_result_effect_invalid"),
        )
    except OpenRundError:
        raise CapabilityProtocolError(code="capability_result_effect_invalid") from None


def _decode_evidence(value: JsonValue) -> EvidenceEntry:
    item = _required_object(value, "capability_result_evidence_invalid")
    _exact_keys(
        item,
        frozenset({"artifactId", "description", "metadata"}),
        "capability_result_evidence_invalid",
    )
    artifact_id = item.get("artifactId", MISSING)
    if artifact_id is not MISSING and artifact_id is not None and not isinstance(artifact_id, str):
        raise CapabilityProtocolError(code="capability_result_evidence_invalid")
    try:
        return EvidenceEntry(
            artifact_id=(
                ArtifactId(value=artifact_id) if isinstance(artifact_id, str) else artifact_id
            ),
            description=_optional_text(item, "description", "capability_result_evidence_invalid"),
            metadata=_optional_object(item, "metadata", "capability_result_evidence_invalid"),
        )
    except OpenRundError:
        raise CapabilityProtocolError(code="capability_result_evidence_invalid") from None


def _decode_inline_artifact(value: JsonValue) -> CapabilityInlineArtifact:
    item = _required_object(value, "capability_inline_artifact_invalid")
    _exact_keys(
        item,
        frozenset({"kind", "contentBase64", "contentType", "preview", "metadata"}),
        "capability_inline_artifact_invalid",
    )
    kind = item.get("kind")
    encoded = item.get("contentBase64")
    if not isinstance(kind, str) or kind == "" or not isinstance(encoded, str):
        raise CapabilityProtocolError(code="capability_inline_artifact_invalid")
    try:
        content = base64.b64decode(encoded.encode("ascii"), validate=True)
    except (UnicodeEncodeError, binascii.Error, ValueError):
        raise CapabilityProtocolError(code="capability_inline_artifact_base64_invalid") from None
    try:
        return CapabilityInlineArtifact(
            kind=kind,
            content=content,
            content_type=_optional_text(item, "contentType", "capability_inline_artifact_invalid"),
            preview=_optional_text(item, "preview", "capability_inline_artifact_invalid"),
            metadata=_optional_object(item, "metadata", "capability_inline_artifact_invalid"),
        )
    except OpenRundError:
        raise CapabilityProtocolError(code="capability_inline_artifact_invalid") from None


def decode_capability_result(value: JsonValue, /) -> CapabilityResult:
    result = _required_object(value, "capability_result_object_required")
    _exact_keys(result, _RESULT_KEYS, "capability_result_key_unsupported")
    effects_value = result.get("effects")
    evidence_value = result.get("evidence")
    inline_value = result.get("inlineArtifacts")
    if effects_value is not None and not isinstance(effects_value, JsonArray):
        raise CapabilityProtocolError(code="capability_result_effects_invalid")
    if evidence_value is not None and not isinstance(evidence_value, JsonArray):
        raise CapabilityProtocolError(code="capability_result_evidence_invalid")
    if inline_value is not None and not isinstance(inline_value, JsonArray):
        raise CapabilityProtocolError(code="capability_result_inline_artifacts_invalid")
    try:
        return CapabilityResult(
            output=result.get("output", MISSING),
            preview=_optional_text(result, "preview", "capability_result_preview_invalid"),
            effects=tuple(_decode_effect(item) for item in effects_value or ()),
            evidence=tuple(_decode_evidence(item) for item in evidence_value or ()),
            artifact_ids=_decode_ids(
                result.get("artifactIds"), "capability_result_artifact_ids_invalid"
            ),
            inline_artifacts=tuple(_decode_inline_artifact(item) for item in inline_value or ()),
            metadata=_optional_object(result, "metadata", "capability_result_metadata_invalid"),
        )
    except CapabilityProtocolError:
        raise
    except OpenRundError:
        raise CapabilityProtocolError(code="capability_result_invalid") from None


def encode_capability_result(result: CapabilityResult, /) -> JsonObject:
    if not isinstance(result, CapabilityResult):
        raise CapabilityProtocolError(code="capability_result_type_invalid")
    values: dict[str, object] = {}
    if result.output is not MISSING:
        values["output"] = result.output
    if result.preview is not MISSING:
        values["preview"] = result.preview
    if result.effects:
        values["effects"] = [
            {
                "kind": item.kind,
                **({"summary": item.summary} if isinstance(item.summary, str) else {}),
                **(
                    {"artifactIds": [value.value for value in item.artifact_ids]}
                    if item.artifact_ids
                    else {}
                ),
                **({"metadata": item.metadata} if isinstance(item.metadata, JsonObject) else {}),
            }
            for item in result.effects
        ]
    if result.evidence:
        values["evidence"] = [
            {
                **(
                    {"artifactId": item.artifact_id.value}
                    if isinstance(item.artifact_id, ArtifactId)
                    else {}
                ),
                **({"description": item.description} if isinstance(item.description, str) else {}),
                **({"metadata": item.metadata} if isinstance(item.metadata, JsonObject) else {}),
            }
            for item in result.evidence
        ]
    if result.artifact_ids:
        values["artifactIds"] = [item.value for item in result.artifact_ids]
    if result.inline_artifacts:
        values["inlineArtifacts"] = [
            {
                "kind": item.kind,
                "contentBase64": base64.b64encode(item.content).decode("ascii"),
                **(
                    {"contentType": item.content_type} if isinstance(item.content_type, str) else {}
                ),
                **({"preview": item.preview} if isinstance(item.preview, str) else {}),
                **({"metadata": item.metadata} if isinstance(item.metadata, JsonObject) else {}),
            }
            for item in result.inline_artifacts
        ]
    if result.metadata is not MISSING:
        values["metadata"] = result.metadata
    frozen = freeze_json(values)
    assert isinstance(frozen, JsonObject)
    return frozen


@final
class InProcessTransport:
    __slots__ = ("_handler",)
    kind: Final = CapabilityTransportKind.IN_PROCESS

    def __init__(self, handler: CapabilityHandler) -> None:
        if not callable(handler):
            raise ValidationError(code="capability_handler_invalid")
        self._handler = handler

    async def invoke(self, invocation: CapabilityInvocation, /) -> CapabilityResult:
        if not isinstance(invocation, CapabilityInvocation):
            raise ValidationError(code="capability_transport_invocation_invalid")
        try:
            result = await self._handler(invocation)
        except asyncio.CancelledError:
            raise
        except (CapabilityExecutionError, CapabilityProtocolError, CapabilityTransportError):
            raise
        except Exception:
            raise CapabilityTransportError(code="capability_handler_failed") from None
        if not isinstance(result, CapabilityResult):
            raise CapabilityProtocolError(code="capability_result_type_invalid")
        return result


@final
@dataclass(frozen=True, slots=True, kw_only=True)
class StdioJsonRpcConfig:
    command: tuple[str, ...]
    cwd: PathInput | None = None
    environment: tuple[tuple[str, str], ...] = ()
    timeout_ms: int = 30_000
    max_response_bytes: int = 8 * 1024 * 1024
    max_stderr_bytes: int = 64 * 1024

    def __post_init__(self) -> None:
        try:
            command = tuple(self.command)
            environment = tuple(self.environment)
        except TypeError as error:
            raise ValidationError(code="stdio_transport_config_invalid") from error
        if not command or any(
            not isinstance(item, str) or item == "" or "\x00" in item for item in command
        ):
            raise ValidationError(code="stdio_transport_command_invalid")
        executable = Path(command[0])
        if not executable.is_absolute():
            raise ValidationError(code="stdio_transport_executable_not_absolute")
        if self.cwd is not None:
            cwd = normalize_local_path(self.cwd)
            if not cwd.path.is_absolute():
                raise ValidationError(code="stdio_transport_cwd_not_absolute")
            object.__setattr__(self, "cwd", cwd.raw)
        if any(
            not isinstance(item, tuple)
            or len(item) != 2
            or not isinstance(item[0], str)
            or item[0] == ""
            or "=" in item[0]
            or "\x00" in item[0]
            or not isinstance(item[1], str)
            or "\x00" in item[1]
            for item in environment
        ):
            raise ValidationError(code="stdio_transport_environment_invalid")
        if len({item[0] for item in environment}) != len(environment):
            raise ValidationError(code="stdio_transport_environment_duplicate")
        for name, value in (
            ("timeout_ms", self.timeout_ms),
            ("max_response_bytes", self.max_response_bytes),
            ("max_stderr_bytes", self.max_stderr_bytes),
        ):
            if isinstance(value, bool) or not isinstance(value, int) or value < 1:
                raise ValidationError(code=f"stdio_transport_{name}_invalid")
        object.__setattr__(self, "command", command)
        object.__setattr__(self, "environment", environment)


async def _read_bounded(
    stream: asyncio.StreamReader | None,
    limit: int,
    code: str,
) -> bytes:
    if stream is None:
        raise CapabilityTransportError(code="capability_worker_pipe_missing")
    chunks: list[bytes] = []
    size = 0
    while True:
        chunk = await stream.read(min(65_536, limit + 1 - size))
        if not chunk:
            return b"".join(chunks)
        chunks.append(chunk)
        size += len(chunk)
        if size > limit:
            raise CapabilityProtocolError(code=code)


async def _stop_process(process: asyncio.subprocess.Process) -> None:
    if process.returncode is not None:
        return
    try:
        process.terminate()
    except ProcessLookupError:
        return
    try:
        await asyncio.wait_for(process.wait(), timeout=1.0)
    except TimeoutError:
        try:
            process.kill()
        except ProcessLookupError:
            return
        await process.wait()


@final
class StdioJsonRpcTransport:
    __slots__ = ("_active", "_closed", "_config")
    kind: Final = CapabilityTransportKind.STDIO_JSON_RPC

    def __init__(self, config: StdioJsonRpcConfig) -> None:
        if not isinstance(config, StdioJsonRpcConfig):
            raise ValidationError(code="stdio_transport_config_invalid")
        self._config = config
        self._active: set[asyncio.subprocess.Process] = set()
        self._closed = False

    async def __aenter__(self) -> Self:
        if self._closed:
            raise ResourceClosedError(resource="stdio_transport")
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
        if active:
            await asyncio.gather(*(_stop_process(process) for process in active))
        self._active.clear()

    def _closed_now(self) -> bool:
        """Re-read state after a spawn await, where another task may have closed us."""

        return self._closed

    async def invoke(self, invocation: CapabilityInvocation, /) -> CapabilityResult:
        if self._closed_now():
            raise ResourceClosedError(resource="stdio_transport")
        if not isinstance(invocation, CapabilityInvocation):
            raise ValidationError(code="capability_transport_invocation_invalid")
        request_value = freeze_json(
            {
                "jsonrpc": _JSONRPC_VERSION,
                "id": _REQUEST_ID,
                "method": "capability.invoke",
                "params": encode_invocation(invocation),
            }
        )
        request = encode_json_value(request_value)
        try:
            process = await asyncio.create_subprocess_exec(
                *self._config.command,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=self._config.cwd,
                env=dict(self._config.environment),
            )
        except (OSError, ValueError):
            raise CapabilityTransportError(code="capability_worker_spawn_failed") from None
        self._active.add(process)
        if self._closed_now():
            await _stop_process(process)
            self._active.discard(process)
            raise ResourceClosedError(resource="stdio_transport")
        try:
            return await self._communicate(process, request)
        finally:
            self._active.discard(process)

    async def _communicate(
        self,
        process: asyncio.subprocess.Process,
        request: bytes,
    ) -> CapabilityResult:
        try:
            assert process.stdin is not None
            process.stdin.write(request)
            await process.stdin.drain()
            process.stdin.close()
            async with asyncio.timeout(self._config.timeout_ms / 1000):
                stdout_task = asyncio.create_task(
                    _read_bounded(
                        process.stdout,
                        self._config.max_response_bytes,
                        "capability_worker_response_too_large",
                    )
                )
                stderr_task = asyncio.create_task(
                    _read_bounded(
                        process.stderr,
                        self._config.max_stderr_bytes,
                        "capability_worker_stderr_too_large",
                    )
                )
                try:
                    stdout, stderr, returncode = await asyncio.gather(
                        stdout_task,
                        stderr_task,
                        process.wait(),
                    )
                except BaseException:
                    stdout_task.cancel()
                    stderr_task.cancel()
                    raise
        except asyncio.CancelledError:
            await _stop_process(process)
            raise
        except TimeoutError:
            await _stop_process(process)
            raise CapabilityTransportError(code="capability_worker_timeout") from None
        except CapabilityProtocolError:
            await _stop_process(process)
            raise
        except (BrokenPipeError, ConnectionError, OSError):
            await _stop_process(process)
            raise CapabilityTransportError(code="capability_worker_transport_lost") from None
        if returncode != 0:
            raise CapabilityTransportError(code="capability_worker_failed")
        if stderr:
            raise CapabilityProtocolError(code="capability_worker_stderr_forbidden")
        try:
            response_value = decode_json_value(stdout)
        except OpenRundError:
            raise CapabilityProtocolError(code="capability_worker_response_invalid") from None
        response = _required_object(response_value, "capability_worker_response_invalid")
        _exact_keys(response, _RESPONSE_KEYS, "capability_worker_response_key_unsupported")
        if response.get("jsonrpc") != _JSONRPC_VERSION or response.get("id") != _REQUEST_ID:
            raise CapabilityProtocolError(code="capability_worker_response_mismatch")
        has_result = "result" in response
        has_error = "error" in response
        if has_result == has_error:
            raise CapabilityProtocolError(code="capability_worker_response_branch_invalid")
        if has_error:
            error = _required_object(response.get("error"), "capability_worker_error_invalid")
            _exact_keys(
                error, frozenset({"code", "message", "data"}), "capability_worker_error_invalid"
            )
            if not isinstance(error.get("code"), int) or not isinstance(error.get("message"), str):
                raise CapabilityProtocolError(code="capability_worker_error_invalid")
            error_code = "capability_worker_rejected"
            data = error.get("data")
            if isinstance(data, JsonObject):
                worker_code = data.get("code")
                if isinstance(worker_code, str) and worker_code.startswith(
                    ("documents_", "filesystem_")
                ):
                    error_code = worker_code
            raise CapabilityExecutionError(code=error_code)
        return decode_capability_result(response["result"])
