from __future__ import annotations

import asyncio
from collections.abc import Iterator

import pytest

from openrund._testing.memory import MemoryEventStore
from openrund.contracts.commands import (
    AcceptedCommandDecision,
    AddMessageOperation,
    BootstrapRunOperation,
    Command,
    CommandOrigin,
    CreateActionOperation,
    ModelCallFailureClassification,
    RejectedCommandDecision,
)
from openrund.contracts.content import Content
from openrund.contracts.events import (
    ModelCallCancelledPayload,
    ModelCallCompletedPayload,
    ModelCallFailedPayload,
    ModelCallStartedPayload,
)
from openrund.contracts.ids import (
    ActionId,
    CapabilityId,
    CommandId,
    EventId,
    MessageId,
    ModelCallId,
    RunId,
    RuntimeId,
)
from openrund.contracts.time import Timestamp
from openrund.engine import EngineDependencies, RuntimeEngine
from openrund.errors import (
    ProviderProtocolError,
    ProviderResponseError,
    ProviderTransportError,
)
from openrund.ports.providers import ModelProposal, ModelRequest
from openrund.runtime import DurableRunLoop, DurableRunLoopDependencies


class _Clock:
    def now(self) -> Timestamp:
        return Timestamp(value="2026-08-06T10:00:00.000Z")


class _Factory[TId: RuntimeId]:
    def __init__(self, values: Iterator[TId]) -> None:
        self._values = values

    def new_id(self) -> TId:
        return next(self._values)


def _ids[TId: RuntimeId](kind: type[TId], prefix: str) -> Iterator[TId]:
    index = 1
    while True:
        yield kind(value=f"{prefix}-{index}")
        index += 1


def _engine(store: MemoryEventStore) -> RuntimeEngine:
    return RuntimeEngine(
        EngineDependencies(
            event_store=store,
            clock=_Clock(),
            event_ids=_Factory(_ids(EventId, "event")),
            message_ids=_Factory(_ids(MessageId, "message")),
            conflict_retries=10,
        )
    )


async def _bootstrap(engine: RuntimeEngine, run_id: RunId) -> None:
    result = await engine.submit(
        Command(
            command_id=CommandId(value=f"bootstrap-{run_id.value}"),
            run_id=run_id,
            origin=CommandOrigin.SYSTEM,
            operation=BootstrapRunOperation(root_id=run_id),
        )
    )
    assert isinstance(result.decision, AcceptedCommandDecision)


def _proposal(request: ModelRequest, operation: object | None = None) -> ModelProposal:
    return ModelProposal(
        model_call_id=request.model_call_id,
        provider="fixed-provider",
        response=Content(preview="provider response"),
        operation=(
            AddMessageOperation(message=Content(preview="assistant answer"))
            if operation is None
            else operation  # type: ignore[arg-type]
        ),
        metadata={"fixed": True},  # type: ignore[arg-type]
    )


class _ObservingProvider:
    def __init__(self, store: MemoryEventStore) -> None:
        self.store = store
        self.calls: list[ModelRequest] = []

    async def propose(self, request: ModelRequest, /) -> ModelProposal:
        history = await self.store.read(request.run_id)
        assert any(isinstance(event.payload, ModelCallStartedPayload) for event in history.events)
        self.calls.append(request)
        return _proposal(request)


class _RejectingProposalProvider:
    async def propose(self, request: ModelRequest, /) -> ModelProposal:
        return _proposal(
            request,
            CreateActionOperation(
                action_id=ActionId(value="ungranted-action"),
                capability_id=CapabilityId(value="filesystem"),
                action_name="read",
                input=Content(data={"path": "README.md"}),  # type: ignore[arg-type]
            ),
        )


class _ErrorProvider:
    def __init__(self, error: Exception) -> None:
        self.error = error

    async def propose(self, request: ModelRequest, /) -> ModelProposal:
        raise self.error


class _MismatchProvider:
    async def propose(self, request: ModelRequest, /) -> ModelProposal:
        return ModelProposal(
            model_call_id=ModelCallId(value="wrong-call"),
            provider="fixed-provider",
            response=Content(preview="wrong"),
            operation=AddMessageOperation(message=Content(preview="wrong")),
        )


class _BlockingProvider:
    def __init__(self) -> None:
        self.started = asyncio.Event()
        self.release = asyncio.Event()
        self.closed = False

    async def propose(self, request: ModelRequest, /) -> ModelProposal:
        self.started.set()
        await self.release.wait()
        return _proposal(request)

    async def aclose(self) -> None:
        self.closed = True
        self.release.set()


class _CountingProvider:
    def __init__(self) -> None:
        self.calls = 0

    async def propose(self, request: ModelRequest, /) -> ModelProposal:
        self.calls += 1
        await asyncio.sleep(0)
        return _proposal(request)


def _loop(
    engine: RuntimeEngine,
    provider: object,
    *,
    own_provider: bool = False,
) -> DurableRunLoop:
    return DurableRunLoop(
        DurableRunLoopDependencies(
            engine=engine,
            provider=provider,  # type: ignore[arg-type]
            clock=_Clock(),
            model_call_ids=_Factory(_ids(ModelCallId, "model")),
            command_ids=_Factory(_ids(CommandId, "loop-command")),
            own_provider=own_provider,
        )
    )


def test_success_records_start_then_completion_before_model_command() -> None:
    async def scenario() -> None:
        store = MemoryEventStore()
        engine = _engine(store)
        run_id = RunId(value="run-success")
        await _bootstrap(engine, run_id)
        provider = _ObservingProvider(store)
        loop = _loop(engine, provider)

        result = await loop.step(
            run_id,
            Content(preview="context"),
            remaining_requests=4,
        )
        history = await store.read(run_id)
        payloads = tuple(event.payload for event in history.events)
        started_at = next(
            index
            for index, payload in enumerate(payloads)
            if isinstance(payload, ModelCallStartedPayload)
        )
        completed_at = next(
            index
            for index, payload in enumerate(payloads)
            if isinstance(payload, ModelCallCompletedPayload)
        )
        message_at = next(
            index
            for index, event in enumerate(history.events)
            if event.event_type.value == "message.added"
        )

        assert result.status == "proposed"
        assert isinstance(result.proposal_result.decision, AcceptedCommandDecision)  # type: ignore[union-attr]
        assert started_at < completed_at < message_at
        assert len(provider.calls) == 1
        assert provider.calls[0].remaining_requests == 4
        assert provider.calls[0].model_call_id == result.model_call_id

    asyncio.run(scenario())


def test_engine_rejection_of_proposal_is_normal_result_after_completed_call() -> None:
    async def scenario() -> None:
        store = MemoryEventStore()
        engine = _engine(store)
        run_id = RunId(value="run-rejected-proposal")
        await _bootstrap(engine, run_id)

        result = await _loop(engine, _RejectingProposalProvider()).step(
            run_id,
            Content(preview="context"),
            remaining_requests=1,
        )
        history = await store.read(run_id)

        assert result.status == "proposed"
        assert isinstance(result.proposal_result.decision, RejectedCommandDecision)  # type: ignore[union-attr]
        assert result.proposal_result.decision.reason == "capability_not_registered"  # type: ignore[union-attr]
        assert (
            len(
                [
                    event
                    for event in history.events
                    if isinstance(event.payload, ModelCallCompletedPayload)
                ]
            )
            == 1
        )

    asyncio.run(scenario())


@pytest.mark.parametrize(
    ("error", "classification", "retryable", "failure_code"),
    [
        (
            ProviderResponseError(status=503),
            ModelCallFailureClassification.PROVIDER,
            True,
            "provider_response_error",
        ),
        (
            ProviderTransportError(code="provider_http_timeout"),
            ModelCallFailureClassification.TRANSPORT,
            True,
            "provider_http_timeout",
        ),
        (
            ProviderProtocolError(code="provider_response_json_invalid"),
            ModelCallFailureClassification.PARSE,
            False,
            "provider_response_json_invalid",
        ),
        (
            RuntimeError("raw secret failure"),
            ModelCallFailureClassification.PROVIDER,
            False,
            "provider_unexpected_failure",
        ),
    ],
)
def test_failures_become_safe_durable_model_call_facts(
    error: Exception,
    classification: ModelCallFailureClassification,
    retryable: bool,
    failure_code: str,
) -> None:
    async def scenario() -> None:
        store = MemoryEventStore()
        engine = _engine(store)
        run_id = RunId(value=f"run-failure-{classification.value}-{failure_code}")
        await _bootstrap(engine, run_id)

        result = await _loop(engine, _ErrorProvider(error)).step(
            run_id,
            Content(preview="context"),
            remaining_requests=1,
        )
        history = await store.read(run_id)
        failures = tuple(
            event.payload
            for event in history.events
            if isinstance(event.payload, ModelCallFailedPayload)
        )

        assert result.status == "failed"
        assert result.failure_code == failure_code
        assert result.proposal_result is None
        assert len(failures) == 1
        assert failures[0].classification == classification.value
        assert failures[0].retryable is retryable
        assert "raw secret" not in failures[0].message

    asyncio.run(scenario())


def test_mismatched_provider_identity_is_parse_failure() -> None:
    async def scenario() -> None:
        store = MemoryEventStore()
        engine = _engine(store)
        run_id = RunId(value="run-mismatch")
        await _bootstrap(engine, run_id)

        result = await _loop(engine, _MismatchProvider()).step(
            run_id,
            Content(preview="context"),
            remaining_requests=1,
        )

        assert result.status == "failed"
        assert result.failure_code == "provider_model_call_mismatch"

    asyncio.run(scenario())


def test_caller_cancellation_is_recorded_exactly_once() -> None:
    async def scenario() -> None:
        store = MemoryEventStore()
        engine = _engine(store)
        run_id = RunId(value="run-cancel")
        await _bootstrap(engine, run_id)
        provider = _BlockingProvider()
        loop = _loop(engine, provider)
        task = asyncio.create_task(
            loop.step(run_id, Content(preview="context"), remaining_requests=1)
        )
        await provider.started.wait()

        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task
        history = await store.read(run_id)
        cancelled = tuple(
            event.payload
            for event in history.events
            if isinstance(event.payload, ModelCallCancelledPayload)
        )

        assert len(cancelled) == 1
        assert cancelled[0].reason == "provider call cancelled"
        assert not any(
            isinstance(event.payload, ModelCallCompletedPayload) for event in history.events
        )

    asyncio.run(scenario())


def test_context_close_cancels_active_call_and_closes_owned_provider() -> None:
    async def scenario() -> None:
        store = MemoryEventStore()
        engine = _engine(store)
        run_id = RunId(value="run-close")
        await _bootstrap(engine, run_id)
        provider = _BlockingProvider()
        loop = _loop(engine, provider, own_provider=True)
        task = asyncio.create_task(
            loop.step(run_id, Content(preview="context"), remaining_requests=1)
        )
        await provider.started.wait()

        await loop.aclose()
        with pytest.raises(asyncio.CancelledError):
            await task
        history = await store.read(run_id)

        assert provider.closed is True
        assert (
            len(
                [
                    event
                    for event in history.events
                    if isinstance(event.payload, ModelCallCancelledPayload)
                ]
            )
            == 1
        )
        with pytest.raises(ProviderTransportError, match="run_loop_closed"):
            await loop.step(run_id, Content(preview="late"), remaining_requests=1)

    asyncio.run(scenario())


def test_concurrent_steps_do_not_share_lifecycle_state() -> None:
    async def scenario() -> None:
        store = MemoryEventStore()
        engine = _engine(store)
        run_id = RunId(value="run-concurrent-model")
        await _bootstrap(engine, run_id)
        provider = _CountingProvider()
        loop = _loop(engine, provider)

        first, second = await asyncio.gather(
            loop.step(run_id, Content(preview="one"), remaining_requests=2),
            loop.step(run_id, Content(preview="two"), remaining_requests=1),
        )
        history = await store.read(run_id)

        assert first.model_call_id != second.model_call_id
        assert first.status == second.status == "proposed"
        assert provider.calls == 2
        assert (
            len(
                [
                    event
                    for event in history.events
                    if isinstance(event.payload, ModelCallStartedPayload)
                ]
            )
            == 2
        )
        assert (
            len(
                [
                    event
                    for event in history.events
                    if isinstance(event.payload, ModelCallCompletedPayload)
                ]
            )
            == 2
        )

    asyncio.run(scenario())
