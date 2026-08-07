"""Durable ordered Event custody over the private SQLite kernel."""

from __future__ import annotations

import sqlite3
from collections.abc import Iterable
from typing import Final, Self, final

from openrund.codec import decode_event, decode_json_value, encode_event, encode_json_value
from openrund.contracts.events import RuntimeEvent
from openrund.contracts.ids import CommandId, CorrelationId, EventId, RunId
from openrund.contracts.json import JsonObject, JsonValue, MissingType
from openrund.errors import (
    ExpectedPositionConflict,
    OpenRundError,
    ResourceClosedError,
    StorageIntegrityError,
    ValidationError,
)
from openrund.paths import PathInput
from openrund.ports.events import (
    AppendEventsInput,
    AppendEventsResult,
    AppendManyEventsInput,
    AppendManyEventsResult,
    EventSlice,
)
from openrund.storage._database import _Database

_MAX_SAFE_INTEGER: Final = 9_007_199_254_740_991

type _EventRow = tuple[
    str,
    str,
    int,
    str,
    int,
    str,
    str,
    str | None,
    str | None,
    str,
    str | None,
]


def _read_position(value: object, *, code: str, minimum: int) -> int:
    if (
        isinstance(value, bool)
        or not isinstance(value, int)
        or not minimum <= value <= _MAX_SAFE_INTEGER
    ):
        raise ValidationError(code=code)
    return value


def _optional_id(value: EventId | CorrelationId | CommandId | MissingType) -> str | None:
    if isinstance(value, MissingType):
        return None
    return value.value


def _encode_row(event: RuntimeEvent) -> _EventRow:
    frame = encode_event(event)
    envelope = decode_json_value(frame)
    if not isinstance(envelope, JsonObject):
        raise StorageIntegrityError(code="event_codec_invalid")
    payload_json = encode_json_value(envelope["payload"]).decode("utf-8")[:-1]
    return (
        event.event_id.value,
        event.run_id.value,
        event.position,
        event.event_type.value,
        event.version,
        event.timestamp.value,
        event.actor.value,
        _optional_id(event.causation_id),
        _optional_id(event.correlation_id),
        payload_json,
        _optional_id(event.command_id),
    )


def _required_text(row: sqlite3.Row, name: str) -> str:
    value = row[name]
    if not isinstance(value, str):
        raise StorageIntegrityError(code="event_row_invalid")
    return value


def _optional_text(row: sqlite3.Row, name: str) -> str | None:
    value = row[name]
    if value is not None and not isinstance(value, str):
        raise StorageIntegrityError(code="event_row_invalid")
    return value


def _required_integer(row: sqlite3.Row, name: str) -> int:
    value = row[name]
    if isinstance(value, bool) or not isinstance(value, int):
        raise StorageIntegrityError(code="event_row_invalid")
    return value


def _normalize_persisted_payload(*, event_type: str, version: int, payload: JsonValue) -> JsonValue:
    if (
        event_type == "run.created"
        and version == 1
        and isinstance(payload, JsonObject)
        and "rootID" in payload
        and "initialStatus" not in payload
    ):
        return JsonObject(entries=(*payload.entries, ("initialStatus", "created")))
    return payload


def _decode_row(row: sqlite3.Row) -> RuntimeEvent:
    try:
        event_type = _required_text(row, "type")
        version = _required_integer(row, "version")
        payload = _normalize_persisted_payload(
            event_type=event_type,
            version=version,
            payload=decode_json_value(_required_text(row, "payload_json") + "\n"),
        )
        entries: list[tuple[str, JsonValue]] = [
            ("id", _required_text(row, "event_id")),
            ("runID", _required_text(row, "run_id")),
            ("position", _required_integer(row, "position")),
            ("type", event_type),
            ("version", version),
            ("timestamp", _required_text(row, "timestamp")),
            ("actor", _required_text(row, "actor")),
        ]
        for column, wire_name in (
            ("causation_id", "causationID"),
            ("correlation_id", "correlationID"),
            ("command_id", "commandID"),
        ):
            value = _optional_text(row, column)
            if value is not None:
                entries.append((wire_name, value))
        entries.append(("payload", payload))
        return decode_event(encode_json_value(JsonObject(entries=tuple(entries))))
    except StorageIntegrityError:
        raise
    except (OpenRundError, KeyError, UnicodeError, ValueError, TypeError):
        raise StorageIntegrityError(code="event_row_invalid") from None


def _watermark(connection: sqlite3.Connection, run_id: RunId) -> int:
    row = connection.execute(
        "SELECT COUNT(*), MIN(position), MAX(position) FROM run_events WHERE run_id = ?",
        (run_id.value,),
    ).fetchone()
    if row is None:
        raise StorageIntegrityError(code="event_history_invalid")
    count, minimum, maximum = row
    if isinstance(count, bool) or not isinstance(count, int) or count < 0:
        raise StorageIntegrityError(code="event_history_invalid")
    if count == 0:
        if minimum is not None or maximum is not None:
            raise StorageIntegrityError(code="event_history_invalid")
        return 0
    if (
        isinstance(minimum, bool)
        or not isinstance(minimum, int)
        or isinstance(maximum, bool)
        or not isinstance(maximum, int)
        or minimum != 1
        or maximum != count
        or maximum > _MAX_SAFE_INTEGER
    ):
        raise StorageIntegrityError(code="event_history_invalid")
    return maximum


def _preflight_event_ids(connection: sqlite3.Connection, rows: Iterable[_EventRow]) -> None:
    for row in rows:
        if (
            connection.execute(
                "SELECT 1 FROM run_events WHERE event_id = ? LIMIT 1", (row[0],)
            ).fetchone()
            is not None
        ):
            raise StorageIntegrityError(code="event_id_duplicate")


@final
class SqliteRunEventStore:
    """Expected-watermark Event store with atomic multi-Run commits."""

    def __init__(self, database_path: PathInput, *, busy_timeout_ms: int = 5_000) -> None:
        self._database = _Database(database_path, busy_timeout_ms=busy_timeout_ms)
        self._closed = False

    async def __aenter__(self) -> Self:
        if self._closed:
            raise ResourceClosedError(resource="event_store")
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: object | None,
    ) -> None:
        await self.aclose()

    async def aclose(self) -> None:
        self._closed = True

    def _ensure_open(self) -> None:
        if self._closed:
            raise ResourceClosedError(resource="event_store")

    async def append(self, value: AppendEventsInput, /) -> AppendEventsResult:
        self._ensure_open()
        if not isinstance(value, AppendEventsInput):
            raise ValidationError(code="append_events_input_invalid")
        many = await self.append_many(AppendManyEventsInput(batches=(value,)))
        return many.results[0]

    async def append_many(self, value: AppendManyEventsInput, /) -> AppendManyEventsResult:
        self._ensure_open()
        if not isinstance(value, AppendManyEventsInput):
            raise ValidationError(code="append_many_input_invalid")
        encoded = tuple(
            (batch, tuple(_encode_row(event) for event in batch.events)) for batch in value.batches
        )

        def commit(connection: sqlite3.Connection) -> AppendManyEventsResult:
            for batch, _rows in encoded:
                actual = _watermark(connection, batch.run_id)
                if actual != batch.expected_position:
                    raise ExpectedPositionConflict(
                        run_id=batch.run_id.value,
                        expected_position=batch.expected_position,
                        actual_position=actual,
                    )
            all_rows = tuple(row for _batch, rows in encoded for row in rows)
            _preflight_event_ids(connection, all_rows)
            connection.executemany(
                "INSERT INTO run_events "
                "(event_id, run_id, position, type, version, timestamp, actor, "
                "causation_id, correlation_id, payload_json, command_id) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                all_rows,
            )
            return AppendManyEventsResult(
                results=tuple(
                    AppendEventsResult(
                        run_id=batch.run_id,
                        appended=batch.events,
                        next_position=batch.events[-1].position,
                    )
                    for batch, _rows in encoded
                )
            )

        return await self._database.write(commit)

    async def read(
        self,
        run_id: RunId,
        /,
        *,
        from_position: int = 1,
        limit: int | None = None,
    ) -> EventSlice:
        self._ensure_open()
        if not isinstance(run_id, RunId):
            raise ValidationError(code="event_read_run_id_invalid")
        start = _read_position(from_position, code="event_read_position_invalid", minimum=1)
        bounded_limit = (
            None
            if limit is None
            else _read_position(limit, code="event_read_limit_invalid", minimum=1)
        )

        def select(connection: sqlite3.Connection) -> EventSlice:
            _watermark(connection, run_id)
            sql = (
                "SELECT event_id, run_id, position, type, version, timestamp, actor, "
                "causation_id, correlation_id, payload_json, command_id "
                "FROM run_events WHERE run_id = ? AND position >= ? ORDER BY position"
            )
            parameters: tuple[object, ...] = (run_id.value, start)
            if bounded_limit is not None:
                sql += " LIMIT ?"
                parameters += (bounded_limit,)
            rows = connection.execute(sql, parameters).fetchall()
            events = tuple(_decode_row(row) for row in rows)
            for expected, event in enumerate(events, start=start):
                if event.run_id != run_id or event.position != expected:
                    raise StorageIntegrityError(code="event_history_invalid")
            next_position = start if not events else events[-1].position + 1
            return EventSlice(run_id=run_id, events=events, next_position=next_position)

        return await self._database.read(select)

    async def has_event(self, event_id: EventId, /) -> bool:
        self._ensure_open()
        if not isinstance(event_id, EventId):
            raise ValidationError(code="event_lookup_id_invalid")

        def select(connection: sqlite3.Connection) -> bool:
            return (
                connection.execute(
                    "SELECT 1 FROM run_events WHERE event_id = ? LIMIT 1",
                    (event_id.value,),
                ).fetchone()
                is not None
            )

        return await self._database.read(select)
