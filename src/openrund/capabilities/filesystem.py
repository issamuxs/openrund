"""Workspace-bounded filesystem Capability definitions and actions."""

from __future__ import annotations

import base64
import binascii
import difflib
import errno
import hashlib
import os
import stat
import tempfile
from collections.abc import Mapping
from dataclasses import dataclass
from typing import final

from openrund.capabilities._registry import ActionTransportBinding, RegisteredCapability
from openrund.capabilities._sandbox import (
    FilesystemMount,
    ResolvedSandboxPath,
    RootSandbox,
    open_read_no_follow,
)
from openrund.capabilities._transports import InProcessTransport
from openrund.codec import encode_json_value
from openrund.contracts.capabilities import (
    Capability,
    CapabilityAccessMode,
    CapabilityAction,
    CapabilityArtifact,
    CapabilityInlineArtifact,
    CapabilityReliability,
    CapabilityResult,
    CapabilityTransportKind,
    CapabilityTransportMetadata,
)
from openrund.contracts.content import EffectEntry, EvidenceEntry
from openrund.contracts.ids import CapabilityId
from openrund.contracts.json import JsonObject, freeze_json
from openrund.errors import CapabilityExecutionError, ValidationError
from openrund.ports.capabilities import CapabilityInvocation


def _schema(value: object) -> JsonObject:
    frozen = freeze_json(value)
    assert isinstance(frozen, JsonObject)
    return frozen


_INPUT_SCHEMA = _schema(
    {
        "type": "object",
        "required": ["mount"],
        "properties": {
            "mount": {"type": "string", "minLength": 1},
            "path": {"type": "string", "minLength": 1},
        },
        "additionalProperties": False,
    }
)
_OUTPUT_SCHEMA = _schema({"type": "object", "additionalProperties": True})
_CONTENT_PROPERTIES = {
    "mount": {"type": "string", "minLength": 1},
    "path": {"type": "string", "minLength": 1},
    "text": {"type": "string"},
    "contentBase64": {"type": "string"},
    "expectedSha256": {"type": "string", "minLength": 64, "maxLength": 64},
    "overwrite": {"type": "boolean"},
    "createParents": {"type": "boolean"},
}
_WRITE_SCHEMA = _schema(
    {
        "type": "object",
        "required": ["mount", "path"],
        "properties": _CONTENT_PROPERTIES,
        "additionalProperties": False,
    }
)
_DELETE_SCHEMA = _schema(
    {
        "type": "object",
        "required": ["mount", "path", "expectedSha256"],
        "properties": {
            "mount": {"type": "string", "minLength": 1},
            "path": {"type": "string", "minLength": 1},
            "expectedSha256": {"type": "string", "minLength": 64, "maxLength": 64},
        },
        "additionalProperties": False,
    }
)
_MOVE_SCHEMA = _schema(
    {
        "type": "object",
        "required": ["mount", "path", "toMount", "toPath", "expectedSha256"],
        "properties": {
            "mount": {"type": "string", "minLength": 1},
            "path": {"type": "string", "minLength": 1},
            "toMount": {"type": "string", "minLength": 1},
            "toPath": {"type": "string", "minLength": 1},
            "expectedSha256": {"type": "string", "minLength": 64, "maxLength": 64},
            "expectedTargetSha256": {
                "type": "string",
                "minLength": 64,
                "maxLength": 64,
            },
            "overwrite": {"type": "boolean"},
            "createParents": {"type": "boolean"},
        },
        "additionalProperties": False,
    }
)
_DIFF_SCHEMA = _schema(
    {
        "type": "object",
        "required": ["mount", "path", "against"],
        "properties": {
            "mount": {"type": "string", "minLength": 1},
            "path": {"type": "string", "minLength": 1},
            "against": {"type": "string"},
            "context": {"type": "integer", "minimum": 0, "maximum": 100},
        },
        "additionalProperties": False,
    }
)


def _action(
    name: str,
    description: str,
    *,
    posture: CapabilityAccessMode = CapabilityAccessMode.READ,
    reliability: CapabilityReliability = CapabilityReliability.READ_ONLY,
    input_schema: JsonObject = _INPUT_SCHEMA,
    artifacts: tuple[CapabilityArtifact, ...] = (),
) -> CapabilityAction:
    return CapabilityAction(
        name=name,
        description=description,
        posture=posture,
        reliability=reliability,
        input_schema=input_schema,
        output_schema=_OUTPUT_SCHEMA,
        artifacts=artifacts,
        transport=CapabilityTransportMetadata(kind=CapabilityTransportKind.IN_PROCESS),
    )


def _input(invocation: CapabilityInvocation) -> tuple[str, str | None]:
    data = _data(invocation)
    if not isinstance(data, JsonObject):
        raise CapabilityExecutionError(code="filesystem_input_invalid")
    mount = data.get("mount")
    path = data.get("path")
    if not isinstance(mount, str) or (path is not None and not isinstance(path, str)):
        raise CapabilityExecutionError(code="filesystem_input_invalid")
    return mount, path


def _data(invocation: CapabilityInvocation) -> JsonObject:
    data = invocation.input.data
    if not isinstance(data, JsonObject):
        raise CapabilityExecutionError(code="filesystem_input_invalid")
    return data


def _required_text(data: JsonObject, name: str) -> str:
    value = data.get(name)
    if not isinstance(value, str):
        raise CapabilityExecutionError(code="filesystem_input_invalid")
    return value


def _flag(data: JsonObject, name: str) -> bool:
    value = data.get(name)
    if value is None:
        return False
    if not isinstance(value, bool):
        raise CapabilityExecutionError(code="filesystem_input_invalid")
    return value


def _expected_hash(data: JsonObject, name: str = "expectedSha256") -> str | None:
    value = data.get(name)
    if value is None:
        return None
    if (
        not isinstance(value, str)
        or len(value) != 64
        or any(character not in "0123456789abcdef" for character in value)
    ):
        raise CapabilityExecutionError(code="filesystem_expected_hash_invalid")
    return value


def _input_bytes(data: JsonObject, limit: int) -> bytes:
    text = data.get("text")
    encoded = data.get("contentBase64")
    if (isinstance(text, str)) == (isinstance(encoded, str)):
        raise CapabilityExecutionError(code="filesystem_content_branch_invalid")
    if isinstance(text, str):
        try:
            content = text.encode("utf-8", errors="strict")
        except UnicodeEncodeError:
            raise CapabilityExecutionError(code="filesystem_content_utf8_invalid") from None
    elif isinstance(encoded, str):
        try:
            content = base64.b64decode(encoded.encode("ascii"), validate=True)
        except (UnicodeEncodeError, binascii.Error, ValueError):
            raise CapabilityExecutionError(code="filesystem_content_base64_invalid") from None
    else:
        raise CapabilityExecutionError(code="filesystem_content_branch_invalid")
    if len(content) > limit:
        raise CapabilityExecutionError(code="filesystem_write_too_large")
    return content


def _read_descriptor(descriptor: int, limit: int) -> bytes:
    chunks: list[bytes] = []
    size = 0
    try:
        while True:
            chunk = os.read(descriptor, min(65_536, limit + 1 - size))
            if not chunk:
                return b"".join(chunks)
            chunks.append(chunk)
            size += len(chunk)
            if size > limit:
                raise CapabilityExecutionError(code="filesystem_read_too_large")
    finally:
        os.close(descriptor)


def _text_preview(content: bytes) -> tuple[str | None, str]:
    try:
        text = content.decode("utf-8", errors="strict")
    except UnicodeDecodeError:
        return None, "application/octet-stream"
    preview = text[:512]
    return preview, "text/plain; charset=utf-8"


def _file_bytes(path: ResolvedSandboxPath, limit: int) -> bytes:
    descriptor, status = open_read_no_follow(path)
    if status.st_size > limit:
        os.close(descriptor)
        raise CapabilityExecutionError(code="filesystem_read_too_large")
    return _read_descriptor(descriptor, limit)


def _fsync_directory(path: os.PathLike[str] | str) -> None:
    flags = os.O_RDONLY | getattr(os, "O_DIRECTORY", 0) | getattr(os, "O_NOFOLLOW", 0)
    try:
        descriptor = os.open(path, flags)
        try:
            os.fsync(descriptor)
        finally:
            os.close(descriptor)
    except OSError:
        raise CapabilityExecutionError(code="filesystem_directory_sync_failed") from None


def _receipt(kind: str, values: Mapping[str, object]) -> CapabilityInlineArtifact:
    payload = freeze_json({"operation": kind, **values})
    metadata = freeze_json(values)
    assert isinstance(metadata, JsonObject)
    return CapabilityInlineArtifact(
        kind="filesystem.receipt",
        content=encode_json_value(payload),
        content_type="application/json",
        metadata=metadata,
    )


def _atomic_replace(target: ResolvedSandboxPath, content: bytes) -> None:
    parent = target.path.parent
    descriptor: int | None = None
    temporary: str | None = None
    try:
        descriptor, temporary = tempfile.mkstemp(prefix=".openrund-stage-", dir=parent)
        view = memoryview(content)
        written = 0
        while written < len(view):
            count = os.write(descriptor, view[written:])
            if count < 1:
                raise CapabilityExecutionError(code="filesystem_stage_write_failed")
            written += count
        os.fsync(descriptor)
        os.close(descriptor)
        descriptor = None
        os.replace(temporary, target.path)
        temporary = None
        _fsync_directory(parent)
    except CapabilityExecutionError:
        raise
    except OSError:
        raise CapabilityExecutionError(code="filesystem_atomic_replace_failed") from None
    finally:
        if descriptor is not None:
            os.close(descriptor)
        if temporary is not None:
            try:
                os.unlink(temporary)
            except FileNotFoundError:
                pass
            except OSError:
                raise CapabilityExecutionError(code="filesystem_stage_cleanup_failed") from None


@final
@dataclass(frozen=True, slots=True, kw_only=True)
class FilesystemCapability:
    mounts: tuple[FilesystemMount, ...]
    max_read_bytes: int = 8 * 1024 * 1024
    max_write_bytes: int = 8 * 1024 * 1024
    max_diff_bytes: int = 2 * 1024 * 1024
    max_list_entries: int = 10_000

    def __post_init__(self) -> None:
        try:
            mounts = tuple(self.mounts)
        except TypeError as error:
            raise ValidationError(code="filesystem_mounts_invalid") from error
        RootSandbox(mounts)
        for name, value in (
            ("max_read_bytes", self.max_read_bytes),
            ("max_write_bytes", self.max_write_bytes),
            ("max_diff_bytes", self.max_diff_bytes),
            ("max_list_entries", self.max_list_entries),
        ):
            if isinstance(value, bool) or not isinstance(value, int) or value < 1:
                raise ValidationError(code=f"filesystem_{name}_invalid")
        object.__setattr__(self, "mounts", mounts)

    @property
    def sandbox(self) -> RootSandbox:
        return RootSandbox(self.mounts)

    async def __call__(self, invocation: CapabilityInvocation, /) -> CapabilityResult:
        if invocation.action_name in ("write", "update"):
            return self._write(invocation, update=invocation.action_name == "update")
        if invocation.action_name == "delete":
            return self._delete(invocation)
        if invocation.action_name == "move":
            return self._move(invocation)
        if invocation.action_name == "diff":
            return self._diff(invocation)
        mount, relative = _input(invocation)
        if invocation.action_name == "read":
            return self._read(mount, relative)
        if invocation.action_name == "list":
            return self._list(mount, relative)
        if invocation.action_name == "stat":
            return self._stat(mount, relative)
        raise CapabilityExecutionError(code="filesystem_action_unsupported")

    def _write(self, invocation: CapabilityInvocation, *, update: bool) -> CapabilityResult:
        data = _data(invocation)
        mount = _required_text(data, "mount")
        relative = _required_text(data, "path")
        content = _input_bytes(data, self.max_write_bytes)
        expected = _expected_hash(data)
        overwrite = _flag(data, "overwrite")
        create_parents = _flag(data, "createParents")
        target = self.sandbox.prepare_write_target(
            mount,
            relative,
            create_parents=create_parents,
        )
        before: str | None = None
        if target.exists:
            before_content = _file_bytes(target, self.max_read_bytes)
            before = hashlib.sha256(before_content).hexdigest()
            if update and expected is None:
                raise CapabilityExecutionError(code="filesystem_expected_hash_required")
            if expected is not None and expected != before:
                raise CapabilityExecutionError(code="filesystem_stale_hash")
            if not update and not overwrite:
                raise CapabilityExecutionError(code="filesystem_target_exists")
            if not update and expected is None:
                raise CapabilityExecutionError(code="filesystem_expected_hash_required")
        else:
            if update:
                raise CapabilityExecutionError(code="filesystem_update_target_missing")
            if expected is not None:
                raise CapabilityExecutionError(code="filesystem_expected_hash_without_target")
        after = hashlib.sha256(content).hexdigest()
        current_target = self.sandbox.prepare_write_target(mount, relative)
        if current_target.exists != target.exists:
            raise CapabilityExecutionError(code="filesystem_target_changed")
        if current_target.exists:
            current_hash = hashlib.sha256(
                _file_bytes(current_target, self.max_read_bytes)
            ).hexdigest()
            if current_hash != before:
                raise CapabilityExecutionError(code="filesystem_target_changed")
        _atomic_replace(current_target, content)
        operation = "update" if update else "write"
        receipt = {
            "mount": mount,
            "path": relative,
            "beforeSha256": before,
            "afterSha256": after,
            "byteLength": len(content),
            "atomic": True,
        }
        return CapabilityResult(
            output=receipt,  # type: ignore[arg-type]
            preview=f"{operation} {relative}",
            effects=(EffectEntry(kind=f"filesystem.{operation}", summary=relative),),
            evidence=(EvidenceEntry(description=f"sha256:{after}"),),
            inline_artifacts=(_receipt(operation, receipt),),
        )

    def _delete(self, invocation: CapabilityInvocation) -> CapabilityResult:
        data = _data(invocation)
        mount = _required_text(data, "mount")
        relative = _required_text(data, "path")
        expected = _expected_hash(data)
        assert expected is not None
        target = self.sandbox.resolve(mount, relative, write=True)
        content = _file_bytes(target, self.max_read_bytes)
        before = hashlib.sha256(content).hexdigest()
        if expected != before:
            raise CapabilityExecutionError(code="filesystem_stale_hash")
        try:
            current = target.path.lstat()
            if stat.S_ISLNK(current.st_mode) or not stat.S_ISREG(current.st_mode):
                raise CapabilityExecutionError(code="filesystem_delete_file_required")
            target.path.unlink()
            _fsync_directory(target.path.parent)
        except CapabilityExecutionError:
            raise
        except OSError:
            raise CapabilityExecutionError(code="filesystem_delete_failed") from None
        receipt = {"mount": mount, "path": relative, "beforeSha256": before}
        return CapabilityResult(
            output=receipt,  # type: ignore[arg-type]
            preview=f"delete {relative}",
            effects=(EffectEntry(kind="filesystem.delete", summary=relative),),
            evidence=(EvidenceEntry(description=f"deleted-sha256:{before}"),),
            inline_artifacts=(_receipt("delete", receipt),),
        )

    def _move(self, invocation: CapabilityInvocation) -> CapabilityResult:
        data = _data(invocation)
        mount = _required_text(data, "mount")
        relative = _required_text(data, "path")
        to_mount = _required_text(data, "toMount")
        to_path = _required_text(data, "toPath")
        if mount == to_mount and relative == to_path:
            raise CapabilityExecutionError(code="filesystem_move_same_path")
        expected = _expected_hash(data)
        assert expected is not None
        overwrite = _flag(data, "overwrite")
        source = self.sandbox.resolve(mount, relative, write=True)
        source_content = _file_bytes(source, self.max_read_bytes)
        source_hash = hashlib.sha256(source_content).hexdigest()
        if source_hash != expected:
            raise CapabilityExecutionError(code="filesystem_stale_hash")
        target = self.sandbox.prepare_write_target(
            to_mount,
            to_path,
            create_parents=_flag(data, "createParents"),
        )
        target_before: str | None = None
        if target.exists:
            if not overwrite:
                raise CapabilityExecutionError(code="filesystem_target_exists")
            target_content = _file_bytes(target, self.max_read_bytes)
            target_before = hashlib.sha256(target_content).hexdigest()
            expected_target = _expected_hash(data, "expectedTargetSha256")
            if expected_target is None:
                raise CapabilityExecutionError(code="filesystem_target_hash_required")
            if expected_target != target_before:
                raise CapabilityExecutionError(code="filesystem_target_stale_hash")
        try:
            source_parent = source.path.parent.stat()
            target_parent = target.path.parent.stat()
            if source_parent.st_dev != target_parent.st_dev:
                raise CapabilityExecutionError(code="filesystem_cross_device_move_forbidden")
            source_current = _file_bytes(source, self.max_read_bytes)
            if hashlib.sha256(source_current).hexdigest() != expected:
                raise CapabilityExecutionError(code="filesystem_stale_hash")
            current_target = self.sandbox.prepare_write_target(to_mount, to_path)
            if current_target.exists != target.exists:
                raise CapabilityExecutionError(code="filesystem_target_changed")
            if current_target.exists:
                current_target_hash = hashlib.sha256(
                    _file_bytes(current_target, self.max_read_bytes)
                ).hexdigest()
                if current_target_hash != target_before:
                    raise CapabilityExecutionError(code="filesystem_target_changed")
            os.replace(source.path, target.path)
            _fsync_directory(source.path.parent)
            if target.path.parent != source.path.parent:
                _fsync_directory(target.path.parent)
        except CapabilityExecutionError:
            raise
        except OSError as error:
            if error.errno == errno.EXDEV:
                raise CapabilityExecutionError(
                    code="filesystem_cross_device_move_forbidden"
                ) from None
            raise CapabilityExecutionError(code="filesystem_move_failed") from None
        receipt = {
            "mount": mount,
            "path": relative,
            "toMount": to_mount,
            "toPath": to_path,
            "sha256": source_hash,
            "replacedSha256": target_before,
            "atomic": True,
        }
        return CapabilityResult(
            output=receipt,  # type: ignore[arg-type]
            preview=f"move {relative} to {to_path}",
            effects=(EffectEntry(kind="filesystem.move", summary=relative),),
            evidence=(EvidenceEntry(description=f"sha256:{source_hash}"),),
            inline_artifacts=(_receipt("move", receipt),),
        )

    def _diff(self, invocation: CapabilityInvocation) -> CapabilityResult:
        data = _data(invocation)
        mount = _required_text(data, "mount")
        relative = _required_text(data, "path")
        against = _required_text(data, "against")
        context_value = data.get("context")
        context = 3 if context_value is None else context_value
        if isinstance(context, bool) or not isinstance(context, int) or not 0 <= context <= 100:
            raise CapabilityExecutionError(code="filesystem_diff_context_invalid")
        target = self.sandbox.resolve(mount, relative)
        content = _file_bytes(target, self.max_read_bytes)
        try:
            current = content.decode("utf-8", errors="strict")
        except UnicodeDecodeError:
            raise CapabilityExecutionError(code="filesystem_diff_text_required") from None
        diff_text = "".join(
            difflib.unified_diff(
                current.splitlines(keepends=True),
                against.splitlines(keepends=True),
                fromfile=relative,
                tofile=f"{relative} (proposed)",
                n=context,
            )
        )
        diff_bytes = diff_text.encode("utf-8")
        if len(diff_bytes) > self.max_diff_bytes:
            raise CapabilityExecutionError(code="filesystem_diff_too_large")
        digest = hashlib.sha256(content).hexdigest()
        return CapabilityResult(
            output={
                "mount": mount,
                "path": relative,
                "sha256": digest,
                "changed": current != against,
                "diffByteLength": len(diff_bytes),
            },  # type: ignore[arg-type]
            preview=diff_text[:512],
            effects=(EffectEntry(kind="filesystem.diff", summary=relative),),
            evidence=(EvidenceEntry(description=f"base-sha256:{digest}"),),
            inline_artifacts=(
                CapabilityInlineArtifact(
                    kind="filesystem.diff",
                    content=diff_bytes,
                    content_type="text/x-diff; charset=utf-8",
                    preview=diff_text[:512],
                ),
            ),
        )

    def _read(self, mount: str, relative: str | None) -> CapabilityResult:
        if relative is None:
            raise CapabilityExecutionError(code="filesystem_file_path_required")
        resolved = self.sandbox.resolve(mount, relative)
        descriptor, status = open_read_no_follow(resolved)
        if status.st_size > self.max_read_bytes:
            os.close(descriptor)
            raise CapabilityExecutionError(code="filesystem_read_too_large")
        content = _read_descriptor(descriptor, self.max_read_bytes)
        preview, content_type = _text_preview(content)
        digest = hashlib.sha256(content).hexdigest()
        return CapabilityResult(
            output={
                "mount": mount,
                "path": relative,
                "byteLength": len(content),
                "sha256": digest,
                "text": preview,
            },  # type: ignore[arg-type]
            preview=preview,
            effects=(EffectEntry(kind="filesystem.read", summary=relative),),
            evidence=(EvidenceEntry(description=f"sha256:{digest}"),),
            inline_artifacts=(
                CapabilityInlineArtifact(
                    kind="filesystem.file",
                    content=content,
                    content_type=content_type,
                    preview=preview,
                    metadata={"mount": mount, "path": relative, "sha256": digest},  # type: ignore[arg-type]
                ),
            ),
        )

    def _list(self, mount: str, relative: str | None) -> CapabilityResult:
        resolved = self.sandbox.resolve(mount, relative)
        try:
            status = resolved.path.lstat()
        except OSError:
            raise CapabilityExecutionError(code="filesystem_path_unavailable") from None
        if not stat.S_ISDIR(status.st_mode):
            raise CapabilityExecutionError(code="filesystem_not_directory")
        entries: list[dict[str, object]] = []
        try:
            with os.scandir(resolved.path) as iterator:
                for entry in iterator:
                    if len(entries) >= self.max_list_entries:
                        raise CapabilityExecutionError(code="filesystem_list_too_large")
                    entry_status = entry.stat(follow_symlinks=False)
                    if entry.is_symlink():
                        kind = "symlink"
                    elif stat.S_ISREG(entry_status.st_mode):
                        kind = "file"
                    elif stat.S_ISDIR(entry_status.st_mode):
                        kind = "directory"
                    else:
                        kind = "other"
                    entries.append(
                        {
                            "name": entry.name,
                            "kind": kind,
                            "byteLength": entry_status.st_size if kind == "file" else None,
                        }
                    )
        except CapabilityExecutionError:
            raise
        except OSError:
            raise CapabilityExecutionError(code="filesystem_list_failed") from None
        entries.sort(key=lambda item: str(item["name"]).encode("utf-8", errors="surrogateescape"))
        return CapabilityResult(
            output={
                "mount": mount,
                "path": relative,
                "entries": entries,
                "count": len(entries),
            },  # type: ignore[arg-type]
            effects=(EffectEntry(kind="filesystem.list", summary=relative),),
        )

    def _stat(self, mount: str, relative: str | None) -> CapabilityResult:
        resolved = self.sandbox.resolve(mount, relative)
        try:
            status = resolved.path.lstat()
        except OSError:
            raise CapabilityExecutionError(code="filesystem_stat_failed") from None
        if stat.S_ISREG(status.st_mode):
            kind = "file"
            descriptor, _ = open_read_no_follow(resolved)
            content = _read_descriptor(descriptor, self.max_read_bytes)
            digest: str | None = hashlib.sha256(content).hexdigest()
        elif stat.S_ISDIR(status.st_mode):
            kind = "directory"
            digest = None
        else:
            raise CapabilityExecutionError(code="filesystem_type_unsupported")
        return CapabilityResult(
            output={
                "mount": mount,
                "path": relative,
                "kind": kind,
                "byteLength": status.st_size if kind == "file" else None,
                "sha256": digest,
                "modifiedNs": status.st_mtime_ns,
            },  # type: ignore[arg-type]
            effects=(EffectEntry(kind="filesystem.stat", summary=relative),),
        )

    def registered(self, capability_id: CapabilityId | None = None) -> RegisteredCapability:
        capability_id = CapabilityId(value="filesystem") if capability_id is None else capability_id
        if not isinstance(capability_id, CapabilityId):
            raise ValidationError(code="filesystem_capability_id_invalid")
        actions = (
            _action(
                "read",
                "Read one bounded regular file",
                artifacts=(CapabilityArtifact(kind="filesystem.file", required=True),),
            ),
            _action("list", "List one bounded directory without following symlinks"),
            _action("stat", "Inspect one file or directory without following symlinks"),
            _action(
                "write",
                "Create or explicitly overwrite one regular file atomically",
                posture=CapabilityAccessMode.WRITE,
                reliability=CapabilityReliability.IDEMPOTENT_MUTATION,
                input_schema=_WRITE_SCHEMA,
                artifacts=(CapabilityArtifact(kind="filesystem.receipt", required=True),),
            ),
            _action(
                "update",
                "Update one regular file atomically at an expected hash",
                posture=CapabilityAccessMode.READ_WRITE,
                reliability=CapabilityReliability.IDEMPOTENT_MUTATION,
                input_schema=_WRITE_SCHEMA,
                artifacts=(CapabilityArtifact(kind="filesystem.receipt", required=True),),
            ),
            _action(
                "delete",
                "Delete one regular file at an expected hash",
                posture=CapabilityAccessMode.WRITE,
                reliability=CapabilityReliability.IDEMPOTENT_MUTATION,
                input_schema=_DELETE_SCHEMA,
                artifacts=(CapabilityArtifact(kind="filesystem.receipt", required=True),),
            ),
            _action(
                "move",
                "Atomically move one regular file between governed roots",
                posture=CapabilityAccessMode.READ_WRITE,
                reliability=CapabilityReliability.IDEMPOTENT_MUTATION,
                input_schema=_MOVE_SCHEMA,
                artifacts=(CapabilityArtifact(kind="filesystem.receipt", required=True),),
            ),
            _action(
                "diff",
                "Build a bounded unified text diff without mutation",
                input_schema=_DIFF_SCHEMA,
                artifacts=(CapabilityArtifact(kind="filesystem.diff", required=True),),
            ),
        )
        definition = Capability(capability_id=capability_id, version="1", actions=actions)
        transport = InProcessTransport(self)
        return RegisteredCapability(
            definition=definition,
            bindings=tuple(
                ActionTransportBinding(action_name=action.name, transport=transport)
                for action in actions
            ),
        )
