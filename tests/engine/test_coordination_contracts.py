from __future__ import annotations

import pytest

from openrund.contracts.capabilities import ActionReliability
from openrund.contracts.commands import (
    CancelWaitOperation,
    CompleteDelegationOperation,
    ExpireWaitOperation,
    GrantCapabilityAuthorityOperation,
    MarkActionUnknownOperation,
    ReconcileActionOperation,
    RecordAnnotationOperation,
    RecordCheckOperation,
    ResolveApprovalOperation,
    ResolveInteractionWaitOperation,
    ResumeApprovedActionOperation,
)
from openrund.contracts.content import Content
from openrund.contracts.ids import (
    ActionId,
    CapabilityId,
    EventId,
    ModelCallId,
    RunId,
    WaitId,
)
from openrund.contracts.runs import CheckStatus, WaitKind
from openrund.errors import ValidationError
from openrund.ports.providers import ModelProposal


def test_coordination_operations_are_frozen_validated_values() -> None:
    wait_id = WaitId(value="wait_1")
    response = Content(preview="approved")

    assert ResolveApprovalOperation(wait_id=wait_id, decision="approved").wait_id == wait_id
    assert ResumeApprovedActionOperation(wait_id=wait_id).wait_id == wait_id
    assert ResolveInteractionWaitOperation(wait_id=wait_id, response=response).response == response
    assert (
        CancelWaitOperation(wait_id=wait_id, wait_kind=WaitKind.TIMER).wait_kind is WaitKind.TIMER
    )
    assert ExpireWaitOperation(wait_id=wait_id, wait_kind=WaitKind.APPROVAL).wait_id == wait_id
    assert (
        CompleteDelegationOperation(delegated_run_id=RunId(value="child")).delegated_run_id.value
        == "child"
    )
    assert (
        GrantCapabilityAuthorityOperation(
            capability_id=CapabilityId(value="filesystem")
        ).capability_id.value
        == "filesystem"
    )


def test_recovery_and_evidence_operations_validate_required_evidence() -> None:
    action_id = ActionId(value="action_1")
    unknown_id = EventId(value="unknown_1")
    unknown = MarkActionUnknownOperation(
        action_id=action_id,
        reliability=ActionReliability.TRANSPORT_LOST,
        reason="worker response lost",
    )
    reconciled = ReconcileActionOperation(
        action_id=action_id,
        unknown_event_id=unknown_id,
        outcome="completed",
        evidence=Content(preview="receipt verified"),
    )
    check = RecordCheckOperation(
        subject="run_1",
        rule="completion",
        status=CheckStatus.PASSED,
        validator="pytest",
        summary="all checks passed",
        check_count=1,
        result=Content(preview="passed"),
    )
    annotation = RecordAnnotationOperation(content=Content(preview="operator note"))

    assert unknown.action_id == action_id
    assert reconciled.unknown_event_id == unknown_id
    assert check.status is CheckStatus.PASSED
    assert annotation.content.preview == "operator note"

    with pytest.raises(ValidationError, match="reconcile_action_evidence_invalid"):
        ReconcileActionOperation(
            action_id=action_id,
            unknown_event_id=unknown_id,
            outcome="completed",
            evidence=None,  # type: ignore[arg-type]
        )


def test_non_approved_resolution_cannot_carry_revised_input() -> None:
    with pytest.raises(ValidationError, match="resolve_approval_input_forbidden"):
        ResolveApprovalOperation(
            wait_id=WaitId(value="wait_1"),
            decision="denied",
            approved_input={"path": "report.md"},  # type: ignore[arg-type]
        )


def test_runtime_coordination_operation_is_not_a_model_proposal() -> None:
    with pytest.raises(ValidationError, match="model_proposal_operation_invalid"):
        ModelProposal(
            model_call_id=ModelCallId(value="model_1"),
            operation=ResumeApprovedActionOperation(wait_id=WaitId(value="wait_1")),  # type: ignore[arg-type]
            response=Content(),
            provider="test",
        )
