from __future__ import annotations

import asyncio
from dataclasses import replace
from typing import Literal

import pytest

from openrund._testing.memory import MemoryEventStore
from openrund.contracts.commands import (
    AcceptedCommandDecision,
    CancelDelegationOperation,
    CancelRunOperation,
    Command,
    CommandOrigin,
    CommandResult,
    CompleteDelegationOperation,
    CompleteRunOperation,
    FailDelegationOperation,
    FailRunOperation,
    OpenJoinWaitOperation,
    RejectedCommandDecision,
    ResolveJoinWaitOperation,
)
from openrund.contracts.content import RunResult
from openrund.contracts.events import (
    CanonicalAnnotationRecordedPayload,
    DelegationCancelledPayload,
    DelegationCompletedPayload,
    DelegationFailedPayload,
)
from openrund.contracts.ids import CommandId, RunId, WaitId
from openrund.contracts.runs import DelegationJoinMode
from openrund.engine import EngineDependencies, RuntimeEngine
from openrund.views import CompleteViewReplay, rebuild_views
from tests.engine.test_delegation import (
    PARENT_ID,
    _contract,
    _operation,
    _seed_parent,
)
from tests.engine.test_delegation import (
    _command as _delegation_command,
)


def _parent_command(command_id: str, operation: object) -> Command:
    return Command(
        command_id=CommandId(value=command_id),
        run_id=PARENT_ID,
        origin=CommandOrigin.OPERATOR,
        operation=operation,  # type: ignore[arg-type]
    )


def _child_command(child_id: RunId, command_id: str, operation: object) -> Command:
    return Command(
        command_id=CommandId(value=command_id),
        run_id=child_id,
        origin=CommandOrigin.SYSTEM,
        operation=operation,  # type: ignore[arg-type]
    )


def _establish(
    engine: RuntimeEngine,
    child_id: RunId,
    *,
    policy: Literal["ignore", "surface", "add_to_context"] = "surface",
    on_parent_cancel: Literal["cancel", "detach", "allow_completion"] = "cancel",
) -> None:
    contract = replace(
        _contract(),
        late_handoff=policy,
        on_parent_cancel=on_parent_cancel,
    )
    result = asyncio.run(
        engine.submit(
            _delegation_command(
                f"establish-{child_id.value}",
                _operation(contract, child_id=child_id),
            )
        )
    )
    assert isinstance(result.decision, AcceptedCommandDecision)


def _complete_child(engine: RuntimeEngine, child_id: RunId) -> None:
    result = asyncio.run(
        engine.submit(
            _child_command(
                child_id,
                f"complete-{child_id.value}",
                CompleteRunOperation(result=RunResult(kind="analysis")),
            )
        )
    )
    assert isinstance(result.decision, AcceptedCommandDecision)


def _handoff(engine: RuntimeEngine, child_id: RunId, command_id: str) -> CommandResult:
    return asyncio.run(
        engine.submit(
            _parent_command(
                command_id,
                CompleteDelegationOperation(delegated_run_id=child_id),
            )
        )
    )


@pytest.mark.parametrize(
    ("mode", "child_count", "required", "quorum"),
    (
        (DelegationJoinMode.ALL, 2, 2, None),
        (DelegationJoinMode.ANY, 2, 1, None),
        (DelegationJoinMode.QUORUM, 3, 2, 2),
    ),
)
def test_all_any_and_quorum_join_need_explicit_handoffs_and_resolution(
    mode: DelegationJoinMode,
    child_count: int,
    required: int,
    quorum: int | None,
    engine_dependencies: EngineDependencies,
    event_store: MemoryEventStore,
) -> None:
    _seed_parent(event_store)
    engine = RuntimeEngine(engine_dependencies)
    children = tuple(RunId(value=f"join_child_{index}") for index in range(child_count))
    for child_id in children:
        _establish(engine, child_id)
    wait_id = WaitId(value=f"join_{mode.value}")
    opened = asyncio.run(
        engine.submit(
            _parent_command(
                "open-join",
                OpenJoinWaitOperation(
                    wait_id=wait_id,
                    target_run_ids=children,
                    mode=mode,
                    quorum=quorum,
                    outcome_filter="completed_only",
                    failure_policy="wait_for_all_terminal",
                    on_satisfied="keep_bound",
                    late_handoff_policy="surface",
                ),
            )
        )
    )
    early = asyncio.run(
        engine.submit(
            _parent_command(
                "resolve-early",
                ResolveJoinWaitOperation(wait_id=wait_id),
            )
        )
    )
    assert isinstance(opened.decision, AcceptedCommandDecision)
    assert isinstance(early.decision, RejectedCommandDecision)
    assert early.decision.reason == "join_not_satisfied"

    for child_id in children[:required]:
        _complete_child(engine, child_id)
        child_only = asyncio.run(event_store.read(PARENT_ID))
        child_only_replay = rebuild_views(
            child_only.events,
            watermark=child_only.next_position - 1,
        )
        assert isinstance(child_only_replay, CompleteViewReplay)
        assert child_only_replay.views.delegation.delegated_runs[child_id].terminal is None
        handed_off = _handoff(engine, child_id, f"handoff-{child_id.value}")
        assert isinstance(handed_off.decision, AcceptedCommandDecision)

    resolved = asyncio.run(
        engine.submit(_parent_command("resolve", ResolveJoinWaitOperation(wait_id=wait_id)))
    )
    duplicate_handoff = _handoff(engine, children[0], "handoff-duplicate")
    assert isinstance(resolved.decision, AcceptedCommandDecision)
    assert isinstance(duplicate_handoff.decision, RejectedCommandDecision)
    assert duplicate_handoff.decision.reason == "delegation_already_terminal"

    parent = asyncio.run(event_store.read(PARENT_ID))
    replay = rebuild_views(parent.events, watermark=parent.next_position - 1)
    assert isinstance(replay, CompleteViewReplay)
    assert replay.views.run_status.status == "running"
    assert replay.views.waits.joins.pending == ()


@pytest.mark.parametrize(
    ("policy", "accepted", "target_count"),
    (
        ("ignore", False, 0),
        ("surface", True, 1),
        ("add_to_context", True, 2),
    ),
)
def test_late_handoff_policy_never_resurrects_terminal_parent(
    policy: Literal["ignore", "surface", "add_to_context"],
    accepted: bool,
    target_count: int,
    engine_dependencies: EngineDependencies,
    event_store: MemoryEventStore,
) -> None:
    _seed_parent(event_store)
    engine = RuntimeEngine(engine_dependencies)
    child_id = RunId(value=f"late_{policy}")
    _establish(engine, child_id, policy=policy)
    parent_completed = asyncio.run(
        engine.submit(
            _parent_command(
                "complete-parent",
                CompleteRunOperation(result=RunResult(kind="parent")),
            )
        )
    )
    _complete_child(engine, child_id)
    handoff = _handoff(engine, child_id, "late-handoff")

    assert isinstance(parent_completed.decision, AcceptedCommandDecision)
    if accepted:
        assert isinstance(handoff.decision, AcceptedCommandDecision)
        assert len(handoff.decision.result_event_ids) == target_count
    else:
        assert isinstance(handoff.decision, RejectedCommandDecision)
        assert handoff.decision.reason == "late_handoff_ignored"

    parent = asyncio.run(event_store.read(PARENT_ID))
    replay = rebuild_views(parent.events, watermark=parent.next_position - 1)
    assert isinstance(replay, CompleteViewReplay)
    assert replay.views.run_status.status == "completed"
    terminal = replay.views.delegation.delegated_runs[child_id].terminal
    assert (terminal is not None) is accepted
    annotations = tuple(
        event.payload
        for event in parent.events
        if isinstance(event.payload, CanonicalAnnotationRecordedPayload)
    )
    assert bool(annotations) is (policy == "add_to_context")


def test_parent_cancellation_cancels_only_contract_bound_children_atomically(
    engine_dependencies: EngineDependencies,
    event_store: MemoryEventStore,
) -> None:
    _seed_parent(event_store)
    engine = RuntimeEngine(engine_dependencies)
    cancel_child = RunId(value="cancel_child")
    detach_child = RunId(value="detach_child")
    _establish(engine, cancel_child, on_parent_cancel="cancel")
    _establish(engine, detach_child, on_parent_cancel="detach")

    cancelled = asyncio.run(
        engine.submit(
            _parent_command(
                "cancel-parent",
                CancelRunOperation(reason="operator cancelled parent"),
            )
        )
    )

    assert isinstance(cancelled.decision, AcceptedCommandDecision)
    assert len(cancelled.decision.result_event_ids) == 3
    parent = asyncio.run(event_store.read(PARENT_ID))
    cancelled_child = asyncio.run(event_store.read(cancel_child))
    detached_child = asyncio.run(event_store.read(detach_child))
    parent_replay = rebuild_views(parent.events, watermark=parent.next_position - 1)
    cancelled_replay = rebuild_views(
        cancelled_child.events,
        watermark=cancelled_child.next_position - 1,
    )
    detached_replay = rebuild_views(
        detached_child.events,
        watermark=detached_child.next_position - 1,
    )
    assert isinstance(parent_replay, CompleteViewReplay)
    assert isinstance(cancelled_replay, CompleteViewReplay)
    assert isinstance(detached_replay, CompleteViewReplay)
    assert parent_replay.views.run_status.status == "cancelled"
    assert cancelled_replay.views.run_status.status == "cancelled"
    assert detached_replay.views.run_status.status == "running"
    parent_cancelled = parent_replay.views.delegation.delegated_runs[cancel_child]
    parent_detached = parent_replay.views.delegation.delegated_runs[detach_child]
    assert parent_cancelled.status == "cancelled"
    assert parent_detached.status == "running"
    assert parent_cancelled.terminal is not None
    assert isinstance(parent_cancelled.terminal.payload, DelegationCancelledPayload)
    assert not any(isinstance(event.payload, DelegationCompletedPayload) for event in parent.events)


def test_failure_and_cancellation_handoffs_must_match_child_terminal_evidence(
    engine_dependencies: EngineDependencies,
    event_store: MemoryEventStore,
) -> None:
    _seed_parent(event_store)
    engine = RuntimeEngine(engine_dependencies)
    failed_child = RunId(value="failed_child")
    cancelled_child = RunId(value="cancelled_child")
    _establish(engine, failed_child)
    _establish(engine, cancelled_child)
    asyncio.run(
        engine.submit(
            _child_command(
                failed_child,
                "fail-child",
                FailRunOperation(message="actual child failure"),
            )
        )
    )
    asyncio.run(
        engine.submit(
            _child_command(
                cancelled_child,
                "cancel-child",
                CancelRunOperation(reason="actual child cancellation"),
            )
        )
    )

    false_failure = asyncio.run(
        engine.submit(
            _parent_command(
                "false-failure",
                FailDelegationOperation(
                    delegated_run_id=failed_child,
                    message="sanitized claim",
                ),
            )
        )
    )
    false_cancellation = asyncio.run(
        engine.submit(
            _parent_command(
                "false-cancellation",
                CancelDelegationOperation(
                    delegated_run_id=cancelled_child,
                    reason="different reason",
                ),
            )
        )
    )
    exact_failure = asyncio.run(
        engine.submit(
            _parent_command(
                "exact-failure",
                FailDelegationOperation(
                    delegated_run_id=failed_child,
                    message="actual child failure",
                ),
            )
        )
    )
    exact_cancellation = asyncio.run(
        engine.submit(
            _parent_command(
                "exact-cancellation",
                CancelDelegationOperation(
                    delegated_run_id=cancelled_child,
                    reason="actual child cancellation",
                ),
            )
        )
    )

    assert isinstance(false_failure.decision, RejectedCommandDecision)
    assert false_failure.decision.reason == "delegation_failure_evidence_mismatch"
    assert isinstance(false_cancellation.decision, RejectedCommandDecision)
    assert false_cancellation.decision.reason == "delegation_cancellation_evidence_mismatch"
    assert isinstance(exact_failure.decision, AcceptedCommandDecision)
    assert isinstance(exact_cancellation.decision, AcceptedCommandDecision)
    parent = asyncio.run(event_store.read(PARENT_ID))
    failures = tuple(
        event.payload
        for event in parent.events
        if isinstance(event.payload, DelegationFailedPayload)
    )
    cancellations = tuple(
        event.payload
        for event in parent.events
        if isinstance(event.payload, DelegationCancelledPayload)
        and event.payload.delegated_run_id == cancelled_child
    )
    assert tuple(item.message for item in failures) == ("actual child failure",)
    assert tuple(item.reason for item in cancellations) == ("actual child cancellation",)
