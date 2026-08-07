"""Root-bound Markdown operations and strict stdio Capability registration."""

from __future__ import annotations

import difflib
import hashlib
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import final

from openrund.capabilities._registry import ActionTransportBinding, RegisteredCapability
from openrund.capabilities._sandbox import FilesystemMount, RootSandbox
from openrund.capabilities._transports import StdioJsonRpcConfig, StdioJsonRpcTransport
from openrund.capabilities.filesystem import _atomic_replace, _file_bytes
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
from openrund.contracts.json import JsonArray, JsonObject, JsonValue, freeze_json
from openrund.errors import CapabilityExecutionError, ValidationError
from openrund.paths import PathInput, normalize_local_path
from openrund.ports.capabilities import CapabilityInvocation

_HEADING = re.compile(r"^(#{1,6})[ \t]+(.+?)[ \t]*#*[ \t]*$")
_FRONTMATTER_KEY = re.compile(r"^[A-Za-z_][A-Za-z0-9_-]*$")
_ROOTS_ENV = "OPENRUND_DOCUMENT_ROOTS"


def _schema(value: object) -> JsonObject:
    frozen = freeze_json(value)
    assert isinstance(frozen, JsonObject)
    return frozen


_PROPERTIES: dict[str, object] = {
    "mount": {"type": "string", "minLength": 1},
    "path": {"type": "string", "minLength": 1},
    "text": {"type": "string"},
    "expectedSha256": {"type": "string", "minLength": 64, "maxLength": 64},
    "createParents": {"type": "boolean"},
    "heading": {"type": "string", "minLength": 1},
    "occurrence": {"type": "integer", "minimum": 1},
    "startLine": {"type": "integer", "minimum": 1},
    "endLine": {"type": "integer", "minimum": 1},
    "ensureNewline": {"type": "boolean"},
    "frontmatter": {"type": "object", "additionalProperties": True},
    "patches": {
        "type": "array",
        "minItems": 1,
        "items": {"type": "object", "additionalProperties": True},
    },
}
_OUTPUT_SCHEMA = _schema({"type": "object", "additionalProperties": True})


def _input_schema(required: tuple[str, ...]) -> JsonObject:
    return _schema(
        {
            "type": "object",
            "required": list(required),
            "properties": _PROPERTIES,
            "additionalProperties": False,
        }
    )


def _action(
    name: str,
    description: str,
    required: tuple[str, ...],
    *,
    mutation: bool = False,
    artifact_kind: str | None = None,
) -> CapabilityAction:
    return CapabilityAction(
        name=name,
        description=description,
        posture=CapabilityAccessMode.READ_WRITE if mutation else CapabilityAccessMode.READ,
        reliability=(
            CapabilityReliability.IDEMPOTENT_MUTATION
            if mutation
            else CapabilityReliability.READ_ONLY
        ),
        input_schema=_input_schema(required),
        output_schema=_OUTPUT_SCHEMA,
        artifacts=(
            (CapabilityArtifact(kind=artifact_kind, required=True),)
            if artifact_kind is not None
            else ()
        ),
        transport=CapabilityTransportMetadata(kind=CapabilityTransportKind.STDIO_JSON_RPC),
    )


def document_actions() -> tuple[CapabilityAction, ...]:
    return (
        _action(
            "read",
            "Read one Markdown document",
            ("mount", "path"),
            artifact_kind="documents.markdown",
        ),
        _action("headings", "List Markdown headings and line ranges", ("mount", "path")),
        _action("frontmatter_read", "Read deterministic frontmatter", ("mount", "path")),
        _action("section_read", "Read one exact heading section", ("mount", "path", "heading")),
        _action(
            "write",
            "Create or replace a complete Markdown document",
            ("mount", "path", "text"),
            mutation=True,
            artifact_kind="documents.diff",
        ),
        _action(
            "frontmatter_set",
            "Set deterministic frontmatter at an expected hash",
            ("mount", "path", "frontmatter", "expectedSha256"),
            mutation=True,
            artifact_kind="documents.diff",
        ),
        _action(
            "section_replace",
            "Replace one section body at an expected hash",
            ("mount", "path", "heading", "text", "expectedSha256"),
            mutation=True,
            artifact_kind="documents.diff",
        ),
        _action(
            "range_replace",
            "Replace one one-based line range at an expected hash",
            ("mount", "path", "startLine", "endLine", "text", "expectedSha256"),
            mutation=True,
            artifact_kind="documents.diff",
        ),
        _action(
            "append",
            "Append Markdown text at an expected hash",
            ("mount", "path", "text", "expectedSha256"),
            mutation=True,
            artifact_kind="documents.diff",
        ),
        _action(
            "patch",
            "Apply ordered structured Markdown patches at an expected hash",
            ("mount", "path", "patches", "expectedSha256"),
            mutation=True,
            artifact_kind="documents.diff",
        ),
    )


def _data(invocation: CapabilityInvocation) -> JsonObject:
    if not isinstance(invocation.input.data, JsonObject):
        raise CapabilityExecutionError(code="documents_input_invalid")
    return invocation.input.data


def _text(data: JsonObject, name: str) -> str:
    value = data.get(name)
    if not isinstance(value, str):
        raise CapabilityExecutionError(code="documents_input_invalid")
    return value


def _integer(data: JsonObject, name: str) -> int:
    value = data.get(name)
    if isinstance(value, bool) or not isinstance(value, int):
        raise CapabilityExecutionError(code="documents_input_invalid")
    return value


def _bool(data: JsonObject, name: str, default: bool = False) -> bool:
    value = data.get(name)
    if value is None:
        return default
    if not isinstance(value, bool):
        raise CapabilityExecutionError(code="documents_input_invalid")
    return value


def _hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _decode_document(content: bytes) -> str:
    try:
        return content.decode("utf-8", errors="strict")
    except UnicodeDecodeError:
        raise CapabilityExecutionError(code="documents_utf8_required") from None


def _frontmatter(text: str) -> tuple[JsonObject, str, bool]:
    lines = text.splitlines(keepends=True)
    if not lines or lines[0].rstrip("\r\n") != "---":
        empty = JsonObject(entries=())
        return empty, text, False
    closing = next(
        (index for index, line in enumerate(lines[1:], start=1) if line.rstrip("\r\n") == "---"),
        None,
    )
    if closing is None:
        raise CapabilityExecutionError(code="documents_frontmatter_unclosed")
    values: dict[str, JsonValue] = {}
    for line in lines[1:closing]:
        stripped = line.strip()
        if stripped == "" or stripped.startswith("#"):
            continue
        key, separator, raw_value = stripped.partition(":")
        if separator == "" or _FRONTMATTER_KEY.fullmatch(key) is None or key in values:
            raise CapabilityExecutionError(code="documents_frontmatter_invalid")
        candidate = raw_value.strip()
        try:
            parsed: object = json.loads(candidate) if candidate != "" else ""
        except json.JSONDecodeError:
            parsed = candidate
        try:
            values[key] = freeze_json(parsed)
        except ValidationError:
            raise CapabilityExecutionError(code="documents_frontmatter_invalid") from None
    frozen = freeze_json(values)
    assert isinstance(frozen, JsonObject)
    return frozen, "".join(lines[closing + 1 :]), True


def _render_frontmatter(values: JsonObject, body: str) -> str:
    rendered = ["---\n"]
    for key, value in sorted(values.entries, key=lambda item: item[0]):
        if _FRONTMATTER_KEY.fullmatch(key) is None:
            raise CapabilityExecutionError(code="documents_frontmatter_key_invalid")
        if isinstance(value, (JsonObject, JsonArray)):
            raise CapabilityExecutionError(code="documents_frontmatter_value_invalid")
        rendered.append(f"{key}: {json.dumps(value, ensure_ascii=False)}\n")
    rendered.append("---\n")
    if body and not body.startswith("\n"):
        rendered.append("\n")
    rendered.append(body)
    return "".join(rendered)


def _heading_entries(text: str) -> list[dict[str, object]]:
    lines = text.splitlines(keepends=True)
    raw: list[tuple[int, int, str]] = []
    fence: str | None = None
    for index, line in enumerate(lines, start=1):
        stripped = line.lstrip()
        marker = (
            "```" if stripped.startswith("```") else "~~~" if stripped.startswith("~~~") else None
        )
        if marker is not None:
            fence = None if fence == marker else marker if fence is None else fence
            continue
        if fence is not None:
            continue
        match = _HEADING.match(line.rstrip("\r\n"))
        if match is not None:
            raw.append((index, len(match.group(1)), match.group(2).strip()))
    entries: list[dict[str, object]] = []
    for offset, (start, level, title) in enumerate(raw):
        end = len(lines) + 1
        for candidate_start, candidate_level, _candidate_title in raw[offset + 1 :]:
            if candidate_level <= level:
                end = candidate_start
                break
        entries.append({"title": title, "level": level, "startLine": start, "endLine": end})
    return entries


def _section(data: JsonObject, text: str) -> tuple[int, int, dict[str, object]]:
    title = _text(data, "heading")
    matches = [entry for entry in _heading_entries(text) if entry["title"] == title]
    occurrence_value = data.get("occurrence")
    if occurrence_value is None:
        if len(matches) > 1:
            raise CapabilityExecutionError(code="documents_section_ambiguous")
        occurrence = 1
    elif isinstance(occurrence_value, int) and not isinstance(occurrence_value, bool):
        occurrence = occurrence_value
    else:
        raise CapabilityExecutionError(code="documents_input_invalid")
    if occurrence < 1 or occurrence > len(matches):
        raise CapabilityExecutionError(code="documents_section_not_found")
    selected = matches[occurrence - 1]
    selected_start = selected["startLine"]
    selected_end = selected["endLine"]
    assert isinstance(selected_start, int) and isinstance(selected_end, int)
    return selected_start, selected_end, selected


def _replace_range(text: str, start: int, end: int, replacement: str) -> str:
    lines = text.splitlines(keepends=True)
    if start < 1 or end < start or end > len(lines) + 1:
        raise CapabilityExecutionError(code="documents_range_invalid")
    lines[start - 1 : end - 1] = replacement.splitlines(keepends=True)
    return "".join(lines)


def _diff(before: str, after: str, path: str) -> str:
    return "".join(
        difflib.unified_diff(
            before.splitlines(keepends=True),
            after.splitlines(keepends=True),
            fromfile=path,
            tofile=f"{path} (updated)",
        )
    )


@final
@dataclass(frozen=True, slots=True, kw_only=True)
class MarkdownDocumentsHandler:
    mounts: tuple[FilesystemMount, ...]
    max_document_bytes: int = 8 * 1024 * 1024
    max_diff_bytes: int = 2 * 1024 * 1024

    def __post_init__(self) -> None:
        mounts = tuple(self.mounts)
        RootSandbox(mounts)
        if any(
            isinstance(value, bool) or not isinstance(value, int) or value < 1
            for value in (self.max_document_bytes, self.max_diff_bytes)
        ):
            raise ValidationError(code="documents_limit_invalid")
        object.__setattr__(self, "mounts", mounts)

    @property
    def sandbox(self) -> RootSandbox:
        return RootSandbox(tuple(self.mounts))

    def _read(self, data: JsonObject) -> tuple[str, str, str]:
        mount = _text(data, "mount")
        path = _text(data, "path")
        resolved = self.sandbox.resolve(mount, path)
        content = _file_bytes(resolved, self.max_document_bytes)
        document = _decode_document(content)
        return path, document, hashlib.sha256(content).hexdigest()

    def _mutation(self, data: JsonObject, operation: str) -> CapabilityResult:
        path, before, before_hash = self._read(data)
        expected = _text(data, "expectedSha256")
        if expected != before_hash:
            raise CapabilityExecutionError(code="documents_stale_hash")
        after = self._apply(data, before, operation)
        diff_text = _diff(before, after, path)
        diff_bytes = diff_text.encode("utf-8")
        if len(diff_bytes) > self.max_diff_bytes:
            raise CapabilityExecutionError(code="documents_diff_too_large")
        target = self.sandbox.prepare_write_target(_text(data, "mount"), path)
        _atomic_replace(target, after.encode("utf-8"))
        after_hash = _hash(after)
        return CapabilityResult(
            output={
                "path": path,
                "beforeSha256": before_hash,
                "afterSha256": after_hash,
                "changed": before != after,
                "diffByteLength": len(diff_bytes),
            },  # type: ignore[arg-type]
            preview=diff_text[:512],
            effects=(EffectEntry(kind=f"documents.{operation}", summary=path),),
            evidence=(EvidenceEntry(description=f"sha256:{after_hash}"),),
            inline_artifacts=(
                CapabilityInlineArtifact(
                    kind="documents.diff",
                    content=diff_bytes,
                    content_type="text/x-diff; charset=utf-8",
                    preview=diff_text[:512],
                ),
            ),
        )

    def _apply(self, data: JsonObject, text: str, operation: str) -> str:
        if operation == "frontmatter_set":
            values = data.get("frontmatter")
            if not isinstance(values, JsonObject):
                raise CapabilityExecutionError(code="documents_input_invalid")
            _current, body, _present = _frontmatter(text)
            return _render_frontmatter(values, body)
        if operation == "section_replace":
            start, end, _entry = _section(data, text)
            lines = text.splitlines(keepends=True)
            heading_line = lines[start - 1]
            replacement = _text(data, "text")
            if replacement and not replacement.endswith("\n"):
                replacement += "\n"
            return _replace_range(text, start, end, heading_line + replacement)
        if operation == "range_replace":
            return _replace_range(
                text,
                _integer(data, "startLine"),
                _integer(data, "endLine"),
                _text(data, "text"),
            )
        if operation == "append":
            appended = _text(data, "text")
            if _bool(data, "ensureNewline", True) and text and not text.endswith("\n"):
                text += "\n"
            return text + appended
        if operation == "patch":
            patches = data.get("patches")
            if not isinstance(patches, JsonArray):
                raise CapabilityExecutionError(code="documents_patch_invalid")
            ranges: list[tuple[int, int]] = []
            for patch in patches:
                if not isinstance(patch, JsonObject):
                    raise CapabilityExecutionError(code="documents_patch_invalid")
                if patch.get("op") == "replace_range":
                    patch_start = patch.get("startLine")
                    patch_end = patch.get("endLine")
                    if (
                        isinstance(patch_start, bool)
                        or not isinstance(patch_start, int)
                        or isinstance(patch_end, bool)
                        or not isinstance(patch_end, int)
                    ):
                        raise CapabilityExecutionError(code="documents_patch_invalid")
                    if any(
                        patch_start < prior_end and prior_start < patch_end
                        for prior_start, prior_end in ranges
                    ):
                        raise CapabilityExecutionError(code="documents_patch_overlap")
                    ranges.append((patch_start, patch_end))
            current = text
            for patch in patches:
                assert isinstance(patch, JsonObject)
                current = self._apply_patch(current, patch)
            return current
        raise CapabilityExecutionError(code="documents_operation_unsupported")

    def _apply_patch(self, text: str, patch: JsonObject) -> str:
        operation = patch.get("op")
        if operation == "replace_range":
            replacement = patch.get("text")
            start = patch.get("startLine")
            end = patch.get("endLine")
            if (
                not isinstance(replacement, str)
                or isinstance(start, bool)
                or not isinstance(start, int)
                or isinstance(end, bool)
                or not isinstance(end, int)
            ):
                raise CapabilityExecutionError(code="documents_patch_invalid")
            return _replace_range(text, start, end, replacement)
        if operation == "append":
            value = patch.get("text")
            if not isinstance(value, str):
                raise CapabilityExecutionError(code="documents_patch_invalid")
            return text + value
        if operation == "set_frontmatter":
            values = patch.get("frontmatter")
            if not isinstance(values, JsonObject):
                raise CapabilityExecutionError(code="documents_patch_invalid")
            _old, body, _present = _frontmatter(text)
            return _render_frontmatter(values, body)
        if operation == "replace_section":
            heading = patch.get("heading")
            value = patch.get("text")
            if not isinstance(heading, str) or not isinstance(value, str):
                raise CapabilityExecutionError(code="documents_patch_invalid")
            patch_data = freeze_json({"heading": heading})
            assert isinstance(patch_data, JsonObject)
            start, end, _entry = _section(patch_data, text)
            lines = text.splitlines(keepends=True)
            if value and not value.endswith("\n"):
                value += "\n"
            return _replace_range(text, start, end, lines[start - 1] + value)
        raise CapabilityExecutionError(code="documents_patch_operation_unsupported")

    def _write(self, data: JsonObject) -> CapabilityResult:
        mount = _text(data, "mount")
        path = _text(data, "path")
        after = _text(data, "text")
        encoded = after.encode("utf-8")
        if len(encoded) > self.max_document_bytes:
            raise CapabilityExecutionError(code="documents_document_too_large")
        target = self.sandbox.prepare_write_target(
            mount,
            path,
            create_parents=_bool(data, "createParents"),
        )
        before = ""
        before_hash: str | None = None
        expected_value = data.get("expectedSha256")
        if target.exists:
            before = _decode_document(_file_bytes(target, self.max_document_bytes))
            before_hash = _hash(before)
            if not isinstance(expected_value, str):
                raise CapabilityExecutionError(code="documents_expected_hash_required")
            if expected_value != before_hash:
                raise CapabilityExecutionError(code="documents_stale_hash")
        elif expected_value is not None:
            raise CapabilityExecutionError(code="documents_expected_hash_without_target")
        diff_text = _diff(before, after, path)
        diff_bytes = diff_text.encode("utf-8")
        if len(diff_bytes) > self.max_diff_bytes:
            raise CapabilityExecutionError(code="documents_diff_too_large")
        _atomic_replace(target, encoded)
        after_hash = _hash(after)
        return CapabilityResult(
            output={
                "path": path,
                "beforeSha256": before_hash,
                "afterSha256": after_hash,
                "changed": before != after,
                "diffByteLength": len(diff_bytes),
            },  # type: ignore[arg-type]
            preview=diff_text[:512],
            effects=(EffectEntry(kind="documents.write", summary=path),),
            evidence=(EvidenceEntry(description=f"sha256:{after_hash}"),),
            inline_artifacts=(
                CapabilityInlineArtifact(
                    kind="documents.diff",
                    content=diff_bytes,
                    content_type="text/x-diff; charset=utf-8",
                    preview=diff_text[:512],
                ),
            ),
        )

    async def __call__(self, invocation: CapabilityInvocation, /) -> CapabilityResult:
        data = _data(invocation)
        if invocation.action_name == "write":
            return self._write(data)
        if invocation.action_name in {
            "frontmatter_set",
            "section_replace",
            "range_replace",
            "append",
            "patch",
        }:
            return self._mutation(data, invocation.action_name)
        path, document, digest = self._read(data)
        if invocation.action_name == "read":
            return CapabilityResult(
                output={"path": path, "text": document, "sha256": digest},  # type: ignore[arg-type]
                preview=document[:512],
                effects=(EffectEntry(kind="documents.read", summary=path),),
                evidence=(EvidenceEntry(description=f"sha256:{digest}"),),
                inline_artifacts=(
                    CapabilityInlineArtifact(
                        kind="documents.markdown",
                        content=document.encode("utf-8"),
                        content_type="text/markdown; charset=utf-8",
                        preview=document[:512],
                    ),
                ),
            )
        if invocation.action_name == "headings":
            return CapabilityResult(
                output={"path": path, "sha256": digest, "headings": _heading_entries(document)}  # type: ignore[arg-type]
            )
        if invocation.action_name == "frontmatter_read":
            values, _body, present = _frontmatter(document)
            return CapabilityResult(
                output={
                    "path": path,
                    "sha256": digest,
                    "present": present,
                    "frontmatter": values,
                }  # type: ignore[arg-type]
            )
        if invocation.action_name == "section_read":
            start, end, entry = _section(data, document)
            lines = document.splitlines(keepends=True)
            return CapabilityResult(
                output={
                    "path": path,
                    "sha256": digest,
                    "heading": entry,
                    "text": "".join(lines[start - 1 : end - 1]),
                }  # type: ignore[arg-type]
            )
        raise CapabilityExecutionError(code="documents_action_unsupported")


@final
@dataclass(frozen=True, slots=True, kw_only=True)
class DocumentsCapability:
    mounts: tuple[FilesystemMount, ...]
    max_document_bytes: int = 8 * 1024 * 1024
    max_diff_bytes: int = 2 * 1024 * 1024

    def __post_init__(self) -> None:
        mounts = tuple(self.mounts)
        MarkdownDocumentsHandler(
            mounts=mounts,
            max_document_bytes=self.max_document_bytes,
            max_diff_bytes=self.max_diff_bytes,
        )
        object.__setattr__(self, "mounts", mounts)

    def registered(
        self,
        *,
        capability_id: CapabilityId | None = None,
        python_executable: PathInput | None = None,
        module_search_path: PathInput | None = None,
        timeout_ms: int = 30_000,
    ) -> RegisteredCapability:
        identifier = CapabilityId(value="documents") if capability_id is None else capability_id
        executable = (
            Path(sys.executable)
            if python_executable is None
            else normalize_local_path(python_executable).path
        )
        if not executable.is_absolute():
            raise ValidationError(code="documents_python_executable_invalid")
        roots = json.dumps(
            [
                {"name": item.name, "root": str(item.root), "access": item.access.value}
                for item in self.mounts
            ],
            ensure_ascii=False,
            separators=(",", ":"),
        )
        environment: list[tuple[str, str]] = [
            ("PYTHONUTF8", "1"),
            (_ROOTS_ENV, roots),
            ("OPENRUND_DOCUMENT_MAX_BYTES", str(self.max_document_bytes)),
            ("OPENRUND_DOCUMENT_MAX_DIFF_BYTES", str(self.max_diff_bytes)),
        ]
        if module_search_path is not None:
            search = normalize_local_path(module_search_path)
            if not search.path.is_absolute():
                raise ValidationError(code="documents_module_search_path_invalid")
            environment.append(("PYTHONPATH", search.raw))
        transport = StdioJsonRpcTransport(
            StdioJsonRpcConfig(
                command=(str(executable), "-m", "openrund.capabilities.documents_worker"),
                environment=tuple(environment),
                timeout_ms=timeout_ms,
            )
        )
        actions = document_actions()
        return RegisteredCapability(
            definition=Capability(capability_id=identifier, version="1", actions=actions),
            bindings=tuple(
                ActionTransportBinding(action_name=action.name, transport=transport)
                for action in actions
            ),
        )


def mounts_from_worker_environment(value: str) -> tuple[FilesystemMount, ...]:
    try:
        decoded = json.loads(value)
    except (json.JSONDecodeError, TypeError):
        raise CapabilityExecutionError(code="documents_worker_roots_invalid") from None
    if not isinstance(decoded, list):
        raise CapabilityExecutionError(code="documents_worker_roots_invalid")
    mounts: list[FilesystemMount] = []
    try:
        for item in decoded:
            if not isinstance(item, dict) or set(item) != {"name", "root", "access"}:
                raise CapabilityExecutionError(code="documents_worker_roots_invalid")
            mounts.append(
                FilesystemMount(
                    name=item["name"],
                    root=item["root"],
                    access=CapabilityAccessMode(item["access"]),
                )
            )
    except (KeyError, TypeError, ValueError, ValidationError):
        raise CapabilityExecutionError(code="documents_worker_roots_invalid") from None
    return tuple(mounts)
