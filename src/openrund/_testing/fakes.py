"""Seeded private port fakes with immutable ordered observations."""

from __future__ import annotations

from dataclasses import replace
from typing import final

from openrund.contracts.capabilities import CapabilityResult
from openrund.contracts.ids import RuntimeId
from openrund.contracts.time import Timestamp
from openrund.errors import CapabilityProtocolError, ProviderTransportError, ValidationError
from openrund.ports.capabilities import CapabilityInvocation
from openrund.ports.providers import ModelProposal, ModelRequest
from openrund.ports.runtime import ReportEntry


@final
class SeededClock:
    def __init__(self, values: tuple[Timestamp, ...]) -> None:
        if any(not isinstance(value, Timestamp) for value in values):
            raise ValidationError(code="seeded_clock_value_invalid")
        self._values = tuple(values)
        self._index = 0

    @property
    def remaining(self) -> int:
        return len(self._values) - self._index

    def now(self) -> Timestamp:
        if self._index >= len(self._values):
            raise ValidationError(code="seeded_clock_exhausted")
        value = self._values[self._index]
        self._index += 1
        return value


@final
class SeededIdFactory[TId: RuntimeId]:
    def __init__(self, values: tuple[TId, ...]) -> None:
        self._values = tuple(values)
        self._index = 0

    @property
    def remaining(self) -> int:
        return len(self._values) - self._index

    def new_id(self) -> TId:
        if self._index >= len(self._values):
            raise ValidationError(code="seeded_id_factory_exhausted")
        value = self._values[self._index]
        self._index += 1
        return value


@final
class FakeModelProvider:
    def __init__(self, proposals: tuple[ModelProposal, ...]) -> None:
        if any(not isinstance(proposal, ModelProposal) for proposal in proposals):
            raise ValidationError(code="fake_model_proposal_invalid")
        self._proposals = tuple(proposals)
        self._index = 0
        self._calls: list[ModelRequest] = []

    @property
    def calls(self) -> tuple[ModelRequest, ...]:
        return tuple(self._calls)

    async def propose(self, request: ModelRequest, /) -> ModelProposal:
        self._calls.append(replace(request))
        if self._index >= len(self._proposals):
            raise ProviderTransportError(code="fake_model_provider_exhausted")
        proposal = self._proposals[self._index]
        self._index += 1
        if proposal.model_call_id != request.model_call_id:
            raise ProviderTransportError(code="fake_model_provider_call_mismatch")
        return replace(proposal)


@final
class FakeCapabilityTransport:
    def __init__(self, results: tuple[CapabilityResult, ...]) -> None:
        if any(not isinstance(result, CapabilityResult) for result in results):
            raise ValidationError(code="fake_capability_result_invalid")
        self._results = tuple(results)
        self._index = 0
        self._calls: list[CapabilityInvocation] = []

    @property
    def calls(self) -> tuple[CapabilityInvocation, ...]:
        return tuple(self._calls)

    async def invoke(self, invocation: CapabilityInvocation, /) -> CapabilityResult:
        self._calls.append(replace(invocation))
        if self._index >= len(self._results):
            raise CapabilityProtocolError(code="fake_capability_transport_exhausted")
        result = self._results[self._index]
        self._index += 1
        return replace(result)


@final
class RecordingReporter:
    def __init__(self) -> None:
        self._entries: list[ReportEntry] = []

    @property
    def entries(self) -> tuple[ReportEntry, ...]:
        return tuple(self._entries)

    async def report(self, entry: ReportEntry, /) -> None:
        self._entries.append(replace(entry))
