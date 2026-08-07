"""Immutable values for portable ``.orun`` Bundle operations."""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import StrEnum
from pathlib import PureWindowsPath
from typing import Final, cast, final

from openrund._version import __version__
from openrund.contracts.ids import ArtifactId, RunId
from openrund.contracts.portable import BundleProfile
from openrund.contracts.time import Timestamp
from openrund.errors import ValidationError
from openrund.paths import PortablePath

BUNDLE_SCHEMA_VERSION: Final = 1
BUNDLE_EVENT_GRAMMAR_VERSION: Final = 1
BUNDLE_VIEW_SCHEMA_VERSION: Final = 1
BUNDLE_POLICY_MANIFEST_VERSION: Final = 1
BUNDLE_CAPABILITY_MANIFEST_VERSION: Final = 1

_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_KNOWN_CRITICAL_FIELDS: Final = frozenset(
    {"version", "compatibility", "source", "layout", "integrity", "resume"}
)


def _text(value: object, code: str) -> str:
    if not isinstance(value, str) or value == "":
        raise ValidationError(code=code)
    return value


def _strings(value: object, code: str) -> tuple[str, ...]:
    try:
        items: tuple[object, ...] = tuple(value)  # type: ignore[arg-type]
    except TypeError as error:
        raise ValidationError(code=code) from error
    if any(not isinstance(item, str) or item == "" for item in items):
        raise ValidationError(code=code)
    if len(set(items)) != len(items):
        raise ValidationError(code=code)
    return cast(tuple[str, ...], items)


def _artifacts(value: object, code: str) -> tuple[ArtifactId, ...]:
    try:
        items: tuple[object, ...] = tuple(value)  # type: ignore[arg-type]
    except TypeError as error:
        raise ValidationError(code=code) from error
    if any(not isinstance(item, ArtifactId) for item in items) or len(set(items)) != len(items):
        raise ValidationError(code=code)
    return cast(tuple[ArtifactId, ...], items)


def _sha256(value: object, code: str) -> str:
    if not isinstance(value, str) or _SHA256.fullmatch(value) is None:
        raise ValidationError(code=code)
    return value


def _artifact_component(value: ArtifactId) -> str:
    component = value.value
    if (
        component in {".", ".."}
        or "\x00" in component
        or "/" in component
        or "\\" in component
        or PureWindowsPath(component).drive
    ):
        raise ValidationError(code="bundle_artifact_id_invalid")
    return component


@final
@dataclass(frozen=True, slots=True, kw_only=True)
class BundleCompatibility:
    runtime_version: str = __version__
    runtime_range: str = f"^{__version__}"
    bundle_schema: int = BUNDLE_SCHEMA_VERSION
    event_grammar: int = BUNDLE_EVENT_GRAMMAR_VERSION
    view_schema: int = BUNDLE_VIEW_SCHEMA_VERSION
    policy_manifest: int = BUNDLE_POLICY_MANIFEST_VERSION
    capability_manifest: int = BUNDLE_CAPABILITY_MANIFEST_VERSION

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "runtime_version", _text(self.runtime_version, "bundle_runtime_version_invalid")
        )
        object.__setattr__(
            self, "runtime_range", _text(self.runtime_range, "bundle_runtime_range_invalid")
        )
        expected = (
            (self.bundle_schema, BUNDLE_SCHEMA_VERSION),
            (self.event_grammar, BUNDLE_EVENT_GRAMMAR_VERSION),
            (self.view_schema, BUNDLE_VIEW_SCHEMA_VERSION),
            (self.policy_manifest, BUNDLE_POLICY_MANIFEST_VERSION),
            (self.capability_manifest, BUNDLE_CAPABILITY_MANIFEST_VERSION),
        )
        if any(actual != required for actual, required in expected):
            raise ValidationError(code="bundle_compatibility_unsupported")


@final
@dataclass(frozen=True, slots=True, kw_only=True)
class BundleLayout:
    manifest: str = "manifest.json"
    events: str = "events.jsonl"
    artifacts: str = "artifacts/"
    views: str = "views/"
    policy: str = "policy/"
    capabilities: str = "capabilities/"
    exports: str = "exports/"

    def __post_init__(self) -> None:
        if (
            self.manifest,
            self.events,
            self.artifacts,
            self.views,
            self.policy,
            self.capabilities,
            self.exports,
        ) != (
            "manifest.json",
            "events.jsonl",
            "artifacts/",
            "views/",
            "policy/",
            "capabilities/",
            "exports/",
        ):
            raise ValidationError(code="bundle_layout_unsupported")


@final
@dataclass(frozen=True, slots=True, kw_only=True)
class BundleFileCommitment:
    path: PortablePath
    sha256: str
    byte_length: int

    def __post_init__(self) -> None:
        if not isinstance(self.path, PortablePath):
            raise ValidationError(code="bundle_file_path_invalid")
        object.__setattr__(self, "sha256", _sha256(self.sha256, "bundle_file_hash_invalid"))
        if (
            isinstance(self.byte_length, bool)
            or not isinstance(self.byte_length, int)
            or self.byte_length < 0
        ):
            raise ValidationError(code="bundle_file_length_invalid")


@final
@dataclass(frozen=True, slots=True, kw_only=True)
class BundleEventCommitment:
    count: int
    head: str
    algorithm: str = "sha256-chain-v1"

    def __post_init__(self) -> None:
        if self.algorithm != "sha256-chain-v1":
            raise ValidationError(code="bundle_event_algorithm_unsupported")
        if isinstance(self.count, bool) or not isinstance(self.count, int) or self.count < 0:
            raise ValidationError(code="bundle_event_count_invalid")
        object.__setattr__(self, "head", _sha256(self.head, "bundle_event_head_invalid"))


@final
@dataclass(frozen=True, slots=True, kw_only=True)
class BundleCommitment:
    sha256: str
    algorithm: str = "sha256-canonical-json-v1"

    def __post_init__(self) -> None:
        if self.algorithm != "sha256-canonical-json-v1":
            raise ValidationError(code="bundle_algorithm_unsupported")
        object.__setattr__(self, "sha256", _sha256(self.sha256, "bundle_hash_invalid"))


@final
@dataclass(frozen=True, slots=True, kw_only=True)
class BundleIntegrity:
    files: tuple[BundleFileCommitment, ...]
    events: BundleEventCommitment
    bundle: BundleCommitment

    def __post_init__(self) -> None:
        try:
            files = tuple(self.files)
        except TypeError as error:
            raise ValidationError(code="bundle_files_invalid") from error
        if any(not isinstance(item, BundleFileCommitment) for item in files):
            raise ValidationError(code="bundle_files_invalid")
        if len({item.path.value for item in files}) != len(files):
            raise ValidationError(code="bundle_file_duplicate")
        if any(item.path.value == "manifest.json" for item in files):
            raise ValidationError(code="bundle_manifest_self_commitment")
        if not isinstance(self.events, BundleEventCommitment) or not isinstance(
            self.bundle, BundleCommitment
        ):
            raise ValidationError(code="bundle_integrity_invalid")
        object.__setattr__(self, "files", files)


class BundleCompletenessStatus(StrEnum):
    COMPLETE = "complete"
    PARTIAL = "partial"


@final
@dataclass(frozen=True, slots=True, kw_only=True)
class BundleCompleteness:
    status: BundleCompletenessStatus
    excluded_artifact_ids: tuple[ArtifactId, ...] = ()

    def __post_init__(self) -> None:
        if not isinstance(self.status, BundleCompletenessStatus):
            raise ValidationError(code="bundle_completeness_status_invalid")
        excluded = _artifacts(self.excluded_artifact_ids, "bundle_excluded_artifact_ids_invalid")
        if (self.status is BundleCompletenessStatus.COMPLETE) != (not excluded):
            raise ValidationError(code="bundle_completeness_inconsistent")
        object.__setattr__(self, "excluded_artifact_ids", excluded)


class BundleArtifactAvailability(StrEnum):
    INCLUDED = "included"
    OMITTED = "omitted"
    UNAVAILABLE = "unavailable"
    EXTERNAL = "external"


class BundleArtifactOmission(StrEnum):
    PROFILE = "profile"
    MISSING_BYTES = "missing_bytes"
    REDACTED = "redacted"
    EXTERNAL_REFERENCE = "external_reference"
    UNAVAILABLE = "unavailable"


@final
@dataclass(frozen=True, slots=True, kw_only=True)
class BundleArtifact:
    artifact_id: ArtifactId
    kind: str
    availability: BundleArtifactAvailability
    available: bool
    required_for_resume: bool
    content_type: str | None = None
    byte_length: int | None = None
    sha256: str | None = None
    path: PortablePath | None = None
    omission: BundleArtifactOmission | None = None
    omission_reason: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.artifact_id, ArtifactId):
            raise ValidationError(code="bundle_artifact_id_invalid")
        component = _artifact_component(self.artifact_id)
        object.__setattr__(self, "kind", _text(self.kind, "bundle_artifact_kind_invalid"))
        if not isinstance(self.availability, BundleArtifactAvailability):
            raise ValidationError(code="bundle_artifact_availability_invalid")
        if not isinstance(self.available, bool) or not isinstance(self.required_for_resume, bool):
            raise ValidationError(code="bundle_artifact_flags_invalid")
        if self.content_type is not None:
            object.__setattr__(
                self,
                "content_type",
                _text(self.content_type, "bundle_artifact_content_type_invalid"),
            )
        if self.byte_length is not None and (
            isinstance(self.byte_length, bool)
            or not isinstance(self.byte_length, int)
            or self.byte_length < 0
        ):
            raise ValidationError(code="bundle_artifact_length_invalid")
        if self.sha256 is not None:
            object.__setattr__(self, "sha256", _sha256(self.sha256, "bundle_artifact_hash_invalid"))
        included = self.availability is BundleArtifactAvailability.INCLUDED
        if included:
            if (
                not self.available
                or self.path is None
                or self.byte_length is None
                or self.sha256 is None
                or self.omission is not None
                or self.omission_reason is not None
            ):
                raise ValidationError(code="bundle_artifact_included_invalid")
            assert self.path is not None
            if self.path.value != f"artifacts/{component}.bin":
                raise ValidationError(code="bundle_artifact_path_invalid")
        elif (
            self.path is not None
            or self.omission is None
            or self.omission_reason is None
            or self.omission_reason == ""
        ):
            raise ValidationError(code="bundle_artifact_omission_invalid")


@final
@dataclass(frozen=True, slots=True, kw_only=True)
class BundleViews:
    status: str
    current_position: int
    pending_waits: tuple[str, ...]
    event_count: int

    def __post_init__(self) -> None:
        object.__setattr__(self, "status", _text(self.status, "bundle_view_status_invalid"))
        for value in (self.current_position, self.event_count):
            if isinstance(value, bool) or not isinstance(value, int) or value < 0:
                raise ValidationError(code="bundle_view_count_invalid")
        if self.current_position != self.event_count:
            raise ValidationError(code="bundle_view_watermark_mismatch")
        object.__setattr__(
            self, "pending_waits", _strings(self.pending_waits, "bundle_pending_waits_invalid")
        )


@final
@dataclass(frozen=True, slots=True, kw_only=True)
class BundlePolicy:
    rules: tuple[str, ...]
    key: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "rules", _strings(self.rules, "bundle_policy_rules_invalid"))
        object.__setattr__(self, "key", _sha256(self.key, "bundle_policy_key_invalid"))


@final
@dataclass(frozen=True, slots=True, kw_only=True)
class BundleExports:
    runtime_audit_json: PortablePath
    runtime_audit_markdown: PortablePath
    action_receipts: tuple[PortablePath, ...] = ()
    check_json: PortablePath | None = None
    check_markdown: PortablePath | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.runtime_audit_json, PortablePath) or not isinstance(
            self.runtime_audit_markdown, PortablePath
        ):
            raise ValidationError(code="bundle_exports_invalid")
        try:
            receipts = tuple(self.action_receipts)
        except TypeError as error:
            raise ValidationError(code="bundle_receipts_invalid") from error
        if any(not isinstance(item, PortablePath) for item in receipts):
            raise ValidationError(code="bundle_receipts_invalid")
        if len({item.value for item in receipts}) != len(receipts):
            raise ValidationError(code="bundle_receipts_duplicate")
        for item in (self.check_json, self.check_markdown):
            if item is not None and not isinstance(item, PortablePath):
                raise ValidationError(code="bundle_exports_invalid")
        object.__setattr__(self, "action_receipts", receipts)


@final
@dataclass(frozen=True, slots=True, kw_only=True)
class BundleResumeRequirements:
    required_root_mappings: tuple[str, ...]
    required_capabilities: tuple[str, ...]
    required_providers: tuple[str, ...]
    pending_waits: tuple[str, ...]
    unavailable_artifacts: tuple[ArtifactId, ...]

    def __post_init__(self) -> None:
        for name in (
            "required_root_mappings",
            "required_capabilities",
            "required_providers",
            "pending_waits",
        ):
            object.__setattr__(
                self, name, _strings(getattr(self, name), f"bundle_resume_{name}_invalid")
            )
        object.__setattr__(
            self,
            "unavailable_artifacts",
            _artifacts(self.unavailable_artifacts, "bundle_resume_artifacts_invalid"),
        )


@final
@dataclass(frozen=True, slots=True, kw_only=True)
class BundleManifest:
    run_id: RunId
    source_run_id: RunId
    exported_at: Timestamp
    compatibility: BundleCompatibility
    profile: BundleProfile
    critical_fields: tuple[str, ...]
    layout: BundleLayout
    completeness: BundleCompleteness
    integrity: BundleIntegrity
    views: BundleViews
    capability_grants: tuple[str, ...]
    provider_ids: tuple[str, ...]
    policy: BundlePolicy
    exports: BundleExports
    artifacts: tuple[BundleArtifact, ...]
    resume: BundleResumeRequirements
    version: int = BUNDLE_SCHEMA_VERSION

    def __post_init__(self) -> None:
        if self.version != BUNDLE_SCHEMA_VERSION:
            raise ValidationError(code="bundle_schema_unsupported")
        if not isinstance(self.run_id, RunId) or not isinstance(self.source_run_id, RunId):
            raise ValidationError(code="bundle_run_id_invalid")
        if self.run_id != self.source_run_id:
            raise ValidationError(code="bundle_run_id_mismatch")
        if not isinstance(self.exported_at, Timestamp):
            raise ValidationError(code="bundle_exported_at_invalid")
        if not isinstance(self.compatibility, BundleCompatibility):
            raise ValidationError(code="bundle_compatibility_invalid")
        if not isinstance(self.profile, BundleProfile):
            raise ValidationError(code="bundle_profile_invalid")
        critical = _strings(self.critical_fields, "bundle_critical_fields_invalid")
        if set(critical) - _KNOWN_CRITICAL_FIELDS:
            raise ValidationError(code="bundle_critical_field_unknown")
        required = {"version", "compatibility", "source", "layout", "integrity", "resume"}
        if set(critical) != required:
            raise ValidationError(code="bundle_critical_fields_incomplete")
        for value, kind, code in (
            (self.layout, BundleLayout, "bundle_layout_invalid"),
            (self.completeness, BundleCompleteness, "bundle_completeness_invalid"),
            (self.integrity, BundleIntegrity, "bundle_integrity_invalid"),
            (self.views, BundleViews, "bundle_views_invalid"),
            (self.policy, BundlePolicy, "bundle_policy_invalid"),
            (self.exports, BundleExports, "bundle_exports_invalid"),
            (self.resume, BundleResumeRequirements, "bundle_resume_invalid"),
        ):
            if not isinstance(value, kind):
                raise ValidationError(code=code)
        grants = _strings(self.capability_grants, "bundle_capability_grants_invalid")
        providers = _strings(self.provider_ids, "bundle_providers_invalid")
        try:
            artifacts = tuple(self.artifacts)
        except TypeError as error:
            raise ValidationError(code="bundle_artifacts_invalid") from error
        if any(not isinstance(item, BundleArtifact) for item in artifacts):
            raise ValidationError(code="bundle_artifacts_invalid")
        if len({item.artifact_id for item in artifacts}) != len(artifacts):
            raise ValidationError(code="bundle_artifact_duplicate")
        if self.integrity.events.count != self.views.event_count:
            raise ValidationError(code="bundle_event_count_mismatch")
        if grants != self.resume.required_capabilities:
            raise ValidationError(code="bundle_capability_requirements_mismatch")
        if providers != self.resume.required_providers:
            raise ValidationError(code="bundle_provider_requirements_mismatch")
        excluded = set(self.completeness.excluded_artifact_ids)
        unavailable = set(self.resume.unavailable_artifacts)
        declared_unavailable = {
            item.artifact_id
            for item in artifacts
            if item.availability is not BundleArtifactAvailability.INCLUDED
            and (
                item.required_for_resume
                or item.availability is BundleArtifactAvailability.UNAVAILABLE
            )
        }
        if not excluded.issubset(unavailable) or declared_unavailable != unavailable:
            raise ValidationError(code="bundle_artifact_requirements_mismatch")
        object.__setattr__(self, "critical_fields", critical)
        object.__setattr__(self, "capability_grants", grants)
        object.__setattr__(self, "provider_ids", providers)
        object.__setattr__(self, "artifacts", artifacts)


@final
@dataclass(frozen=True, slots=True, kw_only=True)
class BundleVerificationCheck:
    name: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "name", _text(self.name, "bundle_check_name_invalid"))


@final
@dataclass(frozen=True, slots=True, kw_only=True)
class BundleVerification:
    bundle_path: str
    manifest: BundleManifest
    checks: tuple[BundleVerificationCheck, ...]


class ResumeIssueKind(StrEnum):
    MISSING_ROOT_MAPPING = "missing_root_mapping"
    MISSING_CAPABILITY = "missing_capability"
    MISSING_PROVIDER = "missing_provider"
    POLICY_INCOMPATIBLE = "policy_incompatible"
    PENDING_WAIT = "pending_wait"
    ARTIFACT_UNAVAILABLE = "artifact_unavailable"
    TERMINAL_STATE = "terminal_state"
    BUNDLE_INCOMPLETE = "bundle_incomplete"
    SCHEMA_INCOMPATIBLE = "schema_incompatible"


class ResumeIssueSeverity(StrEnum):
    BLOCKING = "blocking"
    WARNING = "warning"


@final
@dataclass(frozen=True, slots=True, kw_only=True)
class ResumeIssue:
    kind: ResumeIssueKind
    severity: ResumeIssueSeverity
    subject: str
    evidence_pointer: str

    def __post_init__(self) -> None:
        if not isinstance(self.kind, ResumeIssueKind) or not isinstance(
            self.severity, ResumeIssueSeverity
        ):
            raise ValidationError(code="resume_issue_kind_invalid")
        object.__setattr__(self, "subject", _text(self.subject, "resume_issue_subject_invalid"))
        pointer = _text(self.evidence_pointer, "resume_issue_pointer_invalid")
        if not pointer.startswith("/"):
            raise ValidationError(code="resume_issue_pointer_invalid")
        object.__setattr__(self, "evidence_pointer", pointer)


@final
@dataclass(frozen=True, slots=True, kw_only=True)
class ResumeAssessment:
    resumable: bool
    issues: tuple[ResumeIssue, ...]
    missing_root_mappings: tuple[str, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.resumable, bool):
            raise ValidationError(code="resume_assessment_flag_invalid")
        try:
            issues = tuple(self.issues)
        except TypeError as error:
            raise ValidationError(code="resume_assessment_issues_invalid") from error
        if any(not isinstance(item, ResumeIssue) for item in issues):
            raise ValidationError(code="resume_assessment_issues_invalid")
        missing = _strings(self.missing_root_mappings, "resume_missing_roots_invalid")
        blocked = any(item.severity is ResumeIssueSeverity.BLOCKING for item in issues)
        if self.resumable == blocked:
            raise ValidationError(code="resume_assessment_inconsistent")
        object.__setattr__(self, "issues", issues)
        object.__setattr__(self, "missing_root_mappings", missing)


@final
@dataclass(frozen=True, slots=True, kw_only=True)
class ImportedBundle:
    bundle_path: str
    manifest: BundleManifest
    root_mappings: tuple[tuple[str, str], ...]
    import_id: str
    imported_at: Timestamp

    def __post_init__(self) -> None:
        object.__setattr__(self, "bundle_path", _text(self.bundle_path, "import_path_invalid"))
        if not isinstance(self.manifest, BundleManifest):
            raise ValidationError(code="import_manifest_invalid")
        object.__setattr__(self, "import_id", _text(self.import_id, "import_id_invalid"))
        if not isinstance(self.imported_at, Timestamp):
            raise ValidationError(code="import_timestamp_invalid")
        try:
            mappings = tuple(self.root_mappings)
        except TypeError as error:
            raise ValidationError(code="import_root_mappings_invalid") from error
        if any(
            not isinstance(item, tuple)
            or len(item) != 2
            or not isinstance(item[0], str)
            or item[0] == ""
            or not isinstance(item[1], str)
            or item[1] == ""
            for item in mappings
        ):
            raise ValidationError(code="import_root_mappings_invalid")
        if len({item[0] for item in mappings}) != len(mappings):
            raise ValidationError(code="import_root_mapping_duplicate")
        object.__setattr__(self, "root_mappings", mappings)
