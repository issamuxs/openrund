from __future__ import annotations

import asyncio
from dataclasses import replace

import pytest

from openrund._testing.memory import MemoryEventStore
from openrund.contracts.commands import (
    AcceptedCommandDecision,
    Command,
    CommandOrigin,
    CompleteRunOperation,
    CreateDelegationOperation,
    RejectedCommandDecision,
)
from openrund.contracts.content import RunResult
from openrund.contracts.events import (
    CapabilityAuthorityGrantedPayload,
    CoreEventType,
    RunCreatedPayload,
    RunStartedPayload,
)
from openrund.contracts.ids import (
    AuthorityId,
    CapabilityId,
    CommandId,
    EventId,
    RunId,
)
from openrund.contracts.json import JsonObject, freeze_json
from openrund.contracts.runs import (
    AuthorityGrant,
    DelegatedRunKind,
    DelegationBudget,
    DelegationContract,
    DelegationInput,
)
from openrund.engine import EngineDependencies, RuntimeEngine
from openrund.ports.events import AppendEventsInput
from openrund.views import CompleteViewReplay, rebuild_views
from tests.engine.conftest import runtime_event

PARENT_ID = RunId(value="run_1")
CHILD_ID = RunId(value="child_explicit")


def _json(value: object) -> JsonObject:
    frozen = freeze_json(value)
    assert isinstance(frozen, JsonObject)
    return frozen


def _contract(
    *,
    capability: str = "filesystem",
    actions: tuple[str, ...] = ("read",),
    max_requests: int = 2,
    allow_nested: bool = False,
    run_kind: DelegatedRunKind = DelegatedRunKind.WORKER,
) -> DelegationContract:
    return DelegationContract(
        run_kind=run_kind,
        objective="Inspect source files",
        authority_grants=(
            AuthorityGrant(
                capability_id=CapabilityId(value=capability),
                actions=actions,
            ),
        ),
        authority_drift="snapshot",
        budget=DelegationBudget(
            max_requests=max_requests,
            wall_clock_timeout_ms=30_000,
        ),
        result_kind="analysis",
        required_artifact_kinds=(),
        allow_nested_delegation=allow_nested,
        on_parent_cancel="cancel",
        late_handoff="surface",
    )


def _command(command_id: str, operation: CreateDelegationOperation) -> Command:
    return Command(
        command_id=CommandId(value=command_id),
        run_id=PARENT_ID,
        origin=CommandOrigin.MODEL,
        operation=operation,
    )


def _seed_parent(
    event_store: MemoryEventStore,
    *,
    parent_run_id: RunId | None = None,
    metadata: JsonObject | None = None,
) -> None:
    events = (
        runtime_event(
            CoreEventType.RUN_CREATED,
            RunCreatedPayload(
                root_id=PARENT_ID if parent_run_id is None else RunId(value="root"),
                initial_status="created",
                parent_run_id=parent_run_id,
                metadata=metadata,
            ),
            1,
        ),
        runtime_event(CoreEventType.RUN_STARTED, RunStartedPayload(), 2),
        runtime_event(
            CoreEventType.AUTHORITY_GRANTED,
            CapabilityAuthorityGrantedPayload(
                capability_id=CapabilityId(value="filesystem"),
                authority_id=AuthorityId(value="parent_authority"),
                constraints=_json(
                    {
                        "actions": ["read"],
                        "writableRoots": ["/workspace"],
                    }
                ),
            ),
            3,
        ),
    )
    asyncio.run(
        event_store.append(AppendEventsInput(run_id=PARENT_ID, expected_position=0, events=events))
    )


def _operation(
    contract: DelegationContract | None = None,
    *,
    child_id: RunId | None = CHILD_ID,
) -> CreateDelegationOperation:
    return CreateDelegationOperation(
        delegated_run_id=child_id,
        contract=_contract() if contract is None else contract,
        input=DelegationInput(data=_json({"path": "README.md"})),
    )


def test_delegation_establishes_parent_and_child_atomically(
    engine_dependencies: EngineDependencies,
    event_store: MemoryEventStore,
) -> None:
    _seed_parent(event_store)
    engine = RuntimeEngine(engine_dependencies)
    command = _command("delegate", _operation())

    result = asyncio.run(engine.submit(command))
    duplicate = asyncio.run(engine.submit(command))

    assert isinstance(result.decision, AcceptedCommandDecision)
    assert duplicate == result
    assert len(result.decision.result_event_ids) == 5
    parent = asyncio.run(event_store.read(PARENT_ID))
    child = asyncio.run(event_store.read(CHILD_ID))
    assert tuple(event.event_type for event in parent.events[-3:]) == (
        CoreEventType.COMMAND_RECORDED,
        CoreEventType.DELEGATION_CREATED,
        CoreEventType.DELEGATION_CREATED,
    )
    assert tuple(event.event_type for event in child.events) == (
        CoreEventType.RUN_CREATED,
        CoreEventType.RUN_STARTED,
        CoreEventType.AUTHORITY_GRANTED,
    )
    assert child.events[0].causation_id == parent.events[-2].event_id
    assert child.events[0].command_id == command.command_id
    assert any(call.operation == "append_many" for call in event_store.calls)

    parent_replay = rebuild_views(parent.events, watermark=parent.next_position - 1)
    child_replay = rebuild_views(child.events, watermark=child.next_position - 1)
    assert isinstance(parent_replay, CompleteViewReplay)
    assert isinstance(child_replay, CompleteViewReplay)
    assert parent_replay.views.delegation.delegated_runs[CHILD_ID].status == "running"
    child_run = child_replay.views.run_status.run
    assert child_run is not None
    assert child_run.root_id == PARENT_ID
    assert child_run.creation.parent_run_id == PARENT_ID
    child_authority = child_replay.views.run_status.capability_authority[
        CapabilityId(value="filesystem")
    ]
    assert child_authority.payload.constraints == _json(
        {"writableRoots": ["/workspace"], "actions": ["read"]}
    )

    child_engine = RuntimeEngine(engine_dependencies)
    wrong_result = asyncio.run(
        child_engine.submit(
            Command(
                command_id=CommandId(value="wrong-result"),
                run_id=CHILD_ID,
                origin=CommandOrigin.SYSTEM,
                operation=CompleteRunOperation(result=RunResult(kind="unexpected")),
            )
        )
    )
    correct_result = asyncio.run(
        child_engine.submit(
            Command(
                command_id=CommandId(value="correct-result"),
                run_id=CHILD_ID,
                origin=CommandOrigin.SYSTEM,
                operation=CompleteRunOperation(result=RunResult(kind="analysis")),
            )
        )
    )
    assert isinstance(wrong_result.decision, RejectedCommandDecision)
    assert wrong_result.decision.reason == "delegation_result_kind_mismatch"
    assert isinstance(correct_result.decision, AcceptedCommandDecision)


@pytest.mark.parametrize(
    ("contract", "reason"),
    (
        (_contract(capability="process"), "delegation_authority_expansion"),
        (_contract(actions=("write",)), "delegation_action_expansion"),
        (
            _contract(allow_nested=True),
            "worker_nested_delegation_forbidden",
        ),
    ),
)
def test_delegation_legality_rejects_authority_or_nesting_expansion(
    contract: DelegationContract,
    reason: str,
    engine_dependencies: EngineDependencies,
    event_store: MemoryEventStore,
) -> None:
    _seed_parent(event_store)
    result = asyncio.run(
        RuntimeEngine(engine_dependencies).submit(_command("invalid", _operation(contract)))
    )

    assert isinstance(result.decision, RejectedCommandDecision)
    assert result.decision.reason == reason
    child = asyncio.run(event_store.read(CHILD_ID))
    assert child.events == ()


def test_nested_child_budget_cannot_expand_parent_contract(
    engine_dependencies: EngineDependencies,
    event_store: MemoryEventStore,
) -> None:
    metadata = _json(
        {
            "delegation_contract": {
                "allow_nested_delegation": True,
                "budget": {
                    "max_requests": 2,
                    "wall_clock_timeout_ms": 30_000,
                },
            }
        }
    )
    _seed_parent(event_store, parent_run_id=RunId(value="parent"), metadata=metadata)
    result = asyncio.run(
        RuntimeEngine(engine_dependencies).submit(
            _command(
                "budget-expansion",
                _operation(
                    _contract(
                        max_requests=3,
                        run_kind=DelegatedRunKind.AGENT,
                    )
                ),
            )
        )
    )

    assert isinstance(result.decision, RejectedCommandDecision)
    assert result.decision.reason == "delegation_request_budget_expansion"
    assert asyncio.run(event_store.read(CHILD_ID)).events == ()


def test_child_collision_and_missing_atomic_custody_fail_closed(
    engine_dependencies: EngineDependencies,
    event_store: MemoryEventStore,
) -> None:
    _seed_parent(event_store)
    asyncio.run(
        event_store.append(
            AppendEventsInput(
                run_id=CHILD_ID,
                expected_position=0,
                events=(
                    replace(
                        runtime_event(
                            CoreEventType.RUN_CREATED,
                            RunCreatedPayload(
                                root_id=CHILD_ID,
                                initial_status="created",
                            ),
                            1,
                            run_id=CHILD_ID,
                        ),
                        event_id=EventId(value="child_history_1"),
                    ),
                ),
            )
        )
    )
    collision = asyncio.run(
        RuntimeEngine(engine_dependencies).submit(_command("collision", _operation()))
    )
    assert isinstance(collision.decision, RejectedCommandDecision)
    assert collision.decision.reason == "delegated_run_already_exists"

    generated_store = MemoryEventStore()
    _seed_parent(generated_store)
    without_atomic = replace(
        engine_dependencies,
        event_store=generated_store,
        atomic_event_store=None,
    )
    unavailable = asyncio.run(
        RuntimeEngine(without_atomic).submit(_command("no-atomic", _operation(child_id=None)))
    )
    assert isinstance(unavailable.decision, RejectedCommandDecision)
    assert unavailable.decision.reason == "atomic_event_store_required"
    assert asyncio.run(generated_store.read(RunId(value="child_1"))).events == ()
