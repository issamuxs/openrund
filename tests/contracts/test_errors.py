from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import FrozenInstanceError

import pytest

from openrund.errors import (
    CapabilityProtocolError,
    CapabilityTransportError,
    ConcurrencyError,
    ContractError,
    DecodeError,
    EncodeError,
    ExpectedPositionConflict,
    OpenRundError,
    ProviderProtocolError,
    ProviderResponseError,
    ProviderTransportError,
    ResourceClosedError,
    StorageError,
    StorageIntegrityError,
    TransportError,
    UnsupportedVersionError,
    ValidationError,
)


def test_exception_hierarchy_preserves_failure_categories() -> None:
    assert issubclass(ContractError, OpenRundError)
    assert issubclass(ValidationError, ContractError)
    assert issubclass(DecodeError, ContractError)
    assert issubclass(EncodeError, ContractError)
    assert issubclass(UnsupportedVersionError, ContractError)
    assert issubclass(ConcurrencyError, OpenRundError)
    assert issubclass(ExpectedPositionConflict, ConcurrencyError)
    assert issubclass(StorageError, OpenRundError)
    assert issubclass(StorageIntegrityError, StorageError)
    assert issubclass(TransportError, OpenRundError)
    assert issubclass(ProviderTransportError, TransportError)
    assert issubclass(ProviderProtocolError, OpenRundError)
    assert issubclass(ProviderResponseError, OpenRundError)
    assert issubclass(ResourceClosedError, OpenRundError)
    assert issubclass(CapabilityTransportError, TransportError)
    assert issubclass(CapabilityProtocolError, OpenRundError)


@pytest.mark.parametrize(
    ("error", "code"),
    [
        (ValidationError(code="id_empty"), "id_empty"),
        (DecodeError(), "decode_error"),
        (EncodeError(), "encode_error"),
        (UnsupportedVersionError(version=2), "unsupported_version"),
        (ConcurrencyError(), "concurrency_error"),
        (StorageError(), "storage_error"),
        (StorageIntegrityError(), "storage_integrity_error"),
        (TransportError(), "transport_error"),
        (ProviderTransportError(), "provider_transport_error"),
        (CapabilityTransportError(), "capability_transport_error"),
        (CapabilityProtocolError(), "capability_protocol_error"),
    ],
)
def test_exceptions_expose_stable_safe_codes(error: OpenRundError, code: str) -> None:
    assert error.code == code
    assert code in str(error)
    assert code in repr(error)


def test_validation_error_preserves_json_pointer_and_bounded_safe_detail() -> None:
    error = ValidationError(
        code="event_missing_required_field",
        pointer="/payload/runID",
        safe_detail="required field is absent" * 40,
    )

    assert error.pointer == "/payload/runID"
    assert error.safe_detail is not None
    assert len(error.safe_detail.encode("utf-8")) <= 256
    assert error.pointer in str(error)

    with pytest.raises(FrozenInstanceError):
        error.code = "changed"


@pytest.mark.parametrize(
    "unsafe_detail",
    [
        "token=super-secret-value",
        "Authorization: Bearer provider-secret",
        "provider body contains private response",
        "/Users/alice/private/run.db",
        r"C:\\Users\\alice\\private\\run.db",
    ],
)
def test_error_text_and_repr_redact_sensitive_safe_detail(unsafe_detail: str) -> None:
    error = ProviderTransportError(safe_detail=unsafe_detail)

    rendered = f"{error!s} {error!r}"
    assert unsafe_detail not in rendered
    assert "super-secret-value" not in rendered
    assert "provider-secret" not in rendered
    assert "/Users/alice" not in rendered
    assert "C:\\Users\\alice" not in rendered
    assert error.safe_detail == "[redacted]"


def test_error_detail_rejects_raw_bytes_and_invalid_pointer() -> None:
    with pytest.raises(TypeError):
        ValidationError(code="invalid", safe_detail=b"raw-secret")  # type: ignore[arg-type]

    with pytest.raises(ValueError):
        ValidationError(code="invalid", pointer="payload/value")


def test_expected_position_conflict_keeps_safe_structured_fields() -> None:
    error = ExpectedPositionConflict(
        run_id="run-public-id",
        expected_position=4,
        actual_position=5,
    )

    assert error.code == "expected_position_conflict"
    assert error.run_id == "run-public-id"
    assert error.expected_position == 4
    assert error.actual_position == 5
    assert "run-public-id" in str(error)
    assert "4" in str(error)
    assert "5" in str(error)


def test_expected_position_conflict_rejects_boolean_or_negative_positions() -> None:
    with pytest.raises(TypeError):
        ExpectedPositionConflict(run_id="run", expected_position=True, actual_position=1)

    with pytest.raises(ValueError):
        ExpectedPositionConflict(run_id="run", expected_position=-1, actual_position=1)


def test_unsupported_version_preserves_only_a_safe_scalar_version() -> None:
    error = UnsupportedVersionError(version=2, pointer="/version")

    assert error.version == 2
    assert error.pointer == "/version"

    with pytest.raises(TypeError):
        UnsupportedVersionError(version=b"private body")  # type: ignore[arg-type]


def test_semantic_immutability_allows_python_exception_runtime_metadata() -> None:
    @contextmanager
    def reraising_boundary() -> Iterator[None]:
        try:
            yield
        except ValidationError:
            raise

    error = ValidationError(code="boundary_failure")

    with pytest.raises(ValidationError, match="boundary_failure"), reraising_boundary():
        raise error
    assert error.__traceback__ is not None
    error.__traceback__ = None
    with pytest.raises(FrozenInstanceError):
        error.code = "changed"
