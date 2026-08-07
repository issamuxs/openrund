"""Deterministic human and JSON rendering for operator results."""

from __future__ import annotations

from openrund.codec import encode_json_value
from openrund.contracts.json import JsonArray, JsonObject, JsonValue, freeze_json
from openrund.operator._model import (
    ActionReceiptData,
    ArtifactInspectionData,
    BundleAssessmentData,
    BundleExportData,
    BundleImportData,
    BundleReplayData,
    BundleVerificationData,
    CommandExplanationData,
    CommandResultData,
    DemoResultData,
    HelpData,
    OperatorResult,
    RunChecksData,
    RunInspectionData,
    RunReadinessData,
    RunReplayData,
    RunTimelineData,
    RunWaitsData,
)


def _object(value: object) -> JsonObject:
    frozen = freeze_json(value)
    if not isinstance(frozen, JsonObject):
        raise TypeError("operator_result_data_invalid")
    return frozen


def operator_data_json(data: object, /) -> JsonObject:
    """Convert typed operator-domain payloads at the presentation boundary."""

    if isinstance(data, JsonObject):
        return data
    if isinstance(data, HelpData):
        return _object({"usage": data.usage})
    if isinstance(data, CommandResultData):
        value: dict[str, object] = {
            "run_id": data.run_id,
            "command_id": data.command_id,
            "decision": data.decision,
        }
        if data.decision == "accepted":
            value["result_event_ids"] = data.result_event_ids
        elif data.decision == "deferred":
            value["wait_ids"] = data.wait_ids
            value["reason"] = data.reason
        elif data.decision == "superseded":
            value["superseded_by_command_id"] = data.superseded_by_command_id
            value["reason"] = data.reason
        elif data.reason is not None:
            value["reason"] = data.reason
        return _object(value)
    if isinstance(data, BundleExportData):
        return _object(
            {
                "run_id": data.run_id,
                "bundle_path": data.bundle_path,
                "profile": data.profile,
                "completeness": data.completeness,
                "commitment": data.commitment,
            }
        )
    if isinstance(data, BundleVerificationData):
        return _object(
            {
                "bundle_path": data.bundle_path,
                "run_id": data.run_id,
                "profile": data.profile,
                "checks": data.checks,
            }
        )
    if isinstance(data, BundleReplayData):
        return _object(
            {
                "bundle_path": data.bundle_path,
                "run_id": data.run_id,
                "event_count": data.event_count,
                "status": data.status,
            }
        )
    if isinstance(data, BundleImportData):
        return _object(
            {
                "bundle_path": data.bundle_path,
                "run_id": data.run_id,
                "import_id": data.import_id,
                "resumable": data.resumable,
                "issues": data.issues,
            }
        )
    if isinstance(data, BundleAssessmentData):
        return _object(
            {
                "bundle_path": data.bundle_path,
                "run_id": data.run_id,
                "resumable": data.resumable,
                "missing_root_mappings": data.missing_root_mappings,
                "issues": data.issues,
            }
        )
    if isinstance(data, RunInspectionData):
        return _object(
            {
                "run_id": data.run_id,
                "status": data.status,
                "watermark": data.watermark,
                "root_id": data.root_id,
                "title": data.title,
                "objective": data.objective,
                "pending_waits": data.pending_waits,
                "capability_authorities": data.capability_authorities,
                "policy_authorities": data.policy_authorities,
            }
        )
    if isinstance(data, RunReplayData):
        return _object(
            {
                "run_id": data.run_id,
                "event_count": data.event_count,
                "watermark": data.watermark,
                "status": data.status,
            }
        )
    if isinstance(data, RunTimelineData):
        return _object({"run_id": data.run_id, "entries": data.entries})
    if isinstance(data, RunWaitsData):
        return _object({"run_id": data.run_id, "pending": data.pending, "terminal": data.terminal})
    if isinstance(data, CommandExplanationData):
        return _object(
            {
                "run_id": data.run_id,
                "command_id": data.command_id,
                "origin": data.origin,
                "actor": data.actor,
                "provider": data.provider,
                "operation": data.operation,
                "decision": data.decision,
                "reason": data.reason,
                "trace": data.trace,
                "result_event_ids": data.result_event_ids,
                "result_event_types": data.result_event_types,
                "wait_id": data.wait_id,
                "superseded_by_command_id": data.superseded_by_command_id,
            }
        )
    if isinstance(data, ActionReceiptData):
        return data.receipt
    if isinstance(data, RunReadinessData):
        return _object(
            {
                "run_id": data.run_id,
                "status": data.status,
                "ready": data.ready,
                "requirements": data.requirements,
                "output_artifacts": data.output_artifacts,
                "semantic_checks": data.semantic_checks,
                "diagnostic_checks": data.diagnostic_checks,
                "source_coverage": data.source_coverage,
                "unresolved_unknown_outcomes": data.unresolved_unknown_outcomes,
                "pending_waits": data.pending_waits,
                "blockers": data.blockers,
            }
        )
    if isinstance(data, RunChecksData):
        return _object({"run_id": data.run_id, "reports": data.reports})
    if isinstance(data, ArtifactInspectionData):
        return _object(
            {
                "run_id": data.run_id,
                "artifact_id": data.artifact_id,
                "kind": data.kind,
                "available": data.available,
                "preview": data.preview,
                "content_type": data.content_type,
                "byte_length": data.byte_length,
                "sha256": data.sha256,
                "metadata": data.metadata,
            }
        )
    if isinstance(data, DemoResultData):
        return _object(
            {
                "run_id": data.run_id,
                "status": data.status,
                "runtime_home": data.runtime_home,
                "workspace_root": data.workspace_root,
                "workspace_selected_by": data.workspace_selected_by,
                "bundle_path": data.bundle_path,
                "event_count": data.event_count,
                "illegal_mutation": data.illegal_mutation,
                "approval": data.approval,
                "builtins": data.builtins,
                "unknown_outcome_reconciled": data.unknown_outcome_reconciled,
                "delegated_join_resolved": data.delegated_join_resolved,
                "check_gate_rejection": data.check_gate_rejection,
                "completion_ready": data.completion_ready,
                "timeline_entries": data.timeline_entries,
                "check_reports": data.check_reports,
                "bundle_commitment": data.bundle_commitment,
                "bundle_verified": data.bundle_verified,
                "bundle_event_count": data.bundle_event_count,
                "bundle_import_id": data.bundle_import_id,
                "bundle_resumable": data.bundle_resumable,
            }
        )
    raise TypeError("operator_result_data_invalid")


def _text_value(value: JsonValue) -> str:
    if value is None:
        return "null"
    if value is True:
        return "true"
    if value is False:
        return "false"
    if isinstance(value, str):
        return value
    if isinstance(value, (int, float)):
        return str(value)
    return encode_json_value(value).decode("utf-8").rstrip("\n")


def render_operator_text(result: OperatorResult[object], /) -> str:
    if not isinstance(result, OperatorResult):
        raise TypeError("operator_result_invalid")
    lines = [result.title]
    if result.failure is not None:
        lines.extend((f"error: {result.failure.code}", f"message: {result.failure.message}"))
    data = operator_data_json(result.data)
    lines.extend(f"{key}: {_text_value(value)}" for key, value in data.entries)
    return "\n".join(lines) + "\n"


def render_operator_json(result: OperatorResult[object], /) -> str:
    if not isinstance(result, OperatorResult):
        raise TypeError("operator_result_invalid")
    error: JsonValue = None
    if result.failure is not None:
        error = JsonObject(
            entries=(
                ("code", result.failure.code),
                ("message", result.failure.message),
            )
        )
    payload = JsonObject(
        entries=(
            ("ok", result.ok),
            ("command", result.command),
            ("exit_code", int(result.exit_code)),
            ("data", operator_data_json(result.data)),
            ("error", error),
        )
    )
    return encode_json_value(payload).decode("utf-8")


def operator_result_values(result: OperatorResult[object], /) -> JsonArray:
    """Return ordered values for hosts that render their own presentation."""

    return JsonArray(values=tuple(value for _key, value in operator_data_json(result.data).entries))
