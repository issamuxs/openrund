from __future__ import annotations

import asyncio
import json
from pathlib import Path

import pytest

from openrund.bundles import export_bundle, import_bundle, verify_bundle
from openrund.errors import BundleImportError, BundleIntegrityError

from .conftest import BundleSource


def _source(tmp_path: Path, bundle_source: BundleSource) -> Path:
    return asyncio.run(
        export_bundle(
            run_id=bundle_source.run_id,
            output_path=tmp_path / "source.orun",
            event_store=bundle_source.event_store,
            artifact_store=bundle_source.artifact_store,
            exported_at=bundle_source.timestamp,
        )
    ).bundle_path


def test_import_reverifies_and_atomically_publishes_exact_content(
    tmp_path: Path, bundle_source: BundleSource
) -> None:
    source = _source(tmp_path, bundle_source)
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    imported = import_bundle(
        source,
        runtime_home=tmp_path / "runtime",
        root_mappings={"workspace": workspace},
        imported_at=bundle_source.timestamp,
        import_id="imp_fixed",
        capture_resume_snapshot=True,
    )
    target = Path(imported.bundle_path)
    assert verify_bundle(target).manifest == imported.manifest
    assert {
        item.relative_to(source): item.read_bytes() for item in source.rglob("*") if item.is_file()
    } == {
        item.relative_to(target): item.read_bytes() for item in target.rglob("*") if item.is_file()
    }
    record = json.loads((target.parent / "import.json").read_text(encoding="utf-8"))
    assert record["verification"]["ok"] is True
    assert record["resumeSnapshot"]["resumable"] is True


def test_import_requires_mappings_and_never_publishes_partial_state(
    tmp_path: Path, bundle_source: BundleSource
) -> None:
    source = _source(tmp_path, bundle_source)
    runtime = tmp_path / "runtime"
    with pytest.raises(BundleImportError, match="bundle_root_mapping_missing"):
        import_bundle(
            source,
            runtime_home=runtime,
            root_mappings={},
            imported_at=bundle_source.timestamp,
            import_id="imp_missing",
        )
    assert not (runtime / "imports" / "imp_missing").exists()


def test_import_collision_is_absent_only(tmp_path: Path, bundle_source: BundleSource) -> None:
    source = _source(tmp_path, bundle_source)
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    kwargs = {
        "runtime_home": tmp_path / "runtime",
        "root_mappings": {"workspace": workspace},
        "imported_at": bundle_source.timestamp,
        "import_id": "imp_collision",
    }
    first = import_bundle(source, **kwargs)  # type: ignore[arg-type]
    first_record = (Path(first.bundle_path).parent / "import.json").read_bytes()
    with pytest.raises(BundleImportError, match="bundle_import_exists"):
        import_bundle(source, **kwargs)  # type: ignore[arg-type]
    assert (Path(first.bundle_path).parent / "import.json").read_bytes() == first_record


def test_import_rejects_source_tampering_before_stage_creation(
    tmp_path: Path, bundle_source: BundleSource
) -> None:
    source = _source(tmp_path, bundle_source)
    (source / "events.jsonl").write_bytes(b"{}\n")
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    with pytest.raises(BundleIntegrityError):
        import_bundle(
            source,
            runtime_home=tmp_path / "runtime",
            root_mappings={"workspace": workspace},
            imported_at=bundle_source.timestamp,
            import_id="imp_tampered",
        )
    imports = tmp_path / "runtime" / "imports"
    assert not imports.exists() or not tuple(imports.iterdir())
