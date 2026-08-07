from __future__ import annotations

import asyncio
import json
import os
from pathlib import Path

import pytest

from openrund.bundles import BundleExportResult, export_bundle, verify_bundle
from openrund.errors import BundleError, BundleIntegrityError

from .conftest import BundleSource


def _export(tmp_path: Path, source: BundleSource) -> BundleExportResult:
    return asyncio.run(
        export_bundle(
            run_id=source.run_id,
            output_path=tmp_path / "run.orun",
            event_store=source.event_store,
            artifact_store=source.artifact_store,
            exported_at=source.timestamp,
            required_providers=("local",),
        )
    )


def test_verify_accepts_exact_exported_tree(tmp_path: Path, bundle_source: BundleSource) -> None:
    exported = _export(tmp_path, bundle_source)
    result = verify_bundle(exported.bundle_path)
    assert result.manifest == exported.manifest
    assert tuple(item.name for item in result.checks) == (
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


def test_verify_rejects_tampered_and_extra_files(
    tmp_path: Path, bundle_source: BundleSource
) -> None:
    exported = _export(tmp_path, bundle_source)
    (exported.bundle_path / "events.jsonl").write_bytes(b"{}\n")
    with pytest.raises(BundleIntegrityError, match="bundle_file_integrity_mismatch"):
        verify_bundle(exported.bundle_path)

    other = asyncio.run(
        export_bundle(
            run_id=bundle_source.run_id,
            output_path=tmp_path / "other.orun",
            event_store=bundle_source.event_store,
            exported_at=bundle_source.timestamp,
        )
    )
    (other.bundle_path / "undeclared.txt").write_text("no", encoding="utf-8")
    with pytest.raises(BundleIntegrityError, match="bundle_file_table_mismatch"):
        verify_bundle(other.bundle_path)


def test_verify_rejects_manifest_run_mismatch_before_replay(
    tmp_path: Path, bundle_source: BundleSource
) -> None:
    exported = _export(tmp_path, bundle_source)
    manifest_path = exported.bundle_path / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["source"]["runID"] = "run_other"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    with pytest.raises(BundleError, match="bundle_manifest_malformed"):
        verify_bundle(exported.bundle_path)


def test_verify_rejects_symlinks_anywhere_in_tree(
    tmp_path: Path, bundle_source: BundleSource
) -> None:
    exported = _export(tmp_path, bundle_source)
    target = exported.bundle_path / "views" / "summary.json"
    content = target.read_bytes()
    target.unlink()
    outside = tmp_path / "outside.json"
    outside.write_bytes(content)
    os.symlink(outside, target)
    with pytest.raises(BundleIntegrityError, match="bundle_symlink_forbidden"):
        verify_bundle(exported.bundle_path)
