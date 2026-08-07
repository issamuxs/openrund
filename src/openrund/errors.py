"""Safe, stable exceptions for semantic and infrastructure boundaries."""

from __future__ import annotations

import re
from dataclasses import FrozenInstanceError
from typing import Final

_MAX_SAFE_DETAIL_BYTES: Final = 256
_EXCEPTION_RUNTIME_FIELDS: Final = frozenset(
    {"__cause__", "__context__", "__notes__", "__suppress_context__", "__traceback__"}
)
_SENSITIVE_DETAIL: Final = re.compile(
    r"(?i)(authorization|bearer|token|secret|password|api[-_ ]?key|credential|"
    r"provider\s+body|raw\s+body)|(?:^|\s)/(?:Users|home|private|var|tmp|etc)/|"
    r"\b[A-Za-z]:[\\/]"
)


def _validate_code(code: object) -> str:
    if not isinstance(code, str):
        raise TypeError("error_code_type_invalid")
    if not code:
        raise ValueError("error_code_empty")
    return code


def _validate_pointer(pointer: object | None) -> str | None:
    if pointer is None:
        return None
    if not isinstance(pointer, str):
        raise TypeError("error_pointer_type_invalid")
    if pointer != "" and not pointer.startswith("/"):
        raise ValueError("error_pointer_invalid")
    return pointer


def _sanitize_safe_detail(safe_detail: object | None) -> str | None:
    if safe_detail is None:
        return None
    if not isinstance(safe_detail, str):
        raise TypeError("error_safe_detail_type_invalid")
    if _SENSITIVE_DETAIL.search(safe_detail):
        return "[redacted]"
    encoded = safe_detail.encode("utf-8")
    if len(encoded) <= _MAX_SAFE_DETAIL_BYTES:
        return safe_detail
    return encoded[:_MAX_SAFE_DETAIL_BYTES].decode("utf-8", errors="ignore")


class OpenRundError(Exception):
    """Base for safe caller-visible OpenRund failures."""

    __slots__ = ("_frozen", "code", "pointer", "safe_detail")
    _frozen: bool
    code: str
    pointer: str | None
    safe_detail: str | None

    def __init__(
        self,
        *,
        code: str = "openrund_error",
        pointer: str | None = None,
        safe_detail: str | None = None,
    ) -> None:
        validated_code = _validate_code(code)
        validated_pointer = _validate_pointer(pointer)
        sanitized_detail = _sanitize_safe_detail(safe_detail)
        object.__setattr__(self, "code", validated_code)
        object.__setattr__(self, "pointer", validated_pointer)
        object.__setattr__(self, "safe_detail", sanitized_detail)
        Exception.__init__(self, self._render())
        object.__setattr__(self, "_frozen", True)

    def __setattr__(self, name: str, value: object) -> None:
        if name in _EXCEPTION_RUNTIME_FIELDS:
            BaseException.__setattr__(self, name, value)
            return
        if getattr(self, "_frozen", False):
            raise FrozenInstanceError(f"cannot assign to field {name!r}")
        object.__setattr__(self, name, value)

    def _render(self) -> str:
        parts = [self.code]
        if self.pointer is not None:
            parts.append(f"at {self.pointer or '/'}")
        if self.safe_detail is not None:
            parts.append(self.safe_detail)
        return ": ".join(parts)

    def __repr__(self) -> str:
        return (
            f"{type(self).__name__}(code={self.code!r}, pointer={self.pointer!r}, "
            f"safe_detail={self.safe_detail!r})"
        )


class ResourceClosedError(OpenRundError):
    """An operation targeted a resource after its explicit async lifetime ended."""

    __slots__ = ("resource",)
    resource: str

    def __init__(self, *, resource: str) -> None:
        if not isinstance(resource, str) or resource == "":
            raise TypeError("closed_resource_invalid")
        object.__setattr__(self, "resource", resource)
        super().__init__(code="resource_closed", safe_detail=f"resource={resource}")


class ContractError(OpenRundError):
    """A semantic value or codec contract was violated."""

    __slots__ = ()

    def __init__(
        self,
        *,
        code: str = "contract_error",
        pointer: str | None = None,
        safe_detail: str | None = None,
    ) -> None:
        super().__init__(code=code, pointer=pointer, safe_detail=safe_detail)


class ValidationError(ContractError):
    """An untrusted runtime value failed semantic validation."""

    __slots__ = ()

    def __init__(
        self, *, code: str, pointer: str | None = None, safe_detail: str | None = None
    ) -> None:
        super().__init__(code=code, pointer=pointer, safe_detail=safe_detail)


class DecodeError(ContractError):
    __slots__ = ()

    def __init__(
        self,
        *,
        code: str = "decode_error",
        pointer: str | None = None,
        safe_detail: str | None = None,
    ) -> None:
        super().__init__(code=code, pointer=pointer, safe_detail=safe_detail)


class EncodeError(ContractError):
    __slots__ = ()

    def __init__(
        self,
        *,
        code: str = "encode_error",
        pointer: str | None = None,
        safe_detail: str | None = None,
    ) -> None:
        super().__init__(code=code, pointer=pointer, safe_detail=safe_detail)


class UnsupportedVersionError(ContractError):
    __slots__ = ("version",)
    version: int | str

    def __init__(
        self,
        *,
        version: int | str,
        code: str = "unsupported_version",
        pointer: str | None = None,
        safe_detail: str | None = None,
    ) -> None:
        if isinstance(version, bool) or not isinstance(version, (int, str)):
            raise TypeError("unsupported_version_type_invalid")
        if isinstance(version, str) and not version:
            raise ValueError("unsupported_version_empty")
        object.__setattr__(self, "version", version)
        detail = safe_detail if safe_detail is not None else f"version={version}"
        super().__init__(code=code, pointer=pointer, safe_detail=detail)


class ConcurrencyError(OpenRundError):
    __slots__ = ()

    def __init__(
        self,
        *,
        code: str = "concurrency_error",
        safe_detail: str | None = None,
    ) -> None:
        super().__init__(code=code, safe_detail=safe_detail)


class ExpectedPositionConflict(ConcurrencyError):
    __slots__ = ("actual_position", "expected_position", "run_id")
    actual_position: int
    expected_position: int
    run_id: str

    def __init__(self, *, run_id: str, expected_position: int, actual_position: int) -> None:
        if not isinstance(run_id, str):
            raise TypeError("run_id_type_invalid")
        if not run_id:
            raise ValueError("run_id_empty")
        for name, position in (
            ("expected_position", expected_position),
            ("actual_position", actual_position),
        ):
            if isinstance(position, bool) or not isinstance(position, int):
                raise TypeError(f"{name}_type_invalid")
            if position < 0:
                raise ValueError(f"{name}_invalid")
        object.__setattr__(self, "run_id", run_id)
        object.__setattr__(self, "expected_position", expected_position)
        object.__setattr__(self, "actual_position", actual_position)
        super().__init__(
            code="expected_position_conflict",
            safe_detail=(
                f"run_id={run_id} expected_position={expected_position} "
                f"actual_position={actual_position}"
            ),
        )


class StorageBusyError(ConcurrencyError):
    """A local storage lock remained unavailable for its configured bound."""

    __slots__ = ()

    def __init__(self) -> None:
        super().__init__(code="storage_busy")


class StorageError(OpenRundError):
    __slots__ = ()

    def __init__(self, *, code: str = "storage_error", safe_detail: str | None = None) -> None:
        super().__init__(code=code, safe_detail=safe_detail)


class StorageIntegrityError(StorageError):
    __slots__ = ()

    def __init__(
        self, *, code: str = "storage_integrity_error", safe_detail: str | None = None
    ) -> None:
        super().__init__(code=code, safe_detail=safe_detail)


class BundleError(OpenRundError):
    """A portable Bundle operation failed at a safe, classified boundary."""

    __slots__ = ()

    def __init__(
        self,
        *,
        code: str = "bundle_error",
        pointer: str | None = None,
        safe_detail: str | None = None,
    ) -> None:
        super().__init__(code=code, pointer=pointer, safe_detail=safe_detail)


class BundleIntegrityError(BundleError):
    """Bundle bytes or semantic commitments failed verification."""

    __slots__ = ()

    def __init__(
        self,
        *,
        code: str = "bundle_integrity_error",
        pointer: str | None = None,
        safe_detail: str | None = None,
    ) -> None:
        super().__init__(code=code, pointer=pointer, safe_detail=safe_detail)


class BundleImportError(BundleError):
    """Verified Bundle content could not be published into import custody."""

    __slots__ = ()

    def __init__(
        self,
        *,
        code: str = "bundle_import_error",
        pointer: str | None = None,
        safe_detail: str | None = None,
    ) -> None:
        super().__init__(code=code, pointer=pointer, safe_detail=safe_detail)


class TransportError(OpenRundError):
    __slots__ = ()

    def __init__(self, *, code: str = "transport_error", safe_detail: str | None = None) -> None:
        super().__init__(code=code, safe_detail=safe_detail)


class ProviderTransportError(TransportError):
    __slots__ = ()

    def __init__(
        self, *, code: str = "provider_transport_error", safe_detail: str | None = None
    ) -> None:
        super().__init__(code=code, safe_detail=safe_detail)


class ProviderProtocolError(OpenRundError):
    """A provider response could not be safely normalized."""

    __slots__ = ()

    def __init__(
        self, *, code: str = "provider_protocol_error", safe_detail: str | None = None
    ) -> None:
        super().__init__(code=code, safe_detail=safe_detail)


class ProviderResponseError(OpenRundError):
    """A provider returned a non-success HTTP response without exposing its body."""

    __slots__ = ("retryable", "status")
    retryable: bool
    status: int

    def __init__(self, *, status: int) -> None:
        if isinstance(status, bool) or not isinstance(status, int) or not 100 <= status <= 599:
            raise TypeError("provider_status_invalid")
        object.__setattr__(self, "status", status)
        object.__setattr__(self, "retryable", status in {408, 409, 425, 429} or status >= 500)
        super().__init__(
            code="provider_response_error",
            safe_detail=f"status={status}",
        )


class ProviderToolArgumentsError(ProviderProtocolError):
    """A present tool argument payload was malformed or not an object."""

    __slots__ = ("input_classification",)
    input_classification: str

    def __init__(self, *, input_classification: str) -> None:
        if input_classification not in {"malformed_json", "non_object"}:
            raise TypeError("provider_tool_arguments_classification_invalid")
        object.__setattr__(self, "input_classification", input_classification)
        super().__init__(
            code="provider_tool_arguments_invalid",
            safe_detail=f"classification={input_classification}",
        )


class CapabilityTransportError(TransportError):
    __slots__ = ()

    def __init__(
        self, *, code: str = "capability_transport_error", safe_detail: str | None = None
    ) -> None:
        super().__init__(code=code, safe_detail=safe_detail)


class CapabilityProtocolError(OpenRundError):
    __slots__ = ()

    def __init__(
        self, *, code: str = "capability_protocol_error", safe_detail: str | None = None
    ) -> None:
        super().__init__(code=code, safe_detail=safe_detail)


class CapabilityExecutionError(OpenRundError):
    """A worker-confirmed rejection that proves no ambiguous successful result."""

    __slots__ = ()

    def __init__(
        self, *, code: str = "capability_execution_error", safe_detail: str | None = None
    ) -> None:
        super().__init__(code=code, safe_detail=safe_detail)
