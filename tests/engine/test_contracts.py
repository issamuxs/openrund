from __future__ import annotations

from collections.abc import Callable
from dataclasses import FrozenInstanceError
from typing import cast

import pytest

from openrund.contracts.commands import (
    BootstrapRunOperation,
    CancelModelCallOperation,
    Command,
    CommandOrigin,
    CompleteModelCallOperation,
    FailModelCallOperation,
    MessageDeltaOperation,
    ModelCallFailureClassification,
    StartModelCallOperation,
    StartRunOperation,
)
from openrund.contracts.content import Content
from openrund.contracts.ids import CommandId, EventId, MessageId, ModelCallId, RunId
from openrund.engine import EngineDependencies
from openrund.errors import ValidationError
from openrund.ports.events import EventStore
from openrund.ports.providers import ModelProposal
from openrund.ports.runtime import Clock, IdFactory


def test_runtime_operations_are_precise_frozen_values() -> None:
    model_call_id = ModelCallId(value="model_1")
    operations = (
        BootstrapRunOperation(
            root_id=RunId(value="run_1"),
            title="title",
            objective="objective",
            metadata={"tenant": "one"},  # type: ignore[arg-type]
            start_reason="created",
        ),
        StartRunOperation(reason="resume"),
        MessageDeltaOperation(message_id=MessageId(value="message_1"), delta="chunk"),
        StartModelCallOperation(model_call_id=model_call_id),
        CompleteModelCallOperation(model_call_id=model_call_id, outcome="proposal"),
        FailModelCallOperation(
            model_call_id=model_call_id,
            message="transport failed",
            classification=ModelCallFailureClassification.TRANSPORT,
            retryable=True,
            evidence=Content(preview="safe"),
        ),
        CancelModelCallOperation(model_call_id=model_call_id, reason="run cancelled"),
    )

    for operation in operations:
        assert not hasattr(operation, "__dict__")
        with pytest.raises((FrozenInstanceError, AttributeError)):
            operation.kind = "changed"  # type: ignore[assignment, misc]


@pytest.mark.parametrize(
    ("constructor", "code"),
    [
        (
            lambda: BootstrapRunOperation(root_id=cast(RunId, "run")),
            "bootstrap_run_root_id_invalid",
        ),
        (
            lambda: MessageDeltaOperation(message_id=cast(MessageId, "message"), delta="chunk"),
            "message_delta_id_invalid",
        ),
        (
            lambda: CompleteModelCallOperation(model_call_id=ModelCallId(value="m1"), outcome=""),
            "complete_model_call_outcome_invalid",
        ),
        (
            lambda: FailModelCallOperation(
                model_call_id=ModelCallId(value="m1"),
                message="failed",
                retryable=cast(bool, 1),
            ),
            "fail_model_call_retryable_invalid",
        ),
    ],
)
def test_runtime_operation_validation(constructor: Callable[[], object], code: str) -> None:
    with pytest.raises(ValidationError, match=code):
        constructor()


def test_command_accepts_runtime_operation_but_model_proposal_does_not() -> None:
    operation = StartModelCallOperation(model_call_id=ModelCallId(value="model_1"))
    command = Command(
        command_id=CommandId(value="command_1"),
        run_id=RunId(value="run_1"),
        origin=CommandOrigin.SYSTEM,
        operation=operation,
    )

    assert command.operation is operation
    with pytest.raises(ValidationError, match="model_proposal_operation_invalid"):
        ModelProposal(
            model_call_id=ModelCallId(value="model_1"),
            operation=operation,  # type: ignore[arg-type]
            response=Content(preview="response"),
            provider="provider",
        )


def test_engine_dependencies_validate_bounded_retry_policy() -> None:
    for invalid in (-1, 101, True):
        with pytest.raises(ValidationError, match="engine_conflict_retries_invalid"):
            EngineDependencies(
                event_store=cast(EventStore, object()),
                clock=cast(Clock, object()),
                event_ids=cast(IdFactory[EventId], object()),
                message_ids=cast(IdFactory[MessageId], object()),
                conflict_retries=invalid,
            )
