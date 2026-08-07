"""Advisory post-commit Event observation with isolated subscriber failures."""

from __future__ import annotations

from collections.abc import Awaitable, Callable, Iterable
from contextlib import suppress
from dataclasses import dataclass
from typing import cast, final

from openrund.contracts.events import RuntimeEvent
from openrund.contracts.ids import EventId, RunId
from openrund.errors import ValidationError
from openrund.ports.events import AppendEventsInput, AppendEventsResult, EventSlice, EventStore

type EventSubscriber = Callable[[tuple[RuntimeEvent, ...]], Awaitable[None]]
type SubscriberFailureSink = Callable[["PostCommitSubscriberFailure"], Awaitable[None]]


@final
@dataclass(frozen=True, slots=True, kw_only=True)
class PostCommitSubscriberFailure:
    """Sanitized advisory failure identity with no exception message or payload."""

    subscriber_index: int
    event_ids: tuple[EventId, ...]
    code: str = "post_commit_subscriber_failed"

    def __post_init__(self) -> None:
        if (
            isinstance(self.subscriber_index, bool)
            or not isinstance(self.subscriber_index, int)
            or self.subscriber_index < 0
        ):
            raise ValidationError(code="subscriber_failure_index_invalid")
        try:
            event_ids: tuple[object, ...] = tuple(self.event_ids)
        except TypeError as error:
            raise ValidationError(code="subscriber_failure_event_ids_invalid") from error
        if any(not isinstance(event_id, EventId) for event_id in event_ids):
            raise ValidationError(code="subscriber_failure_event_ids_invalid")
        if self.code != "post_commit_subscriber_failed":
            raise ValidationError(code="subscriber_failure_code_invalid")
        object.__setattr__(self, "event_ids", cast(tuple[EventId, ...], event_ids))


@final
class PostCommitEventLog:
    """Delegate durable storage first, then notify ordered advisory subscribers."""

    def __init__(
        self,
        store: EventStore,
        subscribers: Iterable[EventSubscriber],
        failure_sink: SubscriberFailureSink,
    ) -> None:
        if not all(
            callable(getattr(store, name, None)) for name in ("append", "read", "has_event")
        ):
            raise ValidationError(code="post_commit_store_invalid")
        try:
            ordered: tuple[object, ...] = tuple(subscribers)
        except TypeError as error:
            raise ValidationError(code="post_commit_subscribers_invalid") from error
        if any(not callable(subscriber) for subscriber in ordered):
            raise ValidationError(code="post_commit_subscribers_invalid")
        if not callable(failure_sink):
            raise ValidationError(code="post_commit_failure_sink_invalid")
        self._store = store
        self._subscribers = cast(tuple[EventSubscriber, ...], ordered)
        self._failure_sink = failure_sink

    async def append(self, value: AppendEventsInput, /) -> AppendEventsResult:
        result = await self._store.append(value)
        committed = result.appended
        event_ids = tuple(event.event_id for event in committed)
        for index, subscriber in enumerate(self._subscribers):
            try:
                await subscriber(committed)
            except Exception:
                failure = PostCommitSubscriberFailure(
                    subscriber_index=index,
                    event_ids=event_ids,
                )
                with suppress(Exception):
                    await self._failure_sink(failure)
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
