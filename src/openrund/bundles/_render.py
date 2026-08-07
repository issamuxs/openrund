"""Compact deterministic explanatory Bundle surfaces."""

from __future__ import annotations

from openrund.contracts.json import JsonArray, JsonObject, JsonValue
from openrund.views._model import RunViewBundle


def _strings(values: tuple[str, ...]) -> JsonArray:
    return JsonArray(values=values)


def view_summary(run_id: str, views: RunViewBundle, event_count: int) -> JsonObject:
    pending = tuple(
        JsonObject(
            entries=(
                ("waitID", item.wait_id.value),
                ("kind", item.kind.value),
            )
        )
        for item in views.run_status.pending_waits
    )
    blockers = tuple(item.code.value for item in views.run_status.completion_readiness.blockers)
    return JsonObject(
        entries=(
            ("runID", run_id),
            ("status", views.run_status.status),
            ("currentPosition", views.run_status.source_watermark),
            ("pendingWaits", JsonArray(values=pending)),
            ("eventCount", event_count),
            (
                "completionReadiness",
                JsonObject(
                    entries=(
                        ("ready", views.run_status.completion_readiness.ready),
                        ("blockers", JsonArray(values=blockers)),
                        (
                            "unresolvedUnknownOutcomes",
                            views.run_status.completion_readiness.unresolved_unknown_outcomes,
                        ),
                    )
                ),
            ),
        )
    )


def policy_snapshot(views: RunViewBundle) -> JsonArray:
    return JsonArray(
        values=tuple(
            JsonObject(
                entries=(
                    ("ruleID", rule_id.value),
                    ("rule", entry.payload.rule),
                )
            )
            for rule_id, entry in views.run_status.policy_authority.items()
        )
    )


def capability_snapshot(views: RunViewBundle, required_providers: tuple[str, ...]) -> JsonObject:
    grants = tuple(
        JsonObject(
            entries=(
                ("capabilityID", capability_id.value),
                (
                    "metadata",
                    entry.payload.metadata
                    if isinstance(entry.payload.metadata, JsonObject)
                    else JsonObject(entries=()),
                ),
            )
        )
        for capability_id, entry in views.run_status.capability_authority.items()
    )
    return JsonObject(
        entries=(
            ("grants", JsonArray(values=grants)),
            ("providers", _strings(required_providers)),
        )
    )


def report_json(views: RunViewBundle) -> JsonObject:
    reports: list[JsonValue] = []
    for report in views.reports:
        reports.append(
            JsonObject(
                entries=(
                    ("eventID", report.event_id.value),
                    ("checkID", report.check_id.value),
                    ("timestamp", report.timestamp.value),
                    ("subject", report.subject),
                    ("rule", report.rule),
                    ("status", report.status.value),
                    ("validator", report.validator),
                    ("summary", report.summary),
                    ("checkCount", report.check_count),
                    (
                        "artifactIDs",
                        JsonArray(values=tuple(item.value for item in report.artifact_ids)),
                    ),
                )
            )
        )
    return JsonObject(entries=(("reports", JsonArray(values=tuple(reports))),))


def runtime_audit(run_id: str, views: RunViewBundle, event_types: tuple[str, ...]) -> JsonObject:
    return JsonObject(
        entries=(
            ("runID", run_id),
            ("status", views.run_status.status),
            ("currentPosition", views.run_status.source_watermark),
            ("eventCount", len(event_types)),
            (
                "pendingWaits",
                JsonArray(values=tuple(item.kind.value for item in views.run_status.pending_waits)),
            ),
            ("reportCount", len(views.reports)),
            ("actionReceiptCount", len(views.action_receipts)),
            ("eventTypes", JsonArray(values=event_types)),
        )
    )


def runtime_audit_markdown(audit: JsonObject) -> bytes:
    values = {key: value for key, value in audit.entries}
    lines = (
        "# Runtime Audit",
        "",
        f"- Run: {values['runID']}",
        f"- Status: {values['status']}",
        f"- Event count: {values['eventCount']}",
        f"- Current position: {values['currentPosition']}",
        f"- Reports: {values['reportCount']}",
        f"- Action receipts: {values['actionReceiptCount']}",
        "",
    )
    return "\n".join(lines).encode()


def reports_markdown(views: RunViewBundle) -> bytes:
    lines = ["# Check Reports", ""]
    for report in views.reports:
        lines.extend(
            (
                f"## {report.check_id.value}",
                "",
                f"- Status: {report.status.value}",
                f"- Validator: {report.validator}",
                f"- Summary: {report.summary}",
                "",
            )
        )
    return "\n".join(lines).encode()


def action_receipt_markdown(receipt: object) -> bytes:
    action_id = getattr(getattr(receipt, "action_id", None), "value", "unknown")
    capability_id = getattr(getattr(receipt, "capability_id", None), "value", "unknown")
    action_name = getattr(receipt, "action_name", "unknown")
    status = getattr(receipt, "status", "unknown")
    return (
        f"# Action Receipt\n\n- Action: {action_id}\n- Capability: "
        f"{capability_id}.{action_name}\n- Status: {status}\n"
    ).encode()
