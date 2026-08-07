from __future__ import annotations

import asyncio
import hashlib
import json
import os
from dataclasses import replace
from pathlib import Path
from typing import cast

import pytest

from openrund.bundles import (
    BundleArtifact,
    BundleArtifactAvailability,
    BundleIntegrity,
    bundle_commitment,
    event_frame_commitment,
    export_bundle,
    verify_bundle,
)
from openrund.bundles._wire import manifest_bytes, manifest_from_bytes
from openrund.contracts.ids import ArtifactId
from openrund.contracts.json import JsonObject, freeze_json
from openrund.errors import BundleError, BundleIntegrityError, ValidationError
from openrund.paths import PortablePath

from .conftest import BundleSource


def _export(tmp_path: Path, source: BundleSource) -> Path:
    return asyncio.run(
        export_bundle(
            run_id=source.run_id,
            output_path=tmp_path / "run.orun",
            event_store=source.event_store,
            artifact_store=source.artifact_store,
            exported_at=source.timestamp,
        )
    ).bundle_path


def _reseal_events(path: Path, mutate: object) -> None:
    manifest_path = path / "manifest.json"
    manifest = manifest_from_bytes(manifest_path.read_bytes())
    rows = [json.loads(line) for line in (path / "events.jsonl").read_text().splitlines()]
    if mutate == "gap":
        rows[1]["position"] = 4
    elif mutate == "run":
        rows[1]["runID"] = "run_other"
    else:
        raise AssertionError("unknown mutation")
    content = b"".join(
        (json.dumps(item, ensure_ascii=False, separators=(",", ":")) + "\n").encode()
        for item in rows
    )
    (path / "events.jsonl").write_bytes(content)
    frames = tuple(freeze_json(item) for item in rows)
    assert all(isinstance(item, JsonObject) for item in frames)
    event_integrity = event_frame_commitment(cast(tuple[JsonObject, ...], frames))
    files = tuple(
        replace(
            item,
            sha256=hashlib.sha256(content).hexdigest(),
            byte_length=len(content),
        )
        if item.path.value == "events.jsonl"
        else item
        for item in manifest.integrity.files
    )
    commitment = bundle_commitment(
        profile=manifest.profile,
        source_run_id=manifest.source_run_id,
        compatibility=manifest.compatibility,
        events=event_integrity,
        files=files,
    )
    manifest = replace(
        manifest,
        integrity=BundleIntegrity(
            files=files,
            events=event_integrity,
            bundle=commitment,
        ),
    )
    manifest_path.write_bytes(manifest_bytes(manifest))


@pytest.mark.parametrize(
    ("mutation", "code"),
    (("gap", "bundle_event_position_invalid"), ("run", "bundle_event_run_mismatch")),
)
def test_resealed_malicious_event_history_still_fails_semantics(
    tmp_path: Path, bundle_source: BundleSource, mutation: str, code: str
) -> None:
    path = _export(tmp_path, bundle_source)
    _reseal_events(path, mutation)
    with pytest.raises(BundleIntegrityError, match=code):
        verify_bundle(path)


def test_manifest_cannot_hide_artifact_or_resume_inconsistency(
    tmp_path: Path, bundle_source: BundleSource
) -> None:
    path = _export(tmp_path, bundle_source)
    manifest_path = path / "manifest.json"
    raw = json.loads(manifest_path.read_text(encoding="utf-8"))
    raw["artifacts"][0]["kind"] = "different"
    manifest_path.write_text(json.dumps(raw), encoding="utf-8")
    with pytest.raises(BundleIntegrityError, match="bundle_artifact_manifest_mismatch"):
        verify_bundle(path)

    other = asyncio.run(
        export_bundle(
            run_id=bundle_source.run_id,
            output_path=tmp_path / "other.orun",
            event_store=bundle_source.event_store,
            artifact_store=bundle_source.artifact_store,
            exported_at=bundle_source.timestamp,
        )
    ).bundle_path
    other_manifest = other / "manifest.json"
    raw = json.loads(other_manifest.read_text(encoding="utf-8"))
    raw["resume"]["requiredProviders"] = ["undeclared"]
    other_manifest.write_text(json.dumps(raw), encoding="utf-8")
    with pytest.raises(BundleError, match="bundle_provider_requirements_mismatch"):
        verify_bundle(other)


def test_extra_directories_and_symlink_ancestors_are_rejected(
    tmp_path: Path, bundle_source: BundleSource
) -> None:
    path = _export(tmp_path, bundle_source)
    (path / "extra").mkdir()
    with pytest.raises(BundleIntegrityError, match="bundle_directory_table_mismatch"):
        verify_bundle(path)

    real = tmp_path / "real"
    real.mkdir()
    linked = tmp_path / "linked"
    os.symlink(real, linked)
    with pytest.raises(BundleError, match="bundle_output_parent_invalid"):
        asyncio.run(
            export_bundle(
                run_id=bundle_source.run_id,
                output_path=linked / "unsafe.orun",
                event_store=bundle_source.event_store,
                exported_at=bundle_source.timestamp,
            )
        )


def test_artifact_identity_cannot_create_a_manifest_path() -> None:
    with pytest.raises(ValidationError, match="bundle_artifact_id_invalid"):
        BundleArtifact(
            artifact_id=ArtifactId(value="../events.jsonl"),
            kind="bad",
            availability=BundleArtifactAvailability.INCLUDED,
            available=True,
            required_for_resume=True,
            byte_length=0,
            sha256="0" * 64,
            path=PortablePath(value="artifacts/bad.bin"),
        )


def test_unsupported_schema_is_rejected_before_file_reads(
    tmp_path: Path, bundle_source: BundleSource
) -> None:
    path = _export(tmp_path, bundle_source)
    manifest = path / "manifest.json"
    raw = json.loads(manifest.read_text(encoding="utf-8"))
    raw["version"] = 2
    manifest.write_text(json.dumps(raw), encoding="utf-8")
    with pytest.raises(BundleError, match="bundle_manifest_malformed"):
        verify_bundle(path)
