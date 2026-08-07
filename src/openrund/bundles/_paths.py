"""Portable path validation helpers for Bundle manifest fields."""

from __future__ import annotations

from pathlib import Path

from openrund._localfs import LocalFilesystemError, secure_directory_tree
from openrund.errors import BundleError, ValidationError
from openrund.paths import PortablePath


def bundle_file_path(value: object, *, pointer: str | None = None) -> PortablePath:
    try:
        path = PortablePath(value=value)  # type: ignore[arg-type]
    except (TypeError, ValidationError):
        raise BundleError(code="bundle_path_invalid", pointer=pointer) from None
    if path.value.endswith("/"):
        raise BundleError(code="bundle_path_invalid", pointer=pointer)
    return path


def bundle_directory_path(value: object, *, pointer: str | None = None) -> str:
    if not isinstance(value, str) or not value.endswith("/"):
        raise BundleError(code="bundle_directory_invalid", pointer=pointer)
    try:
        PortablePath(value=value[:-1])
    except (TypeError, ValidationError):
        raise BundleError(code="bundle_directory_invalid", pointer=pointer) from None
    return value


def secure_directory(path: Path, *, create: bool, code: str) -> Path:
    """Inspect every lexical ancestor and optionally materialize missing directories."""

    try:
        return secure_directory_tree(path, create=create)
    except LocalFilesystemError:
        raise BundleError(code=code) from None
