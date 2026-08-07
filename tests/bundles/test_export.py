from __future__ import annotations

import asyncio
import hashlib
from pathlib import Path

import pytest

from openrund.bundles import BundleArtifactAvailability, BundleExportResult, export_bundle
from openrund.contracts.portable import BundleProfile
from openrund.errors import BundleImportError, ValidationError

from .conftest import BundleSource


def _export(**kwargs: object) -> BundleExportResult:
    return asyncio.run(export_bundle(**kwargs))  # type: ignore[arg-type]


@pytest.mark.parametrize("profile", tuple(BundleProfile))
def test_export_profiles_are_explicit_and_deterministic(
    tmp_path: Path, bundle_source: BundleSource, profile: BundleProfile
) -> None:
    first = _export(
        run_id=bundle_source.run_id,
        output_path=tmp_path / f"first-{profile.value}.orun",
        event_store=bundle_source.event_store,
        artifact_store=bundle_source.artifact_store,
        profile=profile,
        runtime_version="2.0.0",
        exported_at=bundle_source.timestamp,
        required_providers=("local",),
    )
    second = _export(
        run_id=bundle_source.run_id,
        output_path=tmp_path / f"second-{profile.value}.orun",
        event_store=bundle_source.event_store,
        artifact_store=bundle_source.artifact_store,
        profile=profile,
        runtime_version="2.0.0",
        exported_at=bundle_source.timestamp,
        required_providers=("local",),
    )
    first_tree = {
        item.relative_to(first.bundle_path): item.read_bytes()
        for item in first.bundle_path.rglob("*")
        if item.is_file()
    }
    second_tree = {
        item.relative_to(second.bundle_path): item.read_bytes()
        for item in second.bundle_path.rglob("*")
        if item.is_file()
    }
    assert first_tree == second_tree
    assert first.manifest.provider_ids == ("local",)
    artifact = first.manifest.artifacts[0]
    artifact_path = first.bundle_path / "artifacts" / f"{bundle_source.artifact_id.value}.bin"
    if profile is BundleProfile.COMPLETE:
        assert artifact.availability is BundleArtifactAvailability.INCLUDED
        assert artifact_path.read_bytes() == bundle_source.artifact_bytes
    else:
        assert artifact.availability is BundleArtifactAvailability.OMITTED
        assert not artifact_path.exists()


def test_export_file_table_commits_every_non_manifest_file(
    tmp_path: Path, bundle_source: BundleSource
) -> None:
    result = _export(
        run_id=bundle_source.run_id,
        output_path=tmp_path / "run.orun",
        event_store=bundle_source.event_store,
        artifact_store=bundle_source.artifact_store,
        exported_at=bundle_source.timestamp,
    )
    declared = {item.path.value: item for item in result.manifest.integrity.files}
    actual = {
        item.relative_to(result.bundle_path).as_posix(): item
        for item in result.bundle_path.rglob("*")
        if item.is_file() and item.relative_to(result.bundle_path).as_posix() != "manifest.json"
    }
    assert set(declared) == set(actual)
    for path, item in actual.items():
        content = item.read_bytes()
        assert declared[path].byte_length == len(content)
        assert declared[path].sha256 == hashlib.sha256(content).hexdigest()


def test_export_is_absent_only_and_requires_orun_suffix(
    tmp_path: Path, bundle_source: BundleSource
) -> None:
    target = tmp_path / "run.orun"
    target.mkdir()
    with pytest.raises(BundleImportError, match="bundle_output_exists"):
        _export(
            run_id=bundle_source.run_id,
            output_path=target,
            event_store=bundle_source.event_store,
            exported_at=bundle_source.timestamp,
        )
    with pytest.raises(ValidationError, match="bundle_output_suffix_invalid"):
        _export(
            run_id=bundle_source.run_id,
            output_path=tmp_path / "run",
            event_store=bundle_source.event_store,
            exported_at=bundle_source.timestamp,
        )


def test_audit_without_blob_declares_missing_bytes(
    tmp_path: Path, bundle_source: BundleSource
) -> None:
    result = _export(
        run_id=bundle_source.run_id,
        output_path=tmp_path / "run.orun",
        event_store=bundle_source.event_store,
        artifact_store=None,
        profile=BundleProfile.AUDIT,
        exported_at=bundle_source.timestamp,
    )
    artifact = result.manifest.artifacts[0]
    assert artifact.omission is not None
    assert artifact.omission.value == "missing_bytes"
