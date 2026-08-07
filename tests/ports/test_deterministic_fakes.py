from __future__ import annotations

import asyncio
from typing import assert_type

import pytest

from openrund._testing.fakes import (
    FakeCapabilityTransport,
    FakeModelProvider,
    RecordingReporter,
    SeededClock,
    SeededIdFactory,
)
from openrund.contracts.capabilities import CapabilityResult
from openrund.contracts.commands import AddMessageOperation
from openrund.contracts.content import Content
from openrund.contracts.ids import ActionId, CapabilityId, EventId, ModelCallId, RunId
from openrund.contracts.time import Timestamp
from openrund.errors import CapabilityProtocolError, ProviderTransportError, ValidationError
from openrund.ports.capabilities import CapabilityInvocation, CapabilityTransport
from openrund.ports.providers import ModelProposal, ModelProvider, ModelRequest
from openrund.ports.runtime import Clock, IdFactory, ReportEntry, Reporter


def _timestamp(second: int) -> Timestamp:
    return Timestamp(value=f"2026-01-02T03:04:{second:02d}.000Z")


def _request(call_id: str) -> ModelRequest:
    return ModelRequest(
        model_call_id=ModelCallId(value=call_id),
        run_id=RunId(value="r1"),
        context=Content(preview="context"),
        remaining_requests=1,
    )


def _proposal(call_id: str, preview: str) -> ModelProposal:
    return ModelProposal(
        model_call_id=ModelCallId(value=call_id),
        operation=AddMessageOperation(message=Content(preview=preview)),
        response=Content(preview=preview),
        provider="fake",
    )


def test_seeded_clock_and_id_factory_are_typed_ordered_and_exhaustible() -> None:
    clock: Clock = SeededClock((_timestamp(1), _timestamp(2)))
    ids: IdFactory[EventId] = SeededIdFactory((EventId(value="e1"), EventId(value="e2")))

    assert clock.now() == _timestamp(1)
    assert clock.now() == _timestamp(2)
    assert_type(ids.new_id(), EventId)
    assert ids.new_id() == EventId(value="e2")
    with pytest.raises(ValidationError, match="seeded_clock_exhausted"):
        clock.now()
    with pytest.raises(ValidationError, match="seeded_id_factory_exhausted"):
        ids.new_id()


def test_fake_provider_returns_seed_order_and_records_immutable_calls() -> None:
    async def scenario() -> None:
        provider = FakeModelProvider((_proposal("m1", "one"), _proposal("m2", "two")))
        typed: ModelProvider = provider
        first = _request("m1")
        second = _request("m2")

        assert (await typed.propose(first)).response.preview == "one"
        assert (await typed.propose(second)).response.preview == "two"
        assert provider.calls == (first, second)
        assert provider.calls is not provider.calls
        with pytest.raises(ProviderTransportError, match="fake_model_provider_exhausted"):
            await typed.propose(_request("m3"))

    asyncio.run(scenario())


def test_provider_mismatch_fails_with_safe_stable_code() -> None:
    async def scenario() -> None:
        provider = FakeModelProvider((_proposal("seeded", "one"),))
        with pytest.raises(ProviderTransportError) as raised:
            await provider.propose(_request("actual"))
        assert raised.value.code == "fake_model_provider_call_mismatch"
        assert "actual" not in str(raised.value)

    asyncio.run(scenario())


def test_fake_transport_returns_typed_results_and_exhausts() -> None:
    async def scenario() -> None:
        transport = FakeCapabilityTransport(
            (CapabilityResult(preview="one"), CapabilityResult(preview="two"))
        )
        typed: CapabilityTransport = transport
        invocation = CapabilityInvocation(
            action_id=ActionId(value="a1"),
            capability_id=CapabilityId(value="cap1"),
            action_name="read",
            input=Content(preview="input"),
        )

        assert (await typed.invoke(invocation)).preview == "one"
        assert (await typed.invoke(invocation)).preview == "two"
        assert transport.calls == (invocation, invocation)
        with pytest.raises(CapabilityProtocolError, match="fake_capability_transport_exhausted"):
            await typed.invoke(invocation)

    asyncio.run(scenario())


def test_recording_reporter_exposes_only_immutable_ordered_entries() -> None:
    async def scenario() -> None:
        reporter = RecordingReporter()
        typed: Reporter = reporter
        first = ReportEntry(timestamp=_timestamp(1), category="runtime", message="one")
        second = ReportEntry(timestamp=_timestamp(2), category="runtime", message="two")

        await typed.report(first)
        await typed.report(second)

        assert reporter.entries == (first, second)
        assert reporter.entries is not reporter.entries

    asyncio.run(scenario())


def test_fakes_expose_no_authority_or_event_fabrication_path() -> None:
    forbidden = {
        "append",
        "append_event",
        "create_event",
        "decide_legality",
        "grant_authority",
    }

    for fake_type in (
        SeededClock,
        SeededIdFactory,
        FakeModelProvider,
        FakeCapabilityTransport,
        RecordingReporter,
    ):
        assert forbidden.isdisjoint(dir(fake_type))
