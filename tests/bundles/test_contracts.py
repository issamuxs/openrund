from __future__ import annotations

import pytest

from openrund.bundles import (
    BundleArtifact,
    BundleArtifactAvailability,
    BundleArtifactOmission,
    BundleCompleteness,
    BundleCompletenessStatus,
    ResumeAssessment,
    ResumeIssue,
    ResumeIssueKind,
    ResumeIssueSeverity,
    bundle_directory_path,
    bundle_file_path,
)
from openrund.contracts.ids import ArtifactId
from openrund.errors import BundleError, ValidationError
from openrund.paths import PortablePath


def test_included_artifact_requires_exact_integrity_metadata() -> None:
    artifact = BundleArtifact(
        artifact_id=ArtifactId(value="art_1"),
        kind="report",
        availability=BundleArtifactAvailability.INCLUDED,
        available=True,
        required_for_resume=True,
        byte_length=3,
        sha256="a" * 64,
        path=PortablePath(value="artifacts/art_1.bin"),
    )
    assert artifact.path == PortablePath(value="artifacts/art_1.bin")

    with pytest.raises(ValidationError, match="bundle_artifact_included_invalid"):
        BundleArtifact(
            artifact_id=ArtifactId(value="art_1"),
            kind="report",
            availability=BundleArtifactAvailability.INCLUDED,
            available=True,
            required_for_resume=True,
        )


def test_omitted_artifact_requires_classified_reason() -> None:
    artifact = BundleArtifact(
        artifact_id=ArtifactId(value="art_1"),
        kind="report",
        availability=BundleArtifactAvailability.OMITTED,
        available=True,
        required_for_resume=True,
        byte_length=3,
        sha256="a" * 64,
        omission=BundleArtifactOmission.PROFILE,
        omission_reason="omitted by audit profile",
    )
    assert artifact.omission is BundleArtifactOmission.PROFILE


def test_completeness_status_cannot_disagree_with_exclusions() -> None:
    with pytest.raises(ValidationError, match="bundle_completeness_inconsistent"):
        BundleCompleteness(
            status=BundleCompletenessStatus.COMPLETE,
            excluded_artifact_ids=(ArtifactId(value="art_1"),),
        )


def test_resume_assessment_is_consistent_with_blocking_issues() -> None:
    issue = ResumeIssue(
        kind=ResumeIssueKind.MISSING_PROVIDER,
        severity=ResumeIssueSeverity.BLOCKING,
        subject="provider-a",
        evidence_pointer="/resume/requiredProviders",
    )
    assessment = ResumeAssessment(
        resumable=False,
        issues=(issue,),
        missing_root_mappings=(),
    )
    assert not assessment.resumable
    with pytest.raises(ValidationError, match="resume_assessment_inconsistent"):
        ResumeAssessment(resumable=True, issues=(issue,), missing_root_mappings=())


@pytest.mark.parametrize(
    "value",
    ("../manifest.json", "/manifest.json", "C:/manifest.json", "a\\b", "a//b", "a/./b"),
)
def test_bundle_file_paths_reject_platform_and_traversal_confusion(value: str) -> None:
    with pytest.raises(BundleError, match="bundle_path_invalid"):
        bundle_file_path(value)


def test_bundle_directory_paths_require_one_portable_trailing_separator() -> None:
    assert bundle_directory_path("artifacts/") == "artifacts/"
    with pytest.raises(BundleError, match="bundle_directory_invalid"):
        bundle_directory_path("artifacts")
