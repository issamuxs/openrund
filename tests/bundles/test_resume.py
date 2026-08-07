from __future__ import annotations

import asyncio
from dataclasses import replace
from pathlib import Path

from openrund.bundles import (
    BundleArtifactAvailability,
    BundleArtifactOmission,
    BundleCompleteness,
    BundleCompletenessStatus,
    BundleManifest,
    BundleResumeRequirements,
    BundleViews,
    ImportedBundle,
    ResumeIssueKind,
    assess_resume,
    export_bundle,
)
from openrund.contracts.time import Timestamp

from .conftest import BundleSource


def _imported_with_all_issues(tmp_path: Path, bundle_source: BundleSource) -> ImportedBundle:
    result = asyncio.run(
        export_bundle(
            run_id=bundle_source.run_id,
            output_path=tmp_path / "resume-source.orun",
            event_store=bundle_source.event_store,
            artifact_store=bundle_source.artifact_store,
            exported_at=bundle_source.timestamp,
        )
    )
    manifest: BundleManifest = result.manifest
    original = manifest.artifacts[0]
    omitted = replace(
        original,
        availability=BundleArtifactAvailability.OMITTED,
        path=None,
        omission=BundleArtifactOmission.PROFILE,
        omission_reason="omitted",
    )
    resume = BundleResumeRequirements(
        required_root_mappings=("workspace",),
        required_capabilities=("cap.required",),
        required_providers=("provider.required",),
        pending_waits=("approval",),
        unavailable_artifacts=(original.artifact_id,),
    )
    manifest = replace(
        manifest,
        completeness=BundleCompleteness(
            status=BundleCompletenessStatus.PARTIAL,
            excluded_artifact_ids=(original.artifact_id,),
        ),
        views=BundleViews(
            status="completed",
            current_position=manifest.views.current_position,
            pending_waits=("approval",),
            event_count=manifest.views.event_count,
        ),
        capability_grants=("cap.required",),
        provider_ids=("provider.required",),
        artifacts=(omitted,),
        resume=resume,
    )
    return ImportedBundle(
        bundle_path="/import/run.orun",
        manifest=manifest,
        root_mappings=(),
        import_id="imp_test",
        imported_at=Timestamp(value="2026-08-06T12:00:00.000Z"),
    )


def test_resume_assessment_reports_every_missing_environment_requirement(
    tmp_path: Path,
    bundle_source: BundleSource,
) -> None:
    imported = _imported_with_all_issues(tmp_path, bundle_source)
    assessment = assess_resume(imported, supported_policy_key="0" * 64)
    assert not assessment.resumable
    assert tuple(item.kind for item in assessment.issues) == (
        ResumeIssueKind.BUNDLE_INCOMPLETE,
        ResumeIssueKind.MISSING_ROOT_MAPPING,
        ResumeIssueKind.MISSING_CAPABILITY,
        ResumeIssueKind.MISSING_PROVIDER,
        ResumeIssueKind.POLICY_INCOMPATIBLE,
        ResumeIssueKind.PENDING_WAIT,
        ResumeIssueKind.ARTIFACT_UNAVAILABLE,
        ResumeIssueKind.TERMINAL_STATE,
    )


def test_resume_assessment_accepts_explicit_compatible_bindings(
    tmp_path: Path,
    bundle_source: BundleSource,
) -> None:
    imported = _imported_with_all_issues(tmp_path, bundle_source)
    manifest = replace(
        imported.manifest,
        completeness=BundleCompleteness(
            status=BundleCompletenessStatus.COMPLETE,
            excluded_artifact_ids=(),
        ),
        views=replace(imported.manifest.views, status="running"),
        artifacts=(replace(imported.manifest.artifacts[0], required_for_resume=False),),
        resume=replace(
            imported.manifest.resume,
            unavailable_artifacts=(),
        ),
    )
    imported = replace(
        imported,
        manifest=manifest,
        root_mappings=(("workspace", "/workspace"),),
    )
    assessment = assess_resume(
        imported,
        available_capabilities=("cap.equivalent",),
        available_providers=("provider.required",),
        supported_policy_key=manifest.policy.key,
        compatible_capabilities={"cap.required": ("cap.equivalent",)},
        resumable_wait_kinds=("approval",),
    )
    assert assessment.resumable
    assert assessment.issues == ()
