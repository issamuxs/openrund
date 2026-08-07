from __future__ import annotations

from dataclasses import FrozenInstanceError, is_dataclass

import pytest

from openrund.contracts.content import Content, RunResult
from openrund.contracts.ids import (
    ActionId,
    AnnotationId,
    ArtifactId,
    AuthorityId,
    CapabilityId,
    CheckId,
    CheckpointId,
    CommandId,
    DelegationId,
    EventId,
    LeaseId,
    MessageId,
    ModelCallId,
    PolicyRuleId,
    RunId,
    WaitId,
)
from openrund.contracts.json import JsonObject
from openrund.contracts.runs import (
    Annotation,
    ApprovalWait,
    Artifact,
    Authority,
    AuthorityGrant,
    Check,
    Checkpoint,
    CheckRequirement,
    CheckStatus,
    DelegatedRunKind,
    Delegation,
    DelegationBudget,
    DelegationContract,
    DelegationInput,
    DelegationJoinContract,
    DelegationJoinMode,
    DelegationLineage,
    InteractionWait,
    JoinWait,
    KnownActionOutcomesRequirement,
    Lease,
    Message,
    MessageRole,
    ModelCall,
    OutputArtifactRequirement,
    ReconciliationWait,
    Run,
    RunContract,
    RunStatus,
    SourceCoverageRequirement,
    TimerWait,
    WaitKind,
)
from openrund.contracts.time import Timestamp
from openrund.errors import ValidationError
from openrund.paths import LocalPath


def rid(value: str = "run_root") -> RunId:
    return RunId(value=value)


def ts(value: str = "2026-08-04T12:00:00.000Z") -> Timestamp:
    return Timestamp(value=value)


def authority_grant() -> AuthorityGrant:
    return AuthorityGrant(
        capability_id=CapabilityId(value="cap_filesystem"),
        actions=("read", "write"),
        policy_rule_ids=(PolicyRuleId(value="policy_workspace"),),
    )


def delegation_contract() -> DelegationContract:
    return DelegationContract(
        run_kind=DelegatedRunKind.WORKER,
        objective="Inspect one bounded source",
        authority_grants=(authority_grant(),),
        authority_drift="snapshot",
        budget=DelegationBudget(max_requests=3, wall_clock_timeout_ms=30_000),
        result_kind="research_result",
        required_artifact_kinds=("report",),
        allow_nested_delegation=False,
        on_parent_cancel="cancel",
        late_handoff="surface",
    )


def test_root_concepts_are_frozen_slotted_keyword_only_values() -> None:
    run_id = rid()
    child_id = rid("run_child")
    contract = delegation_contract()
    join_contract = DelegationJoinContract(
        wait_id=WaitId(value="wait_join"),
        target_run_ids=(child_id,),
        mode=DelegationJoinMode.ALL,
        outcome_filter="completed_only",
        failure_policy="fail_fast",
        on_satisfied="keep_bound",
        late_handoff_policy="surface",
    )
    specimens = (
        Run(run_id=run_id, root_id=run_id, status=RunStatus.RUNNING),
        Message(
            message_id=MessageId(value="msg_1"),
            run_id=run_id,
            role=MessageRole.USER,
            content=Content(preview="hello"),
        ),
        ModelCall(
            model_call_id=ModelCallId(value="model_1"),
            run_id=run_id,
            request=Content(preview="choose one operation"),
        ),
        Delegation(
            delegation_id=DelegationId(value="delegation_1"),
            parent_run_id=run_id,
            delegated_run_id=child_id,
            contract=contract,
            input=DelegationInput(data={"source": "one"}),  # type: ignore[arg-type]
            lineage=DelegationLineage(parent_run_id=run_id, delegated_run_id=child_id),
            join_contract=join_contract,
        ),
        Check(
            check_id=CheckId(value="check_1"),
            run_id=run_id,
            name="schema",
            status=CheckStatus.PASSED,
            report=Content(preview="valid"),
        ),
        Checkpoint(
            checkpoint_id=CheckpointId(value="checkpoint_1"),
            run_id=run_id,
            from_position=1,
            to_position=4,
        ),
        Annotation(
            annotation_id=AnnotationId(value="annotation_1"),
            run_id=run_id,
            content=Content(preview="observed"),
        ),
        Artifact(
            artifact_id=ArtifactId(value="artifact_1"),
            run_id=run_id,
            kind="report",
            byte_length=12,
            sha256="a" * 64,
        ),
        Authority(
            authority_id=AuthorityId(value="authority_1"),
            run_id=run_id,
            grants=(authority_grant(),),
        ),
        Lease(
            lease_id=LeaseId(value="lease_1"),
            run_id=run_id,
            owner="worker-1",
            token="token-1",
            acquired_at=ts(),
            expires_at=ts("2026-08-04T12:01:00.000Z"),
        ),
    )

    for specimen in specimens:
        assert is_dataclass(specimen)
        assert getattr(type(specimen), "__final__", False)
        assert not hasattr(specimen, "__dict__")
        with pytest.raises((FrozenInstanceError, AttributeError, TypeError)):
            specimen.unexpected = True  # type: ignore[union-attr]


def test_wait_is_a_precise_five_branch_union() -> None:
    run_id = rid()
    command_id = CommandId(value="cmd_wait")
    child_id = rid("run_child")
    join_contract = DelegationJoinContract(
        wait_id=WaitId(value="wait_join"),
        target_run_ids=(child_id,),
        mode=DelegationJoinMode.ALL,
        outcome_filter="terminal_any",
        failure_policy="wait_for_all_terminal",
        on_satisfied="keep_bound",
        late_handoff_policy="surface",
    )
    waits = (
        ApprovalWait(
            wait_id=WaitId(value="wait_approval"),
            run_id=run_id,
            opened_by_command_id=command_id,
            target="filesystem.write",
            reason="authorization required",
        ),
        InteractionWait(
            wait_id=WaitId(value="wait_interaction"),
            run_id=run_id,
            opened_by_command_id=command_id,
            prompt="Provide the missing value",
        ),
        TimerWait(
            wait_id=WaitId(value="wait_timer"),
            run_id=run_id,
            opened_by_command_id=command_id,
            fire_at=ts(),
        ),
        JoinWait(
            wait_id=WaitId(value="wait_join"),
            run_id=run_id,
            opened_by_command_id=command_id,
            contract=join_contract,
        ),
        ReconciliationWait(
            wait_id=WaitId(value="wait_reconcile"),
            run_id=run_id,
            opened_by_command_id=command_id,
            action_id=ActionId(value="action_unknown"),
            reason="outcome unknown",
        ),
    )

    assert tuple(wait.kind for wait in waits) == tuple(WaitKind)
    with pytest.raises(TypeError):
        TimerWait(  # type: ignore[call-arg]
            wait_id=WaitId(value="wait_bad"),
            run_id=run_id,
            opened_by_command_id=command_id,
            prompt="not a timer field",
        )


def test_join_contract_enforces_quorum_and_kind_safe_ids() -> None:
    children = (rid("run_a"), rid("run_b"))
    with pytest.raises(ValidationError, match="delegation_join_quorum_required"):
        DelegationJoinContract(
            wait_id=WaitId(value="wait_join"),
            target_run_ids=children,
            mode=DelegationJoinMode.QUORUM,
            outcome_filter="completed_only",
            failure_policy="fail_fast",
            on_satisfied="cancel_remaining",
            late_handoff_policy="ignore",
        )
    with pytest.raises(ValidationError, match="delegation_join_target_ids_invalid"):
        DelegationJoinContract(
            wait_id=WaitId(value="wait_join"),
            target_run_ids=(EventId(value="evt_wrong"),),  # type: ignore[arg-type]
            mode=DelegationJoinMode.ALL,
            outcome_filter="completed_only",
            failure_policy="fail_fast",
            on_satisfied="cancel_remaining",
            late_handoff_policy="ignore",
        )


def test_delegation_contract_and_completion_requirements_are_precise() -> None:
    requirement = OutputArtifactRequirement(
        capability_id=CapabilityId(value="cap_documents"),
        format="markdown",
        writable_root=LocalPath(raw="/workspace/output"),
        action_name="write",
        artifact_kind="report",
    )
    contract = RunContract(
        output=requirement,
        check=CheckRequirement(checks=("schema", "citations")),
        delegation=SourceCoverageRequirement(),
        completion=KnownActionOutcomesRequirement(),
        metadata={"strict": True},  # type: ignore[arg-type]
    )

    assert contract.output is requirement
    assert isinstance(contract.metadata, JsonObject)
    with pytest.raises(ValidationError, match="delegation_budget_max_requests_invalid"):
        DelegationBudget(max_requests=0, wall_clock_timeout_ms=1)
    with pytest.raises(ValidationError, match="run_contract_output_invalid"):
        RunContract(output=Content(preview="wrong"))  # type: ignore[arg-type]


def test_nested_data_is_deeply_frozen_and_cross_field_ranges_reject() -> None:
    annotation = Annotation(
        annotation_id=AnnotationId(value="annotation_1"),
        run_id=rid(),
        content=Content(preview="note"),
        metadata={"nested": [1, 2]},  # type: ignore[arg-type]
    )
    assert isinstance(annotation.metadata, JsonObject)
    with pytest.raises(ValidationError, match="checkpoint_range_invalid"):
        Checkpoint(
            checkpoint_id=CheckpointId(value="checkpoint_bad"),
            run_id=rid(),
            from_position=4,
            to_position=3,
        )
    with pytest.raises(ValidationError, match="artifact_sha256_invalid"):
        Artifact(
            artifact_id=ArtifactId(value="artifact_bad"),
            run_id=rid(),
            kind="report",
            byte_length=1,
            sha256="not-a-digest",
        )


def test_wrong_id_kinds_and_ambiguous_root_fields_reject() -> None:
    with pytest.raises(ValidationError, match="run_id_invalid"):
        Run(
            run_id=EventId(value="evt_wrong"),  # type: ignore[arg-type]
            root_id=rid(),
            status=RunStatus.CREATED,
        )
    with pytest.raises(TypeError):
        Run(  # type: ignore[call-arg]
            run_id=rid(),
            root_id=rid(),
            status=RunStatus.CREATED,
            payload={"opaque": True},
        )


def test_run_result_remains_a_value_on_the_root_run() -> None:
    result = RunResult(kind="answer", summary="done")
    run = Run(
        run_id=rid(),
        root_id=rid(),
        status=RunStatus.COMPLETED,
        result=result,
    )
    assert run.result is result
