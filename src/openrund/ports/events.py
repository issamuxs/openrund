"""Domain-valued Event storage contracts without persistence behavior."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, cast, final

from openrund.contracts.events import Event, RuntimeEvent
from openrund.contracts.ids import EventId, RunId
from openrund.errors import ValidationError

_MAX_SAFE_INTEGER = 9_007_199_254_740_991


def _position(value: object, code: str, *, minimum: int = 0) -> int:
    if (
        isinstance(value, bool)
        or not isinstance(value, int)
        or not minimum <= value <= _MAX_SAFE_INTEGER
    ):
        raise ValidationError(code=code)
    return value


def _events(value: object, run_id: RunId, code: str) -> tuple[RuntimeEvent, ...]:
    try:
        events: tuple[object, ...] = tuple(value)  # type: ignore[arg-type]
    except TypeError as error:
        raise ValidationError(code=code) from error
    if any(not isinstance(event, Event) or event.run_id != run_id for event in events):
        raise ValidationError(code=code)
    return cast(tuple[RuntimeEvent, ...], events)


@final
@dataclass(frozen=True, slots=True, kw_only=True)
class EventSlice:
    run_id: RunId
    events: tuple[RuntimeEvent, ...]
    next_position: int

    def __post_init__(self) -> None:
        if not isinstance(self.run_id, RunId):
            raise ValidationError(code="event_slice_run_id_invalid")
        object.__setattr__(
            self, "events", _events(self.events, self.run_id, "event_slice_events_invalid")
        )
        object.__setattr__(
            self,
            "next_position",
            _position(self.next_position, "event_slice_position_invalid"),
        )


@final
@dataclass(frozen=True, slots=True, kw_only=True)
class AppendEventsInput:
    run_id: RunId
    expected_position: int
    events: tuple[RuntimeEvent, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.run_id, RunId):
            raise ValidationError(code="append_events_run_id_invalid")
        expected = _position(self.expected_position, "append_events_position_invalid")
        events = _events(self.events, self.run_id, "append_events_events_invalid")
        if not events:
            raise ValidationError(code="append_events_empty")
        if any(event.position != expected + index for index, event in enumerate(events, start=1)):
            raise ValidationError(code="append_events_positions_invalid")
        object.__setattr__(self, "expected_position", expected)
        object.__setattr__(self, "events", events)


@final
@dataclass(frozen=True, slots=True, kw_only=True)
class AppendEventsResult:
    run_id: RunId
    appended: tuple[RuntimeEvent, ...]
    next_position: int

    def __post_init__(self) -> None:
        if not isinstance(self.run_id, RunId):
            raise ValidationError(code="append_result_run_id_invalid")
        appended = _events(self.appended, self.run_id, "append_result_events_invalid")
        next_position = _position(self.next_position, "append_result_position_invalid")
        if appended and appended[-1].position != next_position:
            raise ValidationError(code="append_result_position_mismatch")
        object.__setattr__(self, "appended", appended)
        object.__setattr__(self, "next_position", next_position)


@final
@dataclass(frozen=True, slots=True, kw_only=True)
class AppendManyEventsInput:
    batches: tuple[AppendEventsInput, ...]

    def __post_init__(self) -> None:
        try:
            batches: tuple[object, ...] = tuple(self.batches)
        except TypeError as error:
            raise ValidationError(code="append_many_batches_invalid") from error
        if not batches or any(not isinstance(batch, AppendEventsInput) for batch in batches):
            raise ValidationError(code="append_many_batches_invalid")
        typed = cast(tuple[AppendEventsInput, ...], batches)
        run_ids = tuple(batch.run_id for batch in typed)
        if len(set(run_ids)) != len(run_ids):
            raise ValidationError(code="append_many_run_duplicate")
        event_ids = tuple(event.event_id for batch in typed for event in batch.events)
        if len(set(event_ids)) != len(event_ids):
            raise ValidationError(code="append_many_event_duplicate")
        object.__setattr__(self, "batches", typed)


@final
@dataclass(frozen=True, slots=True, kw_only=True)
class AppendManyEventsResult:
    results: tuple[AppendEventsResult, ...]

    def __post_init__(self) -> None:
        try:
            results: tuple[object, ...] = tuple(self.results)
        except TypeError as error:
            raise ValidationError(code="append_many_results_invalid") from error
        if not results or any(not isinstance(result, AppendEventsResult) for result in results):
            raise ValidationError(code="append_many_results_invalid")
        typed = cast(tuple[AppendEventsResult, ...], results)
        if len({result.run_id for result in typed}) != len(typed):
            raise ValidationError(code="append_many_result_run_duplicate")
        object.__setattr__(self, "results", typed)


class EventStore(Protocol):
    async def append(self, value: AppendEventsInput, /) -> AppendEventsResult: ...

    async def read(
        self,
        run_id: RunId,
        /,
        *,
        from_position: int = 1,
        limit: int | None = None,
    ) -> EventSlice: ...

    async def has_event(self, event_id: EventId, /) -> bool: ...


class AtomicEventStore(EventStore, Protocol):
    async def append_many(self, value: AppendManyEventsInput, /) -> AppendManyEventsResult: ...
