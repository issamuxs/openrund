"""Fail-closed byte and semantic verification for portable Bundles."""

from __future__ import annotations

import os
import stat
from dataclasses import dataclass
from pathlib import Path
from typing import Final, final

from openrund._localfs import LocalFilesystemError, read_regular_file
from openrund.codec import canonical_json_bytes, decode_event, decode_json_value, encode_json_value
from openrund.contracts.events import RuntimeEvent
from openrund.contracts.json import JsonObject, freeze_json
from openrund.errors import BundleIntegrityError, OpenRundError
from openrund.paths import PathInput, normalize_local_path
from openrund.views import CompleteViewReplay, RunViewBundle, rebuild_views

from ._hashing import bundle_commitment, event_frame_commitment, hash_bytes
from ._model import (
    BundleArtifactAvailability,
    BundleManifest,
    BundleVerification,
    BundleVerificationCheck,
)
from ._paths import secure_directory
from ._wire import manifest_from_bytes, parse_json_bytes

MAX_BUNDLE_FILE_BYTES: Final = 64 * 1024 * 1024
MAX_EVENT_LOG_BYTES: Final = 256 * 1024 * 1024


@final
@dataclass(frozen=True, slots=True, kw_only=True)
class _VerifiedBundle:
    path: Path
    manifest: BundleManifest
    events: tuple[RuntimeEvent, ...]
    views: RunViewBundle
    checks: tuple[BundleVerificationCheck, ...]


def _regular_bytes(path: Path, *, limit: int, code: str) -> bytes:
    try:
        return read_regular_file(path, limit=limit)
    except LocalFilesystemError:
        raise BundleIntegrityError(code=code) from None


def _bundle_root(value: PathInput) -> Path:
    path = Path(normalize_local_path(value).path)
    try:
        path = secure_directory(path, create=False, code="bundle_root_invalid")
    except BundleIntegrityError:
        raise
    except OpenRundError:
        raise BundleIntegrityError(code="bundle_root_invalid") from None
    try:
        status = path.lstat()
    except OSError:
        raise BundleIntegrityError(code="bundle_not_found") from None
    if stat.S_ISLNK(status.st_mode) or not stat.S_ISDIR(status.st_mode):
        raise BundleIntegrityError(code="bundle_root_invalid")
    return path


def _tree_entries(root: Path) -> tuple[set[str], set[str]]:
    files: set[str] = set()
    directories: set[str] = set()

    def walk(directory: Path, prefix: tuple[str, ...]) -> None:
        try:
            entries = sorted(os.scandir(directory), key=lambda item: item.name)
        except OSError:
            raise BundleIntegrityError(code="bundle_tree_invalid") from None
        for entry in entries:
            relative = (*prefix, entry.name)
            try:
                status = entry.stat(follow_symlinks=False)
            except OSError:
                raise BundleIntegrityError(code="bundle_tree_invalid") from None
            if stat.S_ISLNK(status.st_mode):
                raise BundleIntegrityError(code="bundle_symlink_forbidden")
            path = Path(entry.path)
            if stat.S_ISDIR(status.st_mode):
                directories.add("/".join(relative))
                walk(path, relative)
            elif stat.S_ISREG(status.st_mode):
                files.add("/".join(relative))
            else:
                raise BundleIntegrityError(code="bundle_special_file_forbidden")

    walk(root, ())
    return files, directories


def _expected_directories(files: set[str]) -> set[str]:
    result = {
        "artifacts",
        "views",
        "policy",
        "capabilities",
        "exports",
        "exports/action-receipts",
    }
    for item in files:
        components = item.split("/")[:-1]
        result.update("/".join(components[:index]) for index in range(1, len(components) + 1))
    return result


def _normalized_frame(frame: JsonObject) -> JsonObject:
    event_type = frame.get("type")
    payload = frame.get("payload")
    if (
        event_type == "run.created"
        and isinstance(payload, JsonObject)
        and "initialStatus" not in payload
    ):
        normalized_payload = JsonObject(entries=(*payload.entries, ("initialStatus", "created")))
        return JsonObject(
            entries=tuple(
                (key, normalized_payload if key == "payload" else value)
                for key, value in frame.entries
            )
        )
    return frame


def _events(
    content: bytes, manifest: BundleManifest
) -> tuple[tuple[RuntimeEvent, ...], tuple[JsonObject, ...]]:
    if not content or not content.endswith(b"\n") or content.endswith(b"\r\n"):
        raise BundleIntegrityError(code="bundle_event_log_malformed")
    lines = content.splitlines(keepends=True)
    frames: list[JsonObject] = []
    events: list[RuntimeEvent] = []
    for index, line in enumerate(lines, start=1):
        try:
            frame = decode_json_value(line)
            if not isinstance(frame, JsonObject):
                raise BundleIntegrityError(code="bundle_event_log_malformed")
            event = decode_event(encode_json_value(_normalized_frame(frame)))
        except BundleIntegrityError:
            raise
        except OpenRundError:
            raise BundleIntegrityError(code="bundle_event_log_malformed") from None
        if event.position != index:
            raise BundleIntegrityError(code="bundle_event_position_invalid")
        if event.run_id != manifest.run_id:
            raise BundleIntegrityError(code="bundle_event_run_mismatch")
        frames.append(frame)
        events.append(event)
    if len(events) != manifest.integrity.events.count:
        raise BundleIntegrityError(code="bundle_event_count_mismatch")
    if len({event.event_id for event in events}) != len(events):
        raise BundleIntegrityError(code="bundle_event_id_duplicate")
    return tuple(events), tuple(frames)


def _required_paths(manifest: BundleManifest) -> set[str]:
    result = {
        "events.jsonl",
        "views/summary.json",
        "policy/snapshot.json",
        "capabilities/manifest.json",
        manifest.exports.runtime_audit_json.value,
        manifest.exports.runtime_audit_markdown.value,
        *(item.value for item in manifest.exports.action_receipts),
    }
    if manifest.exports.check_json is not None:
        result.add(manifest.exports.check_json.value)
    if manifest.exports.check_markdown is not None:
        result.add(manifest.exports.check_markdown.value)
    result.update(
        item.path.value
        for item in manifest.artifacts
        if item.availability is BundleArtifactAvailability.INCLUDED and item.path is not None
    )
    return result


def _metadata(root: Path, manifest: BundleManifest, views: RunViewBundle) -> None:
    summary = parse_json_bytes(
        _regular_bytes(
            root / "views" / "summary.json",
            limit=MAX_BUNDLE_FILE_BYTES,
            code="bundle_view_summary_invalid",
        ),
        code="bundle_view_summary_invalid",
    )
    if not isinstance(summary, dict):
        raise BundleIntegrityError(code="bundle_view_summary_invalid")
    expected = {
        "runID": manifest.run_id.value,
        "status": views.run_status.status,
        "currentPosition": manifest.views.current_position,
        "eventCount": manifest.views.event_count,
    }
    if any(summary.get(key) != value for key, value in expected.items()):
        raise BundleIntegrityError(code="bundle_view_summary_mismatch")
    policy_content = _regular_bytes(
        root / "policy" / "snapshot.json",
        limit=MAX_BUNDLE_FILE_BYTES,
        code="bundle_policy_manifest_invalid",
    )
    policy = parse_json_bytes(policy_content, code="bundle_policy_manifest_invalid")
    if hash_bytes(canonical_json_bytes(freeze_json(policy))) != manifest.policy.key:
        raise BundleIntegrityError(code="bundle_policy_key_mismatch")
    if not isinstance(policy, list):
        raise BundleIntegrityError(code="bundle_policy_manifest_invalid")
    policy_ids = tuple(item.get("ruleID") for item in policy if isinstance(item, dict))
    if policy_ids != manifest.policy.rules:
        raise BundleIntegrityError(code="bundle_policy_manifest_mismatch")
    capabilities = parse_json_bytes(
        _regular_bytes(
            root / "capabilities" / "manifest.json",
            limit=MAX_BUNDLE_FILE_BYTES,
            code="bundle_capability_manifest_invalid",
        ),
        code="bundle_capability_manifest_invalid",
    )
    if isinstance(capabilities, list):
        if capabilities or manifest.capability_grants or manifest.provider_ids:
            raise BundleIntegrityError(code="bundle_capability_manifest_mismatch")
    elif isinstance(capabilities, dict):
        raw_grants = capabilities.get("grants")
        raw_providers = capabilities.get("providers")
        if not isinstance(raw_grants, list) or not isinstance(raw_providers, list):
            raise BundleIntegrityError(code="bundle_capability_manifest_invalid")
        grant_ids = tuple(item.get("capabilityID") for item in raw_grants if isinstance(item, dict))
        if grant_ids != manifest.capability_grants or tuple(raw_providers) != manifest.provider_ids:
            raise BundleIntegrityError(code="bundle_capability_manifest_mismatch")
    else:
        raise BundleIntegrityError(code="bundle_capability_manifest_invalid")


def load_verified_bundle(bundle_path: PathInput) -> _VerifiedBundle:
    root = _bundle_root(bundle_path)
    manifest = manifest_from_bytes(
        _regular_bytes(
            root / "manifest.json", limit=MAX_BUNDLE_FILE_BYTES, code="bundle_manifest_malformed"
        )
    )
    actual_files, actual_directories = _tree_entries(root)
    declared_files = {item.path.value for item in manifest.integrity.files}
    if actual_files != declared_files | {"manifest.json"}:
        raise BundleIntegrityError(code="bundle_file_table_mismatch")
    if actual_directories != _expected_directories(declared_files):
        raise BundleIntegrityError(code="bundle_directory_table_mismatch")
    required = _required_paths(manifest)
    if not required.issubset(declared_files):
        raise BundleIntegrityError(code="bundle_required_file_undeclared")
    for item in manifest.integrity.files:
        content = _regular_bytes(
            root.joinpath(*item.path.components),
            limit=(
                MAX_EVENT_LOG_BYTES if item.path.value == "events.jsonl" else MAX_BUNDLE_FILE_BYTES
            ),
            code="bundle_file_invalid",
        )
        if len(content) != item.byte_length or hash_bytes(content) != item.sha256:
            raise BundleIntegrityError(code="bundle_file_integrity_mismatch")
    events_content = _regular_bytes(
        root / "events.jsonl",
        limit=MAX_EVENT_LOG_BYTES,
        code="bundle_event_log_malformed",
    )
    events, frames = _events(events_content, manifest)
    if event_frame_commitment(frames) != manifest.integrity.events:
        raise BundleIntegrityError(code="bundle_event_chain_mismatch")
    expected_bundle = bundle_commitment(
        profile=manifest.profile,
        source_run_id=manifest.source_run_id,
        compatibility=manifest.compatibility,
        events=manifest.integrity.events,
        files=manifest.integrity.files,
    )
    if expected_bundle != manifest.integrity.bundle:
        raise BundleIntegrityError(code="bundle_commitment_mismatch")
    replay = rebuild_views(events, watermark=manifest.views.current_position)
    if not isinstance(replay, CompleteViewReplay):
        raise BundleIntegrityError(code="bundle_replay_incomplete")
    if replay.run_id != manifest.run_id or replay.views.run_status.status != manifest.views.status:
        raise BundleIntegrityError(code="bundle_view_manifest_mismatch")
    waits = tuple(item.kind.value for item in replay.views.run_status.pending_waits)
    if waits != manifest.views.pending_waits or waits != manifest.resume.pending_waits:
        raise BundleIntegrityError(code="bundle_wait_requirements_mismatch")
    projected_artifacts = replay.views.artifact_index
    if {item.artifact_id for item in manifest.artifacts} != set(projected_artifacts):
        raise BundleIntegrityError(code="bundle_artifact_manifest_mismatch")
    for artifact in manifest.artifacts:
        projected = projected_artifacts[artifact.artifact_id]
        if projected.kind != artifact.kind or projected.available != artifact.available:
            raise BundleIntegrityError(code="bundle_artifact_manifest_mismatch")
        if artifact.availability is BundleArtifactAvailability.INCLUDED:
            assert artifact.path is not None
            commitment = next(
                (item for item in manifest.integrity.files if item.path == artifact.path), None
            )
            if (
                commitment is None
                or commitment.sha256 != artifact.sha256
                or commitment.byte_length != artifact.byte_length
            ):
                raise BundleIntegrityError(code="bundle_artifact_manifest_mismatch")
    has_report_exports = (
        manifest.exports.check_json is not None and manifest.exports.check_markdown is not None
    )
    if bool(replay.views.reports) != has_report_exports:
        raise BundleIntegrityError(code="bundle_report_manifest_mismatch")
    _metadata(root, manifest, replay.views)
    checks = tuple(
        BundleVerificationCheck(name=name)
        for name in (
            "manifest",
            "tree",
            "file_integrity",
            "event_chain",
            "bundle_commitment",
            "semantic_replay",
            "metadata",
            "artifacts",
            "resume_requirements",
        )
    )
    return _VerifiedBundle(
        path=root,
        manifest=manifest,
        events=events,
        views=replay.views,
        checks=checks,
    )


def verify_bundle(bundle_path: PathInput) -> BundleVerification:
    verified = load_verified_bundle(bundle_path)
    return BundleVerification(
        bundle_path=os.fspath(verified.path),
        manifest=verified.manifest,
        checks=verified.checks,
    )
