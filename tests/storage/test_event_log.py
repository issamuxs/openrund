from __future__ import annotations

import ast
import asyncio
from pathlib import Path

import pytest

from openrund._testing.memory import MemoryEventStore
from openrund.contracts.events import CoreEventType, Event, EventActor, RunStartedPayload
from openrund.contracts.ids import EventId, RunId
from openrund.contracts.time import Timestamp
from openrund.errors import ExpectedPositionConflict
from openrund.ports.events import AppendEventsInput
from openrund.storage import PostCommitEventLog, PostCommitSubscriberFailure


def _event(position: int = 1) -> Event[CoreEventType, RunStartedPayload]:
    return Event(
        event_id=EventId(value=f"event-{position}"),
        run_id=RunId(value="run-1"),
        position=position,
        event_type=CoreEventType.RUN_STARTED,
        timestamp=Timestamp(value="2026-01-02T03:04:05.000Z"),
        actor=EventActor.SYSTEM,
        payload=RunStartedPayload(),
    )


def _append(position: int = 1, expected: int = 0) -> AppendEventsInput:
    event = _event(position)
    return AppendEventsInput(
        run_id=event.run_id,
        expected_position=expected,
        events=(event,),
    )


def test_post_commit_log_commits_before_ordered_callbacks_and_delegates_reads() -> None:
    async def scenario() -> None:
        store = MemoryEventStore()
        observations: list[tuple[str, tuple[object, ...]]] = []
        failures: list[PostCommitSubscriberFailure] = []

        async def first(events: tuple[object, ...]) -> None:
            committed = await store.has_event(_event().event_id)
            observations.append(("first", (events, committed)))

        async def second(events: tuple[object, ...]) -> None:
            observations.append(("second", (events,)))

        async def sink(failure: PostCommitSubscriberFailure) -> None:
            failures.append(failure)

        log = PostCommitEventLog(store, (first, second), sink)
        result = await log.append(_append())
        assert result.next_position == 1
        assert observations == [
            ("first", (result.appended, True)),
            ("second", (result.appended,)),
        ]
        assert failures == []
        assert await log.has_event(_event().event_id) is True
        assert (await log.read(RunId(value="run-1"))).events == result.appended

    asyncio.run(scenario())


def test_subscriber_failures_are_sanitized_isolated_and_never_retry_append() -> None:
    async def scenario() -> None:
        store = MemoryEventStore()
        received: list[tuple[object, ...]] = []
        failures: list[PostCommitSubscriberFailure] = []

        async def fail(_events: tuple[object, ...]) -> None:
            raise RuntimeError("secret payload and path /private/tmp/sensitive")

        async def observe(events: tuple[object, ...]) -> None:
            received.append(events)

        async def sink(failure: PostCommitSubscriberFailure) -> None:
            failures.append(failure)

        log = PostCommitEventLog(
            store,
            (fail, observe, fail),
            sink,
        )
        result = await log.append(_append())
        assert received == [result.appended]
        assert received[0] is result.appended
        assert failures == [
            PostCommitSubscriberFailure(subscriber_index=0, event_ids=(_event().event_id,)),
            PostCommitSubscriberFailure(subscriber_index=2, event_ids=(_event().event_id,)),
        ]
        assert tuple(call.operation for call in store.calls).count("append") == 1
        assert "secret" not in repr(failures)

    asyncio.run(scenario())


def test_failed_store_append_notifies_nobody() -> None:
    async def scenario() -> None:
        store = MemoryEventStore()
        delivered = 0
        reported = 0

        async def subscriber(_events: tuple[object, ...]) -> None:
            nonlocal delivered
            delivered += 1

        async def sink(_failure: PostCommitSubscriberFailure) -> None:
            nonlocal reported
            reported += 1

        log = PostCommitEventLog(store, (subscriber,), sink)
        await log.append(_append())
        with pytest.raises(ExpectedPositionConflict):
            await log.append(_append())
        assert delivered == 1
        assert reported == 0
        assert tuple(call.operation for call in store.calls).count("append") == 2

    asyncio.run(scenario())


def test_cancellation_is_not_swallowed_after_commit() -> None:
    async def scenario() -> None:
        store = MemoryEventStore()
        failures: list[PostCommitSubscriberFailure] = []

        async def cancel(_events: tuple[object, ...]) -> None:
            raise asyncio.CancelledError

        async def sink(failure: PostCommitSubscriberFailure) -> None:
            failures.append(failure)

        log = PostCommitEventLog(store, (cancel,), sink)
        with pytest.raises(asyncio.CancelledError):
            await log.append(_append())
        assert await store.has_event(_event().event_id) is True
        assert failures == []

    asyncio.run(scenario())


def test_post_commit_wrapper_has_no_persistence_or_authority_bypass() -> None:
    source = Path(__file__).parents[2] / "src" / "openrund" / "storage" / "_event_log.py"
    tree = ast.parse(source.read_text(encoding="utf-8"))
    imports = {
        node.module
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom) and node.module is not None
    }
    assert all(
        not name.startswith(("sqlite3", "openrund.codec", "openrund.engine")) for name in imports
    )
    assert {"append", "read", "has_event"}.issubset(dir(PostCommitEventLog))
    assert {"append_many", "decide_legality", "grant_authority"}.isdisjoint(dir(PostCommitEventLog))
