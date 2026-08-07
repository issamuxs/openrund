"""Deterministic Run lifecycle and non-authoritative completion readiness."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from enum import StrEnum
from types import MappingProxyType
from typing import Literal, final

from openrund.contracts.events import (
    CapabilityAuthorityGrantedPayload,
    CapabilityAuthorityRevokedPayload,
    CheckRecordedReportPayload,
    PolicyAuthorityGrantedPayload,
    PolicyAuthorityRevokedPayload,
    RunCancelledPayload,
    RunCompletedPayload,
    RunCreatedPayload,
    RunFailedPayload,
    RunStartedPayload,
)
from openrund.contracts.ids import (
    ActionId,
    ArtifactId,
    CapabilityId,
    CheckId,
    EventId,
    PolicyRuleId,
    RunId,
    WaitId,
)
from openrund.contracts.json import MISSING, JsonArray, JsonObject
from openrund.contracts.time import Timestamp
from openrund.views._actions import ActionViews, reduce_actions
from openrund.views._artifacts import ArtifactIndexEntry, reduce_artifact_index
from openrund.views._history import KnownHistory
from openrund.views._waits import PendingWait, WaitQueues, reduce_waits

type RunViewStatus = Literal[
    "unknown",
    "created",
    "running",
    "waiting",
    "completed",
    "failed",
    "cancelled",
]
type RunTerminalPayload = RunCompletedPayload | RunFailedPayload | RunCancelledPayload
type NamedCheckStatus = Literal["passed", "failed", "blocked"]


class ReadinessBlockerCode(StrEnum):
    PENDING_WAIT = "pending_wait"
    MISSING_REQUIRED_ARTIFACT = "missing_required_artifact"
    UNRESOLVED_ACTION_OUTCOME = "unresolved_action_outcome"
    UNSATISFIED_SEMANTIC_CHECK = "unsatisfied_semantic_check"


@final
@dataclass(frozen=True, slots=True, kw_only=True)
class RunDescriptorView:
    run_id: RunId
    root_id: RunId
    creation_event_id: EventId
    created_at: Timestamp
    creation: RunCreatedPayload


type AuthorityPayload = (
    CapabilityAuthorityGrantedPayload
    | CapabilityAuthorityRevokedPayload
    | PolicyAuthorityGrantedPayload
    | PolicyAuthorityRevokedPayload
)


@final
@dataclass(frozen=True, slots=True, kw_only=True)
class AuthorityFact:
    event_id: EventId
    recorded_at: Timestamp
    payload: AuthorityPayload


@final
@dataclass(frozen=True, slots=True, kw_only=True)
class CapabilityAuthorityEntry:
    event_id: EventId
    granted_at: Timestamp
    payload: CapabilityAuthorityGrantedPayload


@final
@dataclass(frozen=True, slots=True, kw_only=True)
class PolicyAuthorityEntry:
    event_id: EventId
    granted_at: Timestamp
    payload: PolicyAuthorityGrantedPayload


@final
@dataclass(frozen=True, slots=True, kw_only=True)
class NamedCheckResult:
    name: str
    status: NamedCheckStatus
    check_id: CheckId
    event_id: EventId


@final
@dataclass(frozen=True, slots=True, kw_only=True)
class CheckSummaryView:
    event_id: EventId
    recorded_at: Timestamp
    payload: CheckRecordedReportPayload
    named_results: tuple[NamedCheckResult, ...]


@final
@dataclass(frozen=True, slots=True, kw_only=True)
class CompletionRequirements:
    artifact_kinds: tuple[str, ...]
    semantic_checks: tuple[str, ...]
    require_known_action_outcomes: bool
    source_coverage_required: bool


@final
@dataclass(frozen=True, slots=True, kw_only=True)
class ArtifactRequirementStatus:
    artifact_kind: str
    satisfied: bool
    artifact_ids: tuple[ArtifactId, ...]


@final
@dataclass(frozen=True, slots=True, kw_only=True)
class SourceCoverageView:
    required: bool
    satisfied: bool
    evidence_check_id: CheckId | None


@final
@dataclass(frozen=True, slots=True, kw_only=True)
class ReadinessBlocker:
    code: ReadinessBlockerCode
    wait_id: WaitId | None = None
    artifact_kind: str | None = None
    action_id: ActionId | None = None
    check: str | None = None
    observed_check_status: NamedCheckStatus | None = None


@final
@dataclass(frozen=True, slots=True, kw_only=True)
class RunCompletionReadiness:
    requirements: CompletionRequirements
    output_artifacts: tuple[ArtifactRequirementStatus, ...]
    passed_checks: tuple[str, ...]
    semantic_checks: tuple[NamedCheckResult, ...]
    diagnostic_checks: tuple[NamedCheckResult, ...]
    source_coverage: SourceCoverageView
    unresolved_unknown_outcomes: int
    blockers: tuple[ReadinessBlocker, ...]
    ready: bool


@final
@dataclass(frozen=True, slots=True, kw_only=True)
class RunStatusView:
    run: RunDescriptorView | None
    status: RunViewStatus
    pending_waits: tuple[PendingWait, ...]
    capability_authority: Mapping[CapabilityId, CapabilityAuthorityEntry]
    policy_authority: Mapping[PolicyRuleId, PolicyAuthorityEntry]
    authority_history: tuple[AuthorityFact, ...]
    checks: Mapping[CheckId, CheckSummaryView]
    latest_check: CheckSummaryView | None
    completion_readiness: RunCompletionReadiness
    source_watermark: int
    terminal_event_id: EventId | None
    terminal_at: Timestamp | None
    terminal: RunTerminalPayload | None


def _object(value: object) -> JsonObject | None:
    return value if isinstance(value, JsonObject) else None


def _strings(value: object) -> tuple[str, ...]:
    if not isinstance(value, JsonArray):
        return ()
    return tuple(item for item in value if isinstance(item, str) and item != "")


def _dedupe(values: tuple[str, ...]) -> tuple[str, ...]:
    return tuple(dict.fromkeys(values))


def _requirements(run: RunDescriptorView | None) -> CompletionRequirements:
    empty = CompletionRequirements(
        artifact_kinds=(),
        semantic_checks=(),
        require_known_action_outcomes=False,
        source_coverage_required=False,
    )
    if run is None:
        return empty
    metadata = _object(run.creation.metadata)
    if metadata is None:
        return empty
    contract = _object(metadata.get("run_contract"))
    if contract is None:
        return empty

    artifact_kinds = _strings(contract.get("required_artifact_kinds"))
    output = _object(contract.get("output"))
    if output is not None and isinstance(output.get("artifact_kind"), str):
        artifact_kind = output["artifact_kind"]
        assert isinstance(artifact_kind, str)
        artifact_kinds += (artifact_kind,)

    check = _object(contract.get("check"))
    semantic_checks = _strings(check.get("checks")) if check is not None else ()
    delegation = _object(contract.get("delegation"))
    source_coverage_required = (
        delegation is not None and delegation.get("kind") == "source_coverage"
    )
    if source_coverage_required:
        semantic_checks += ("source_coverage",)
    completion = _object(contract.get("completion"))
    require_known = completion is not None and completion.get("kind") == "known_action_outcomes"
    return CompletionRequirements(
        artifact_kinds=_dedupe(artifact_kinds),
        semantic_checks=_dedupe(semantic_checks),
        require_known_action_outcomes=require_known,
        source_coverage_required=source_coverage_required,
    )


def _named_results(
    event_id: EventId,
    payload: CheckRecordedReportPayload,
) -> tuple[NamedCheckResult, ...]:
    data = _object(payload.result.data)
    checks = data.get("checks") if data is not None else None
    if not isinstance(checks, JsonArray):
        return ()
    results: list[NamedCheckResult] = []
    for value in checks:
        item = _object(value)
        if item is None:
            continue
        name = item.get("check")
        raw_status = item.get("status")
        if not isinstance(name, str) or name == "":
            continue
        if raw_status == "passed":
            status: NamedCheckStatus = "passed"
        elif raw_status == "failed":
            status = "failed"
        elif raw_status == "blocked":
            status = "blocked"
        else:
            continue
        results.append(
            NamedCheckResult(
                name=name,
                status=status,
                check_id=payload.check_id,
                event_id=event_id,
            )
        )
    return tuple(results)


def _artifact_requirements(
    requirements: CompletionRequirements,
    artifact_index: Mapping[ArtifactId, ArtifactIndexEntry],
) -> tuple[ArtifactRequirementStatus, ...]:
    return tuple(
        ArtifactRequirementStatus(
            artifact_kind=kind,
            artifact_ids=tuple(
                artifact_id
                for artifact_id, entry in artifact_index.items()
                if entry.kind == kind and entry.available
            ),
            satisfied=any(
                entry.kind == kind and entry.available for entry in artifact_index.values()
            ),
        )
        for kind in requirements.artifact_kinds
    )


def _readiness(
    requirements: CompletionRequirements,
    waits: WaitQueues,
    actions: ActionViews,
    artifact_index: Mapping[ArtifactId, ArtifactIndexEntry],
    named_checks: Mapping[str, NamedCheckResult],
) -> RunCompletionReadiness:
    artifacts = _artifact_requirements(requirements, artifact_index)
    semantic = tuple(
        result for name, result in named_checks.items() if name in requirements.semantic_checks
    )
    diagnostic = tuple(
        result for name, result in named_checks.items() if name not in requirements.semantic_checks
    )
    passed = tuple(name for name, result in named_checks.items() if result.status == "passed")
    source_result = named_checks.get("source_coverage")
    source_coverage = SourceCoverageView(
        required=requirements.source_coverage_required,
        satisfied=(
            not requirements.source_coverage_required
            or (source_result is not None and source_result.status == "passed")
        ),
        evidence_check_id=(source_result.check_id if source_result is not None else None),
    )

    blockers: list[ReadinessBlocker] = []
    blockers.extend(
        ReadinessBlocker(code=ReadinessBlockerCode.PENDING_WAIT, wait_id=wait.wait_id)
        for wait in waits.all_pending
    )
    blockers.extend(
        ReadinessBlocker(
            code=ReadinessBlockerCode.MISSING_REQUIRED_ARTIFACT,
            artifact_kind=requirement.artifact_kind,
        )
        for requirement in artifacts
        if not requirement.satisfied
    )
    if requirements.require_known_action_outcomes:
        blockers.extend(
            ReadinessBlocker(
                code=ReadinessBlockerCode.UNRESOLVED_ACTION_OUTCOME,
                action_id=pending.action_id,
            )
            for pending in actions.reconciliation.pending
        )
    for check_name in requirements.semantic_checks:
        observed = named_checks.get(check_name)
        if observed is None or observed.status != "passed":
            blockers.append(
                ReadinessBlocker(
                    code=ReadinessBlockerCode.UNSATISFIED_SEMANTIC_CHECK,
                    check=check_name,
                    observed_check_status=(observed.status if observed is not None else None),
                )
            )

    return RunCompletionReadiness(
        requirements=requirements,
        output_artifacts=artifacts,
        passed_checks=passed,
        semantic_checks=semantic,
        diagnostic_checks=diagnostic,
        source_coverage=source_coverage,
        unresolved_unknown_outcomes=len(actions.reconciliation.pending),
        blockers=tuple(blockers),
        ready=not blockers,
    )


def _authority_matches(current: object, revoked_authority_id: object) -> bool:
    if revoked_authority_id is MISSING or revoked_authority_id is None:
        return True
    payload = getattr(current, "payload", None)
    return getattr(payload, "authority_id", None) == revoked_authority_id


def reduce_run_status(
    history: KnownHistory,
    *,
    waits: WaitQueues | None = None,
    actions: ActionViews | None = None,
    artifact_index: Mapping[ArtifactId, ArtifactIndexEntry] | None = None,
) -> RunStatusView:
    """Derive lifecycle and readiness facts; ``ready`` never grants completion authority."""

    wait_view = reduce_waits(history) if waits is None else waits
    action_view = reduce_actions(history) if actions is None else actions
    artifacts = reduce_artifact_index(history) if artifact_index is None else artifact_index

    run: RunDescriptorView | None = None
    base_status: RunViewStatus = "unknown"
    capability_authority: dict[CapabilityId, CapabilityAuthorityEntry] = {}
    policy_authority: dict[PolicyRuleId, PolicyAuthorityEntry] = {}
    authority_history: list[AuthorityFact] = []
    checks: dict[CheckId, CheckSummaryView] = {}
    named_checks: dict[str, NamedCheckResult] = {}
    latest_check: CheckSummaryView | None = None
    terminal_event_id: EventId | None = None
    terminal_at: Timestamp | None = None
    terminal: RunTerminalPayload | None = None

    for event in history.events:
        payload = event.payload
        if isinstance(payload, RunCreatedPayload) and terminal is None:
            run = RunDescriptorView(
                run_id=event.run_id,
                root_id=payload.root_id,
                creation_event_id=event.event_id,
                created_at=event.timestamp,
                creation=payload,
            )
            base_status = "created"
        elif isinstance(payload, RunStartedPayload) and terminal is None:
            base_status = "running"
        elif isinstance(payload, RunCompletedPayload) and terminal is None:
            base_status = "completed"
            terminal_event_id = event.event_id
            terminal_at = event.timestamp
            terminal = payload
        elif isinstance(payload, RunFailedPayload) and terminal is None:
            base_status = "failed"
            terminal_event_id = event.event_id
            terminal_at = event.timestamp
            terminal = payload
        elif isinstance(payload, RunCancelledPayload) and terminal is None:
            base_status = "cancelled"
            terminal_event_id = event.event_id
            terminal_at = event.timestamp
            terminal = payload
        elif isinstance(payload, CapabilityAuthorityGrantedPayload):
            authority_history.append(
                AuthorityFact(event_id=event.event_id, recorded_at=event.timestamp, payload=payload)
            )
            capability_authority[payload.capability_id] = CapabilityAuthorityEntry(
                event_id=event.event_id,
                granted_at=event.timestamp,
                payload=payload,
            )
        elif isinstance(payload, PolicyAuthorityGrantedPayload):
            authority_history.append(
                AuthorityFact(event_id=event.event_id, recorded_at=event.timestamp, payload=payload)
            )
            policy_authority[payload.rule_id] = PolicyAuthorityEntry(
                event_id=event.event_id,
                granted_at=event.timestamp,
                payload=payload,
            )
        elif isinstance(payload, CapabilityAuthorityRevokedPayload):
            authority_history.append(
                AuthorityFact(event_id=event.event_id, recorded_at=event.timestamp, payload=payload)
            )
            current_capability = capability_authority.get(payload.capability_id)
            if current_capability is not None and _authority_matches(
                current_capability, payload.authority_id
            ):
                capability_authority.pop(payload.capability_id)
        elif isinstance(payload, PolicyAuthorityRevokedPayload):
            authority_history.append(
                AuthorityFact(event_id=event.event_id, recorded_at=event.timestamp, payload=payload)
            )
            current_policy = policy_authority.get(payload.rule_id)
            if current_policy is not None and _authority_matches(
                current_policy, payload.authority_id
            ):
                policy_authority.pop(payload.rule_id)
        elif isinstance(payload, CheckRecordedReportPayload):
            summary = CheckSummaryView(
                event_id=event.event_id,
                recorded_at=event.timestamp,
                payload=payload,
                named_results=_named_results(event.event_id, payload),
            )
            checks[payload.check_id] = summary
            latest_check = summary
            for result in summary.named_results:
                named_checks[result.name] = result

    terminal_status = base_status in ("completed", "failed", "cancelled")
    status: RunViewStatus = (
        "waiting"
        if not terminal_status and run is not None and wait_view.all_pending
        else base_status
    )
    requirements = _requirements(run)
    return RunStatusView(
        run=run,
        status=status,
        pending_waits=wait_view.all_pending,
        capability_authority=MappingProxyType(capability_authority),
        policy_authority=MappingProxyType(policy_authority),
        authority_history=tuple(authority_history),
        checks=MappingProxyType(checks),
        latest_check=latest_check,
        completion_readiness=_readiness(
            requirements,
            wait_view,
            action_view,
            artifacts,
            named_checks,
        ),
        source_watermark=history.watermark,
        terminal_event_id=terminal_event_id,
        terminal_at=terminal_at,
        terminal=terminal,
    )
