from __future__ import annotations

import json
from dataclasses import FrozenInstanceError
from pathlib import Path
from typing import cast

import pytest

from openrund.contracts.capabilities import ActionOutcome
from openrund.contracts.commands import (
    AcceptedCommandDecision,
    AcceptedDecisionRecord,
    AddMessageOperation,
    CancelRunOperation,
    Command,
    CommandDecisionRecord,
    CommandDecisionTraceEntry,
    CommandOrigin,
    CommandRejectionRecord,
    CommandResult,
    CommandWaitRecord,
    CompleteRunOperation,
    CreateActionOperation,
    CreateCheckpointOperation,
    CreateDelegationOperation,
    DeferredCommandDecision,
    DeferredDecisionRecord,
    FailRunOperation,
    LegalityCriterion,
    LegalityCriterionResult,
    OpenApprovalWaitOperation,
    OpenInteractionWaitOperation,
    OpenJoinWaitOperation,
    OpenTimerWaitOperation,
    OperationBatch,
    RejectedCommandDecision,
    RejectedDecisionRecord,
    SupersededCommandDecision,
    SupersededDecisionRecord,
    TargetEventAbsent,
    TargetEventPresent,
)
from openrund.contracts.content import Content, Mutation, MutationOperationKind, RunResult
from openrund.contracts.ids import (
    ActionId,
    CapabilityId,
    CommandId,
    EventId,
    ModelCallId,
    RunId,
    WaitId,
)
from openrund.contracts.json import JsonObject
from openrund.contracts.runs import (
    DelegatedRunKind,
    DelegationBudget,
    DelegationContract,
    DelegationInput,
    DelegationJoinMode,
    WaitKind,
)
from openrund.contracts.time import Timestamp
from openrund.errors import ValidationError

FIXTURE_MANIFEST = Path(__file__).parents[1] / "fixtures" / "compatibility" / "v1" / "manifest.json"


def trace(
    result: LegalityCriterionResult = LegalityCriterionResult.PASS,
) -> tuple[CommandDecisionTraceEntry, ...]:
    return (
        CommandDecisionTraceEntry(
            criterion=LegalityCriterion.RUN_LIFECYCLE,
            result=result,
            metadata={"checked": True},  # type: ignore[arg-type]
        ),
    )


def delegation_contract() -> DelegationContract:
    return DelegationContract(
        run_kind=DelegatedRunKind.WORKER,
        objective="bounded work",
        authority_grants=(),
        authority_drift="snapshot",
        budget=DelegationBudget(max_requests=1, wall_clock_timeout_ms=1_000),
        result_kind="answer",
        allow_nested_delegation=False,
        on_parent_cancel="cancel",
    )


def test_operation_branches_are_precise_frozen_values() -> None:
    action = CreateActionOperation(
        action_id=ActionId(value="action_1"),
        capability_id=CapabilityId(value="cap_filesystem"),
        action_name="read",
        input=Content(data={"path": "README.md"}),  # type: ignore[arg-type]
        mutation=Mutation(
            affected_resources=({"path": "README.md"},),  # type: ignore[arg-type]
            operation_kind=MutationOperationKind.INSPECT,
        ),
    )
    operations = (
        AddMessageOperation(message=Content(preview="hello")),
        action,
        CreateDelegationOperation(
            delegated_run_id=RunId(value="run_child"),
            contract=delegation_contract(),
            input=DelegationInput(data={"source": "one"}),  # type: ignore[arg-type]
        ),
        OpenApprovalWaitOperation(target="filesystem.write", reason="approval"),
        OpenInteractionWaitOperation(prompt="Need a value"),
        OpenTimerWaitOperation(fire_at=Timestamp(value="2026-08-04T12:00:00.000Z")),
        OpenJoinWaitOperation(
            target_run_ids=(RunId(value="run_child"),),
            mode=DelegationJoinMode.ALL,
            outcome_filter="terminal_any",
            failure_policy="wait_for_all_terminal",
            on_satisfied="keep_bound",
            late_handoff_policy="surface",
        ),
        CreateCheckpointOperation(from_position=1, to_position=2),
        CompleteRunOperation(result=RunResult(kind="answer")),
        FailRunOperation(message="failed", retryable=False),
        CancelRunOperation(reason="operator"),
        OperationBatch(actions=(action,)),
    )

    assert len({operation.kind for operation in operations}) >= 8
    for operation in operations:
        assert not hasattr(operation, "__dict__")
        with pytest.raises((FrozenInstanceError, AttributeError)):
            operation.kind = "changed"  # type: ignore[assignment, misc]
    with pytest.raises(TypeError):
        OpenTimerWaitOperation(prompt="wrong branch")  # type: ignore[call-arg]
    with pytest.raises(ValidationError, match="operation_batch_actions_empty"):
        OperationBatch(actions=())


def test_runtime_decisions_are_normal_values_with_required_reasons() -> None:
    event_id = EventId(value="evt_result")
    wait_id = WaitId(value="wait_approval")
    replacement = CommandId(value="cmd_replacement")
    decisions = (
        AcceptedCommandDecision(trace=trace(), result_event_ids=(event_id,)),
        RejectedCommandDecision(reason="illegal", trace=trace(LegalityCriterionResult.FAIL)),
        DeferredCommandDecision(reason="approval required", trace=trace(), wait_ids=(wait_id,)),
        SupersededCommandDecision(
            reason="already committed",
            trace=trace(),
            superseded_by_command_id=replacement,
        ),
    )

    assert [decision.kind for decision in decisions] == [
        "accepted",
        "rejected",
        "deferred",
        "superseded",
    ]
    assert all(isinstance(decision, object) for decision in decisions)
    with pytest.raises(TypeError):
        RejectedCommandDecision(trace=trace())  # type: ignore[call-arg]
    with pytest.raises(ValidationError, match="command_decision_reason_invalid"):
        DeferredCommandDecision(reason="", trace=trace(), wait_ids=(wait_id,))


def test_command_and_result_retain_exact_typed_linkage() -> None:
    command_id = CommandId(value="cmd_1")
    run_id = RunId(value="run_1")
    decision = AcceptedCommandDecision(trace=trace(), result_event_ids=(EventId(value="evt_1"),))
    command = Command(
        command_id=command_id,
        run_id=run_id,
        origin=CommandOrigin.MODEL,
        operation=AddMessageOperation(message=Content(preview="answer")),
        model_call_id=ModelCallId(value="model_1"),
        created_at=Timestamp(value="2026-08-04T12:00:00.000Z"),
        metadata={"attempt": 1},  # type: ignore[arg-type]
    )
    result = CommandResult(command_id=command_id, decision=decision)

    assert command.command_id is command_id
    assert isinstance(command.metadata, JsonObject)
    assert result.decision is decision
    with pytest.raises(ValidationError, match="command_run_id_invalid"):
        Command(
            command_id=command_id,
            run_id=EventId(value="evt_wrong"),  # type: ignore[arg-type]
            origin=CommandOrigin.MODEL,
            operation=AddMessageOperation(message=Content(preview="answer")),
        )


def test_standalone_records_losslessly_model_all_frozen_evidence_branches() -> None:
    manifest = cast(dict[str, object], json.loads(FIXTURE_MANIFEST.read_text()))
    command_cases = cast(list[dict[str, object]], manifest["commands"])
    records: dict[str, CommandDecisionRecord] = {}

    for case in command_cases:
        meaning = cast(dict[str, object], case["decodedMeaning"])
        command_id = CommandId(value=cast(str, meaning["commandID"]))
        raw_trace = cast(list[dict[str, str]], meaning["decisionTrace"])
        entries = tuple(
            CommandDecisionTraceEntry(
                criterion=LegalityCriterion.ORACLE_FIXTURE,
                result=LegalityCriterionResult(item["result"]),
            )
            for item in raw_trace
        )
        result_event_ids = tuple(
            EventId(value=value) for value in cast(list[str], meaning["resultEventIDs"])
        )
        decision = cast(str, meaning["decision"])
        if decision == "accepted":
            target = cast(dict[str, str], meaning["targetEvent"])
            record = CommandDecisionRecord(
                command_id=command_id,
                branch=AcceptedDecisionRecord(
                    decision_trace=entries,
                    result_event_ids=result_event_ids,
                ),
                target_event=TargetEventPresent(event_id=EventId(value=target["eventID"])),
            )
        elif decision == "rejected":
            rejection = cast(dict[str, str], meaning["rejection"])
            record = CommandDecisionRecord(
                command_id=command_id,
                branch=RejectedDecisionRecord(
                    decision_trace=entries,
                    result_event_ids=(),
                    rejection=CommandRejectionRecord(code=rejection["code"]),
                ),
                target_event=TargetEventAbsent(),
            )
        elif decision == "deferred":
            wait = cast(dict[str, str], meaning["wait"])
            record = CommandDecisionRecord(
                command_id=command_id,
                branch=DeferredDecisionRecord(
                    decision_trace=entries,
                    result_event_ids=(),
                    wait=CommandWaitRecord(
                        wait_id=WaitId(value=wait["waitID"]),
                        kind=WaitKind(wait["kind"]),
                    ),
                ),
                target_event=TargetEventAbsent(),
            )
        else:
            record = CommandDecisionRecord(
                command_id=command_id,
                branch=SupersededDecisionRecord(
                    decision_trace=entries,
                    result_event_ids=(),
                    declaration_only=cast(bool, meaning["declarationOnly"]),
                    replacement_command_id=CommandId(
                        value=cast(str, meaning["replacementCommandID"])
                    ),
                ),
                target_event=TargetEventAbsent(),
            )
        records[decision] = record

    assert set(records) == {"accepted", "rejected", "deferred", "superseded"}
    assert records["accepted"].branch.result_event_ids == (EventId(value="evt_oracle_result"),)
    assert not hasattr(records["rejected"].branch, "reason")
    assert not hasattr(records["deferred"].branch, "reason")
    assert not hasattr(records["superseded"].branch, "reason")


def test_record_cross_branch_fields_and_links_reject() -> None:
    event_id = EventId(value="evt_result")
    with pytest.raises(ValidationError, match="command_record_target_mismatch"):
        CommandDecisionRecord(
            command_id=CommandId(value="cmd_bad"),
            branch=AcceptedDecisionRecord(
                decision_trace=trace(),
                result_event_ids=(event_id,),
            ),
            target_event=TargetEventAbsent(),
        )
    with pytest.raises(ValidationError, match="command_record_result_event_mismatch"):
        CommandDecisionRecord(
            command_id=CommandId(value="cmd_bad"),
            branch=AcceptedDecisionRecord(
                decision_trace=trace(),
                result_event_ids=(EventId(value="evt_other"),),
            ),
            target_event=TargetEventPresent(event_id=event_id),
        )
    with pytest.raises(ValidationError, match="decision_record_results_must_be_empty"):
        RejectedDecisionRecord(
            decision_trace=trace(),
            result_event_ids=(event_id,),
            rejection=CommandRejectionRecord(code="no"),
        )
    with pytest.raises(ValidationError, match="decision_record_declaration_only_invalid"):
        SupersededDecisionRecord(
            decision_trace=trace(),
            result_event_ids=(),
            declaration_only=False,
            replacement_command_id=CommandId(value="cmd_replacement"),
        )


def test_record_target_and_metadata_branches_have_no_optional_bags() -> None:
    with pytest.raises(TypeError):
        TargetEventAbsent(event_id=EventId(value="evt_extra"))  # type: ignore[call-arg]
    with pytest.raises(TypeError):
        AcceptedDecisionRecord(  # type: ignore[call-arg]
            decision_trace=trace(),
            result_event_ids=(EventId(value="evt_1"),),
            rejection=CommandRejectionRecord(code="extra"),
        )
    with pytest.raises(ValidationError, match="command_rejection_code_invalid"):
        CommandRejectionRecord(code="")


def test_action_outcomes_do_not_leak_into_command_legality() -> None:
    assert ActionOutcome.UNKNOWN.value == "unknown"
    decision = DeferredCommandDecision(
        reason="reconciliation required",
        trace=trace(),
        wait_ids=(WaitId(value="wait_reconciliation"),),
    )
    assert decision.kind == "deferred"
