"""Atomic stage-import for already verified Bundle content."""

from __future__ import annotations

import os
import secrets
import shutil
import stat
from collections.abc import Mapping
from pathlib import Path, PureWindowsPath

from openrund.contracts.time import Timestamp
from openrund.errors import BundleError, BundleImportError, ValidationError
from openrund.paths import PathInput, normalize_local_path

from ._export import _fsync_directory, _write_new
from ._hashing import hash_canonical_json
from ._model import ImportedBundle, ResumeAssessment
from ._paths import secure_directory
from ._resume import assess_resume
from ._verify import (
    MAX_BUNDLE_FILE_BYTES,
    MAX_EVENT_LOG_BYTES,
    _regular_bytes,
    load_verified_bundle,
)
from ._wire import pretty_json_bytes


def _component(value: object) -> str:
    if (
        not isinstance(value, str)
        or value in {"", ".", ".."}
        or "\x00" in value
        or "/" in value
        or "\\" in value
        or PureWindowsPath(value).drive
    ):
        raise ValidationError(code="bundle_import_id_invalid")
    return value


def _root_mappings(value: Mapping[str, PathInput]) -> tuple[tuple[str, str], ...]:
    result: list[tuple[str, str]] = []
    for key in sorted(value):
        if not isinstance(key, str) or key == "":
            raise ValidationError(code="bundle_root_mapping_key_invalid")
        path = Path(normalize_local_path(value[key]).path)
        if not path.is_absolute():
            raise ValidationError(code="bundle_root_mapping_relative")
        try:
            path = secure_directory(path, create=False, code="bundle_root_mapping_invalid")
            status = path.lstat()
        except BundleError:
            raise ValidationError(code="bundle_root_mapping_unavailable") from None
        if stat.S_ISLNK(status.st_mode) or not stat.S_ISDIR(status.st_mode):
            raise ValidationError(code="bundle_root_mapping_invalid")
        result.append((key, os.fspath(path)))
    return tuple(result)


def _copy_file(source: Path, target: Path, *, limit: int) -> None:
    target.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    _write_new(target, _regular_bytes(source, limit=limit, code="bundle_import_source_changed"))


def _assessment_mapping(value: ResumeAssessment) -> dict[str, object]:
    return {
        "resumable": value.resumable,
        "issues": [
            {
                "kind": issue.kind.value,
                "severity": issue.severity.value,
                "subject": issue.subject,
                "evidencePointer": issue.evidence_pointer,
            }
            for issue in value.issues
        ],
        "missingRootMappings": list(value.missing_root_mappings),
    }


def _copy_verified_bundle(source: Path, target: Path, paths: tuple[str, ...]) -> None:
    target.mkdir(mode=0o700)
    for relative in (
        "artifacts",
        "views",
        "policy",
        "capabilities",
        "exports",
        "exports/action-receipts",
    ):
        target.joinpath(*relative.split("/")).mkdir(mode=0o700)
    for relative in paths:
        components = tuple(relative.split("/"))
        _copy_file(
            source.joinpath(*components),
            target.joinpath(*components),
            limit=(MAX_EVENT_LOG_BYTES if relative == "events.jsonl" else MAX_BUNDLE_FILE_BYTES),
        )
    _copy_file(
        source / "manifest.json",
        target / "manifest.json",
        limit=MAX_BUNDLE_FILE_BYTES,
    )


def import_bundle(
    bundle_path: PathInput,
    *,
    runtime_home: PathInput,
    root_mappings: Mapping[str, PathInput],
    imported_at: Timestamp,
    import_id: str | None = None,
    capture_resume_snapshot: bool = False,
) -> ImportedBundle:
    if not isinstance(imported_at, Timestamp):
        raise ValidationError(code="bundle_import_timestamp_invalid")
    source = load_verified_bundle(bundle_path)
    mappings = _root_mappings(root_mappings)
    mapping_keys = {key for key, _value in mappings}
    missing = tuple(
        key for key in source.manifest.resume.required_root_mappings if key not in mapping_keys
    )
    if missing:
        raise BundleImportError(code="bundle_root_mapping_missing", safe_detail=",".join(missing))
    resolved_id = _component(
        import_id
        or "imp_"
        + hash_canonical_json(
            {
                "runID": source.manifest.run_id.value,
                "bundle": source.manifest.integrity.bundle.sha256,
                "importedAt": imported_at.value,
            }
        )[:16]
    )
    home = Path(normalize_local_path(runtime_home).path)
    imports = home / "imports"
    try:
        imports = secure_directory(imports, create=True, code="bundle_import_root_invalid")
        imports_status = imports.lstat()
    except (BundleError, OSError):
        raise BundleImportError(code="bundle_import_root_invalid") from None
    if stat.S_ISLNK(imports_status.st_mode) or not stat.S_ISDIR(imports_status.st_mode):
        raise BundleImportError(code="bundle_import_root_invalid")
    target = imports / resolved_id
    if target.exists() or target.is_symlink():
        raise BundleImportError(code="bundle_import_exists")
    stage = imports / f".{resolved_id}.{secrets.token_hex(12)}.stage"
    lock = imports / f".{resolved_id}.publish.lock"
    lock_flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    if hasattr(os, "O_NOFOLLOW"):
        lock_flags |= os.O_NOFOLLOW
    try:
        descriptor = os.open(lock, lock_flags, 0o600)
    except FileExistsError:
        raise BundleImportError(code="bundle_import_busy") from None
    os.close(descriptor)
    published = False
    try:
        stage.mkdir(mode=0o700)
        relative_paths = tuple(item.path.value for item in source.manifest.integrity.files)
        staged_bundle = stage / f"{source.manifest.run_id.value}.orun"
        _copy_verified_bundle(source.path, staged_bundle, relative_paths)
        staged_verified = load_verified_bundle(staged_bundle)
        final_bundle = target / staged_bundle.name
        imported = ImportedBundle(
            bundle_path=os.fspath(final_bundle),
            manifest=staged_verified.manifest,
            root_mappings=mappings,
            import_id=resolved_id,
            imported_at=imported_at,
        )
        snapshot = (
            assess_resume(
                imported,
                available_capabilities=source.manifest.resume.required_capabilities,
                available_providers=source.manifest.resume.required_providers,
                supported_policy_key=source.manifest.policy.key,
                resumable_wait_kinds=source.manifest.resume.pending_waits,
            )
            if capture_resume_snapshot
            else None
        )
        record: dict[str, object] = {
            "importID": resolved_id,
            "runID": source.manifest.run_id.value,
            "sourcePath": os.fspath(source.path),
            "importedAt": imported_at.value,
            "bundlePath": os.fspath(final_bundle),
            "sourceBundleSha256": source.manifest.integrity.bundle.sha256,
            "verification": {
                "ok": True,
                "bundleSchema": source.manifest.compatibility.bundle_schema,
                "eventCount": source.manifest.views.event_count,
            },
            "rootMappings": {key: value for key, value in mappings},
        }
        if snapshot is not None:
            record["resumeSnapshot"] = _assessment_mapping(snapshot)
        _write_new(stage / "import.json", pretty_json_bytes(record))
        _fsync_directory(staged_bundle)
        _fsync_directory(stage)
        if target.exists() or target.is_symlink():
            raise BundleImportError(code="bundle_import_exists")
        os.rename(stage, target)
        _fsync_directory(imports)
        published = True
        return imported
    except (BundleError, ValidationError):
        raise
    except OSError:
        raise BundleImportError(code="bundle_import_failed") from None
    finally:
        if not published and stage.exists():
            shutil.rmtree(stage)
        lock.unlink(missing_ok=True)
