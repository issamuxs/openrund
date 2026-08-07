"""Private low-level mechanics for hardened local filesystem custody."""

from __future__ import annotations

import os
import stat
from dataclasses import dataclass
from pathlib import Path
from typing import Literal, final


@final
@dataclass(frozen=True, slots=True)
class LocalFilesystemError(Exception):
    reason: Literal[
        "missing",
        "create",
        "inspect",
        "symlink",
        "not_directory",
        "not_regular",
        "too_large",
        "open",
        "sync",
        "write",
    ]


def secure_directory_tree(path: Path, *, create: bool, mode: int = 0o700) -> Path:
    """Inspect each lexical component without following a symlink component."""

    absolute = path.absolute()
    current = Path(absolute.anchor)
    for component in absolute.parts[1:]:
        current /= component
        try:
            status = current.lstat()
        except FileNotFoundError:
            if not create:
                raise LocalFilesystemError("missing") from None
            try:
                current.mkdir(mode=mode)
                status = current.lstat()
            except FileExistsError:
                try:
                    status = current.lstat()
                except OSError:
                    raise LocalFilesystemError("inspect") from None
            except OSError:
                raise LocalFilesystemError("create") from None
        except OSError:
            raise LocalFilesystemError("inspect") from None
        if stat.S_ISLNK(status.st_mode):
            raise LocalFilesystemError("symlink")
        if not stat.S_ISDIR(status.st_mode):
            raise LocalFilesystemError("not_directory")
    return absolute


def regular_file_status(path: Path) -> os.stat_result:
    """Inspect one lexical path as a regular file without accepting symlinks."""

    try:
        status = path.lstat()
    except FileNotFoundError:
        raise LocalFilesystemError("missing") from None
    except OSError:
        raise LocalFilesystemError("inspect") from None
    if stat.S_ISLNK(status.st_mode) or not stat.S_ISREG(status.st_mode):
        raise LocalFilesystemError("not_regular")
    return status


def fsync_directory(path: Path) -> None:
    try:
        descriptor = os.open(path, os.O_RDONLY)
        try:
            os.fsync(descriptor)
        finally:
            os.close(descriptor)
    except OSError:
        raise LocalFilesystemError("sync") from None


def write_new_file(path: Path, content: bytes, *, mode: int = 0o600) -> None:
    """Create a new regular file exclusively, flush it, and never overwrite."""

    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    try:
        descriptor = os.open(path, flags, mode)
    except FileExistsError:
        raise
    except OSError:
        raise LocalFilesystemError("open") from None
    try:
        with os.fdopen(descriptor, "wb") as stream:
            descriptor = -1
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
    except OSError:
        raise LocalFilesystemError("write") from None
    finally:
        if descriptor >= 0:
            os.close(descriptor)


def read_regular_file(path: Path, *, limit: int) -> bytes:
    """Read a bounded regular file through a no-follow descriptor."""

    flags = os.O_RDONLY
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    try:
        descriptor = os.open(path, flags)
    except OSError:
        raise LocalFilesystemError("open") from None
    try:
        status = os.fstat(descriptor)
        if not stat.S_ISREG(status.st_mode):
            raise LocalFilesystemError("not_regular")
        if status.st_size > limit:
            raise LocalFilesystemError("too_large")
        with os.fdopen(descriptor, "rb") as stream:
            descriptor = -1
            content = stream.read(limit + 1)
    except OSError:
        raise LocalFilesystemError("open") from None
    finally:
        if descriptor >= 0:
            os.close(descriptor)
    if len(content) > limit:
        raise LocalFilesystemError("too_large")
    return content
