from __future__ import annotations

import asyncio
from dataclasses import replace

from openrund._testing.memory import MemoryEventStore
from openrund.contracts.capabilities import ActionReliability
from openrund.contracts.commands import (
    AcceptedCommandDecision,
    Command,
    CommandOrigin,
    CompleteRunOperation,
    MarkActionUnknownOperation,
    ReconcileActionOperation,
    RejectedCommandDecision,
)
from openrund.contracts.content import Content, RunResult
from openrund.contracts.events import (
    ActionCreatedPayload,
    ActionStartedPayload,
    CoreEventType,
    RunCreatedPayload,
    RunStartedPayload,
)
from openrund.contracts.ids import ActionId, CapabilityId, CommandId, EventId, RunId
from openrund.contracts.json import freeze_json
from openrund.engine import EngineDependencies, RuntimeEngine
from openrund.ports.events import AppendEventsInput
from openrund.views import CompleteViewReplay, rebuild_views
from tests.engine.conftest import runtime_event

RUN_ID = RunId(value="run_1")
ACTION_ID = ActionId(value="action_1")


def _command(command_id: str, operation: object) -> Command:
    return Command(
        command_id=CommandId(value=command_id),
        run_id=RUN_ID,
        origin=CommandOrigin.OPERATOR,
        operation=operation,  # type: ignore[arg-type]
    )


def _seed(event_store: MemoryEventStore) -> None:
    metadata = freeze_json({"run_contract": {"completion": {"kind": "known_action_outcomes"}}})
    events = (
        runtime_event(
            CoreEventType.RUN_CREATED,
            RunCreatedPayload(
                root_id=RUN_ID,
                initial_status="created",
                metadata=metadata,  # type: ignore[arg-type]
            ),
            1,
        ),
        runtime_event(CoreEventType.RUN_STARTED, RunStartedPayload(), 2),
        runtime_event(
            CoreEventType.ACTION_CREATED,
            ActionCreatedPayload(
                action_id=ACTION_ID,
                capability_id=CapabilityId(value="filesystem"),
                action_name="write",
                input=Content(preview="write report"),
            ),
            3,
        ),
        runtime_event(
            CoreEventType.ACTION_STARTED,
            ActionStartedPayload(
                action_id=ACTION_ID,
                capability_id=CapabilityId(value="filesystem"),
                action_name="write",
            ),
            4,
        ),
    )
    asyncio.run(
        event_store.append(AppendEventsInput(run_id=RUN_ID, expected_position=0, events=events))
    )


def test_unknown_outcome_blocks_completion_until_evidence_backed_reconciliation(
    engine_dependencies: EngineDependencies,
    event_store: MemoryEventStore,
) -> None:
    _seed(event_store)
    engine = RuntimeEngine(engine_dependencies)
    marked = asyncio.run(
        engine.submit(
            _command(
                "mark-unknown",
                MarkActionUnknownOperation(
                    action_id=ACTION_ID,
                    reliability=ActionReliability.TIMEOUT_AFTER_DISPATCH,
                    reason="transport timed out after dispatch",
                ),
            )
        )
    )
    assert isinstance(marked.decision, AcceptedCommandDecision)
    assert len(marked.decision.result_event_ids) == 2
    unknown_event_id = marked.decision.result_event_ids[0]

    blocked = asyncio.run(
        engine.submit(
            _command(
                "complete-blocked",
                CompleteRunOperation(result=RunResult(kind="test")),
            )
        )
    )
    wrong_event = asyncio.run(
        engine.submit(
            _command(
                "wrong-event",
                ReconcileActionOperation(
                    action_id=ACTION_ID,
                    unknown_event_id=EventId(value="wrong"),
                    outcome="completed",
                    evidence=Content(preview="receipt confirms completion"),
                ),
            )
        )
    )
    empty_evidence = asyncio.run(
        engine.submit(
            _command(
                "empty-evidence",
                ReconcileActionOperation(
                    action_id=ACTION_ID,
                    unknown_event_id=unknown_event_id,
                    outcome="completed",
                    evidence=Content(),
                ),
            )
        )
    )
    reconciled = asyncio.run(
        engine.submit(
            _command(
                "reconcile",
                ReconcileActionOperation(
                    action_id=ACTION_ID,
                    unknown_event_id=unknown_event_id,
                    outcome="completed",
                    evidence=Content(preview="receipt confirms completion"),
                    reconciled_by="operator",
                ),
            )
        )
    )

    assert isinstance(blocked.decision, RejectedCommandDecision)
    assert blocked.decision.reason == "completion_blocked"
    assert isinstance(wrong_event.decision, RejectedCommandDecision)
    assert wrong_event.decision.reason == "unknown_event_mismatch"
    assert isinstance(empty_evidence.decision, RejectedCommandDecision)
    assert empty_evidence.decision.reason == "reconciliation_evidence_required"
    assert isinstance(reconciled.decision, AcceptedCommandDecision)
    assert len(reconciled.decision.result_event_ids) == 2

    history = asyncio.run(event_store.read(RUN_ID))
    replay = rebuild_views(history.events, watermark=history.next_position - 1)
    assert isinstance(replay, CompleteViewReplay)
    assert replay.views.action_status[ACTION_ID].status == "reconciled"
    assert replay.views.action_status[ACTION_ID].unknown_event_id == unknown_event_id
    assert replay.views.action_reconciliation.pending == ()
    assert replay.views.waits.all_pending == ()
    assert replay.views.run_status.completion_readiness.ready

    duplicate = asyncio.run(
        engine.submit(
            _command(
                "duplicate",
                ReconcileActionOperation(
                    action_id=ACTION_ID,
                    unknown_event_id=unknown_event_id,
                    outcome="failed",
                    evidence=Content(preview="conflicting evidence"),
                ),
            )
        )
    )
    remarked = asyncio.run(
        engine.submit(
            _command(
                "remark",
                MarkActionUnknownOperation(
                    action_id=ACTION_ID,
                    reliability=ActionReliability.UNKNOWN,
                    reason="try to contradict terminal state",
                ),
            )
        )
    )
    completed = asyncio.run(
        engine.submit(_command("complete", CompleteRunOperation(result=RunResult(kind="test"))))
    )

    assert isinstance(duplicate.decision, RejectedCommandDecision)
    assert duplicate.decision.reason == "action_already_reconciled"
    assert isinstance(remarked.decision, RejectedCommandDecision)
    assert remarked.decision.reason == "action_already_terminal"
    assert isinstance(completed.decision, AcceptedCommandDecision)


def test_model_cannot_mark_or_reconcile_action_outcomes(
    engine_dependencies: EngineDependencies,
    event_store: MemoryEventStore,
) -> None:
    _seed(event_store)
    engine = RuntimeEngine(engine_dependencies)

    self_marked = asyncio.run(
        engine.submit(
            replace(
                _command(
                    "model-mark",
                    MarkActionUnknownOperation(
                        action_id=ACTION_ID,
                        reliability=ActionReliability.UNKNOWN,
                        reason="model assertion",
                    ),
                ),
                origin=CommandOrigin.MODEL,
            )
        )
    )

    assert isinstance(self_marked.decision, RejectedCommandDecision)
    assert self_marked.decision.reason == "coordination_origin_forbidden"
    operator_marked = asyncio.run(
        engine.submit(
            _command(
                "operator-mark",
                MarkActionUnknownOperation(
                    action_id=ACTION_ID,
                    reliability=ActionReliability.UNKNOWN,
                    reason="operator recovery",
                ),
            )
        )
    )
    assert isinstance(operator_marked.decision, AcceptedCommandDecision)
    self_reconciled = asyncio.run(
        engine.submit(
            replace(
                _command(
                    "model-reconcile",
                    ReconcileActionOperation(
                        action_id=ACTION_ID,
                        unknown_event_id=operator_marked.decision.result_event_ids[0],
                        outcome="completed",
                        evidence=Content(preview="model assertion"),
                    ),
                ),
                origin=CommandOrigin.MODEL,
            )
        )
    )
    assert isinstance(self_reconciled.decision, RejectedCommandDecision)
    assert self_reconciled.decision.reason == "coordination_origin_forbidden"
    history = asyncio.run(event_store.read(RUN_ID))
    assert sum(event.event_type is CoreEventType.ACTION_UNKNOWN for event in history.events) == 1
    assert not any(event.event_type is CoreEventType.ACTION_RECONCILED for event in history.events)
