from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import replace
from typing import Literal

from openrund.codec import decode_event
from openrund.contracts.events import (
    CoreEventType,
    DelegationCompletedPayload,
    DelegationFailedPayload,
    Event,
    EventActor,
    EventPayload,
    JoinWaitCreatedPayload,
    JoinWaitResolvedPayload,
    RuntimeEvent,
)
from openrund.contracts.ids import EventId, RunId, WaitId
from openrund.contracts.runs import DelegationJoinMode
from openrund.contracts.time import Timestamp
from openrund.views import prepare_history
from openrund.views._delegation import reduce_delegation
from openrund.views._history import KnownHistory
from tests.conftest import CorpusEntry
from tests.views.conftest import read_view_entry

_AT = Timestamp(value="2026-01-02T03:04:05.678Z")
_RUN_ID = RunId(value="run-delegation-parent")


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
        if value["type"] == "wait.created" and payload.get("kind") == "join":
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
        event_id=EventId(value=f"event-delegation-{position}"),
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


def test_delegated_run_lifecycle_matches_all_frozen_states(
    view_entries: tuple[CorpusEntry, ...],
) -> None:
    expected: Mapping[str, str] = {
        "establishing": "establishing",
        "running": "running",
        "completed-handoff": "completed",
        "failed-handoff": "failed",
        "cancelled-handoff": "cancelled",
    }
    child_id = RunId(value="run_oracle_child")
    for case, status in expected.items():
        view = reduce_delegation(_legacy_history(_entry(view_entries, f"view:delegation:{case}")))
        child = view.delegated_runs[child_id]
        assert child.status == status
        assert child.parent_run_id.value.startswith("run_oracle_view_")
        assert child.creation.contract.objective == "Fixed cancel work"
        assert child.creation.contract.budget.max_requests == 2


def test_handoff_preserves_result_failure_and_cancellation_payloads(
    view_entries: tuple[CorpusEntry, ...],
) -> None:
    child_id = RunId(value="run_oracle_child")
    for case, status in (
        ("completed-handoff", "completed"),
        ("failed-handoff", "failed"),
        ("cancelled-handoff", "cancelled"),
    ):
        view = reduce_delegation(_legacy_history(_entry(view_entries, f"view:delegation:{case}")))
        fact = view.handoffs[child_id][0]
        assert fact.status == status
        assert view.delegated_runs[child_id].terminal == fact


def test_delegated_run_terminal_state_ignores_late_conflicting_handoff(
    view_entries: tuple[CorpusEntry, ...],
) -> None:
    completed = _legacy_history(_entry(view_entries, "view:delegation:completed-handoff"))
    assert completed.run_id is not None
    failed = _legacy_history(_entry(view_entries, "view:delegation:failed-handoff"))
    late_failed = replace(
        failed.events[-1],
        event_id=EventId(value="event-delegation-late-failure"),
        run_id=completed.run_id,
        position=4,
    )
    history = prepare_history((*completed.events, late_failed), watermark=4)
    assert isinstance(history, KnownHistory)

    child_id = RunId(value="run_oracle_child")
    view = reduce_delegation(history)

    assert view.delegated_runs[child_id].status == "completed"
    assert len(view.handoffs[child_id]) == 2
    assert view.delegated_runs[child_id].terminal == view.handoffs[child_id][0]


def test_all_any_and_quorum_join_lifecycles_match_frozen_cases(
    view_entries: tuple[CorpusEntry, ...],
) -> None:
    wait_id = WaitId(value="w_oracle_join")
    for mode in ("all", "any", "quorum"):
        for case, expected in (
            ("pending", "pending"),
            ("completed", "completed"),
            ("cancelled", "cancelled"),
        ):
            view = reduce_delegation(
                _legacy_history(_entry(view_entries, f"view:delegation:join-{mode}-{case}"))
            )
            join = view.joins[wait_id]
            assert join.request.mode.value == mode
            assert join.status == expected
            assert join.pending_run_ids == (
                () if expected == "completed" else (RunId(value="run_oracle_child"),)
            )
            if expected == "completed":
                assert join.completed_run_ids == (RunId(value="run_oracle_child"),)
                assert join.satisfied is True


def test_join_satisfaction_is_explanatory_and_does_not_advance_status() -> None:
    child_a = RunId(value="run-child-a")
    child_b = RunId(value="run-child-b")
    child_c = RunId(value="run-child-c")
    targets = (child_a, child_b, child_c)
    events: list[RuntimeEvent] = []
    definitions: tuple[
        tuple[
            str,
            DelegationJoinMode,
            int | None,
            Literal["completed_only", "terminal_any", "completed_or_failed"],
        ],
        ...,
    ] = (
        ("all", DelegationJoinMode.ALL, None, "completed_only"),
        ("any", DelegationJoinMode.ANY, None, "completed_only"),
        ("quorum", DelegationJoinMode.QUORUM, 2, "completed_or_failed"),
    )
    for position, (name, mode, quorum, outcome_filter) in enumerate(definitions, start=1):
        events.append(
            _event(
                position,
                CoreEventType.WAIT_CREATED,
                JoinWaitCreatedPayload(
                    wait_id=WaitId(value=f"wait-{name}"),
                    target_run_ids=targets,
                    mode=mode,
                    quorum=quorum,
                    outcome_filter=outcome_filter,
                    failure_policy="wait_for_all_terminal",
                    on_satisfied="keep_bound",
                    late_handoff_policy="surface",
                ),
            )
        )
    events.extend(
        (
            _event(
                4,
                CoreEventType.DELEGATION_COMPLETED,
                DelegationCompletedPayload(delegated_run_id=child_a),
            ),
            _event(
                5,
                CoreEventType.DELEGATION_FAILED,
                DelegationFailedPayload(delegated_run_id=child_b, message="failed"),
            ),
        )
    )

    joins = reduce_delegation(_history(*events)).joins

    assert joins[WaitId(value="wait-all")].satisfied is False
    assert joins[WaitId(value="wait-any")].satisfied is True
    assert joins[WaitId(value="wait-quorum")].satisfied is True
    assert all(join.status == "pending" for join in joins.values())
    assert joins[WaitId(value="wait-quorum")].pending_run_ids == (child_c,)


def test_join_resolution_preserves_reported_terminal_sets_without_authority() -> None:
    child = RunId(value="run-child-reported")
    wait_id = WaitId(value="wait-reported")
    queues = reduce_delegation(
        _history(
            _event(
                1,
                CoreEventType.WAIT_CREATED,
                JoinWaitCreatedPayload(
                    wait_id=wait_id,
                    target_run_ids=(child,),
                    mode=DelegationJoinMode.ALL,
                    outcome_filter="terminal_any",
                    failure_policy="wait_for_all_terminal",
                    on_satisfied="keep_bound",
                    late_handoff_policy="surface",
                ),
            ),
            _event(
                2,
                CoreEventType.WAIT_RESOLVED,
                JoinWaitResolvedPayload(
                    wait_id=wait_id,
                    target_run_ids=(child,),
                    mode=DelegationJoinMode.ALL,
                    completed_run_ids=(),
                    terminal_run_ids=(child,),
                ),
            ),
        )
    )

    join = queues.joins[wait_id]
    assert join.satisfied is True
    assert join.pending_run_ids == ()
    assert not hasattr(join, "advance_parent")
    assert type(queues.joins).__name__ == "mappingproxy"
