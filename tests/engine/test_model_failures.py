from __future__ import annotations

import asyncio

import pytest

from openrund._testing.memory import MemoryEventStore
from openrund.codec import encode_event
from openrund.contracts.commands import (
    AcceptedCommandDecision,
    BootstrapRunOperation,
    Command,
    CommandOrigin,
    FailModelCallOperation,
    ModelCallFailureClassification,
    StartModelCallOperation,
)
from openrund.contracts.events import ModelCallFailedPayload
from openrund.contracts.ids import CommandId, ModelCallId, RunId
from openrund.engine import EngineDependencies, RuntimeEngine
from openrund.errors import ValidationError

RUN_ID = RunId(value="run_1")


def _command(command_id: str, operation: object) -> Command:
    return Command(
        command_id=CommandId(value=command_id),
        run_id=RUN_ID,
        origin=CommandOrigin.SYSTEM,
        operation=operation,  # type: ignore[arg-type]
    )


@pytest.mark.parametrize(
    "classification",
    tuple(ModelCallFailureClassification),
)
def test_provider_transport_and_parse_failures_are_runtime_lifecycle_facts(
    classification: ModelCallFailureClassification,
    engine_dependencies: EngineDependencies,
    event_store: MemoryEventStore,
) -> None:
    engine = RuntimeEngine(engine_dependencies)
    asyncio.run(engine.submit(_command("bootstrap", BootstrapRunOperation(root_id=RUN_ID))))
    model_call_id = ModelCallId(value=f"model_{classification.value}")
    asyncio.run(
        engine.submit(
            _command(
                "start",
                StartModelCallOperation(model_call_id=model_call_id),
            )
        )
    )

    result = asyncio.run(
        engine.submit(
            _command(
                "failure",
                FailModelCallOperation(
                    model_call_id=model_call_id,
                    message=f"{classification.value} failure",
                    classification=classification,
                    retryable=classification is not ModelCallFailureClassification.PARSE,
                ),
            )
        )
    )
    history = asyncio.run(event_store.read(RUN_ID))
    failure_event = next(
        event for event in history.events if isinstance(event.payload, ModelCallFailedPayload)
    )

    failure_payload = failure_event.payload
    assert isinstance(result.decision, AcceptedCommandDecision)
    assert isinstance(failure_payload, ModelCallFailedPayload)
    assert failure_payload.classification == classification.value
    assert failure_event.command_id == CommandId(value="failure")


def test_failure_classification_rejects_unstable_free_form_values() -> None:
    with pytest.raises(ValidationError, match="fail_model_call_classification_invalid"):
        FailModelCallOperation(
            model_call_id=ModelCallId(value="model_1"),
            message="failed",
            classification="timeout",  # type: ignore[arg-type]
        )


def test_safe_failure_does_not_serialize_unprovided_raw_provider_body(
    engine_dependencies: EngineDependencies,
    event_store: MemoryEventStore,
) -> None:
    engine = RuntimeEngine(engine_dependencies)
    asyncio.run(engine.submit(_command("bootstrap", BootstrapRunOperation(root_id=RUN_ID))))
    model_call_id = ModelCallId(value="model_1")
    asyncio.run(
        engine.submit(_command("start", StartModelCallOperation(model_call_id=model_call_id)))
    )
    asyncio.run(
        engine.submit(
            _command(
                "failure",
                FailModelCallOperation(
                    model_call_id=model_call_id,
                    message="provider request failed",
                    classification=ModelCallFailureClassification.PROVIDER,
                ),
            )
        )
    )
    history = asyncio.run(event_store.read(RUN_ID))
    encoded = b"".join(encode_event(event) for event in history.events)

    assert b"raw-secret-provider-body" not in encoded
    assert b'"classification":"provider"' in encoded
    assert b'"evidence"' not in encode_event(history.events[-1])
