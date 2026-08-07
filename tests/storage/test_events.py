from __future__ import annotations

import asyncio
import sqlite3
from pathlib import Path

import pytest

from openrund.contracts.events import CoreEventType, Event, EventActor, RunStartedPayload
from openrund.contracts.ids import CommandId, CorrelationId, EventId, RunId
from openrund.contracts.json import MISSING
from openrund.contracts.time import Timestamp
from openrund.errors import ExpectedPositionConflict, StorageIntegrityError, ValidationError
from openrund.ports.events import AppendEventsInput
from openrund.storage import SqliteRunEventStore


def _event(
    position: int,
    *,
    run: str = "run-1",
    event_id: str | None = None,
    linked: bool = False,
) -> Event[CoreEventType, RunStartedPayload]:
    return Event(
        event_id=EventId(value=event_id or f"{run}-event-{position}"),
        run_id=RunId(value=run),
        position=position,
        event_type=CoreEventType.RUN_STARTED,
        timestamp=Timestamp(value="2026-01-02T03:04:05.000Z"),
        actor=EventActor.SYSTEM,
        payload=RunStartedPayload(reason="continue"),
        causation_id=EventId(value="cause") if linked else MISSING,
        correlation_id=CorrelationId(value="correlation") if linked else MISSING,
        command_id=CommandId(value="command") if linked else MISSING,
    )


def test_event_store_appends_reads_links_limits_and_reopens(database_path: Path) -> None:
    async def scenario() -> None:
        store = SqliteRunEventStore(database_path)
        first = _event(1)
        linked = _event(2, linked=True)
        result = await store.append(
            AppendEventsInput(
                run_id=RunId(value="run-1"), expected_position=0, events=(first, linked)
            )
        )
        assert result.appended == (first, linked)
        assert result.next_position == 2
        assert await store.has_event(linked.event_id) is True

        page = await store.read(RunId(value="run-1"), from_position=1, limit=1)
        assert page.events == (first,)
        assert page.next_position == 2
        reopened = SqliteRunEventStore(database_path)
        remainder = await reopened.read(RunId(value="run-1"), from_position=2)
        assert remainder.events == (linked,)
        assert remainder.next_position == 3
        assert (await reopened.read(RunId(value="run-1"), from_position=3)).next_position == 3
        assert (await reopened.read(RunId(value="missing"))).next_position == 1

    asyncio.run(scenario())


def test_event_store_rejects_stale_and_duplicate_identity_without_partial_write(
    database_path: Path,
) -> None:
    async def scenario() -> None:
        store = SqliteRunEventStore(database_path)
        first = _event(1)
        await store.append(
            AppendEventsInput(run_id=first.run_id, expected_position=0, events=(first,))
        )
        with pytest.raises(ExpectedPositionConflict) as raised:
            await store.append(
                AppendEventsInput(run_id=first.run_id, expected_position=0, events=(_event(1),))
            )
        assert raised.value.actual_position == 1
        assert raised.value.expected_position == 0

        duplicate = _event(1, run="run-2", event_id=first.event_id.value)
        with pytest.raises(StorageIntegrityError, match="event_id_duplicate"):
            await store.append(
                AppendEventsInput(run_id=duplicate.run_id, expected_position=0, events=(duplicate,))
            )
        assert (await store.read(duplicate.run_id)).events == ()

    asyncio.run(scenario())


@pytest.mark.parametrize("corruption", ["gap", "payload", "position_type"])
def test_event_store_fails_closed_on_corrupt_history(database_path: Path, corruption: str) -> None:
    async def scenario() -> None:
        store = SqliteRunEventStore(database_path)
        events = (_event(1), _event(2))
        await store.append(
            AppendEventsInput(run_id=events[0].run_id, expected_position=0, events=events)
        )
        connection = sqlite3.connect(database_path)
        if corruption == "gap":
            connection.execute("UPDATE run_events SET position = 3 WHERE position = 2")
        elif corruption == "payload":
            connection.execute("UPDATE run_events SET payload_json = 'not-json' WHERE position = 1")
        else:
            connection.execute("UPDATE run_events SET position = 'bad' WHERE position = 1")
        connection.commit()
        connection.close()

        with pytest.raises(StorageIntegrityError):
            await store.read(
                events[0].run_id,
                from_position=3 if corruption == "gap" else 1,
            )

    asyncio.run(scenario())


@pytest.mark.parametrize("from_position,limit", [(0, None), (True, None), (1, 0), (1, True)])
def test_event_store_validates_read_bounds(
    database_path: Path, from_position: object, limit: object
) -> None:
    store = SqliteRunEventStore(database_path)
    with pytest.raises(ValidationError):
        asyncio.run(
            store.read(
                RunId(value="run-1"),
                from_position=from_position,  # type: ignore[arg-type]
                limit=limit,  # type: ignore[arg-type]
            )
        )
