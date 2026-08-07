"""Closed, local-only Git operations on verified repositories."""

from __future__ import annotations

import base64
import hashlib
import os
import re
import stat
from dataclasses import dataclass
from pathlib import Path
from typing import final

from openrund.capabilities._registry import ActionTransportBinding, RegisteredCapability
from openrund.capabilities._sandbox import FilesystemMount, RootSandbox
from openrund.capabilities._transports import InProcessTransport
from openrund.capabilities.process import ProcessBinding, ProcessCapability
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
from openrund.contracts.content import Content, EffectEntry, EvidenceEntry
from openrund.contracts.ids import ActionId, CapabilityId
from openrund.contracts.json import JsonArray, JsonObject, freeze_json
from openrund.errors import CapabilityExecutionError, ValidationError
from openrund.paths import PathInput, PortablePath
from openrund.ports.capabilities import CapabilityInvocation

_IDENTITY_NAME = re.compile(r"^[a-z][a-z0-9._-]{0,63}$")
_OBJECT_ID = re.compile(r"^[0-9a-f]{40}(?:[0-9a-f]{24})?$")
_CONFIG_SECTION = re.compile(r'^\[\s*([A-Za-z][A-Za-z0-9-]*)(?:\s+"(?:[^"\\]|\\.)*")?\s*\]$')
_FORBIDDEN_CONFIG_SECTIONS = frozenset(
    {"alias", "credential", "diff", "filter", "include", "includeif", "pager"}
)
_FORBIDDEN_CORE_KEYS = frozenset(
    {
        "askpass",
        "attributesfile",
        "editor",
        "excludesfile",
        "fsmonitor",
        "gitproxy",
        "hookspath",
        "pager",
        "sshcommand",
    }
)
_MAX_CONFIG_BYTES = 1024 * 1024


def _schema(value: object) -> JsonObject:
    frozen = freeze_json(value)
    assert isinstance(frozen, JsonObject)
    return frozen


def _execution(code: str) -> CapabilityExecutionError:
    return CapabilityExecutionError(code=code)


@final
@dataclass(frozen=True, slots=True, kw_only=True)
class GitIdentity:
    """One explicitly configured commit author and committer identity."""

    name: str
    author_name: str
    author_email: str

    def __post_init__(self) -> None:
        if not isinstance(self.name, str) or _IDENTITY_NAME.fullmatch(self.name) is None:
            raise ValidationError(code="git_identity_name_invalid")
        if (
            not isinstance(self.author_name, str)
            or self.author_name.strip() == ""
            or any(character in self.author_name for character in ("\x00", "\r", "\n"))
        ):
            raise ValidationError(code="git_author_name_invalid")
        if (
            not isinstance(self.author_email, str)
            or self.author_email.strip() != self.author_email
            or "@" not in self.author_email
            or any(character in self.author_email for character in ("\x00", "\r", "\n", "<", ">"))
        ):
            raise ValidationError(code="git_author_email_invalid")


@final
@dataclass(frozen=True, slots=True, kw_only=True)
class _GitRepository:
    mount: FilesystemMount
    path: Path
    relative_path: str | None
    git_directory: Path

    @property
    def display_path(self) -> str:
        return "." if self.relative_path is None else self.relative_path


@final
@dataclass(frozen=True, slots=True, kw_only=True)
class _GitCommandResult:
    stdout: bytes
    stderr: bytes
    stdout_bytes: int
    stderr_bytes: int
    stdout_sha256: str
    stderr_sha256: str
    stdout_truncated: bool
    stderr_truncated: bool


def _data(invocation: CapabilityInvocation) -> JsonObject:
    if not isinstance(invocation.input.data, JsonObject):
        raise _execution("git_input_invalid")
    return invocation.input.data


def _required_text(data: JsonObject, name: str) -> str:
    value = data.get(name)
    if not isinstance(value, str):
        raise _execution("git_input_invalid")
    return value


def _optional_text(data: JsonObject, name: str) -> str | None:
    value = data.get(name)
    if value is None:
        return None
    if not isinstance(value, str):
        raise _execution("git_input_invalid")
    return value


def _flag(data: JsonObject, name: str) -> bool:
    value = data.get(name)
    if value is None:
        return False
    if not isinstance(value, bool):
        raise _execution("git_input_invalid")
    return value


def _paths(data: JsonObject, name: str, *, required: bool) -> tuple[str, ...]:
    value = data.get(name)
    if value is None and not required:
        return ()
    if not isinstance(value, JsonArray) or (required and not value):
        raise _execution("git_paths_invalid")
    return tuple(_portable_git_path(item) for item in value)


def _portable_git_path(value: object) -> str:
    if not isinstance(value, str):
        raise _execution("git_path_invalid")
    try:
        portable = PortablePath(value=value)
    except ValidationError:
        raise _execution("git_path_invalid") from None
    if (
        portable.components[0] == ".git"
        or any(component.startswith("-") for component in portable.components)
        or any(ord(character) < 32 or ord(character) == 127 for character in portable.value)
    ):
        raise _execution("git_path_forbidden")
    return portable.value


def _text_preview(content: bytes, limit: int) -> str:
    return content[:limit].decode("utf-8", errors="replace")


def _metadata(result: _GitCommandResult) -> JsonObject:
    value = freeze_json(
        {
            "stdoutSha256": result.stdout_sha256,
            "stderrSha256": result.stderr_sha256,
            "stdoutBytes": result.stdout_bytes,
            "stderrBytes": result.stderr_bytes,
            "stdoutTruncated": result.stdout_truncated,
            "stderrTruncated": result.stderr_truncated,
        }
    )
    assert isinstance(value, JsonObject)
    return value


@final
@dataclass(frozen=True, slots=True, kw_only=True)
class GitCapability:
    mounts: tuple[FilesystemMount, ...]
    git_executable: PathInput
    identities: tuple[GitIdentity, ...]
    max_output_bytes: int = 1024 * 1024
    max_patch_bytes: int = 4 * 1024 * 1024
    max_stage_file_bytes: int = 64 * 1024 * 1024
    max_paths: int = 1024
    max_path_chars: int = 4096
    max_message_chars: int = 16_384
    max_git_entries: int = 200_000
    timeout_ms: int = 30_000
    preview_bytes: int = 512

    def __post_init__(self) -> None:
        try:
            mounts = tuple(self.mounts)
            identities = tuple(self.identities)
        except TypeError as error:
            raise ValidationError(code="git_configuration_invalid") from error
        RootSandbox(mounts)
        if not identities or any(not isinstance(item, GitIdentity) for item in identities):
            raise ValidationError(code="git_identities_invalid")
        if len({item.name for item in identities}) != len(identities):
            raise ValidationError(code="git_identity_duplicate")
        ProcessBinding(name="git", executable=self.git_executable)
        for name, value in (
            ("max_output_bytes", self.max_output_bytes),
            ("max_patch_bytes", self.max_patch_bytes),
            ("max_stage_file_bytes", self.max_stage_file_bytes),
            ("max_paths", self.max_paths),
            ("max_path_chars", self.max_path_chars),
            ("max_message_chars", self.max_message_chars),
            ("max_git_entries", self.max_git_entries),
            ("timeout_ms", self.timeout_ms),
            ("preview_bytes", self.preview_bytes),
        ):
            if isinstance(value, bool) or not isinstance(value, int) or value < 1:
                raise ValidationError(code=f"git_{name}_invalid")
        object.__setattr__(self, "mounts", mounts)
        object.__setattr__(self, "identities", identities)

    @property
    def sandbox(self) -> RootSandbox:
        return RootSandbox(self.mounts)

    def _properties(self) -> dict[str, object]:
        return {
            "repoMount": {"type": "string", "minLength": 1},
            "repoPath": {"type": "string", "minLength": 1, "maxLength": self.max_path_chars},
            "staged": {"type": "boolean"},
            "paths": {
                "type": "array",
                "minItems": 1,
                "maxItems": self.max_paths,
                "items": {"type": "string", "minLength": 1, "maxLength": self.max_path_chars},
            },
            "patch": {"type": "string"},
            "message": {"type": "string", "minLength": 1, "maxLength": self.max_message_chars},
            "identity": {
                "type": "string",
                "enum": [item.name for item in self.identities],
            },
        }

    def _action(
        self,
        name: str,
        description: str,
        required: tuple[str, ...],
        *,
        optional: tuple[str, ...] = (),
        posture: CapabilityAccessMode,
        reliability: CapabilityReliability,
        artifact: CapabilityArtifact | None = None,
    ) -> CapabilityAction:
        all_properties = self._properties()
        allowed = ("repoMount", "repoPath", *required, *optional)
        schema = _schema(
            {
                "type": "object",
                "required": ["repoMount", *required],
                "properties": {name: all_properties[name] for name in allowed},
                "additionalProperties": False,
            }
        )
        return CapabilityAction(
            name=name,
            description=description,
            posture=posture,
            reliability=reliability,
            input_schema=schema,
            output_schema=_schema({"type": "object", "additionalProperties": True}),
            artifacts=() if artifact is None else (artifact,),
            transport=CapabilityTransportMetadata(kind=CapabilityTransportKind.IN_PROCESS),
        )

    def actions(self) -> tuple[CapabilityAction, ...]:
        read = CapabilityAccessMode.READ
        write = CapabilityAccessMode.WRITE
        return (
            self._action(
                "status",
                "Read bounded porcelain status from a verified local repository",
                (),
                posture=read,
                reliability=CapabilityReliability.READ_ONLY,
                artifact=CapabilityArtifact(
                    kind="git.status", content_type="text/plain", required=True
                ),
            ),
            self._action(
                "diff",
                "Read a bounded local diff without external drivers",
                (),
                optional=("staged", "paths"),
                posture=read,
                reliability=CapabilityReliability.READ_ONLY,
                artifact=CapabilityArtifact(
                    kind="git.diff", content_type="text/x-diff", required=True
                ),
            ),
            self._action(
                "head",
                "Read the current local HEAD object identity",
                (),
                posture=read,
                reliability=CapabilityReliability.READ_ONLY,
            ),
            self._action(
                "apply",
                "Apply one bounded checked patch to the local worktree",
                ("patch",),
                posture=write,
                reliability=CapabilityReliability.IRREVERSIBLE,
            ),
            self._action(
                "stage",
                "Stage explicit portable files without filters or pathspec expansion",
                ("paths",),
                posture=write,
                reliability=CapabilityReliability.IDEMPOTENT_MUTATION,
            ),
            self._action(
                "commit",
                "Create one local commit with a configured identity and no hooks",
                ("message", "identity"),
                posture=write,
                reliability=CapabilityReliability.IRREVERSIBLE,
            ),
        )

    def _repository(self, data: JsonObject) -> _GitRepository:
        mount_name = _required_text(data, "repoMount")
        relative = _optional_text(data, "repoPath")
        resolved = self.sandbox.resolve(mount_name, relative, write=True)
        try:
            root_status = resolved.path.lstat()
        except OSError:
            raise _execution("git_repository_unavailable") from None
        if stat.S_ISLNK(root_status.st_mode) or not stat.S_ISDIR(root_status.st_mode):
            raise _execution("git_repository_invalid")
        git_directory = resolved.path / ".git"
        try:
            git_status = git_directory.lstat()
            resolved_git = git_directory.resolve(strict=True)
        except OSError:
            raise _execution("git_repository_invalid") from None
        if stat.S_ISLNK(git_status.st_mode) or not stat.S_ISDIR(git_status.st_mode):
            raise _execution("git_directory_invalid")
        try:
            resolved_git.relative_to(resolved.mount.resolved_root)
            resolved_git.relative_to(resolved.path.resolve(strict=True))
        except ValueError:
            raise _execution("git_directory_escape") from None
        repository = _GitRepository(
            mount=resolved.mount,
            path=resolved.path,
            relative_path=None if resolved.portable is None else resolved.portable.value,
            git_directory=git_directory,
        )
        self._verify_git_directory(repository)
        return repository

    def _verify_git_directory(self, repository: _GitRepository) -> None:
        if (repository.git_directory / "objects" / "info" / "alternates").exists():
            raise _execution("git_object_alternates_forbidden")
        self._verify_config(repository.git_directory / "config")
        worktree_config = repository.git_directory / "config.worktree"
        if worktree_config.exists():
            self._verify_config(worktree_config)
        entries = 0
        for root, directories, files in os.walk(repository.git_directory, followlinks=False):
            for name in (*directories, *files):
                entries += 1
                if entries > self.max_git_entries:
                    raise _execution("git_directory_too_large")
                candidate = Path(root) / name
                try:
                    status = candidate.lstat()
                except OSError:
                    raise _execution("git_directory_unavailable") from None
                if stat.S_ISLNK(status.st_mode):
                    raise _execution("git_directory_symlink_forbidden")

    def _verify_config(self, path: Path) -> None:
        flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
        try:
            descriptor = os.open(path, flags)
        except OSError:
            raise _execution("git_config_unavailable") from None
        try:
            status = os.fstat(descriptor)
            if not stat.S_ISREG(status.st_mode) or status.st_size > _MAX_CONFIG_BYTES:
                raise _execution("git_config_invalid")
            content = os.read(descriptor, _MAX_CONFIG_BYTES + 1)
        finally:
            os.close(descriptor)
        try:
            text = content.decode("utf-8", errors="strict")
        except UnicodeDecodeError:
            raise _execution("git_config_invalid") from None
        section: str | None = None
        for raw_line in text.splitlines():
            line = raw_line.strip()
            if not line or line.startswith(("#", ";")):
                continue
            if line.startswith("["):
                match = _CONFIG_SECTION.fullmatch(line)
                if match is None:
                    raise _execution("git_config_invalid")
                section = match.group(1).lower()
                if section in _FORBIDDEN_CONFIG_SECTIONS:
                    raise _execution("git_repository_config_forbidden")
                continue
            if section is None:
                raise _execution("git_config_invalid")
            key = line.split("=", 1)[0].strip().lower()
            if section == "core" and key in _FORBIDDEN_CORE_KEYS:
                raise _execution("git_repository_config_forbidden")

    def _process_binding(self, identity: GitIdentity | None) -> ProcessBinding:
        environment: list[tuple[str, str]] = [
            ("GIT_CONFIG_NOSYSTEM", "1"),
            ("GIT_CONFIG_GLOBAL", os.devnull),
            ("GIT_TERMINAL_PROMPT", "0"),
            ("GIT_ASKPASS", ""),
            ("SSH_ASKPASS", ""),
            ("GCM_INTERACTIVE", "Never"),
            ("LC_ALL", "C"),
        ]
        if identity is not None:
            environment.extend(
                (
                    ("GIT_AUTHOR_NAME", identity.author_name),
                    ("GIT_AUTHOR_EMAIL", identity.author_email),
                    ("GIT_COMMITTER_NAME", identity.author_name),
                    ("GIT_COMMITTER_EMAIL", identity.author_email),
                )
            )
        return ProcessBinding(
            name="git",
            executable=self.git_executable,
            environment=tuple(environment),
        )

    def _git_arguments(self, operation: tuple[str, ...]) -> tuple[str, ...]:
        return (
            "--no-pager",
            "-c",
            f"core.hooksPath={os.devnull}",
            "-c",
            "core.fsmonitor=false",
            "-c",
            "core.pager=cat",
            "-c",
            "credential.helper=",
            "-c",
            "credential.interactive=false",
            "-c",
            "commit.gpgSign=false",
            "-c",
            "tag.gpgSign=false",
            "-c",
            "protocol.allow=never",
            *operation,
        )

    async def _run_git(
        self,
        repository: _GitRepository,
        operation: tuple[str, ...],
        *,
        stdin: bytes = b"",
        identity: GitIdentity | None = None,
    ) -> _GitCommandResult:
        process = ProcessCapability(
            mounts=self.mounts,
            bindings=(self._process_binding(identity),),
            max_arguments=max(64, self.max_paths + 32),
            max_argument_chars=max(self.max_path_chars, self.max_message_chars),
            max_stdin_bytes=max(self.max_patch_bytes, self.max_stage_file_bytes),
            max_output_bytes=self.max_output_bytes,
            default_timeout_ms=self.timeout_ms,
            max_timeout_ms=self.timeout_ms,
            preview_bytes=self.preview_bytes,
        )
        payload: dict[str, object] = {
            "executable": "git",
            "args": self._git_arguments(operation),
            "cwdMount": repository.mount.name,
            "timeoutMs": self.timeout_ms,
        }
        if repository.relative_path is not None:
            payload["cwdPath"] = repository.relative_path
        if stdin:
            payload["stdinBase64"] = base64.b64encode(stdin).decode("ascii")
        result = await process(
            CapabilityInvocation(
                action_id=ActionId(value="git-process"),
                capability_id=CapabilityId(value="process"),
                action_name="run",
                input=Content(data=payload),  # type: ignore[arg-type]
            )
        )
        output = result.output
        if not isinstance(output, JsonObject) or len(result.inline_artifacts) != 2:
            raise _execution("git_process_result_invalid")
        if (
            output.get("exitCode") != 0
            or output.get("timedOut") is not False
            or output.get("signal") is not None
        ):
            raise _execution("git_command_failed")
        stdout_artifact, stderr_artifact = result.inline_artifacts
        values = (
            output.get("stdoutBytes"),
            output.get("stderrBytes"),
            output.get("stdoutSha256"),
            output.get("stderrSha256"),
            output.get("stdoutTruncated"),
            output.get("stderrTruncated"),
        )
        if (
            not isinstance(values[0], int)
            or isinstance(values[0], bool)
            or not isinstance(values[1], int)
            or isinstance(values[1], bool)
            or not isinstance(values[2], str)
            or not isinstance(values[3], str)
            or not isinstance(values[4], bool)
            or not isinstance(values[5], bool)
        ):
            raise _execution("git_process_result_invalid")
        return _GitCommandResult(
            stdout=stdout_artifact.content,
            stderr=stderr_artifact.content,
            stdout_bytes=values[0],
            stderr_bytes=values[1],
            stdout_sha256=values[2],
            stderr_sha256=values[3],
            stdout_truncated=values[4],
            stderr_truncated=values[5],
        )

    @staticmethod
    def _control_text(result: _GitCommandResult) -> str:
        if result.stdout_truncated or result.stderr_truncated:
            raise _execution("git_control_output_too_large")
        try:
            return result.stdout.decode("ascii", errors="strict")
        except UnicodeDecodeError:
            raise _execution("git_control_output_invalid") from None

    def _worktree_path(
        self,
        repository: _GitRepository,
        relative: str,
        *,
        allow_missing: bool,
    ) -> tuple[Path, bool]:
        portable = PortablePath(value=relative)
        current = repository.path
        for index, component in enumerate(portable.components):
            current /= component
            final = index == len(portable.components) - 1
            try:
                status = current.lstat()
            except FileNotFoundError:
                if final and allow_missing:
                    return current, False
                raise _execution("git_path_not_found") from None
            except OSError:
                raise _execution("git_path_unavailable") from None
            if stat.S_ISLNK(status.st_mode):
                raise _execution("git_path_symlink_forbidden")
            if not final and not stat.S_ISDIR(status.st_mode):
                raise _execution("git_path_parent_invalid")
        try:
            current.resolve(strict=True).relative_to(repository.path.resolve(strict=True))
        except (OSError, ValueError):
            raise _execution("git_path_escape") from None
        return current, True

    def _read_stage_file(self, path: Path) -> tuple[bytes, str]:
        flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
        try:
            descriptor = os.open(path, flags)
        except OSError:
            raise _execution("git_stage_open_failed") from None
        chunks: list[bytes] = []
        size = 0
        try:
            status = os.fstat(descriptor)
            current = path.lstat()
            if (
                not stat.S_ISREG(status.st_mode)
                or stat.S_ISLNK(current.st_mode)
                or (status.st_dev, status.st_ino) != (current.st_dev, current.st_ino)
            ):
                raise _execution("git_stage_file_changed")
            while True:
                chunk = os.read(descriptor, min(65_536, self.max_stage_file_bytes + 1 - size))
                if not chunk:
                    mode = "100755" if status.st_mode & 0o111 else "100644"
                    return b"".join(chunks), mode
                chunks.append(chunk)
                size += len(chunk)
                if size > self.max_stage_file_bytes:
                    raise _execution("git_stage_file_too_large")
        finally:
            os.close(descriptor)

    async def _status(self, repository: _GitRepository) -> CapabilityResult:
        result = await self._run_git(
            repository,
            ("--no-optional-locks", "status", "--porcelain=v1", "--untracked-files=all"),
        )
        return CapabilityResult(
            output={
                "repoPath": repository.display_path,
                "sha256": result.stdout_sha256,
                "byteLength": result.stdout_bytes,
                "truncated": result.stdout_truncated,
            },  # type: ignore[arg-type]
            preview=_text_preview(result.stdout, self.preview_bytes) or "clean",
            effects=(EffectEntry(kind="git.status.read", summary=repository.display_path),),
            evidence=(EvidenceEntry(description=f"sha256:{result.stdout_sha256}"),),
            inline_artifacts=(
                CapabilityInlineArtifact(
                    kind="git.status",
                    content=result.stdout,
                    content_type="text/plain",
                    preview=_text_preview(result.stdout, self.preview_bytes),
                    metadata=_metadata(result),
                ),
            ),
        )

    async def _diff(self, repository: _GitRepository, data: JsonObject) -> CapabilityResult:
        paths = _paths(data, "paths", required=False)
        for path in paths:
            self._worktree_path(repository, path, allow_missing=True)
        operation = [
            "--no-optional-locks",
            "diff",
            "--no-ext-diff",
            "--no-textconv",
        ]
        if _flag(data, "staged"):
            operation.append("--staged")
        operation.extend(("--", *paths))
        result = await self._run_git(repository, tuple(operation))
        staged = _flag(data, "staged")
        return CapabilityResult(
            output={
                "repoPath": repository.display_path,
                "staged": staged,
                "paths": paths,
                "sha256": result.stdout_sha256,
                "byteLength": result.stdout_bytes,
                "truncated": result.stdout_truncated,
            },  # type: ignore[arg-type]
            preview=_text_preview(result.stdout, self.preview_bytes) or "no diff",
            effects=(EffectEntry(kind="git.diff.read", summary=repository.display_path),),
            evidence=(EvidenceEntry(description=f"sha256:{result.stdout_sha256}"),),
            inline_artifacts=(
                CapabilityInlineArtifact(
                    kind="git.diff",
                    content=result.stdout,
                    content_type="text/x-diff",
                    preview=_text_preview(result.stdout, self.preview_bytes),
                    metadata=_metadata(result),
                ),
            ),
        )

    async def _head(self, repository: _GitRepository) -> CapabilityResult:
        result = await self._run_git(
            repository, ("--no-optional-locks", "rev-parse", "--verify", "HEAD")
        )
        commit = self._control_text(result).strip()
        if _OBJECT_ID.fullmatch(commit) is None:
            raise _execution("git_head_invalid")
        return CapabilityResult(
            output={"repoPath": repository.display_path, "commit": commit},  # type: ignore[arg-type]
            preview=commit,
            effects=(EffectEntry(kind="git.head.read", summary=repository.display_path),),
            evidence=(EvidenceEntry(description=f"commit:{commit}"),),
        )

    async def _apply(self, repository: _GitRepository, data: JsonObject) -> CapabilityResult:
        patch = _required_text(data, "patch")
        try:
            content = patch.encode("utf-8", errors="strict")
        except UnicodeEncodeError:
            raise _execution("git_patch_utf8_invalid") from None
        if not content:
            raise _execution("git_patch_empty")
        if len(content) > self.max_patch_bytes:
            raise _execution("git_patch_too_large")
        await self._run_git(repository, ("apply", "--check", "-"), stdin=content)
        await self._run_git(
            repository,
            ("apply", "--whitespace=nowarn", "-"),
            stdin=content,
        )
        digest = hashlib.sha256(content).hexdigest()
        return CapabilityResult(
            output={"repoPath": repository.display_path, "patchSha256": digest},  # type: ignore[arg-type]
            effects=(EffectEntry(kind="git.patch.applied", summary=repository.display_path),),
            evidence=(EvidenceEntry(description=f"sha256:{digest}"),),
        )

    async def _stage(self, repository: _GitRepository, data: JsonObject) -> CapabilityResult:
        paths = _paths(data, "paths", required=True)
        for relative in paths:
            target, exists = self._worktree_path(repository, relative, allow_missing=True)
            if not exists:
                await self._run_git(repository, ("update-index", "--remove", "--", relative))
                continue
            content, mode = self._read_stage_file(target)
            hashed = await self._run_git(
                repository,
                ("hash-object", "-w", "--stdin"),
                stdin=content,
            )
            object_id = self._control_text(hashed).strip()
            if _OBJECT_ID.fullmatch(object_id) is None:
                raise _execution("git_object_id_invalid")
            await self._run_git(
                repository,
                ("update-index", "--add", "--cacheinfo", mode, object_id, relative),
            )
        return CapabilityResult(
            output={"repoPath": repository.display_path, "paths": paths},  # type: ignore[arg-type]
            effects=(EffectEntry(kind="git.paths.staged", summary=repository.display_path),),
        )

    def _identity(self, name: str) -> GitIdentity:
        identity = next((item for item in self.identities if item.name == name), None)
        if identity is None:
            raise _execution("git_identity_not_configured")
        return identity

    async def _commit(self, repository: _GitRepository, data: JsonObject) -> CapabilityResult:
        message = _required_text(data, "message")
        if message.strip() == "" or "\x00" in message or len(message) > self.max_message_chars:
            raise _execution("git_commit_message_invalid")
        identity = self._identity(_required_text(data, "identity"))
        await self._run_git(
            repository,
            ("commit", "--no-verify", "--no-gpg-sign", "--cleanup=verbatim", "--file=-"),
            stdin=message.encode("utf-8"),
            identity=identity,
        )
        head = await self._run_git(repository, ("rev-parse", "--verify", "HEAD"))
        commit = self._control_text(head).strip()
        if _OBJECT_ID.fullmatch(commit) is None:
            raise _execution("git_head_invalid")
        return CapabilityResult(
            output={
                "repoPath": repository.display_path,
                "commit": commit,
                "messageSha256": hashlib.sha256(message.encode("utf-8")).hexdigest(),
                "identity": identity.name,
            },  # type: ignore[arg-type]
            preview=commit,
            effects=(EffectEntry(kind="git.commit.created", summary=repository.display_path),),
            evidence=(EvidenceEntry(description=f"commit:{commit}"),),
        )

    async def __call__(self, invocation: CapabilityInvocation, /) -> CapabilityResult:
        data = _data(invocation)
        repository = self._repository(data)
        if invocation.action_name == "status":
            return await self._status(repository)
        if invocation.action_name == "diff":
            return await self._diff(repository, data)
        if invocation.action_name == "head":
            return await self._head(repository)
        if invocation.action_name == "apply":
            return await self._apply(repository, data)
        if invocation.action_name == "stage":
            return await self._stage(repository, data)
        if invocation.action_name == "commit":
            return await self._commit(repository, data)
        raise _execution("git_action_unsupported")

    def registered(self, *, capability_id: CapabilityId | None = None) -> RegisteredCapability:
        identifier = CapabilityId(value="git") if capability_id is None else capability_id
        actions = self.actions()
        transport = InProcessTransport(self)
        return RegisteredCapability(
            definition=Capability(capability_id=identifier, version="1", actions=actions),
            bindings=tuple(
                ActionTransportBinding(action_name=action.name, transport=transport)
                for action in actions
            ),
        )
