from __future__ import annotations

import json

import pytest

from openrund.codec import decode_event
from openrund.contracts.content import Content
from openrund.contracts.events import (
    AggregateWaitCreatedPayload,
    AggregateWaitResolvedPayload,
    ApprovalWaitCreatedPayload,
    ApprovalWaitResolvedPayload,
    CoreEventType,
    Event,
    EventActor,
    EventPayload,
    JoinWaitCreatedPayload,
    JoinWaitResolvedPayload,
    ReconciliationWaitCreatedPayload,
    ReconciliationWaitExpiredPayload,
    RuntimeEvent,
    WaitReference,
)
from openrund.contracts.ids import ActionId, CapabilityId, EventId, RunId, WaitId
from openrund.contracts.json import JsonObject
from openrund.contracts.runs import DelegationJoinMode, WaitKind
from openrund.contracts.time import Timestamp
from openrund.errors import ValidationError
from openrund.views import prepare_history
from openrund.views._history import KnownHistory
from openrund.views._waits import reduce_waits
from tests.conftest import CorpusEntry
from tests.views.conftest import read_view_entry

_AT = Timestamp(value="2026-01-02T03:04:05.678Z")
_RUN_ID = RunId(value="run-wait-views")


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
        kind = payload.get("kind")
        event_type = value["type"]
        if event_type == "wait.created" and kind == "approval":
            payload.update(
                {
                    "actionID": "act-oracle-wait",
                    "capabilityID": "cap-oracle-wait",
                    "actionName": "oracle",
                    "requestPayload": {"preview": "oracle"},
                    "policySnapshot": {"preview": "oracle"},
                }
            )
        elif event_type == "wait.created" and kind == "interaction":
            payload["prompt"] = {"preview": "oracle"}
        elif event_type == "wait.resolved" and kind == "interaction":
            payload["response"] = {"preview": "oracle"}
        elif event_type == "wait.resolved" and kind == "timer":
            payload["firedAt"] = value["timestamp"]
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
        event_id=EventId(value=f"event-wait-{position}"),
        run_id=_RUN_ID,
        position=position,
        event_type=event_type,
        timestamp=_AT,
        actor=EventActor.SYSTEM,
        payload=payload,
    )


def _history(*events: RuntimeEvent) -> KnownHistory:
    result = prepare_history(events, watermark=len(events))
    assert isinstance(result, KnownHistory)
    return result


def test_approval_interaction_and_timer_match_all_frozen_lifecycles(
    view_entries: tuple[CorpusEntry, ...],
) -> None:
    cases = {
        "approval-pending": ("approvals", "pending"),
        "approval-resolved": ("approvals", "approved"),
        "approval-cancelled": ("approvals", "cancelled"),
        "approval-expired": ("approvals", "expired"),
        "interaction-pending": ("interactions", "pending"),
        "interaction-resolved": ("interactions", "resolved"),
        "interaction-cancelled": ("interactions", "cancelled"),
        "interaction-expired": ("interactions", "expired"),
        "timer-pending": ("timers", "pending"),
        "timer-fired": ("timers", "fired"),
        "timer-cancelled": ("timers", "cancelled"),
        "timer-expired": ("timers", "expired"),
    }
    for case, (queue_name, outcome) in cases.items():
        queues = reduce_waits(_legacy_history(_entry(view_entries, f"view:waits:{case}")))
        queue = getattr(queues, queue_name)
        if outcome == "pending":
            assert len(queue.pending) == 1 and queue.terminal == ()
        else:
            assert queue.pending == ()
            assert len(queue.terminal) == 1
            assert queue.terminal[0].outcome == outcome
            assert queue.terminal[0].request is not None


def test_join_and_reconciliation_queues_preserve_typed_payloads() -> None:
    join_id = WaitId(value="wait-join")
    reconciliation_id = WaitId(value="wait-reconciliation")
    child_ids = (RunId(value="run-child-a"), RunId(value="run-child-b"))
    history = _history(
        _event(
            1,
            CoreEventType.WAIT_CREATED,
            JoinWaitCreatedPayload(
                wait_id=join_id,
                target_run_ids=child_ids,
                mode=DelegationJoinMode.ALL,
                outcome_filter="terminal_any",
                failure_policy="wait_for_all_terminal",
                on_satisfied="keep_bound",
                late_handoff_policy="surface",
                reason="join children",
            ),
        ),
        _event(
            2,
            CoreEventType.WAIT_CREATED,
            ReconciliationWaitCreatedPayload(
                wait_id=reconciliation_id,
                reason="recover uncertain action",
            ),
        ),
        _event(
            3,
            CoreEventType.WAIT_RESOLVED,
            JoinWaitResolvedPayload(
                wait_id=join_id,
                target_run_ids=child_ids,
                mode=DelegationJoinMode.ALL,
                completed_run_ids=child_ids,
                terminal_run_ids=child_ids,
            ),
        ),
        _event(
            4,
            CoreEventType.WAIT_EXPIRED,
            ReconciliationWaitExpiredPayload(
                wait_id=reconciliation_id,
                expired_at=_AT,
                reason="operator deadline",
            ),
        ),
    )

    queues = reduce_waits(history)

    assert queues.joins.pending == ()
    assert queues.joins.terminal[0].outcome == "resolved"
    assert isinstance(queues.joins.terminal[0].terminal, JoinWaitResolvedPayload)
    assert queues.reconciliations.terminal[0].outcome == "expired"
    assert queues.reconciliations.terminal[0].request is not None


def test_approval_request_and_resolution_preserve_exact_operator_evidence() -> None:
    wait_id = WaitId(value="wait-approval-evidence")
    deadline = Timestamp(value="2026-01-03T03:04:05.678Z")
    approved_input = JsonObject(entries=(("path", "README.md"),))
    queues = reduce_waits(
        _history(
            _event(
                1,
                CoreEventType.WAIT_CREATED,
                ApprovalWaitCreatedPayload(
                    wait_id=wait_id,
                    action_id=ActionId(value="action-approval-evidence"),
                    capability_id=CapabilityId(value="capability-filesystem"),
                    action_name="write",
                    request_payload=Content(preview="Write README.md"),
                    policy_snapshot=Content(preview="requires approval"),
                    target="filesystem.write",
                    reason="irreversible mutation",
                    deadline=deadline,
                ),
            ),
            _event(
                2,
                CoreEventType.WAIT_RESOLVED,
                ApprovalWaitResolvedPayload(
                    wait_id=wait_id,
                    decision="approved",
                    approved_input=approved_input,
                    note=Content(preview="approved by operator"),
                    resolved_by="operator",
                ),
            ),
        )
    )

    terminal = queues.approvals.terminal[0]
    assert terminal.request is not None
    request = terminal.request.request
    assert isinstance(request, ApprovalWaitCreatedPayload)
    assert request.target == "filesystem.write"
    assert request.deadline == deadline
    assert isinstance(terminal.terminal, ApprovalWaitResolvedPayload)
    assert terminal.terminal.approved_input == approved_input
    assert terminal.terminal.resolved_by == "operator"


def test_terminal_without_matching_request_is_explicit_not_pending() -> None:
    wait_id = WaitId(value="wait-orphan-terminal")
    queues = reduce_waits(
        _history(
            _event(
                1,
                CoreEventType.WAIT_EXPIRED,
                ReconciliationWaitExpiredPayload(wait_id=wait_id, reason="orphan"),
            )
        )
    )

    assert queues.reconciliations.pending == ()
    assert queues.reconciliations.terminal[0].request is None


def test_aggregate_wait_forms_remain_ordered_explanatory_facts() -> None:
    wait_id = WaitId(value="wait-aggregate-member")
    queues = reduce_waits(
        _history(
            _event(
                1,
                CoreEventType.WAIT_CREATED,
                AggregateWaitCreatedPayload(
                    waiting_on=(WaitReference(wait_id=wait_id, kind=WaitKind.APPROVAL),),
                    reason="blocked",
                ),
            ),
            _event(
                2,
                CoreEventType.WAIT_RESOLVED,
                AggregateWaitResolvedPayload(
                    resumed_from="approval",
                    trigger_event_id=EventId(value="event-wait-trigger"),
                    kind=WaitKind.APPROVAL,
                ),
            ),
        )
    )

    assert queues.aggregate_created[0].payload.waiting_on[0].wait_id == wait_id
    assert queues.aggregate_resolved[0].payload.resumed_from == "approval"
    assert not hasattr(queues, "resolve")
    assert isinstance(queues.aggregate_created, tuple)

    with pytest.raises(ValidationError):
        AggregateWaitCreatedPayload(waiting_on=())
