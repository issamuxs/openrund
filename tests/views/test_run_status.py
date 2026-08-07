from __future__ import annotations

import json
from collections.abc import Mapping
from typing import Literal

from openrund.codec import decode_event
from openrund.contracts.capabilities import ActionReliability
from openrund.contracts.content import Content
from openrund.contracts.events import (
    ActionUnknownPayload,
    CapabilityAuthorityGrantedPayload,
    CapabilityAuthorityRevokedPayload,
    CheckRecordedReportPayload,
    CoreEventType,
    Event,
    EventActor,
    EventPayload,
    PolicyAuthorityGrantedPayload,
    ReconciliationWaitCreatedPayload,
    RunCompletedPayload,
    RunCreatedPayload,
    RunStartedPayload,
    RuntimeEvent,
)
from openrund.contracts.ids import (
    ActionId,
    ArtifactId,
    AuthorityId,
    CapabilityId,
    CheckId,
    EventId,
    PolicyRuleId,
    RunId,
    WaitId,
)
from openrund.contracts.json import JsonObject, freeze_json
from openrund.contracts.runs import Artifact, CheckStatus
from openrund.contracts.time import Timestamp
from openrund.views import prepare_history
from openrund.views._history import KnownHistory
from openrund.views._run_status import ReadinessBlockerCode, reduce_run_status
from tests.conftest import CorpusEntry
from tests.views.conftest import read_view_entry

_AT = Timestamp(value="2026-01-02T03:04:05.678Z")
_RUN_ID = RunId(value="run-status-view")


def _json(value: object) -> JsonObject:
    frozen = freeze_json(value)
    assert isinstance(frozen, JsonObject)
    return frozen


def _entry(entries: tuple[CorpusEntry, ...], key: str) -> CorpusEntry:
    return next(entry for entry in entries if entry.key == key)


def _legacy_history(entry: CorpusEntry) -> KnownHistory:
    decoded: object = json.loads(read_view_entry(entry))
    assert isinstance(decoded, dict)
    stream = decoded["stream"]
    watermark = decoded["watermark"]
    assert isinstance(stream, list)
    assert isinstance(watermark, int)
    normalized: list[dict[str, object]] = []
    for raw in stream:
        assert isinstance(raw, dict)
        value = dict(raw)
        payload_value = value["payload"]
        assert isinstance(payload_value, dict)
        payload = dict(payload_value)
        if value["type"] == "wait.created" and payload.get("kind") == "approval":
            payload.update(
                {
                    "actionID": "act-oracle-wait",
                    "capabilityID": "cap-oracle-wait",
                    "actionName": "oracle",
                    "requestPayload": {"preview": "oracle"},
                    "policySnapshot": {"preview": "oracle"},
                }
            )
        if value["type"] == "check.recorded":
            payload.setdefault("subject", "run")
            payload.setdefault("rule", "semantic")
        value["payload"] = payload
        normalized.append(value)
    events: tuple[RuntimeEvent, ...] = tuple(
        decode_event(json.dumps(value, separators=(",", ":")) + "\n") for value in normalized
    )
    history = prepare_history(events, watermark=watermark)
    assert isinstance(history, KnownHistory)
    return history


def _event(position: int, event_type: CoreEventType, payload: EventPayload) -> RuntimeEvent:
    return Event(
        event_id=EventId(value=f"event-run-status-{position}"),
        run_id=_RUN_ID,
        position=position,
        event_type=event_type,
        timestamp=_AT,
        actor=EventActor.SYSTEM,
        payload=payload,
    )


def _history(
    *events: RuntimeEvent,
    artifacts: tuple[Artifact, ...] = (),
) -> KnownHistory:
    result = prepare_history(events, watermark=len(events), artifacts=artifacts)
    assert isinstance(result, KnownHistory)
    return result


def _artifact(kind: str, suffix: str) -> Artifact:
    return Artifact(
        artifact_id=ArtifactId(value=f"artifact-{suffix}"),
        run_id=_RUN_ID,
        kind=kind,
        byte_length=1,
        sha256="0" * 64,
    )


def _contract_metadata() -> JsonObject:
    return _json(
        {
            "run_contract": {
                "required_artifact_kinds": ["report", "bundle"],
                "check": {"checks": ["tests_passed"]},
                "delegation": {"kind": "source_coverage"},
                "completion": {"kind": "known_action_outcomes"},
            }
        }
    )


def _check_payload(*, source_status: Literal["passed", "failed"]) -> CheckRecordedReportPayload:
    return CheckRecordedReportPayload(
        check_id=CheckId(value="check-readiness"),
        subject=_RUN_ID.value,
        rule="completion",
        status=CheckStatus.PASSED if source_status == "passed" else CheckStatus.FAILED,
        validator="pytest",
        summary="completion checks",
        check_count=3,
        result=Content(
            data=_json(
                {
                    "checks": [
                        {"check": "tests_passed", "status": "passed"},
                        {"check": "source_coverage", "status": source_status},
                        {"check": "lint", "status": "passed"},
                    ]
                }
            )
        ),
    )


def test_run_status_matches_all_frozen_lifecycle_branches(
    view_entries: tuple[CorpusEntry, ...],
) -> None:
    expected: Mapping[str, tuple[str, int]] = {
        "unknown": ("unknown", 0),
        "created": ("created", 1),
        "running": ("running", 2),
        "waiting": ("waiting", 2),
        "completed": ("completed", 2),
        "failed": ("failed", 2),
        "cancelled": ("cancelled", 2),
    }
    for case, (status, watermark) in expected.items():
        view = reduce_run_status(_legacy_history(_entry(view_entries, f"view:run-status:{case}")))
        assert view.status == status
        assert view.source_watermark == watermark


def test_terminal_run_status_takes_precedence_over_unresolved_wait() -> None:
    history = _history(
        _event(
            1,
            CoreEventType.RUN_CREATED,
            RunCreatedPayload(root_id=_RUN_ID, initial_status="created"),
        ),
        _event(
            2,
            CoreEventType.WAIT_CREATED,
            ReconciliationWaitCreatedPayload(
                wait_id=WaitId(value="wait-still-open"),
                reason="unresolved",
            ),
        ),
        _event(3, CoreEventType.RUN_COMPLETED, RunCompletedPayload()),
        _event(4, CoreEventType.RUN_STARTED, RunStartedPayload(reason="illegal late start")),
    )

    view = reduce_run_status(history)

    assert view.status == "completed"
    assert len(view.pending_waits) == 1
    assert isinstance(view.terminal, RunCompletedPayload)


def test_frozen_readiness_cases_preserve_their_underlying_evidence(
    view_entries: tuple[CorpusEntry, ...],
) -> None:
    views = {
        case: reduce_run_status(
            _legacy_history(_entry(view_entries, f"view:run-status:readiness-{case}"))
        )
        for case in (
            "ready",
            "pending-waits",
            "unresolved-actions",
            "failed-check",
            "missing-artifacts",
            "multiple-blockers",
        )
    }

    assert views["ready"].completion_readiness.ready is True
    assert len(views["pending-waits"].pending_waits) == 1
    assert views["unresolved-actions"].completion_readiness.unresolved_unknown_outcomes == 1
    assert views["failed-check"].latest_check is not None
    assert views["failed-check"].latest_check.payload.status is CheckStatus.FAILED
    assert views["missing-artifacts"].completion_readiness.output_artifacts == ()
    assert len(views["multiple-blockers"].pending_waits) == 1
    assert views["multiple-blockers"].completion_readiness.unresolved_unknown_outcomes == 1


def test_authority_replay_preserves_history_and_rejects_stale_revocation() -> None:
    capability_id = CapabilityId(value="capability-filesystem")
    first_authority = AuthorityId(value="authority-first")
    current_authority = AuthorityId(value="authority-current")
    policy_id = PolicyRuleId(value="policy-write")
    history = _history(
        _event(
            1,
            CoreEventType.AUTHORITY_GRANTED,
            CapabilityAuthorityGrantedPayload(
                capability_id=capability_id,
                authority_id=first_authority,
            ),
        ),
        _event(
            2,
            CoreEventType.AUTHORITY_GRANTED,
            CapabilityAuthorityGrantedPayload(
                capability_id=capability_id,
                authority_id=current_authority,
            ),
        ),
        _event(
            3,
            CoreEventType.AUTHORITY_REVOKED,
            CapabilityAuthorityRevokedPayload(
                capability_id=capability_id,
                authority_id=first_authority,
            ),
        ),
        _event(
            4,
            CoreEventType.AUTHORITY_GRANTED,
            PolicyAuthorityGrantedPayload(rule_id=policy_id, rule=_json({"allow": True})),
        ),
    )

    view = reduce_run_status(history)

    assert view.capability_authority[capability_id].payload.authority_id == current_authority
    assert policy_id in view.policy_authority
    assert len(view.authority_history) == 4


def test_readiness_blockers_are_complete_and_stably_ordered() -> None:
    report = _artifact("report", "report")
    history = _history(
        _event(
            1,
            CoreEventType.RUN_CREATED,
            RunCreatedPayload(
                root_id=_RUN_ID,
                initial_status="created",
                metadata=_contract_metadata(),
            ),
        ),
        _event(
            2,
            CoreEventType.WAIT_CREATED,
            ReconciliationWaitCreatedPayload(wait_id=WaitId(value="wait-readiness")),
        ),
        _event(
            3,
            CoreEventType.ACTION_UNKNOWN,
            ActionUnknownPayload(
                action_id=ActionId(value="action-unknown"),
                reason="worker disconnected",
                reliability=ActionReliability.IDEMPOTENT_MUTATION,
            ),
        ),
        _event(4, CoreEventType.CHECK_RECORDED, _check_payload(source_status="failed")),
        artifacts=(report,),
    )

    readiness = reduce_run_status(history).completion_readiness

    assert tuple(blocker.code for blocker in readiness.blockers) == (
        ReadinessBlockerCode.PENDING_WAIT,
        ReadinessBlockerCode.MISSING_REQUIRED_ARTIFACT,
        ReadinessBlockerCode.UNRESOLVED_ACTION_OUTCOME,
        ReadinessBlockerCode.UNSATISFIED_SEMANTIC_CHECK,
    )
    assert readiness.blockers[1].artifact_kind == "bundle"
    assert readiness.blockers[3].check == "source_coverage"
    assert readiness.blockers[3].observed_check_status == "failed"
    assert readiness.unresolved_unknown_outcomes == 1
    assert readiness.source_coverage.satisfied is False
    assert readiness.ready is False


def test_ready_is_derived_data_and_never_completion_authority() -> None:
    history = _history(
        _event(
            1,
            CoreEventType.RUN_CREATED,
            RunCreatedPayload(
                root_id=_RUN_ID,
                initial_status="created",
                metadata=_contract_metadata(),
            ),
        ),
        _event(2, CoreEventType.CHECK_RECORDED, _check_payload(source_status="passed")),
        artifacts=(_artifact("report", "ready-report"), _artifact("bundle", "ready-bundle")),
    )

    view = reduce_run_status(history)
    readiness = view.completion_readiness

    assert readiness.ready is True
    assert readiness.blockers == ()
    assert readiness.source_coverage.satisfied is True
    assert tuple(result.name for result in readiness.semantic_checks) == (
        "tests_passed",
        "source_coverage",
    )
    assert tuple(result.name for result in readiness.diagnostic_checks) == ("lint",)
    assert not hasattr(readiness, "complete")
    assert not hasattr(view, "append_event")
