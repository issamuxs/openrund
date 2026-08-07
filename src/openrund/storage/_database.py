"""Private SQLite lifecycle, migration, and transaction boundary."""

from __future__ import annotations

import asyncio
import sqlite3
from collections.abc import Callable
from contextlib import suppress
from pathlib import Path
from typing import Final, Never, final

from openrund.errors import (
    OpenRundError,
    StorageBusyError,
    StorageError,
    StorageIntegrityError,
    ValidationError,
)
from openrund.paths import PathInput, normalize_local_path

_SCHEMA_VERSION: Final = 2
_MAX_BUSY_TIMEOUT_MS: Final = 2_147_483_647

_RUN_EVENTS_COLUMNS: Final = (
    "event_id",
    "run_id",
    "position",
    "type",
    "version",
    "timestamp",
    "actor",
    "causation_id",
    "correlation_id",
    "payload_json",
    "command_id",
)
_ARTIFACT_COLUMNS: Final = (
    "artifact_id",
    "kind",
    "created_at",
    "content_type",
    "byte_length",
    "metadata_json",
    "blob_path",
    "unavailable_at",
    "sha256",
)
_LEASE_COLUMNS: Final = (
    "lease_id",
    "run_id",
    "holder",
    "token",
    "acquired_at",
    "expires_at",
)

_CREATE_RUN_EVENTS: Final = """
CREATE TABLE IF NOT EXISTS run_events (
    event_id TEXT PRIMARY KEY,
    run_id TEXT NOT NULL,
    position INTEGER NOT NULL,
    type TEXT NOT NULL,
    version INTEGER NOT NULL,
    timestamp TEXT NOT NULL,
    actor TEXT NOT NULL,
    causation_id TEXT,
    correlation_id TEXT,
    payload_json TEXT NOT NULL,
    command_id TEXT,
    UNIQUE(run_id, position)
)
"""
_CREATE_ARTIFACTS: Final = """
CREATE TABLE IF NOT EXISTS artifacts (
    artifact_id TEXT PRIMARY KEY,
    kind TEXT NOT NULL,
    created_at TEXT NOT NULL,
    content_type TEXT,
    byte_length INTEGER,
    metadata_json TEXT NOT NULL,
    blob_path TEXT,
    unavailable_at TEXT
)
"""
_CREATE_LEASES: Final = """
CREATE TABLE IF NOT EXISTS execution_leases (
    lease_id TEXT PRIMARY KEY,
    run_id TEXT NOT NULL UNIQUE,
    holder TEXT NOT NULL,
    token TEXT NOT NULL,
    acquired_at TEXT NOT NULL,
    expires_at TEXT NOT NULL
)
"""


def _busy_timeout(value: object) -> int:
    if (
        isinstance(value, bool)
        or not isinstance(value, int)
        or not 1 <= value <= _MAX_BUSY_TIMEOUT_MS
    ):
        raise ValidationError(code="storage_busy_timeout_invalid")
    return value


def _translate(error: BaseException) -> Never:
    if isinstance(error, OpenRundError):
        raise error
    if isinstance(error, sqlite3.OperationalError):
        code = getattr(error, "sqlite_errorcode", None)
        if code in (sqlite3.SQLITE_BUSY, sqlite3.SQLITE_LOCKED) or "locked" in str(error).lower():
            raise StorageBusyError() from None
        raise StorageError(code="storage_operation_failed") from None
    if isinstance(error, sqlite3.IntegrityError):
        raise StorageIntegrityError(code="storage_constraint_failed") from None
    if isinstance(error, sqlite3.DatabaseError):
        raise StorageIntegrityError(code="storage_database_invalid") from None
    if isinstance(error, OSError):
        raise StorageError(code="storage_io_failed") from None
    raise error


def _columns(connection: sqlite3.Connection, table: str) -> tuple[str, ...]:
    rows = connection.execute(f'PRAGMA table_info("{table}")').fetchall()
    return tuple(str(row[1]) for row in rows)


def _unique_index_exists(
    connection: sqlite3.Connection, table: str, expected_columns: tuple[str, ...]
) -> bool:
    for row in connection.execute(f'PRAGMA index_list("{table}")').fetchall():
        if int(row[2]) != 1:
            continue
        name = str(row[1]).replace('"', '""')
        columns = tuple(
            str(item[2]) for item in connection.execute(f'PRAGMA index_info("{name}")').fetchall()
        )
        if columns == expected_columns:
            return True
    return False


def _named_index_matches(
    connection: sqlite3.Connection,
    *,
    table: str,
    name: str,
    expected_columns: tuple[str, ...],
) -> bool:
    for row in connection.execute(f'PRAGMA index_list("{table}")').fetchall():
        if str(row[1]) != name or int(row[2]) != 0:
            continue
        escaped = name.replace('"', '""')
        columns = tuple(
            str(item[2])
            for item in connection.execute(f'PRAGMA index_info("{escaped}")').fetchall()
        )
        return columns == expected_columns
    return False


@final
class _Database:
    """Short-lived configured connections over one versioned local database."""

    def __init__(self, database_path: PathInput, *, busy_timeout_ms: int = 5_000) -> None:
        local = normalize_local_path(database_path)
        self._path = Path(local.path)
        self._busy_timeout_ms = _busy_timeout(busy_timeout_ms)
        self._initialize()

    @property
    def path(self) -> Path:
        return self._path

    @property
    def busy_timeout_ms(self) -> int:
        return self._busy_timeout_ms

    async def read[T](self, operation: Callable[[sqlite3.Connection], T], /) -> T:
        return await asyncio.to_thread(self.read_sync, operation)

    async def write[T](self, operation: Callable[[sqlite3.Connection], T], /) -> T:
        return await asyncio.to_thread(self.write_sync, operation)

    def read_sync[T](self, operation: Callable[[sqlite3.Connection], T], /) -> T:
        connection: sqlite3.Connection | None = None
        try:
            connection = self._connect()
            return operation(connection)
        except BaseException as error:
            _translate(error)
        finally:
            if connection is not None:
                connection.close()

    def write_sync[T](self, operation: Callable[[sqlite3.Connection], T], /) -> T:
        connection: sqlite3.Connection | None = None
        began = False
        try:
            connection = self._connect()
            connection.execute("BEGIN IMMEDIATE")
            began = True
            result = operation(connection)
            connection.execute("COMMIT")
            began = False
            return result
        except BaseException as error:
            if connection is not None and began:
                with suppress(sqlite3.Error):
                    connection.execute("ROLLBACK")
            _translate(error)
        finally:
            if connection is not None:
                connection.close()

    def _initialize(self) -> None:
        connection: sqlite3.Connection | None = None
        try:
            self._path.parent.mkdir(parents=True, exist_ok=True)
            connection = self._connect()
            self._migrate(connection)
        except BaseException as error:
            _translate(error)
        finally:
            if connection is not None:
                connection.close()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(
            self._path,
            timeout=self._busy_timeout_ms / 1_000,
            isolation_level=None,
            check_same_thread=True,
        )
        connection.row_factory = sqlite3.Row
        try:
            connection.execute(f"PRAGMA busy_timeout = {self._busy_timeout_ms}")
            connection.execute("PRAGMA foreign_keys = ON")
            journal_mode = connection.execute("PRAGMA journal_mode = WAL").fetchone()
            if journal_mode is None or str(journal_mode[0]).lower() != "wal":
                raise StorageError(code="storage_wal_unavailable")
            connection.execute("PRAGMA synchronous = FULL")
            return connection
        except BaseException:
            connection.close()
            raise

    def _migrate(self, connection: sqlite3.Connection) -> None:
        row = connection.execute("PRAGMA user_version").fetchone()
        version = 0 if row is None else int(row[0])
        if version > _SCHEMA_VERSION:
            raise StorageIntegrityError(code="storage_schema_newer")

        began = False
        try:
            connection.execute("BEGIN IMMEDIATE")
            began = True
            connection.execute(_CREATE_RUN_EVENTS)
            connection.execute(_CREATE_ARTIFACTS)
            connection.execute(_CREATE_LEASES)

            if "command_id" not in _columns(connection, "run_events"):
                connection.execute("ALTER TABLE run_events ADD COLUMN command_id TEXT")
            if "sha256" not in _columns(connection, "artifacts"):
                connection.execute("ALTER TABLE artifacts ADD COLUMN sha256 TEXT")

            connection.execute(
                "CREATE INDEX IF NOT EXISTS idx_run_events_stream ON run_events(run_id, position)"
            )
            connection.execute(
                "CREATE INDEX IF NOT EXISTS idx_execution_leases_active "
                "ON execution_leases(run_id, expires_at)"
            )
            self._validate_schema(connection)
            connection.execute(f"PRAGMA user_version = {_SCHEMA_VERSION}")
            connection.execute("COMMIT")
            began = False
        except BaseException:
            if began:
                with suppress(sqlite3.Error):
                    connection.execute("ROLLBACK")
            raise

    @staticmethod
    def _validate_schema(connection: sqlite3.Connection) -> None:
        expected = {
            "run_events": _RUN_EVENTS_COLUMNS,
            "artifacts": _ARTIFACT_COLUMNS,
            "execution_leases": _LEASE_COLUMNS,
        }
        for table, columns in expected.items():
            if _columns(connection, table) != columns:
                raise StorageIntegrityError(code="storage_schema_invalid")
        if not _named_index_matches(
            connection,
            table="run_events",
            name="idx_run_events_stream",
            expected_columns=("run_id", "position"),
        ) or not _named_index_matches(
            connection,
            table="execution_leases",
            name="idx_execution_leases_active",
            expected_columns=("run_id", "expires_at"),
        ):
            raise StorageIntegrityError(code="storage_schema_invalid")
        if not _unique_index_exists(connection, "run_events", ("run_id", "position")):
            raise StorageIntegrityError(code="storage_schema_invalid")
        if not _unique_index_exists(connection, "execution_leases", ("run_id",)):
            raise StorageIntegrityError(code="storage_schema_invalid")
