from __future__ import annotations

from typing import cast

from openrund.contracts.commands import (
    AcceptedCommandDecision,
    AddMessageOperation,
    BootstrapRunOperation,
    CancelRunOperation,
    Command,
    CommandOrigin,
    CompleteRunOperation,
    RejectedCommandDecision,
    StartRunOperation,
)
from openrund.contracts.content import Content, RunResult
from openrund.contracts.events import (
    CoreEventType,
    RunCompletedPayload,
    RunCreatedPayload,
    RunStartedPayload,
    RuntimeEvent,
)
from openrund.contracts.ids import CommandId, RunId
from openrund.engine._legality import evaluate_command
from openrund.views import CompleteViewReplay, RunViewBundle, rebuild_views
from tests.engine.conftest import runtime_event

RUN_ID = RunId(value="run_1")


def _command(operation: object) -> Command:
    return Command(
        command_id=CommandId(value="command_1"),
        run_id=RUN_ID,
        origin=CommandOrigin.SYSTEM,
        operation=operation,  # type: ignore[arg-type]
    )


def _replay(events: tuple[RuntimeEvent, ...]) -> CompleteViewReplay[RunViewBundle]:
    rebuilt = rebuild_views(events, watermark=len(events))
    return cast(CompleteViewReplay[RunViewBundle], rebuilt)


def _running() -> tuple[RuntimeEvent, ...]:
    return (
        runtime_event(
            CoreEventType.RUN_CREATED,
            RunCreatedPayload(root_id=RUN_ID, initial_status="created"),
            1,
        ),
        runtime_event(CoreEventType.RUN_STARTED, RunStartedPayload(), 2),
    )


def test_only_bootstrap_is_legal_before_run_exists() -> None:
    replay = _replay(())
    bootstrap = _command(BootstrapRunOperation(root_id=RUN_ID))
    add_message = _command(AddMessageOperation(message=Content(preview="hello")))

    assert isinstance(evaluate_command(bootstrap, replay, ()), AcceptedCommandDecision)
    rejected = evaluate_command(add_message, replay, ())
    assert isinstance(rejected, RejectedCommandDecision)
    assert rejected.reason == "run_not_found"


def test_created_run_allows_start_fail_or_cancel_only() -> None:
    events = _running()[:1]
    replay = _replay(events)

    assert isinstance(
        evaluate_command(_command(StartRunOperation()), replay, events),
        AcceptedCommandDecision,
    )
    assert isinstance(
        evaluate_command(_command(CancelRunOperation()), replay, events),
        AcceptedCommandDecision,
    )
    rejected = evaluate_command(
        _command(AddMessageOperation(message=Content(preview="early"))), replay, events
    )
    assert isinstance(rejected, RejectedCommandDecision)
    assert rejected.reason == "run_not_started"


def test_running_run_allows_completion_when_no_blockers_exist() -> None:
    events = _running()
    decision = evaluate_command(
        _command(CompleteRunOperation(result=RunResult(kind="answer"))),
        _replay(events),
        events,
    )

    assert isinstance(decision, AcceptedCommandDecision)
    assert decision.trace[0].reason == "completion_allowed"


def test_terminal_run_rejects_every_later_mutation() -> None:
    events = (
        *_running(),
        runtime_event(CoreEventType.RUN_COMPLETED, RunCompletedPayload(), 3),
    )
    replay = _replay(events)
    for operation in (
        StartRunOperation(),
        AddMessageOperation(message=Content(preview="late")),
        CancelRunOperation(),
        BootstrapRunOperation(root_id=RUN_ID),
    ):
        decision = evaluate_command(_command(operation), replay, events)
        assert isinstance(decision, RejectedCommandDecision)
        assert decision.reason == "run_terminal"
