from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import replace

from openrund.codec import decode_event
from openrund.contracts.events import RuntimeEvent
from openrund.contracts.ids import ActionId, EventId
from openrund.views import prepare_history
from openrund.views._actions import reduce_actions
from openrund.views._history import KnownHistory
from tests.conftest import CorpusEntry
from tests.views.conftest import read_view_entry


def _entry(entries: tuple[CorpusEntry, ...], key: str) -> CorpusEntry:
    return next(entry for entry in entries if entry.key == key)


def _history(entry: CorpusEntry) -> KnownHistory:
    decoded: object = json.loads(read_view_entry(entry))
    assert isinstance(decoded, dict)
    stream = decoded["stream"]
    watermark = decoded["watermark"]
    assert isinstance(stream, list)
    assert isinstance(watermark, int)
    events: tuple[RuntimeEvent, ...] = tuple(
        decode_event(json.dumps(value, separators=(",", ":")) + "\n") for value in stream
    )
    history = prepare_history(events, watermark=watermark)
    assert isinstance(history, KnownHistory)
    return history


def test_action_status_matches_all_frozen_lifecycle_branches(
    view_entries: tuple[CorpusEntry, ...],
) -> None:
    expected: Mapping[str, str] = {
        "requested": "requested",
        "started": "started",
        "completed": "completed",
        "failed": "failed",
        "cancelled": "cancelled",
        "outcome-unknown": "outcome_unknown",
        "reconciled-completed": "reconciled",
        "reconciled-failed": "reconciled",
        "reconciled-cancelled": "reconciled",
    }
    action_id = ActionId(value="act_oracle")
    for case, status in expected.items():
        views = reduce_actions(_history(_entry(view_entries, f"view:action-status:{case}")))
        assert views.status[action_id].status == status


def test_unknown_and_reconciled_status_preserve_source_evidence(
    view_entries: tuple[CorpusEntry, ...],
) -> None:
    action_id = ActionId(value="act_oracle")
    unknown = reduce_actions(
        _history(_entry(view_entries, "view:action-status:outcome-unknown"))
    ).status[action_id]
    reconciled = reduce_actions(
        _history(_entry(view_entries, "view:action-status:reconciled-completed"))
    ).status[action_id]

    assert unknown.unknown_reason == "oracle"
    assert unknown.reliability is not None
    assert reconciled.reconciled_outcome == "completed"
    assert reconciled.unknown_event_id is not None


def test_reconciliation_is_keyed_by_unknown_event_identity(
    view_entries: tuple[CorpusEntry, ...],
) -> None:
    pending = reduce_actions(
        _history(_entry(view_entries, "view:action-reconciliation:pending"))
    ).reconciliation
    mismatched = reduce_actions(
        _history(_entry(view_entries, "view:action-reconciliation:resolved-completed"))
    ).reconciliation

    assert len(pending.pending) == 1
    assert pending.reconciled == ()
    assert len(mismatched.pending) == 1
    assert len(mismatched.reconciled) == 1
    assert mismatched.reconciled[0].outcome == "completed"


def test_receipts_match_every_frozen_status_and_retain_timestamps(
    view_entries: tuple[CorpusEntry, ...],
) -> None:
    cases: Mapping[str, str] = {
        "requested": "requested",
        "started": "started",
        "completed": "completed",
        "failed": "failed",
        "cancelled": "cancelled",
        "outcome-unknown": "outcome_unknown",
        "reconciled-completed": "reconciled",
        "reconciled-failed": "reconciled",
        "reconciled-cancelled": "reconciled",
    }
    action_id = ActionId(value="act_oracle")
    for case, status in cases.items():
        receipt = reduce_actions(
            _history(_entry(view_entries, f"view:action-receipts:{case}"))
        ).receipts[action_id]
        assert receipt.status == status
        assert receipt.requested_at.value == "2026-01-02T03:04:05.678Z"
        assert receipt.run_id.value.startswith("run_oracle_view_")


def test_receipt_outcome_details_are_typed_and_immutable(
    view_entries: tuple[CorpusEntry, ...],
) -> None:
    action_id = ActionId(value="act_oracle")
    completed = reduce_actions(
        _history(_entry(view_entries, "view:action-receipts:completed"))
    ).receipts[action_id]
    failed = reduce_actions(_history(_entry(view_entries, "view:action-receipts:failed"))).receipts[
        action_id
    ]
    reconciled = reduce_actions(
        _history(_entry(view_entries, "view:action-receipts:reconciled-cancelled"))
    ).receipts[action_id]

    assert completed.result is not None
    assert completed.artifact_ids == ()
    assert failed.error is not None and failed.error.code == "oracle"
    assert reconciled.reconciliation is not None
    assert reconciled.reconciliation.outcome == "cancelled"
    assert (
        type(
            reduce_actions(
                _history(_entry(view_entries, "view:action-receipts:requested"))
            ).receipts
        ).__name__
        == "mappingproxy"
    )


def test_action_terminal_state_ignores_late_lifecycle_regression(
    view_entries: tuple[CorpusEntry, ...],
) -> None:
    completed = _history(_entry(view_entries, "view:action-receipts:completed"))
    assert completed.run_id is not None
    started = _history(_entry(view_entries, "view:action-receipts:started")).events[-1]
    late_started = replace(
        started,
        event_id=EventId(value="event-action-late-start"),
        run_id=completed.run_id,
        position=4,
    )
    history = prepare_history((*completed.events, late_started), watermark=4)
    assert isinstance(history, KnownHistory)

    action_id = ActionId(value="act_oracle")
    views = reduce_actions(history)

    assert views.status[action_id].status == "completed"
    assert views.receipts[action_id].status == "completed"
    assert views.receipts[action_id].completed_at is not None
