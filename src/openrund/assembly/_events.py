"""Atomic Event custody with isolated advisory reporting."""

from __future__ import annotations

from openrund.contracts.events import RuntimeEvent
from openrund.contracts.ids import EventId, RunId
from openrund.ports.events import (
    AppendEventsInput,
    AppendEventsResult,
    AppendManyEventsInput,
    AppendManyEventsResult,
    AtomicEventStore,
    EventSlice,
)
from openrund.ports.runtime import ReportEntry, Reporter


class ReportingEventStore:
    """One atomic custody object that reports only after durable success."""

    __slots__ = ("_reporter", "_store")

    def __init__(self, store: AtomicEventStore, reporter: Reporter) -> None:
        self._store = store
        self._reporter = reporter

    async def _report(self, events: tuple[RuntimeEvent, ...]) -> None:
        for event in events:
            try:
                await self._reporter.report(
                    ReportEntry(
                        timestamp=event.timestamp,
                        category="event.committed",
                        message=event.event_type.value,
                        metadata={
                            "run_id": event.run_id.value,
                            "event_id": event.event_id.value,
                            "position": event.position,
                        },  # type: ignore[arg-type]
                    )
                )
            except Exception:
                continue

    async def append(self, value: AppendEventsInput, /) -> AppendEventsResult:
        result = await self._store.append(value)
        await self._report(result.appended)
        return result

    async def append_many(self, value: AppendManyEventsInput, /) -> AppendManyEventsResult:
        result = await self._store.append_many(value)
        await self._report(tuple(event for item in result.results for event in item.appended))
        return result

    async def read(
        self,
        run_id: RunId,
        /,
        *,
        from_position: int = 1,
        limit: int | None = None,
    ) -> EventSlice:
        return await self._store.read(run_id, from_position=from_position, limit=limit)

    async def has_event(self, event_id: EventId, /) -> bool:
        return await self._store.has_event(event_id)
