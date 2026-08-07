from __future__ import annotations

import asyncio
import inspect
from dataclasses import FrozenInstanceError
from typing import assert_type

import pytest

from openrund.contracts.capabilities import CapabilityResult
from openrund.contracts.commands import AddMessageOperation
from openrund.contracts.content import Content
from openrund.contracts.ids import ActionId, CapabilityId, ModelCallId, RunId, RuntimeId
from openrund.contracts.time import Timestamp
from openrund.ports.capabilities import CapabilityInvocation, CapabilityTransport
from openrund.ports.providers import ModelProposal, ModelProvider, ModelRequest
from openrund.ports.runtime import Clock, IdFactory, ReportEntry, Reporter


class FixedClock:
    def now(self) -> Timestamp:
        return Timestamp(value="2026-01-02T03:04:05.000Z")


class FixedIdFactory[TId: RuntimeId]:
    def __init__(self, value: TId) -> None:
        self._value = value

    def new_id(self) -> TId:
        return self._value


class FixedProvider:
    async def propose(self, request: ModelRequest, /) -> ModelProposal:
        return ModelProposal(
            model_call_id=request.model_call_id,
            operation=AddMessageOperation(message=Content(preview="proposal")),
            response=Content(preview="response"),
            provider="fixed",
        )


class FixedTransport:
    async def invoke(self, invocation: CapabilityInvocation, /) -> CapabilityResult:
        return CapabilityResult(preview=invocation.action_name)


class RecordingReporter:
    def __init__(self) -> None:
        self.entries: list[ReportEntry] = []

    async def report(self, entry: ReportEntry, /) -> None:
        self.entries.append(entry)


CLOCK: Clock = FixedClock()
PROVIDER: ModelProvider = FixedProvider()
TRANSPORT: CapabilityTransport = FixedTransport()
REPORTER: Reporter = RecordingReporter()


def _factory[TId: RuntimeId](value: TId) -> IdFactory[TId]:
    return FixedIdFactory(value)


def test_protocol_assignments_are_structural_and_not_runtime_checkable() -> None:
    assert_type(CLOCK, Clock)
    assert_type(PROVIDER, ModelProvider)
    assert_type(TRANSPORT, CapabilityTransport)
    assert_type(REPORTER, Reporter)
    assert inspect.iscoroutinefunction(ModelProvider.propose)
    assert inspect.iscoroutinefunction(CapabilityTransport.invoke)
    assert inspect.iscoroutinefunction(Reporter.report)
    assert not hasattr(ModelProvider, "__runtime_protocol__")


def test_generic_factories_preserve_each_identifier_type() -> None:
    run_ids = _factory(RunId(value="r1"))
    model_call_ids = _factory(ModelCallId(value="m1"))

    assert_type(run_ids.new_id(), RunId)
    assert_type(model_call_ids.new_id(), ModelCallId)
    assert run_ids.new_id().value == "r1"
    assert model_call_ids.new_id().value == "m1"


def test_provider_and_transport_return_proposals_and_results_only() -> None:
    request = ModelRequest(
        model_call_id=ModelCallId(value="m1"),
        run_id=RunId(value="r1"),
        context=Content(preview="context"),
        remaining_requests=1,
    )
    proposal = asyncio.run(PROVIDER.propose(request))
    invocation = CapabilityInvocation(
        action_id=ActionId(value="a1"),
        capability_id=CapabilityId(value="cap1"),
        action_name="read",
        input=Content(preview="input"),
    )
    result = asyncio.run(TRANSPORT.invoke(invocation))

    assert proposal.model_call_id == request.model_call_id
    assert isinstance(proposal.operation, AddMessageOperation)
    assert result.preview == "read"


def test_reporter_receives_immutable_entries() -> None:
    reporter = RecordingReporter()
    entry = ReportEntry(timestamp=CLOCK.now(), category="runtime", message="started")

    asyncio.run(reporter.report(entry))

    assert reporter.entries == [entry]
    with pytest.raises(FrozenInstanceError):
        entry.message = "changed"  # type: ignore[misc]
