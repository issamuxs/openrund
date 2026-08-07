"""Named-root filesystem confinement with portable paths and symlink rejection."""

from __future__ import annotations

import os
import re
import stat
from dataclasses import dataclass, field
from pathlib import Path
from typing import final

from openrund.contracts.capabilities import CapabilityAccessMode
from openrund.errors import CapabilityExecutionError, ValidationError
from openrund.paths import PathInput, PortablePath, normalize_local_path

_MOUNT_NAME = re.compile(r"^[a-z][a-z0-9._-]{0,63}$")


def _execution(code: str) -> CapabilityExecutionError:
    return CapabilityExecutionError(code=code)


@final
@dataclass(frozen=True, slots=True, kw_only=True)
class FilesystemMount:
    name: str
    root: PathInput
    access: CapabilityAccessMode
    resolved_root: Path = field(init=False, repr=False, compare=False)

    def __post_init__(self) -> None:
        if not isinstance(self.name, str) or _MOUNT_NAME.fullmatch(self.name) is None:
            raise ValidationError(code="filesystem_mount_name_invalid")
        if not isinstance(self.access, CapabilityAccessMode):
            raise ValidationError(code="filesystem_mount_access_invalid")
        local = normalize_local_path(self.root)
        if not local.path.is_absolute() or ".." in local.path.parts:
            raise ValidationError(code="filesystem_mount_root_invalid")
        try:
            status = local.path.lstat()
        except OSError as error:
            raise ValidationError(code="filesystem_mount_root_unavailable") from error
        if stat.S_ISLNK(status.st_mode) or not stat.S_ISDIR(status.st_mode):
            raise ValidationError(code="filesystem_mount_root_invalid")
        try:
            resolved = local.path.resolve(strict=True)
        except OSError as error:
            raise ValidationError(code="filesystem_mount_root_unavailable") from error
        object.__setattr__(self, "root", local.raw)
        object.__setattr__(self, "resolved_root", resolved)


@final
@dataclass(frozen=True, slots=True, kw_only=True)
class ResolvedSandboxPath:
    mount: FilesystemMount
    portable: PortablePath | None
    path: Path
    exists: bool


@final
class RootSandbox:
    __slots__ = ("_mounts",)

    def __init__(self, mounts: tuple[FilesystemMount, ...]) -> None:
        try:
            frozen = tuple(mounts)
        except TypeError as error:
            raise ValidationError(code="filesystem_mounts_invalid") from error
        if not frozen or any(not isinstance(item, FilesystemMount) for item in frozen):
            raise ValidationError(code="filesystem_mounts_invalid")
        if len({item.name for item in frozen}) != len(frozen):
            raise ValidationError(code="filesystem_mount_duplicate")
        self._mounts = frozen

    @property
    def mounts(self) -> tuple[FilesystemMount, ...]:
        return self._mounts

    def mount(self, name: str, /, *, write: bool = False) -> FilesystemMount:
        if not isinstance(name, str):
            raise _execution("filesystem_mount_invalid")
        mount = next((item for item in self._mounts if item.name == name), None)
        if mount is None:
            raise _execution("filesystem_mount_not_found")
        if write and mount.access not in (
            CapabilityAccessMode.WRITE,
            CapabilityAccessMode.READ_WRITE,
        ):
            raise _execution("filesystem_mount_read_only")
        if not write and mount.access not in (
            CapabilityAccessMode.READ,
            CapabilityAccessMode.READ_WRITE,
        ):
            raise _execution("filesystem_mount_write_only")
        self._verify_root(mount)
        return mount

    @staticmethod
    def _verify_root(mount: FilesystemMount) -> None:
        root = Path(mount.root)
        try:
            status = root.lstat()
            resolved = root.resolve(strict=True)
        except OSError:
            raise _execution("filesystem_mount_unavailable") from None
        if (
            stat.S_ISLNK(status.st_mode)
            or not stat.S_ISDIR(status.st_mode)
            or resolved != mount.resolved_root
        ):
            raise _execution("filesystem_mount_changed")

    def resolve(
        self,
        mount_name: str,
        relative_path: str | None,
        /,
        *,
        write: bool = False,
        allow_missing_leaf: bool = False,
    ) -> ResolvedSandboxPath:
        mount = self.mount(mount_name, write=write)
        portable: PortablePath | None = None
        if relative_path is not None:
            try:
                portable = PortablePath(value=relative_path)
            except ValidationError:
                raise _execution("filesystem_path_invalid") from None
        current = Path(mount.root)
        components = () if portable is None else portable.components
        for index, component in enumerate(components):
            current /= component
            final = index == len(components) - 1
            try:
                status = current.lstat()
            except FileNotFoundError:
                if final and allow_missing_leaf:
                    return ResolvedSandboxPath(
                        mount=mount,
                        portable=portable,
                        path=current,
                        exists=False,
                    )
                raise _execution("filesystem_path_not_found") from None
            except OSError:
                raise _execution("filesystem_path_unavailable") from None
            if stat.S_ISLNK(status.st_mode):
                raise _execution("filesystem_symlink_forbidden")
            if not final and not stat.S_ISDIR(status.st_mode):
                raise _execution("filesystem_parent_not_directory")
        try:
            resolved = current.resolve(strict=True)
        except FileNotFoundError:
            if allow_missing_leaf:
                return ResolvedSandboxPath(
                    mount=mount,
                    portable=portable,
                    path=current,
                    exists=False,
                )
            raise _execution("filesystem_path_not_found") from None
        except OSError:
            raise _execution("filesystem_path_unavailable") from None
        try:
            resolved.relative_to(mount.resolved_root)
        except ValueError:
            raise _execution("filesystem_path_escape") from None
        return ResolvedSandboxPath(
            mount=mount,
            portable=portable,
            path=current,
            exists=True,
        )

    def prepare_write_target(
        self,
        mount_name: str,
        relative_path: str,
        /,
        *,
        create_parents: bool = False,
    ) -> ResolvedSandboxPath:
        mount = self.mount(mount_name, write=True)
        try:
            portable = PortablePath(value=relative_path)
        except ValidationError:
            raise _execution("filesystem_path_invalid") from None
        if len(portable.components) == 0:
            raise _execution("filesystem_file_path_required")
        parent_components = portable.components[:-1]
        for index in range(len(parent_components)):
            partial = "/".join(parent_components[: index + 1])
            candidate = self.resolve(
                mount.name,
                partial,
                write=True,
                allow_missing_leaf=create_parents,
            )
            if not candidate.exists:
                try:
                    candidate.path.mkdir(mode=0o700)
                except FileExistsError:
                    pass
                except OSError:
                    raise _execution("filesystem_parent_create_failed") from None
                candidate = self.resolve(mount.name, partial, write=True)
            try:
                status = candidate.path.lstat()
            except OSError:
                raise _execution("filesystem_parent_unavailable") from None
            if stat.S_ISLNK(status.st_mode) or not stat.S_ISDIR(status.st_mode):
                raise _execution("filesystem_parent_not_directory")
        return self.resolve(
            mount.name,
            portable.value,
            write=True,
            allow_missing_leaf=True,
        )


def open_read_no_follow(path: ResolvedSandboxPath, /) -> tuple[int, os.stat_result]:
    flags = os.O_RDONLY
    no_follow = getattr(os, "O_NOFOLLOW", 0)
    try:
        descriptor = os.open(path.path, flags | no_follow)
    except OSError:
        raise _execution("filesystem_open_failed") from None
    try:
        status = os.fstat(descriptor)
        current = path.path.lstat()
        if (
            not stat.S_ISREG(status.st_mode)
            or stat.S_ISLNK(current.st_mode)
            or (status.st_dev, status.st_ino) != (current.st_dev, current.st_ino)
        ):
            raise _execution("filesystem_file_changed")
        return descriptor, status
    except BaseException:
        os.close(descriptor)
        raise
