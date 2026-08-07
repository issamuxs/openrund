from __future__ import annotations

import asyncio

from openrund._testing.memory import MemoryEventStore
from openrund.contracts.capabilities import ActionReliability
from openrund.contracts.commands import (
    AcceptedCommandDecision,
    Command,
    CommandOrigin,
    CompleteRunOperation,
    RejectedCommandDecision,
)
from openrund.contracts.content import Content, RunResult
from openrund.contracts.events import (
    ActionUnknownPayload,
    ArtifactMetadataCreatedPayload,
    CheckRecordedReportPayload,
    CoreEventType,
    ReconciliationWaitCreatedPayload,
    RunCreatedPayload,
    RunStartedPayload,
)
from openrund.contracts.ids import (
    ActionId,
    ArtifactId,
    CheckId,
    CommandId,
    RunId,
    WaitId,
)
from openrund.contracts.json import JsonObject, freeze_json
from openrund.contracts.runs import CheckStatus
from openrund.engine import EngineDependencies, RuntimeEngine
from openrund.ports.events import AppendEventsInput
from tests.engine.conftest import runtime_event

RUN_ID = RunId(value="run_1")


def _json(value: object) -> JsonObject:
    frozen = freeze_json(value)
    assert isinstance(frozen, JsonObject)
    return frozen


def _metadata() -> JsonObject:
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


def _check(source_status: str) -> CheckRecordedReportPayload:
    return CheckRecordedReportPayload(
        check_id=CheckId(value="check_1"),
        subject=RUN_ID.value,
        rule="completion",
        status=CheckStatus.PASSED if source_status == "passed" else CheckStatus.FAILED,
        validator="pytest",
        summary="checks",
        check_count=2,
        result=Content(
            data=_json(
                {
                    "checks": [
                        {"check": "tests_passed", "status": "passed"},
                        {"check": "source_coverage", "status": source_status},
                    ]
                }
            )
        ),
    )


def _artifact(position: int, kind: str) -> object:
    return runtime_event(
        CoreEventType.ARTIFACT_CREATED,
        ArtifactMetadataCreatedPayload(
            artifact_id=ArtifactId(value=f"artifact_{kind}"),
            kind=kind,
            metadata=_json({}),
        ),
        position,
    )


def _complete_command() -> Command:
    return Command(
        command_id=CommandId(value="complete"),
        run_id=RUN_ID,
        origin=CommandOrigin.SYSTEM,
        operation=CompleteRunOperation(result=RunResult(kind="answer", summary="done")),
    )


def _seed(event_store: MemoryEventStore, events: tuple[object, ...]) -> None:
    asyncio.run(
        event_store.append(
            AppendEventsInput(
                run_id=RUN_ID,
                expected_position=0,
                events=events,  # type: ignore[arg-type]
            )
        )
    )


def test_completion_rejection_reports_every_current_blocker(
    engine_dependencies: EngineDependencies,
    event_store: MemoryEventStore,
) -> None:
    events = (
        runtime_event(
            CoreEventType.RUN_CREATED,
            RunCreatedPayload(root_id=RUN_ID, initial_status="created", metadata=_metadata()),
            1,
        ),
        runtime_event(CoreEventType.RUN_STARTED, RunStartedPayload(), 2),
        runtime_event(
            CoreEventType.WAIT_CREATED,
            ReconciliationWaitCreatedPayload(
                wait_id=WaitId(value="wait_1"),
                action_id=ActionId(value="action_1"),
            ),
            3,
        ),
        runtime_event(
            CoreEventType.ACTION_UNKNOWN,
            ActionUnknownPayload(
                action_id=ActionId(value="action_1"),
                reliability=ActionReliability.IDEMPOTENT_MUTATION,
                reason="worker lost",
            ),
            4,
        ),
        runtime_event(CoreEventType.CHECK_RECORDED, _check("failed"), 5),
        _artifact(6, "report"),
    )
    _seed(event_store, events)

    result = asyncio.run(RuntimeEngine(engine_dependencies).submit(_complete_command()))
    history = asyncio.run(event_store.read(RUN_ID))

    assert isinstance(result.decision, RejectedCommandDecision)
    assert result.decision.reason == "completion_blocked"
    assert tuple(entry.reason for entry in result.decision.trace) == (
        "completion_pending_wait",
        "completion_missing_artifact",
        "completion_unknown_action_outcome",
        "completion_unsatisfied_check",
    )
    assert tuple(entry.related_entity_ids for entry in result.decision.trace) == (
        ("wait_1",),
        ("bundle",),
        ("action_1",),
        ("source_coverage",),
    )
    assert history.events[-1].event_type is CoreEventType.COMMAND_RECORDED


def test_completion_succeeds_only_after_all_requirements_are_present(
    engine_dependencies: EngineDependencies,
    event_store: MemoryEventStore,
) -> None:
    events = (
        runtime_event(
            CoreEventType.RUN_CREATED,
            RunCreatedPayload(root_id=RUN_ID, initial_status="created", metadata=_metadata()),
            1,
        ),
        runtime_event(CoreEventType.RUN_STARTED, RunStartedPayload(), 2),
        runtime_event(CoreEventType.CHECK_RECORDED, _check("passed"), 3),
        _artifact(4, "report"),
        _artifact(5, "bundle"),
    )
    _seed(event_store, events)

    result = asyncio.run(RuntimeEngine(engine_dependencies).submit(_complete_command()))
    history = asyncio.run(event_store.read(RUN_ID))

    assert isinstance(result.decision, AcceptedCommandDecision)
    assert history.events[-1].event_type is CoreEventType.RUN_COMPLETED
