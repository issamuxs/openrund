"""Stable typed results shared by library and command-line operators."""

from __future__ import annotations

from dataclasses import dataclass
from enum import IntEnum
from typing import final

from openrund.contracts.json import JsonObject, JsonValue, freeze_json
from openrund.errors import ValidationError


class OperatorExitCode(IntEnum):
    OK = 0
    USAGE = 2
    NOT_FOUND = 3
    REJECTED = 4
    INTEGRITY = 5
    UNAVAILABLE = 6
    INTERNAL = 70


@final
@dataclass(frozen=True, slots=True, kw_only=True)
class OperatorFailure:
    code: str
    message: str

    def __post_init__(self) -> None:
        if not isinstance(self.code, str) or self.code == "":
            raise ValidationError(code="operator_failure_code_invalid")
        if not isinstance(self.message, str) or self.message == "":
            raise ValidationError(code="operator_failure_message_invalid")


@final
@dataclass(frozen=True, slots=True, kw_only=True)
class HelpData:
    usage: str


@final
@dataclass(frozen=True, slots=True, kw_only=True)
class CommandResultData:
    run_id: str
    command_id: str
    decision: str
    result_event_ids: tuple[str, ...] = ()
    wait_ids: tuple[str, ...] = ()
    reason: str | None = None
    superseded_by_command_id: str | None = None


@final
@dataclass(frozen=True, slots=True, kw_only=True)
class BundleExportData:
    run_id: str
    bundle_path: str
    profile: str
    completeness: str
    commitment: str


@final
@dataclass(frozen=True, slots=True, kw_only=True)
class BundleVerificationData:
    bundle_path: str
    run_id: str
    profile: str
    checks: tuple[str, ...]


@final
@dataclass(frozen=True, slots=True, kw_only=True)
class BundleReplayData:
    bundle_path: str
    run_id: str
    event_count: int
    status: str


@final
@dataclass(frozen=True, slots=True, kw_only=True)
class BundleImportData:
    bundle_path: str
    run_id: str
    import_id: str
    resumable: bool
    issues: tuple[str, ...]


@final
@dataclass(frozen=True, slots=True, kw_only=True)
class BundleAssessmentData:
    bundle_path: str
    run_id: str
    resumable: bool
    missing_root_mappings: tuple[str, ...]
    issues: tuple[JsonObject, ...]


@final
@dataclass(frozen=True, slots=True, kw_only=True)
class RunInspectionData:
    run_id: str
    status: str
    watermark: int
    root_id: str | None
    title: JsonValue
    objective: JsonValue
    pending_waits: int
    capability_authorities: int
    policy_authorities: int


@final
@dataclass(frozen=True, slots=True, kw_only=True)
class RunReplayData:
    run_id: str
    event_count: int
    watermark: int
    status: str


@final
@dataclass(frozen=True, slots=True, kw_only=True)
class RunTimelineData:
    run_id: str
    entries: tuple[JsonObject, ...]


@final
@dataclass(frozen=True, slots=True, kw_only=True)
class RunWaitsData:
    run_id: str
    pending: tuple[JsonObject, ...]
    terminal: tuple[JsonObject, ...]


@final
@dataclass(frozen=True, slots=True, kw_only=True)
class CommandExplanationData:
    run_id: str
    command_id: str
    origin: str
    actor: JsonValue
    provider: JsonValue
    operation: str
    decision: str
    reason: str | None
    trace: tuple[JsonObject, ...]
    result_event_ids: tuple[str, ...]
    result_event_types: tuple[str, ...]
    wait_id: str | None
    superseded_by_command_id: str | None


@final
@dataclass(frozen=True, slots=True, kw_only=True)
class ActionReceiptData:
    status: str
    receipt: JsonObject


@final
@dataclass(frozen=True, slots=True, kw_only=True)
class RunReadinessData:
    run_id: str
    status: str
    ready: bool
    requirements: JsonObject
    output_artifacts: tuple[JsonObject, ...]
    semantic_checks: tuple[JsonObject, ...]
    diagnostic_checks: tuple[JsonObject, ...]
    source_coverage: JsonObject
    unresolved_unknown_outcomes: int
    pending_waits: int
    blockers: tuple[JsonObject, ...]


@final
@dataclass(frozen=True, slots=True, kw_only=True)
class RunChecksData:
    run_id: str
    reports: tuple[JsonObject, ...]


@final
@dataclass(frozen=True, slots=True, kw_only=True)
class ArtifactInspectionData:
    run_id: str
    artifact_id: str
    kind: str | None
    available: bool
    preview: str | None
    content_type: JsonValue
    byte_length: JsonValue
    sha256: JsonValue
    metadata: JsonValue


@final
@dataclass(frozen=True, slots=True, kw_only=True)
class DemoResultData:
    run_id: str
    status: str
    runtime_home: str
    workspace_root: str
    workspace_selected_by: str
    bundle_path: str
    event_count: int
    illegal_mutation: str
    approval: str
    builtins: tuple[str, ...]
    unknown_outcome_reconciled: bool
    delegated_join_resolved: bool
    check_gate_rejection: str
    completion_ready: bool
    timeline_entries: int
    check_reports: int
    bundle_commitment: str
    bundle_verified: bool
    bundle_event_count: int
    bundle_import_id: str
    bundle_resumable: bool


type OperatorData = (
    HelpData
    | CommandResultData
    | BundleExportData
    | BundleVerificationData
    | BundleReplayData
    | BundleImportData
    | BundleAssessmentData
    | RunInspectionData
    | RunReplayData
    | RunTimelineData
    | RunWaitsData
    | CommandExplanationData
    | ActionReceiptData
    | RunReadinessData
    | RunChecksData
    | ArtifactInspectionData
    | DemoResultData
)


@final
@dataclass(frozen=True, slots=True, kw_only=True)
class OperatorResult[TData_co]:
    command: str
    title: str
    data: TData_co
    exit_code: OperatorExitCode = OperatorExitCode.OK
    failure: OperatorFailure | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.command, str) or self.command == "":
            raise ValidationError(code="operator_result_command_invalid")
        if not isinstance(self.title, str) or self.title == "":
            raise ValidationError(code="operator_result_title_invalid")
        data: object = self.data
        if not isinstance(data, _OPERATOR_DATA_TYPES):
            data = freeze_json(data)
            if not isinstance(data, JsonObject):
                raise ValidationError(code="operator_result_data_invalid")
        if not isinstance(self.exit_code, OperatorExitCode):
            raise ValidationError(code="operator_result_exit_invalid")
        if self.exit_code is OperatorExitCode.OK:
            if self.failure is not None:
                raise ValidationError(code="operator_result_branch_invalid")
        elif not isinstance(self.failure, OperatorFailure):
            raise ValidationError(code="operator_result_branch_invalid")
        object.__setattr__(self, "data", data)

    @property
    def ok(self) -> bool:
        return self.exit_code is OperatorExitCode.OK

    @staticmethod
    def success[TData](*, command: str, title: str, data: TData) -> OperatorResult[TData]:
        return OperatorResult(command=command, title=title, data=data)

    @staticmethod
    def failed(
        *,
        command: str,
        code: str,
        message: str,
        exit_code: OperatorExitCode,
        data: object = (),
    ) -> OperatorResult[JsonObject]:
        frozen = freeze_json({} if data == () else data)
        if not isinstance(frozen, JsonObject):
            raise ValidationError(code="operator_result_data_invalid")
        return OperatorResult(
            command=command,
            title="OpenRund command failed",
            data=frozen,
            exit_code=exit_code,
            failure=OperatorFailure(code=code, message=message),
        )


_OPERATOR_DATA_TYPES = (
    HelpData,
    CommandResultData,
    BundleExportData,
    BundleVerificationData,
    BundleReplayData,
    BundleImportData,
    BundleAssessmentData,
    RunInspectionData,
    RunReplayData,
    RunTimelineData,
    RunWaitsData,
    CommandExplanationData,
    ActionReceiptData,
    RunReadinessData,
    RunChecksData,
    ArtifactInspectionData,
    DemoResultData,
)

type AnyOperatorResult = OperatorResult[OperatorData | JsonObject]
