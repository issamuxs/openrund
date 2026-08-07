from __future__ import annotations

import asyncio

from openrund._testing.memory import MemoryEventStore
from openrund.contracts.commands import (
    AcceptedCommandDecision,
    Command,
    CommandOrigin,
    CompleteRunOperation,
    CreateCheckpointOperation,
    RecordAnnotationOperation,
    RecordCheckOperation,
    RejectedCommandDecision,
)
from openrund.contracts.content import Content, RunResult
from openrund.contracts.events import CoreEventType, RunCreatedPayload, RunStartedPayload
from openrund.contracts.ids import (
    AnnotationId,
    ArtifactId,
    CheckId,
    CheckpointId,
    CommandId,
    RunId,
)
from openrund.contracts.json import JsonObject, freeze_json
from openrund.contracts.runs import CheckStatus
from openrund.engine import EngineDependencies, RuntimeEngine
from openrund.ports.events import AppendEventsInput
from openrund.views import CompleteViewReplay, rebuild_views
from tests.engine.conftest import runtime_event

RUN_ID = RunId(value="run_1")


def _json(value: object) -> JsonObject:
    frozen = freeze_json(value)
    assert isinstance(frozen, JsonObject)
    return frozen


def _command(
    command_id: str,
    operation: object,
    *,
    origin: CommandOrigin = CommandOrigin.OPERATOR,
) -> Command:
    return Command(
        command_id=CommandId(value=command_id),
        run_id=RUN_ID,
        origin=origin,
        operation=operation,  # type: ignore[arg-type]
    )


def _seed(event_store: MemoryEventStore) -> None:
    events = (
        runtime_event(
            CoreEventType.RUN_CREATED,
            RunCreatedPayload(
                root_id=RUN_ID,
                initial_status="created",
                metadata=_json({"run_contract": {"check": {"checks": ["quality"]}}}),
            ),
            1,
        ),
        runtime_event(CoreEventType.RUN_STARTED, RunStartedPayload(), 2),
    )
    asyncio.run(
        event_store.append(AppendEventsInput(run_id=RUN_ID, expected_position=0, events=events))
    )


def _check(check_id: str, name: str, status: str = "passed") -> RecordCheckOperation:
    return RecordCheckOperation(
        check_id=CheckId(value=check_id),
        subject="run",
        rule=name,
        status=CheckStatus.PASSED,
        validator="fixture-validator",
        summary=f"{name} checked",
        check_count=1,
        result=Content(data=_json({"checks": [{"check": name, "status": status}]})),
    )


def test_only_trusted_named_semantic_check_unblocks_completion(
    engine_dependencies: EngineDependencies,
    event_store: MemoryEventStore,
) -> None:
    _seed(event_store)
    engine = RuntimeEngine(engine_dependencies)
    annotation = asyncio.run(
        engine.submit(
            _command(
                "annotation",
                RecordAnnotationOperation(
                    annotation_id=AnnotationId(value="note_1"),
                    content=Content(preview="diagnostic note"),
                ),
            )
        )
    )
    checkpoint = asyncio.run(
        engine.submit(
            _command(
                "checkpoint",
                CreateCheckpointOperation(
                    checkpoint_id=CheckpointId(value="checkpoint_1"),
                    from_position=1,
                    to_position=4,
                    summary="retain annotation",
                    protected_event_types=(CoreEventType.ANNOTATION_RECORDED.value,),
                ),
            )
        )
    )
    diagnostic = asyncio.run(engine.submit(_command("diagnostic", _check("check_1", "diagnostic"))))
    model_self_certification = asyncio.run(
        engine.submit(
            _command(
                "model-check",
                _check("check_2", "quality"),
                origin=CommandOrigin.MODEL,
            )
        )
    )
    blocked = asyncio.run(
        engine.submit(_command("blocked", CompleteRunOperation(result=RunResult(kind="test"))))
    )
    semantic = asyncio.run(engine.submit(_command("semantic", _check("check_3", "quality"))))

    assert isinstance(annotation.decision, AcceptedCommandDecision)
    assert isinstance(checkpoint.decision, AcceptedCommandDecision)
    assert isinstance(diagnostic.decision, AcceptedCommandDecision)
    assert isinstance(model_self_certification.decision, RejectedCommandDecision)
    assert model_self_certification.decision.reason == "check_origin_forbidden"
    assert isinstance(blocked.decision, RejectedCommandDecision)
    assert blocked.decision.reason == "completion_blocked"
    assert isinstance(semantic.decision, AcceptedCommandDecision)

    history = asyncio.run(event_store.read(RUN_ID))
    replay = rebuild_views(history.events, watermark=history.next_position - 1)
    assert isinstance(replay, CompleteViewReplay)
    assert len(replay.views.reports) == 2
    assert len(replay.views.checkpoints.active_checkpoints) == 1
    readiness = replay.views.run_status.completion_readiness
    assert readiness.ready
    assert tuple(item.name for item in readiness.semantic_checks) == ("quality",)
    assert tuple(item.name for item in readiness.diagnostic_checks) == ("diagnostic",)

    completed = asyncio.run(
        engine.submit(_command("complete", CompleteRunOperation(result=RunResult(kind="test"))))
    )
    assert isinstance(completed.decision, AcceptedCommandDecision)


def test_malformed_or_unlinked_explanatory_evidence_rejects(
    engine_dependencies: EngineDependencies,
    event_store: MemoryEventStore,
) -> None:
    _seed(event_store)
    engine = RuntimeEngine(engine_dependencies)

    bad_count = asyncio.run(
        engine.submit(
            _command(
                "bad-count",
                RecordCheckOperation(
                    subject="run",
                    rule="quality",
                    status=CheckStatus.PASSED,
                    validator="validator",
                    summary="wrong count",
                    check_count=2,
                    result=Content(
                        data=_json({"checks": [{"check": "quality", "status": "passed"}]})
                    ),
                ),
            )
        )
    )
    bad_range = asyncio.run(
        engine.submit(
            _command(
                "bad-range",
                CreateCheckpointOperation(from_position=1, to_position=99),
            )
        )
    )
    missing_artifact = asyncio.run(
        engine.submit(
            _command(
                "missing-artifact",
                RecordAnnotationOperation(
                    content=Content(artifact_ids=(ArtifactId(value="missing"),))
                ),
            )
        )
    )

    assert isinstance(bad_count.decision, RejectedCommandDecision)
    assert bad_count.decision.reason == "check_count_mismatch"
    assert isinstance(bad_range.decision, RejectedCommandDecision)
    assert bad_range.decision.reason == "checkpoint_range_out_of_bounds"
    assert isinstance(missing_artifact.decision, RejectedCommandDecision)
    assert missing_artifact.decision.reason == "artifact_not_found"
