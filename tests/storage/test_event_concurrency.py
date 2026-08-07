from __future__ import annotations

import asyncio
import sqlite3
import time
from pathlib import Path

import pytest

from openrund.contracts.events import CoreEventType, Event, EventActor, RunStartedPayload
from openrund.contracts.ids import EventId, RunId
from openrund.contracts.time import Timestamp
from openrund.errors import ExpectedPositionConflict, StorageBusyError, StorageIntegrityError
from openrund.ports.events import AppendEventsInput, AppendManyEventsInput
from openrund.storage import SqliteRunEventStore


def _event(*, run: str, event_id: str) -> Event[CoreEventType, RunStartedPayload]:
    return Event(
        event_id=EventId(value=event_id),
        run_id=RunId(value=run),
        position=1,
        event_type=CoreEventType.RUN_STARTED,
        timestamp=Timestamp(value="2026-01-02T03:04:05.000Z"),
        actor=EventActor.SYSTEM,
        payload=RunStartedPayload(),
    )


def _batch(*, run: str, event_id: str) -> AppendEventsInput:
    event = _event(run=run, event_id=event_id)
    return AppendEventsInput(run_id=event.run_id, expected_position=0, events=(event,))


def test_competing_single_run_writers_have_exactly_one_winner(database_path: Path) -> None:
    async def scenario() -> None:
        stores = (SqliteRunEventStore(database_path), SqliteRunEventStore(database_path))
        barrier = asyncio.Barrier(2)

        async def compete(index: int) -> object:
            await barrier.wait()
            return await stores[index].append(_batch(run="run-1", event_id=f"event-{index}"))

        outcomes = await asyncio.gather(compete(0), compete(1), return_exceptions=True)
        assert sum(not isinstance(outcome, BaseException) for outcome in outcomes) == 1
        assert sum(isinstance(outcome, ExpectedPositionConflict) for outcome in outcomes) == 1
        history = await stores[0].read(RunId(value="run-1"))
        assert len(history.events) == 1
        assert history.events[0].event_id.value in {"event-0", "event-1"}

    asyncio.run(scenario())


def test_overlapping_multi_run_writers_never_mix_commits(database_path: Path) -> None:
    async def scenario() -> None:
        stores = (SqliteRunEventStore(database_path), SqliteRunEventStore(database_path))
        barrier = asyncio.Barrier(2)

        async def compete(label: str, store: SqliteRunEventStore) -> object:
            value = AppendManyEventsInput(
                batches=(
                    _batch(run="run-a", event_id=f"{label}-a"),
                    _batch(run="run-b", event_id=f"{label}-b"),
                )
            )
            await barrier.wait()
            return await store.append_many(value)

        outcomes = await asyncio.gather(
            compete("left", stores[0]),
            compete("right", stores[1]),
            return_exceptions=True,
        )
        assert sum(not isinstance(outcome, BaseException) for outcome in outcomes) == 1
        assert sum(isinstance(outcome, ExpectedPositionConflict) for outcome in outcomes) == 1
        identifiers = {
            (await stores[0].read(RunId(value=run))).events[0].event_id.value
            for run in ("run-a", "run-b")
        }
        assert identifiers in ({"left-a", "left-b"}, {"right-a", "right-b"})

    asyncio.run(scenario())


def test_append_many_rolls_back_every_run_on_sql_fault(database_path: Path) -> None:
    async def scenario() -> None:
        store = SqliteRunEventStore(database_path)
        connection = sqlite3.connect(database_path)
        connection.execute(
            "CREATE TRIGGER reject_run_b BEFORE INSERT ON run_events "
            "WHEN NEW.run_id = 'run-b' BEGIN SELECT RAISE(ABORT, 'injected'); END"
        )
        connection.commit()
        connection.close()

        with pytest.raises(StorageIntegrityError):
            await store.append_many(
                AppendManyEventsInput(
                    batches=(
                        _batch(run="run-a", event_id="event-a"),
                        _batch(run="run-b", event_id="event-b"),
                    )
                )
            )
        assert (await store.read(RunId(value="run-a"))).events == ()
        assert (await store.read(RunId(value="run-b"))).events == ()

    asyncio.run(scenario())


def test_stale_batch_prevents_every_multi_run_insert(database_path: Path) -> None:
    async def scenario() -> None:
        store = SqliteRunEventStore(database_path)
        await store.append(_batch(run="run-a", event_id="existing"))
        with pytest.raises(ExpectedPositionConflict):
            await store.append_many(
                AppendManyEventsInput(
                    batches=(
                        _batch(run="run-a", event_id="stale"),
                        _batch(run="run-b", event_id="must-not-commit"),
                    )
                )
            )
        assert (await store.read(RunId(value="run-b"))).events == ()

    asyncio.run(scenario())


def test_externally_held_write_lock_returns_bounded_busy(database_path: Path) -> None:
    store = SqliteRunEventStore(database_path, busy_timeout_ms=15)
    lock = sqlite3.connect(database_path, isolation_level=None)
    lock.execute("BEGIN IMMEDIATE")
    started = time.monotonic()
    try:
        with pytest.raises(StorageBusyError):
            asyncio.run(store.append(_batch(run="run-1", event_id="event-1")))
    finally:
        lock.execute("ROLLBACK")
        lock.close()
    assert time.monotonic() - started < 1.0
