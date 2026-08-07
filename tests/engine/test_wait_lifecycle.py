from __future__ import annotations

import asyncio

import pytest

from openrund._testing.memory import MemoryEventStore
from openrund.contracts.commands import (
    AcceptedCommandDecision,
    CancelWaitOperation,
    Command,
    CommandOrigin,
    ExpireWaitOperation,
    FireTimerWaitOperation,
    OpenApprovalWaitOperation,
    OpenInteractionWaitOperation,
    OpenTimerWaitOperation,
    RejectedCommandDecision,
    ResolveApprovalOperation,
    ResolveInteractionWaitOperation,
    ResolveJoinWaitOperation,
)
from openrund.contracts.content import Content
from openrund.contracts.events import (
    ApprovalWaitCreatedPayload,
    CoreEventType,
    DelegationCompletedPayload,
    EventPayload,
    InteractionWaitCreatedPayload,
    JoinWaitCreatedPayload,
    ReconciliationWaitCreatedPayload,
    RunCreatedPayload,
    RunStartedPayload,
    TimerWaitCreatedPayload,
)
from openrund.contracts.ids import ActionId, CapabilityId, CommandId, RunId, WaitId
from openrund.contracts.runs import DelegationJoinMode, WaitKind
from openrund.contracts.time import Timestamp
from openrund.engine import EngineDependencies, RuntimeEngine
from openrund.ports.events import AppendEventsInput
from openrund.views import CompleteViewReplay, rebuild_views
from tests.engine.conftest import runtime_event

RUN_ID = RunId(value="run_1")


def _command(command_id: str, operation: object) -> Command:
    return Command(
        command_id=CommandId(value=command_id),
        run_id=RUN_ID,
        origin=CommandOrigin.OPERATOR,
        operation=operation,  # type: ignore[arg-type]
    )


def _seed(
    event_store: MemoryEventStore,
    *payloads: tuple[CoreEventType, EventPayload],
) -> None:
    events = (
        runtime_event(
            CoreEventType.RUN_CREATED,
            RunCreatedPayload(root_id=RUN_ID, initial_status="created"),
            1,
        ),
        runtime_event(CoreEventType.RUN_STARTED, RunStartedPayload(), 2),
        *(
            runtime_event(event_type, payload, index)
            for index, (event_type, payload) in enumerate(payloads, start=3)
        ),
    )
    asyncio.run(
        event_store.append(
            AppendEventsInput(
                run_id=RUN_ID,
                expected_position=0,
                events=events,
            )
        )
    )


def test_open_interaction_timer_and_approval_waits_through_engine(
    engine_dependencies: EngineDependencies,
    event_store: MemoryEventStore,
) -> None:
    _seed(event_store)
    engine = RuntimeEngine(engine_dependencies)
    interaction = WaitId(value="interaction")
    timer = WaitId(value="timer")
    approval = WaitId(value="approval")

    results = (
        asyncio.run(
            engine.submit(
                _command(
                    "open-interaction",
                    OpenInteractionWaitOperation(
                        wait_id=interaction,
                        prompt="Choose a value",
                        deadline=Timestamp(value="2026-08-05T13:00:00.000Z"),
                    ),
                )
            )
        ),
        asyncio.run(
            engine.submit(
                _command(
                    "open-timer",
                    OpenTimerWaitOperation(
                        wait_id=timer,
                        fire_at=Timestamp(value="2026-08-05T13:00:00.000Z"),
                    ),
                )
            )
        ),
        asyncio.run(
            engine.submit(
                _command(
                    "open-approval",
                    OpenApprovalWaitOperation(
                        wait_id=approval,
                        target="filesystem.write",
                        reason="write requires approval",
                        action_id=ActionId(value="action_1"),
                        capability_id=CapabilityId(value="filesystem"),
                        action_name="write",
                        request_payload=Content(preview="write report.md"),
                        policy_snapshot=Content(preview="approval required"),
                    ),
                )
            )
        ),
    )

    assert all(isinstance(result.decision, AcceptedCommandDecision) for result in results)
    history = asyncio.run(event_store.read(RUN_ID))
    replay = rebuild_views(history.events, watermark=history.next_position - 1)
    assert isinstance(replay, CompleteViewReplay)
    assert tuple(wait.wait_id for wait in replay.views.waits.all_pending) == (
        interaction,
        timer,
        approval,
    )
    assert replay.views.run_status.status == "waiting"


def test_interaction_and_approval_resolve_once(
    engine_dependencies: EngineDependencies,
    event_store: MemoryEventStore,
) -> None:
    interaction = WaitId(value="interaction")
    approval = WaitId(value="approval")
    _seed(
        event_store,
        (
            CoreEventType.WAIT_CREATED,
            InteractionWaitCreatedPayload(
                wait_id=interaction,
                prompt=Content(preview="Question"),
            ),
        ),
        (
            CoreEventType.WAIT_CREATED,
            ApprovalWaitCreatedPayload(
                wait_id=approval,
                action_id=ActionId(value="action_1"),
                capability_id=CapabilityId(value="filesystem"),
                action_name="write",
                request_payload=Content(),
                policy_snapshot=Content(),
            ),
        ),
    )
    engine = RuntimeEngine(engine_dependencies)

    first = asyncio.run(
        engine.submit(
            _command(
                "resolve-interaction",
                ResolveInteractionWaitOperation(
                    wait_id=interaction,
                    response=Content(preview="Answer"),
                ),
            )
        )
    )
    approval_result = asyncio.run(
        engine.submit(
            _command(
                "resolve-approval",
                ResolveApprovalOperation(wait_id=approval, decision="denied"),
            )
        )
    )
    duplicate = asyncio.run(
        engine.submit(
            _command(
                "resolve-interaction-again",
                ResolveInteractionWaitOperation(
                    wait_id=interaction,
                    response=Content(preview="Other"),
                ),
            )
        )
    )

    assert isinstance(first.decision, AcceptedCommandDecision)
    assert isinstance(approval_result.decision, AcceptedCommandDecision)
    assert isinstance(duplicate.decision, RejectedCommandDecision)
    assert duplicate.decision.reason == "wait_terminal"


def test_timer_rejects_early_fire_and_expiry_but_accepts_due_timer(
    engine_dependencies: EngineDependencies,
    event_store: MemoryEventStore,
) -> None:
    early = WaitId(value="early")
    due = WaitId(value="due")
    _seed(
        event_store,
        (
            CoreEventType.WAIT_CREATED,
            TimerWaitCreatedPayload(
                wait_id=early,
                fire_at=Timestamp(value="2026-08-05T13:00:00.000Z"),
            ),
        ),
        (
            CoreEventType.WAIT_CREATED,
            TimerWaitCreatedPayload(
                wait_id=due,
                fire_at=Timestamp(value="2026-08-05T11:00:00.000Z"),
            ),
        ),
    )
    engine = RuntimeEngine(engine_dependencies)

    early_fire = asyncio.run(
        engine.submit(_command("fire-early", FireTimerWaitOperation(wait_id=early)))
    )
    early_expiry = asyncio.run(
        engine.submit(
            _command(
                "expire-early",
                ExpireWaitOperation(wait_id=early, wait_kind=WaitKind.TIMER),
            )
        )
    )
    due_fire = asyncio.run(engine.submit(_command("fire-due", FireTimerWaitOperation(wait_id=due))))

    assert isinstance(early_fire.decision, RejectedCommandDecision)
    assert early_fire.decision.reason == "timer_not_due"
    assert isinstance(early_expiry.decision, RejectedCommandDecision)
    assert early_expiry.decision.reason == "wait_not_expired"
    assert isinstance(due_fire.decision, AcceptedCommandDecision)


@pytest.mark.parametrize(
    ("kind", "payload"),
    [
        (
            WaitKind.APPROVAL,
            ApprovalWaitCreatedPayload(
                wait_id=WaitId(value="wait"),
                action_id=ActionId(value="action"),
                capability_id=CapabilityId(value="capability"),
                action_name="write",
                request_payload=Content(),
                policy_snapshot=Content(),
            ),
        ),
        (
            WaitKind.INTERACTION,
            InteractionWaitCreatedPayload(wait_id=WaitId(value="wait"), prompt=Content()),
        ),
        (
            WaitKind.TIMER,
            TimerWaitCreatedPayload(
                wait_id=WaitId(value="wait"),
                fire_at=Timestamp(value="2026-08-05T11:00:00.000Z"),
            ),
        ),
        (
            WaitKind.JOIN,
            JoinWaitCreatedPayload(
                wait_id=WaitId(value="wait"),
                target_run_ids=(RunId(value="child"),),
                mode=DelegationJoinMode.ALL,
                outcome_filter="completed_only",
                failure_policy="wait_for_all_terminal",
                on_satisfied="keep_bound",
                late_handoff_policy="ignore",
            ),
        ),
        (
            WaitKind.RECONCILIATION,
            ReconciliationWaitCreatedPayload(wait_id=WaitId(value="wait")),
        ),
    ],
)
def test_every_wait_kind_can_be_cancelled_exactly_once(
    kind: WaitKind,
    payload: EventPayload,
    engine_dependencies: EngineDependencies,
    event_store: MemoryEventStore,
) -> None:
    _seed(event_store, (CoreEventType.WAIT_CREATED, payload))
    engine = RuntimeEngine(engine_dependencies)
    operation = CancelWaitOperation(wait_id=WaitId(value="wait"), wait_kind=kind)

    first = asyncio.run(engine.submit(_command("cancel", operation)))
    second = asyncio.run(engine.submit(_command("cancel-again", operation)))

    assert isinstance(first.decision, AcceptedCommandDecision)
    assert isinstance(second.decision, RejectedCommandDecision)
    assert second.decision.reason == "wait_terminal"


def test_satisfied_join_requires_explicit_resolution_command(
    engine_dependencies: EngineDependencies,
    event_store: MemoryEventStore,
) -> None:
    wait_id = WaitId(value="join")
    child = RunId(value="child")
    _seed(
        event_store,
        (
            CoreEventType.WAIT_CREATED,
            JoinWaitCreatedPayload(
                wait_id=wait_id,
                target_run_ids=(child,),
                mode=DelegationJoinMode.ALL,
                outcome_filter="completed_only",
                failure_policy="wait_for_all_terminal",
                on_satisfied="keep_bound",
                late_handoff_policy="ignore",
            ),
        ),
        (
            CoreEventType.DELEGATION_COMPLETED,
            DelegationCompletedPayload(delegated_run_id=child),
        ),
    )
    engine = RuntimeEngine(engine_dependencies)
    before = asyncio.run(event_store.read(RUN_ID))
    before_replay = rebuild_views(before.events, watermark=before.next_position - 1)
    assert isinstance(before_replay, CompleteViewReplay)
    assert before_replay.views.delegation.joins[wait_id].satisfied is True
    assert before_replay.views.waits.joins.pending[0].wait_id == wait_id

    result = asyncio.run(
        engine.submit(_command("resolve-join", ResolveJoinWaitOperation(wait_id=wait_id)))
    )

    assert isinstance(result.decision, AcceptedCommandDecision)
    after = asyncio.run(event_store.read(RUN_ID))
    after_replay = rebuild_views(after.events, watermark=after.next_position - 1)
    assert isinstance(after_replay, CompleteViewReplay)
    assert after_replay.views.waits.joins.pending == ()
