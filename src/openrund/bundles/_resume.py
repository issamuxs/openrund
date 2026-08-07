"""Non-authoritative resumability assessment for imported Bundles."""

from __future__ import annotations

from collections.abc import Mapping
from typing import cast

from openrund.errors import ValidationError

from ._model import (
    BundleCompletenessStatus,
    ImportedBundle,
    ResumeAssessment,
    ResumeIssue,
    ResumeIssueKind,
    ResumeIssueSeverity,
)


def _strings(value: object, code: str) -> tuple[str, ...]:
    try:
        items: tuple[object, ...] = tuple(value)  # type: ignore[arg-type]
    except TypeError as error:
        raise ValidationError(code=code) from error
    if any(not isinstance(item, str) or item == "" for item in items):
        raise ValidationError(code=code)
    return cast(tuple[str, ...], items)


def _issue(kind: ResumeIssueKind, subject: str, pointer: str) -> ResumeIssue:
    return ResumeIssue(
        kind=kind,
        severity=ResumeIssueSeverity.BLOCKING,
        subject=subject,
        evidence_pointer=pointer,
    )


def assess_resume(
    imported_bundle: ImportedBundle,
    *,
    available_capabilities: tuple[str, ...] = (),
    available_providers: tuple[str, ...] = (),
    supported_policy_key: str | None = None,
    compatible_policy_keys: tuple[str, ...] = (),
    compatible_capabilities: Mapping[str, tuple[str, ...]] | None = None,
    resumable_wait_kinds: tuple[str, ...] = (),
) -> ResumeAssessment:
    if not isinstance(imported_bundle, ImportedBundle):
        raise ValidationError(code="resume_import_invalid")
    capabilities = _strings(available_capabilities, "resume_capabilities_invalid")
    providers = _strings(available_providers, "resume_providers_invalid")
    policies = _strings(compatible_policy_keys, "resume_policy_keys_invalid")
    waits = frozenset(_strings(resumable_wait_kinds, "resume_wait_kinds_invalid"))
    if supported_policy_key is not None and (
        not isinstance(supported_policy_key, str) or supported_policy_key == ""
    ):
        raise ValidationError(code="resume_policy_key_invalid")
    equivalents = compatible_capabilities or {}
    if any(
        not isinstance(key, str)
        or key == ""
        or any(not isinstance(item, str) or item == "" for item in values)
        for key, values in equivalents.items()
    ):
        raise ValidationError(code="resume_capability_equivalents_invalid")

    manifest = imported_bundle.manifest
    mapping_keys = {key for key, _value in imported_bundle.root_mappings}
    missing_roots = tuple(
        key for key in manifest.resume.required_root_mappings if key not in mapping_keys
    )
    issues: list[ResumeIssue] = []
    if manifest.completeness.status is not BundleCompletenessStatus.COMPLETE:
        issues.append(
            _issue(
                ResumeIssueKind.BUNDLE_INCOMPLETE,
                manifest.completeness.status.value,
                "/completeness",
            )
        )
    issues.extend(
        _issue(
            ResumeIssueKind.MISSING_ROOT_MAPPING,
            key,
            "/resume/requiredRootMappings",
        )
        for key in missing_roots
    )
    for required in manifest.resume.required_capabilities:
        compatible = equivalents.get(required, ())
        if required not in capabilities and not any(item in capabilities for item in compatible):
            issues.append(
                _issue(
                    ResumeIssueKind.MISSING_CAPABILITY,
                    required,
                    "/resume/requiredCapabilities",
                )
            )
    issues.extend(
        _issue(
            ResumeIssueKind.MISSING_PROVIDER,
            required,
            "/resume/requiredProviders",
        )
        for required in manifest.resume.required_providers
        if required not in providers
    )
    policy_compatible = (
        supported_policy_key == manifest.policy.key or manifest.policy.key in policies
    )
    if not policy_compatible:
        issues.append(
            _issue(
                ResumeIssueKind.POLICY_INCOMPATIBLE,
                manifest.policy.key,
                "/policy/key",
            )
        )
    issues.extend(
        _issue(ResumeIssueKind.PENDING_WAIT, wait, "/resume/pendingWaits")
        for wait in manifest.resume.pending_waits
        if wait not in waits
    )
    issues.extend(
        _issue(
            ResumeIssueKind.ARTIFACT_UNAVAILABLE,
            artifact_id.value,
            "/resume/unavailableArtifacts",
        )
        for artifact_id in manifest.resume.unavailable_artifacts
    )
    if manifest.views.status in {"completed", "failed", "cancelled"}:
        issues.append(
            _issue(
                ResumeIssueKind.TERMINAL_STATE,
                manifest.views.status,
                "/views/status",
            )
        )
    return ResumeAssessment(
        resumable=not issues,
        issues=tuple(issues),
        missing_root_mappings=missing_roots,
    )
