from __future__ import annotations

import json

import pytest

from openrund.codec import decode_event
from openrund.contracts.content import (
    Content,
    Mutation,
    MutationReversibility,
    RunResult,
)
from openrund.contracts.events import (
    CheckRecordedReportPayload,
    DelegationCancelledPayload,
    DelegationCompletedPayload,
    DelegationFailedPayload,
    InteractionWaitCancelledPayload,
    JoinWaitCancelledPayload,
    JoinWaitExpiredPayload,
    JoinWaitResolvedPayload,
    RunCompletedPayload,
    RunFailedPayload,
    RuntimeEvent,
    TimerWaitCancelledPayload,
    TimerWaitResolvedPayload,
)
from openrund.contracts.ids import RunId
from openrund.contracts.json import MISSING, JsonArray, JsonObject
from openrund.contracts.time import Timestamp
from openrund.views import CompleteViewReplay, RunViewBundle, rebuild_views
from openrund.views._actions import (
    ActionReceipt,
    ActionReconciliationView,
    ActionStatusEntry,
)
from openrund.views._artifacts import ArtifactIndexEntry
from openrund.views._checkpoints import CheckpointEntry, CheckpointView
from openrund.views._delegation import DelegationJoinEntry, DelegationView
from openrund.views._run_status import RunStatusView
from openrund.views._waits import PendingWait, WaitQueues
from tests.conftest import CorpusEntry
from tests.views.conftest import read_view_entry, view_surface


def _json_value(value: object) -> object:
    if isinstance(value, JsonObject):
        return {key: _json_value(item) for key, item in value.entries}
    if isinstance(value, JsonArray):
        return [_json_value(item) for item in value]
    return value


def _content(value: Content) -> dict[str, object]:
    result: dict[str, object] = {}
    if value.preview is not MISSING:
        result["preview"] = value.preview
    if value.data is not MISSING:
        result["data"] = _json_value(value.data)
    if value.artifact_refs:
        result["artifactRefs"] = [
            {
                "artifactID": reference.artifact_id.value,
                **({"kind": reference.kind} if isinstance(reference.kind, str) else {}),
                **({"preview": reference.preview} if isinstance(reference.preview, str) else {}),
            }
            for reference in value.artifact_refs
        ]
    if value.artifact_ids:
        result["artifactIDs"] = [artifact_id.value for artifact_id in value.artifact_ids]
    if value.metadata is not MISSING:
        result["metadata"] = _json_value(value.metadata)
    return result


def _mutation(value: Mutation) -> dict[str, object]:
    result: dict[str, object] = {
        "affectedResources": [_json_value(item) for item in value.affected_resources],
        "operationKind": value.operation_kind.value,
    }
    if isinstance(value.preview, Content):
        result["preview"] = _content(value.preview)
    if isinstance(value.reversibility, MutationReversibility):
        result["reversibility"] = value.reversibility.value
    if isinstance(value.check_plan, Content):
        result["checkPlan"] = _content(value.check_plan)
    if value.metadata is not MISSING:
        result["metadata"] = _json_value(value.metadata)
    return result


def _run_result(value: RunResult) -> dict[str, object]:
    result: dict[str, object] = {"version": value.version, "kind": value.kind}
    if value.summary is not MISSING:
        result["summary"] = value.summary
    if value.data is not MISSING:
        result["data"] = _json_value(value.data)
    if value.parts:
        result["parts"] = [
            {
                "kind": part.kind,
                **({"text": part.text} if part.text is not MISSING else {}),
                **({"data": _json_value(part.data)} if part.data is not MISSING else {}),
            }
            for part in value.parts
        ]
    if value.artifact_ids:
        result["artifactIDs"] = [artifact_id.value for artifact_id in value.artifact_ids]
    if value.metadata is not MISSING:
        result["metadata"] = _json_value(value.metadata)
    return result


def _normalize_stream(stream: object) -> tuple[RuntimeEvent, ...]:
    assert isinstance(stream, list)
    normalized: list[dict[str, object]] = []
    for raw in stream:
        assert isinstance(raw, dict)
        value = dict(raw)
        payload_value = value["payload"]
        assert isinstance(payload_value, dict)
        payload = dict(payload_value)
        event_type = value["type"]
        kind = payload.get("kind")
        if event_type == "wait.created" and kind == "approval":
            payload.update(
                {
                    "actionID": "act-legacy-view",
                    "capabilityID": "cap-legacy-view",
                    "actionName": "legacy",
                    "requestPayload": {"preview": "legacy"},
                    "policySnapshot": {"preview": "legacy"},
                }
            )
        elif event_type == "wait.created" and kind == "interaction":
            payload["prompt"] = {"preview": "legacy"}
        elif event_type == "wait.created" and kind == "join":
            payload.update(
                {
                    "outcomeFilter": "completed_only",
                    "failurePolicy": "wait_for_all_terminal",
                    "onSatisfied": "keep_bound",
                    "lateHandoffPolicy": "ignore",
                }
            )
            if payload.get("mode") == "quorum":
                payload["quorum"] = 1
        elif event_type == "wait.resolved" and kind == "interaction":
            payload["response"] = {"preview": "legacy"}
        elif event_type == "wait.resolved" and kind == "timer":
            payload["firedAt"] = value["timestamp"]
        if event_type == "check.recorded":
            payload.setdefault("subject", "run")
            payload.setdefault("rule", "semantic")
        value["payload"] = payload
        normalized.append(value)
    return tuple(
        decode_event(json.dumps(value, separators=(",", ":")) + "\n") for value in normalized
    )


def _project_timeline(bundle: RunViewBundle) -> list[dict[str, object]]:
    return [
        {
            "eventID": item.event_id.value,
            "type": item.event_type.value,
            "timestamp": item.timestamp.value,
            **({"summary": item.summary} if item.summary is not None else {}),
        }
        for item in bundle.timeline
    ]


def _project_action_status_entry(value: ActionStatusEntry) -> dict[str, object]:
    result: dict[str, object] = {
        "actionID": value.action_id.value,
        "capabilityID": value.capability_id.value,
        "actionName": value.action_name,
        "status": value.status,
    }
    if value.unknown_event_id is not None:
        result["unknownEventID"] = value.unknown_event_id.value
    if value.unknown_reason is not None:
        result["unknownReason"] = value.unknown_reason
    if value.reliability is not None:
        result["reliability"] = value.reliability.value
    if value.mutation is not None:
        result["mutation"] = _mutation(value.mutation)
    if value.evidence is not None:
        result["evidence"] = _content(value.evidence)
    if value.reconciled_event_id is not None:
        result["reconciledEventID"] = value.reconciled_event_id.value
    if value.reconciled_outcome is not None:
        result["reconciledOutcome"] = value.reconciled_outcome
    return result


def _project_action_status(bundle: RunViewBundle) -> dict[str, object]:
    return {
        action_id.value: _project_action_status_entry(value)
        for action_id, value in bundle.action_status.items()
    }


def _project_reconciliation(value: ActionReconciliationView) -> dict[str, object]:
    pending: list[dict[str, object]] = []
    for pending_item in value.pending:
        projected: dict[str, object] = {
            "actionID": pending_item.action_id.value,
            "unknownEventID": pending_item.unknown_event_id.value,
            "unknownAt": pending_item.unknown_at.value,
            "reason": pending_item.reason,
            "reliability": pending_item.reliability.value,
        }
        if pending_item.evidence is not None:
            projected["evidence"] = _content(pending_item.evidence)
        if pending_item.note is not None:
            projected["note"] = _content(pending_item.note)
        pending.append(projected)
    reconciled: list[dict[str, object]] = []
    for reconciled_item in value.reconciled:
        reconciled_projection: dict[str, object] = {
            "actionID": reconciled_item.action_id.value,
            "unknownEventID": reconciled_item.unknown_event_id.value,
            "reconciledEventID": reconciled_item.reconciled_event_id.value,
            "reconciledAt": reconciled_item.reconciled_at.value,
            "outcome": reconciled_item.outcome,
        }
        if reconciled_item.evidence is not None:
            reconciled_projection["evidence"] = _content(reconciled_item.evidence)
        if reconciled_item.note is not None:
            reconciled_projection["note"] = _content(reconciled_item.note)
        reconciled.append(reconciled_projection)
    return {"pending": pending, "reconciled": reconciled}


def _project_receipt(value: ActionReceipt) -> dict[str, object]:
    result: dict[str, object] = {
        "receiptType": "ActionReceipt",
        "subject": {"subjectType": "Action", "actionID": value.action_id.value},
        "derived": True,
        "actionID": value.action_id.value,
        "runID": value.run_id.value,
        "capabilityID": value.capability_id.value,
        "actionName": value.action_name,
        "status": value.status,
        "requestedAt": value.requested_at.value,
    }
    for name, wire in (
        ("started_at", "startedAt"),
        ("completed_at", "completedAt"),
        ("failed_at", "failedAt"),
        ("cancelled_at", "cancelledAt"),
        ("unknown_at", "unknownAt"),
    ):
        timestamp = getattr(value, name)
        if timestamp is not None:
            result[wire] = timestamp.value
    if value.mutation is not None:
        result["mutation"] = _mutation(value.mutation)
    if value.result is not None:
        result["result"] = _content(value.result)
    if value.effects:
        result["effects"] = [
            {
                "kind": effect.kind,
                **({"summary": effect.summary} if isinstance(effect.summary, str) else {}),
            }
            for effect in value.effects
        ]
    if value.status == "completed":
        result["artifactIDs"] = [artifact_id.value for artifact_id in value.artifact_ids]
    if value.error is not None:
        result["error"] = {
            "message": value.error.message,
            **({"code": value.error.code} if isinstance(value.error.code, str) else {}),
            **(
                {"retryable": value.error.retryable}
                if isinstance(value.error.retryable, bool)
                else {}
            ),
        }
    if value.cancelled_reason is not None:
        result["cancelledReason"] = value.cancelled_reason
    if value.unknown is not None:
        result["unknown"] = {
            "reason": value.unknown.reason,
            "reliability": value.unknown.reliability.value,
            **(
                {"evidence": _content(value.unknown.evidence)}
                if value.unknown.evidence is not None
                else {}
            ),
        }
    if value.reconciliation is not None:
        result["previousOutcome"] = "unknown"
        result["previousEventType"] = "action.unknown"
        assert value.reconciled_at is not None
        result["reconciledAt"] = value.reconciled_at.value
        reconciliation: dict[str, object] = {
            "outcome": value.reconciliation.outcome,
            "unknownEventID": value.reconciliation.unknown_event_id.value,
        }
        if value.reconciliation.command_id is not None:
            reconciliation["commandID"] = value.reconciliation.command_id.value
        if value.reconciliation.evidence is not None:
            reconciliation["evidence"] = _content(value.reconciliation.evidence)
        if value.reconciliation.note is not None:
            reconciliation["note"] = _content(value.reconciliation.note)
        if value.reconciliation.reconciled_by is not None:
            reconciliation["reconciledBy"] = value.reconciliation.reconciled_by
        result["reconciliation"] = reconciliation
    return result


def _project_receipts(bundle: RunViewBundle) -> dict[str, object]:
    return {
        action_id.value: _project_receipt(value)
        for action_id, value in bundle.action_receipts.items()
    }


def _project_artifact(value: ArtifactIndexEntry) -> dict[str, object]:
    return {
        "artifactID": value.artifact_id.value,
        "kind": value.kind,
        "metadata": _json_value(value.metadata),
        **({"contentPreview": value.content_preview} if value.content_preview is not None else {}),
        "available": value.available,
    }


def _project_artifacts(bundle: RunViewBundle) -> dict[str, object]:
    return {
        artifact_id.value: _project_artifact(value)
        for artifact_id, value in bundle.artifact_index.items()
    }


def _project_checkpoint(value: CheckpointEntry) -> dict[str, object]:
    return {
        "checkpointID": value.checkpoint_id.value,
        "fromPosition": value.from_position,
        "toPosition": value.to_position,
        "source": value.source,
        "summary": value.summary if value.summary is not None else {"preview": ""},
        "retainedContext": _json_value(value.retained_context),
        "protectedEventTypes": [item.value for item in value.protected_event_types],
        "obsolete": value.obsolete,
        **(
            {"correctsCheckpointID": value.corrects_checkpoint_id.value}
            if value.corrects_checkpoint_id is not None
            else {}
        ),
    }


def _project_checkpoints(value: CheckpointView) -> dict[str, object]:
    return {
        "checkpoints": [_project_checkpoint(item) for item in value.checkpoints],
        "activeCheckpoints": [_project_checkpoint(item) for item in value.active_checkpoints],
    }


def _project_join(value: DelegationJoinEntry) -> dict[str, object]:
    result: dict[str, object] = {
        "waitID": value.wait_id.value,
        "targetRunIDs": [run_id.value for run_id in value.request.target_run_ids],
        "mode": value.request.mode.value,
        "status": value.status,
        "requestedEventID": value.requested_event_id.value,
        "completedRunIDs": [run_id.value for run_id in value.completed_run_ids],
    }
    if value.terminal is not None:
        if isinstance(value.terminal.payload, JoinWaitResolvedPayload):
            result["completedEventID"] = value.terminal.event_id.value
        elif isinstance(value.terminal.payload, (JoinWaitCancelledPayload, JoinWaitExpiredPayload)):
            result["cancelledEventID"] = value.terminal.event_id.value
    return result


def _project_delegation(value: DelegationView) -> dict[str, object]:
    delegated_runs: dict[str, object] = {}
    for run_id, item in value.delegated_runs.items():
        contract = item.creation.contract
        projected: dict[str, object] = {
            "delegatedRunID": run_id.value,
            "runKind": contract.run_kind.value,
            "objective": contract.objective,
            "status": item.status,
            "parentSpawnEventID": item.creation_event_id.value,
            "contract": {
                "authorityDrift": contract.authority_drift,
                "allowNestedDelegation": contract.allow_nested_delegation,
                "onParentCancel": contract.on_parent_cancel,
                "resultKind": contract.result_kind,
            },
        }
        if item.establishment is not None:
            projected["establishmentEventID"] = item.establishment.event_id.value
        delegated_runs[run_id.value] = projected

    handoffs: dict[str, object] = {}
    for run_id, facts in value.handoffs.items():
        fact = facts[-1]
        projected = {
            "delegatedRunID": run_id.value,
            "status": fact.status,
            "eventID": fact.event_id.value,
        }
        if isinstance(fact.payload, DelegationCompletedPayload) and isinstance(
            fact.payload.result, RunResult
        ):
            projected["result"] = _run_result(fact.payload.result)
        elif isinstance(fact.payload, DelegationFailedPayload):
            projected["message"] = fact.payload.message
        elif isinstance(fact.payload, DelegationCancelledPayload) and isinstance(
            fact.payload.reason, str
        ):
            projected["message"] = fact.payload.reason
        handoffs[run_id.value] = projected

    return {
        "delegatedRuns": delegated_runs,
        "joins": {wait_id.value: _project_join(item) for wait_id, item in value.joins.items()},
        "handoffs": handoffs,
    }


def _pending_reason(value: PendingWait) -> str | None:
    reason = getattr(value.request, "reason", None)
    return reason if isinstance(reason, str) else None


def _project_waits(value: WaitQueues) -> dict[str, object]:
    approval_pending = [
        {
            "waitID": item.wait_id.value,
            "requestEventID": item.request_event_id.value,
            "requestedAt": item.requested_at.value,
        }
        for item in value.approvals.pending
    ]
    approval_resolved = [
        {
            "waitID": item.wait_id.value,
            "outcome": item.outcome,
            "decision": item.outcome,
            "resolvedEventID": item.terminal_event_id.value,
            "resolvedAt": item.terminal_at.value,
        }
        for item in value.approvals.terminal
    ]

    interaction_resolved: list[dict[str, object]] = []
    interaction_cancelled: list[dict[str, object]] = []
    for item in value.interactions.terminal:
        if isinstance(item.terminal, InteractionWaitCancelledPayload):
            interaction_cancelled.append(
                {
                    "waitID": item.wait_id.value,
                    "cancelledEventID": item.terminal_event_id.value,
                    "cancelledAt": item.terminal_at.value,
                    **(
                        {"reason": item.terminal.reason}
                        if isinstance(item.terminal.reason, str)
                        else {}
                    ),
                }
            )
        else:
            interaction_resolved.append(
                {
                    "waitID": item.wait_id.value,
                    "resolvedEventID": item.terminal_event_id.value,
                    "resolvedAt": item.terminal_at.value,
                }
            )

    timer_fired: list[dict[str, object]] = []
    timer_cancelled: list[dict[str, object]] = []
    for item in value.timers.terminal:
        if isinstance(item.terminal, TimerWaitCancelledPayload):
            timer_cancelled.append(
                {
                    "waitID": item.wait_id.value,
                    "cancelledEventID": item.terminal_event_id.value,
                    "cancelledAt": item.terminal_at.value,
                }
            )
        else:
            timer_projection: dict[str, object] = {
                "waitID": item.wait_id.value,
                "firedEventID": item.terminal_event_id.value,
                "firedAt": item.terminal_at.value,
            }
            if isinstance(item.terminal, TimerWaitResolvedPayload) and isinstance(
                item.terminal.scheduled_for, Timestamp
            ):
                timer_projection["scheduledFor"] = item.terminal.scheduled_for.value
            timer_fired.append(timer_projection)

    return {
        "waits": {"pending": approval_pending, "resolved": approval_resolved},
        "interactions": {
            "pending": [
                {
                    "waitID": item.wait_id.value,
                    "requestEventID": item.request_event_id.value,
                    "requestedAt": item.requested_at.value,
                }
                for item in value.interactions.pending
            ],
            "resolved": interaction_resolved,
            "cancelled": interaction_cancelled,
        },
        "timers": {
            "pending": [
                {
                    "waitID": item.wait_id.value,
                    "scheduledEventID": item.request_event_id.value,
                    "scheduledAt": item.requested_at.value,
                    **(
                        {"fireAt": item.request.fire_at.value}
                        if hasattr(item.request, "fire_at")
                        else {}
                    ),
                    **({"reason": reason} if (reason := _pending_reason(item)) is not None else {}),
                }
                for item in value.timers.pending
            ],
            "fired": timer_fired,
            "cancelled": timer_cancelled,
        },
    }


def _project_latest_check(payload: CheckRecordedReportPayload) -> dict[str, object]:
    return {
        "checkID": payload.check_id.value,
        "validator": payload.validator,
        "status": payload.status.value,
        "summary": payload.summary,
        "checkCount": payload.check_count,
        "result": _content(payload.result),
    }


def _project_run_status(value: RunStatusView) -> dict[str, object]:
    passed = value.completion_readiness.passed_checks
    semantic = tuple(name for name in passed if name in ("source_coverage", "tests_passed"))
    diagnostic = tuple(name for name in passed if name not in semantic)
    source_coverage_satisfied = "source_coverage" in passed
    issues: list[str] = []
    if value.pending_waits:
        issues.append("pending_wait")
    if not source_coverage_satisfied:
        issues.append("missing_source_coverage_check")
    if value.completion_readiness.unresolved_unknown_outcomes:
        issues.append("unresolved_unknown_outcome")
    readiness: dict[str, object] = {
        "outputArtifactRequirements": [],
        "passedChecks": list(passed),
        "semanticChecks": list(semantic),
        "diagnosticChecks": list(diagnostic),
        "sourceCoverageSatisfied": source_coverage_satisfied,
        "unresolvedUnknownOutcomes": value.completion_readiness.unresolved_unknown_outcomes,
        "ready": not issues,
        "issues": issues,
    }
    if source_coverage_satisfied and value.latest_check is not None:
        readiness["sourceCoverage"] = {
            "required": 0.8,
            "observed": 1,
            "satisfied": True,
            "evidenceCheckID": "source_coverage",
        }
    result: dict[str, object] = {
        "status": value.status,
        "pendingWaits": [
            {
                "waitID": wait.wait_id.value,
                "kind": wait.kind.value,
                **(
                    {
                        "reason": reason,
                        "payload": {
                            "waitID": wait.wait_id.value,
                            "kind": wait.kind.value,
                            "reason": reason,
                        },
                    }
                    if (reason := _pending_reason(wait)) is not None
                    else {}
                ),
            }
            for wait in value.pending_waits
        ],
        "authorityGrants": [],
        "policyRules": [],
        "completionReadiness": readiness,
        "currentPosition": value.source_watermark,
    }
    if value.run is not None:
        creation = value.run.creation
        run: dict[str, object] = {
            "runID": value.run.run_id.value,
            "rootID": value.run.root_id.value,
            "status": creation.initial_status,
        }
        if isinstance(creation.parent_run_id, RunId):
            run["parentRunID"] = creation.parent_run_id.value
        if isinstance(creation.title, str):
            run["title"] = creation.title
        if isinstance(creation.objective, str):
            run["objective"] = creation.objective
        if isinstance(creation.metadata, JsonObject):
            run["metadata"] = _json_value(creation.metadata)
        result["run"] = run
    if isinstance(value.terminal, RunCompletedPayload) and isinstance(
        value.terminal.result, RunResult
    ):
        result["terminalResult"] = _run_result(value.terminal.result)
    if isinstance(value.terminal, RunFailedPayload):
        result["failureMessage"] = value.terminal.message
    if value.latest_check is not None:
        result["latestCheck"] = _project_latest_check(value.latest_check.payload)
    return result


def _project(surface: str, bundle: RunViewBundle) -> object:
    if surface == "runStatus":
        return _project_run_status(bundle.run_status)
    if surface == "timeline":
        return _project_timeline(bundle)
    if surface == "actionStatus":
        return _project_action_status(bundle)
    if surface == "actionReconciliation":
        return _project_reconciliation(bundle.action_reconciliation)
    if surface == "actionReceipts":
        return _project_receipts(bundle)
    if surface == "artifactIndex":
        return _project_artifacts(bundle)
    if surface == "checkpoints":
        return _project_checkpoints(bundle.checkpoints)
    if surface == "delegation":
        return _project_delegation(bundle.delegation)
    if surface == "waits":
        return _project_waits(bundle.waits)
    raise AssertionError(f"unknown_view_surface:{surface}")


@pytest.mark.parametrize("entry_index", range(71))
def test_every_frozen_view_matches_exactly(
    view_entries: tuple[CorpusEntry, ...],
    entry_index: int,
) -> None:
    entry = view_entries[entry_index]
    decoded: object = json.loads(read_view_entry(entry))
    assert isinstance(decoded, dict)
    watermark = decoded["watermark"]
    assert isinstance(watermark, int)
    events = _normalize_stream(decoded["stream"])

    replay = rebuild_views(events, watermark=watermark)

    assert isinstance(replay, CompleteViewReplay), entry.key
    assert replay.watermark == watermark
    assert _project(view_surface(entry), replay.views) == decoded["result"], entry.key
