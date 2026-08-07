"""Deterministic staged export of portable ``.orun`` Bundle trees."""

from __future__ import annotations

import os
import secrets
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Self, final

from openrund._localfs import LocalFilesystemError, fsync_directory, write_new_file
from openrund._version import __version__
from openrund.contracts.ids import ArtifactId, RunId
from openrund.contracts.json import JsonValue
from openrund.contracts.portable import BundleProfile
from openrund.contracts.time import Timestamp
from openrund.errors import BundleError, BundleImportError, StorageIntegrityError, ValidationError
from openrund.paths import PathInput, PortablePath, normalize_local_path
from openrund.ports.artifacts import ArtifactStore
from openrund.ports.events import EventStore
from openrund.views import CompleteViewReplay, rebuild_views

from ._hashing import (
    bundle_commitment,
    event_commitment,
    hash_bytes,
    hash_canonical_json,
    render_events_jsonl,
)
from ._model import (
    BundleArtifact,
    BundleArtifactAvailability,
    BundleArtifactOmission,
    BundleCompatibility,
    BundleCompleteness,
    BundleCompletenessStatus,
    BundleExports,
    BundleFileCommitment,
    BundleIntegrity,
    BundleLayout,
    BundleManifest,
    BundlePolicy,
    BundleResumeRequirements,
    BundleViews,
)
from ._paths import secure_directory
from ._render import (
    action_receipt_markdown,
    capability_snapshot,
    policy_snapshot,
    report_json,
    reports_markdown,
    runtime_audit,
    runtime_audit_markdown,
    view_summary,
)
from ._wire import manifest_bytes, pretty_json_bytes

_CRITICAL_FIELDS = ("version", "compatibility", "source", "layout", "integrity", "resume")


@final
@dataclass(frozen=True, slots=True, kw_only=True)
class BundleExportResult:
    bundle_path: Path
    manifest: BundleManifest


def _fsync_directory(path: Path) -> None:
    try:
        fsync_directory(path)
    except LocalFilesystemError as error:
        raise OSError(error.reason) from None


def _write_new(path: Path, content: bytes) -> None:
    try:
        write_new_file(path, content)
    except LocalFilesystemError as error:
        raise OSError(error.reason) from None


def _make_layout(stage: Path) -> None:
    stage.mkdir(mode=0o700)
    for relative in (
        "artifacts",
        "views",
        "policy",
        "capabilities",
        "exports",
        "exports/action-receipts",
    ):
        stage.joinpath(*relative.split("/")).mkdir(mode=0o700)


@final
class _Stage:
    def __init__(self, output: Path) -> None:
        self.output = output
        self.parent = output.parent
        self.stage = self.parent / f".{output.name}.{secrets.token_hex(12)}.stage"
        self.lock = self.parent / f".{output.name}.publish.lock"
        self._published = False

    def __enter__(self) -> Self:
        self.parent = secure_directory(
            self.parent, create=True, code="bundle_output_parent_invalid"
        )
        self.output = self.parent / self.output.name
        self.stage = self.parent / self.stage.name
        self.lock = self.parent / self.lock.name
        if self.output.exists() or self.output.is_symlink():
            raise BundleImportError(code="bundle_output_exists")
        lock_flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
        if hasattr(os, "O_NOFOLLOW"):
            lock_flags |= os.O_NOFOLLOW
        try:
            descriptor = os.open(self.lock, lock_flags, 0o600)
        except FileExistsError:
            raise BundleImportError(code="bundle_publish_busy") from None
        os.close(descriptor)
        try:
            _make_layout(self.stage)
        except BaseException:
            self.lock.unlink(missing_ok=True)
            raise
        return self

    def publish(self) -> None:
        if self.output.exists() or self.output.is_symlink():
            raise BundleImportError(code="bundle_output_exists")
        _fsync_directory(self.stage)
        os.rename(self.stage, self.output)
        _fsync_directory(self.parent)
        self._published = True

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: object | None,
    ) -> None:
        try:
            if not self._published and self.stage.exists():
                shutil.rmtree(self.stage)
        finally:
            self.lock.unlink(missing_ok=True)


def _path(value: PathInput) -> Path:
    path = Path(normalize_local_path(value).path)
    if path.suffix != ".orun":
        raise ValidationError(code="bundle_output_suffix_invalid")
    return path


def _write(stage: Path, relative: str, content: bytes, written: list[BundleFileCommitment]) -> None:
    portable = PortablePath(value=relative)
    target = stage.joinpath(*portable.components)
    _write_new(target, content)
    written.append(
        BundleFileCommitment(
            path=portable,
            sha256=hash_bytes(content),
            byte_length=len(content),
        )
    )


def _policy_key(value: JsonValue) -> str:
    return hash_canonical_json(value)


def _omission(
    profile: BundleProfile, *, available: bool, has_blob: bool
) -> tuple[BundleArtifactAvailability, BundleArtifactOmission, str]:
    if not available:
        return (
            BundleArtifactAvailability.UNAVAILABLE,
            BundleArtifactOmission.UNAVAILABLE,
            "artifact was marked unavailable in runtime history",
        )
    if not has_blob:
        return (
            BundleArtifactAvailability.OMITTED,
            BundleArtifactOmission.MISSING_BYTES,
            "artifact bytes were unavailable from the Artifact store during export",
        )
    if profile is BundleProfile.REDACTED:
        return (
            BundleArtifactAvailability.OMITTED,
            BundleArtifactOmission.REDACTED,
            "artifact bytes redacted by export profile",
        )
    return (
        BundleArtifactAvailability.OMITTED,
        BundleArtifactOmission.PROFILE,
        "artifact bytes omitted by audit export profile",
    )


async def _export_bundle(
    *,
    run_id: RunId,
    output_path: PathInput,
    event_store: EventStore,
    artifact_store: ArtifactStore | None,
    profile: BundleProfile,
    runtime_version: str,
    exported_at: Timestamp,
    required_root_mappings: tuple[str, ...],
    required_providers: tuple[str, ...],
) -> BundleExportResult:
    stream = await event_store.read(run_id)
    events = stream.events
    watermark = events[-1].position if events else 0
    replay = rebuild_views(events, watermark=watermark)
    if not isinstance(replay, CompleteViewReplay):
        raise BundleError(code="bundle_source_history_incomplete")
    views = replay.views
    output = _path(output_path)
    with _Stage(output) as staged:
        written: list[BundleFileCommitment] = []
        _write(staged.stage, "events.jsonl", render_events_jsonl(events), written)
        summary = view_summary(run_id.value, views, len(events))
        _write(staged.stage, "views/summary.json", pretty_json_bytes(summary), written)
        policy = policy_snapshot(views)
        _write(staged.stage, "policy/snapshot.json", pretty_json_bytes(policy), written)
        capabilities = capability_snapshot(views, required_providers)
        _write(
            staged.stage,
            "capabilities/manifest.json",
            pretty_json_bytes(capabilities),
            written,
        )
        event_types = tuple(event.event_type.value for event in events)
        audit = runtime_audit(run_id.value, views, event_types)
        _write(staged.stage, "exports/runtime-audit.json", pretty_json_bytes(audit), written)
        _write(
            staged.stage,
            "exports/runtime-audit.md",
            runtime_audit_markdown(audit),
            written,
        )
        receipt_paths: list[PortablePath] = []
        for action_id, receipt in sorted(
            views.action_receipts.items(), key=lambda item: item[0].value
        ):
            relative = f"exports/action-receipts/{action_id.value}.md"
            _write(staged.stage, relative, action_receipt_markdown(receipt), written)
            receipt_paths.append(PortablePath(value=relative))

        check_json: PortablePath | None = None
        check_markdown: PortablePath | None = None
        if views.reports:
            check_json = PortablePath(value="exports/check.json")
            check_markdown = PortablePath(value="exports/check.md")
            _write(staged.stage, check_json.value, pretty_json_bytes(report_json(views)), written)
            _write(staged.stage, check_markdown.value, reports_markdown(views), written)

        artifacts: list[BundleArtifact] = []
        excluded: list[ArtifactId] = []
        unavailable: list[ArtifactId] = []
        for artifact_id, projected in sorted(
            views.artifact_index.items(), key=lambda item: item[0].value
        ):
            entry = await artifact_store.get(artifact_id) if artifact_store is not None else None
            blob = (
                await artifact_store.get_blob(artifact_id) if artifact_store is not None else None
            )
            has_blob = blob is not None
            include = projected.available and has_blob and profile is BundleProfile.COMPLETE
            content_type = None
            byte_length = None
            digest = None
            if blob is not None:
                content_type = blob.content_type if isinstance(blob.content_type, str) else None
                byte_length = len(blob.content)
                digest = hash_bytes(blob.content)
            elif entry is not None:
                content_type = entry.content_type if isinstance(entry.content_type, str) else None
                byte_length = entry.byte_length if isinstance(entry.byte_length, int) else None
                digest = entry.sha256 if isinstance(entry.sha256, str) else None
            if include:
                assert blob is not None
                relative = f"artifacts/{artifact_id.value}.bin"
                _write(staged.stage, relative, blob.content, written)
                artifacts.append(
                    BundleArtifact(
                        artifact_id=artifact_id,
                        kind=projected.kind,
                        availability=BundleArtifactAvailability.INCLUDED,
                        available=True,
                        required_for_resume=True,
                        content_type=content_type,
                        byte_length=byte_length,
                        sha256=digest,
                        path=PortablePath(value=relative),
                    )
                )
                continue
            availability, omission, reason = _omission(
                profile, available=projected.available, has_blob=has_blob
            )
            if projected.available:
                excluded.append(artifact_id)
            unavailable.append(artifact_id)
            artifacts.append(
                BundleArtifact(
                    artifact_id=artifact_id,
                    kind=projected.kind,
                    availability=availability,
                    available=projected.available,
                    required_for_resume=projected.available,
                    content_type=content_type,
                    byte_length=byte_length,
                    sha256=digest,
                    omission=omission,
                    omission_reason=reason,
                )
            )

        capability_ids = tuple(item.value for item in views.run_status.capability_authority)
        policy_rules = tuple(item.value for item in views.run_status.policy_authority)
        event_integrity = event_commitment(events)
        compatibility = BundleCompatibility(runtime_version=runtime_version)
        file_commitments = tuple(written)
        overall = bundle_commitment(
            profile=profile,
            source_run_id=run_id,
            compatibility=compatibility,
            events=event_integrity,
            files=file_commitments,
        )
        manifest = BundleManifest(
            run_id=run_id,
            source_run_id=run_id,
            exported_at=exported_at,
            compatibility=compatibility,
            profile=profile,
            critical_fields=_CRITICAL_FIELDS,
            layout=BundleLayout(),
            completeness=BundleCompleteness(
                status=(
                    BundleCompletenessStatus.PARTIAL
                    if excluded
                    else BundleCompletenessStatus.COMPLETE
                ),
                excluded_artifact_ids=tuple(excluded),
            ),
            integrity=BundleIntegrity(
                files=file_commitments,
                events=event_integrity,
                bundle=overall,
            ),
            views=BundleViews(
                status=views.run_status.status,
                current_position=watermark,
                pending_waits=tuple(item.kind.value for item in views.run_status.pending_waits),
                event_count=len(events),
            ),
            capability_grants=capability_ids,
            provider_ids=required_providers,
            policy=BundlePolicy(rules=policy_rules, key=_policy_key(policy)),
            exports=BundleExports(
                runtime_audit_json=PortablePath(value="exports/runtime-audit.json"),
                runtime_audit_markdown=PortablePath(value="exports/runtime-audit.md"),
                action_receipts=tuple(receipt_paths),
                check_json=check_json,
                check_markdown=check_markdown,
            ),
            artifacts=tuple(artifacts),
            resume=BundleResumeRequirements(
                required_root_mappings=required_root_mappings,
                required_capabilities=capability_ids,
                required_providers=required_providers,
                pending_waits=tuple(item.kind.value for item in views.run_status.pending_waits),
                unavailable_artifacts=tuple(unavailable),
            ),
        )
        _write_new(staged.stage / "manifest.json", manifest_bytes(manifest))
        staged.publish()
    return BundleExportResult(bundle_path=output, manifest=manifest)


async def export_bundle(
    *,
    run_id: RunId,
    output_path: PathInput,
    event_store: EventStore,
    artifact_store: ArtifactStore | None = None,
    profile: BundleProfile = BundleProfile.COMPLETE,
    runtime_version: str = __version__,
    exported_at: Timestamp,
    required_root_mappings: tuple[str, ...] = ("workspace",),
    required_providers: tuple[str, ...] = (),
) -> BundleExportResult:
    if not isinstance(run_id, RunId):
        raise ValidationError(code="bundle_run_id_invalid")
    if not isinstance(profile, BundleProfile):
        raise ValidationError(code="bundle_profile_invalid")
    if not isinstance(exported_at, Timestamp):
        raise ValidationError(code="bundle_exported_at_invalid")
    try:
        roots = tuple(required_root_mappings)
        providers = tuple(required_providers)
    except TypeError as error:
        raise ValidationError(code="bundle_resume_requirements_invalid") from error
    if any(not isinstance(item, str) or item == "" for item in (*roots, *providers)):
        raise ValidationError(code="bundle_resume_requirements_invalid")
    try:
        return await _export_bundle(
            run_id=run_id,
            output_path=output_path,
            event_store=event_store,
            artifact_store=artifact_store,
            profile=profile,
            runtime_version=runtime_version,
            exported_at=exported_at,
            required_root_mappings=roots,
            required_providers=providers,
        )
    except (BundleError, StorageIntegrityError, ValidationError):
        raise
    except OSError:
        raise BundleError(code="bundle_export_failed") from None
