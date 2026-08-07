"""Pure local and portable path value boundaries."""

from __future__ import annotations

import os
import re
from dataclasses import dataclass, field
from pathlib import Path, PurePosixPath
from typing import Final, final

from openrund.errors import ValidationError

_WINDOWS_DRIVE: Final = re.compile(r"^[A-Za-z]:")

type PathInput = str | os.PathLike[str]


@final
@dataclass(frozen=True, slots=True, kw_only=True)
class LocalPath:
    """A local lexical path spelling and its un-resolved ``Path`` value."""

    raw: str
    path: Path = field(init=False, repr=False, compare=False)

    def __post_init__(self) -> None:
        if not isinstance(self.raw, str):
            raise ValidationError(code="local_path_type_invalid")
        if "\x00" in self.raw:
            raise ValidationError(code="local_path_nul")
        object.__setattr__(self, "path", Path(self.raw))

    def __fspath__(self) -> str:
        return self.raw


@final
@dataclass(frozen=True, slots=True, kw_only=True)
class PortablePath:
    """Exact relative POSIX path safe for portable wire fields.

    This is a lexical value only. It never claims sandbox containment; a later
    filesystem adapter must resolve it under an explicit root and inspect
    symlinks before performing I/O.
    """

    value: str
    components: tuple[str, ...] = field(init=False)
    path: PurePosixPath = field(init=False, repr=False, compare=False)

    def __post_init__(self) -> None:
        if not isinstance(self.value, str):
            raise ValidationError(code="portable_path_type_invalid")
        if self.value == "":
            raise ValidationError(code="portable_path_empty")
        if "\x00" in self.value:
            raise ValidationError(code="portable_path_nul")
        if "\\" in self.value:
            raise ValidationError(code="portable_path_backslash")
        if self.value.startswith("/"):
            raise ValidationError(code="portable_path_rooted")
        if _WINDOWS_DRIVE.match(self.value) is not None:
            raise ValidationError(code="portable_path_drive")

        components = tuple(self.value.split("/"))
        if any(component == "" for component in components):
            raise ValidationError(code="portable_path_component_empty")
        if any(component == "." for component in components):
            raise ValidationError(code="portable_path_component_dot")
        if any(component == ".." for component in components):
            raise ValidationError(code="portable_path_component_parent")

        object.__setattr__(self, "components", components)
        object.__setattr__(self, "path", PurePosixPath(*components))

    def __fspath__(self) -> str:
        return self.value


def normalize_local_path(value: PathInput) -> LocalPath:
    """Normalize one string-returning PathLike without filesystem access."""

    try:
        raw = os.fspath(value)
    except TypeError as error:
        raise ValidationError(code="local_path_type_invalid") from error
    if not isinstance(raw, str):
        raise ValidationError(code="local_path_bytes_invalid")
    return LocalPath(raw=raw)
