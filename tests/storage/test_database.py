from __future__ import annotations

import asyncio
import sqlite3
from pathlib import Path

import pytest

from openrund.errors import StorageBusyError, StorageIntegrityError, ValidationError
from openrund.storage._database import _Database


def _column_names(connection: sqlite3.Connection, table: str) -> tuple[str, ...]:
    return tuple(str(row[1]) for row in connection.execute(f"PRAGMA table_info({table})"))


def test_database_creates_exact_additive_schema_and_connection_policy(
    database_path: Path,
) -> None:
    database = _Database(database_path, busy_timeout_ms=37)

    def inspect(connection: sqlite3.Connection) -> tuple[object, ...]:
        return (
            connection.execute("PRAGMA user_version").fetchone()[0],
            connection.execute("PRAGMA journal_mode").fetchone()[0],
            connection.execute("PRAGMA foreign_keys").fetchone()[0],
            connection.execute("PRAGMA synchronous").fetchone()[0],
            connection.execute("PRAGMA busy_timeout").fetchone()[0],
            _column_names(connection, "run_events"),
            _column_names(connection, "artifacts"),
            _column_names(connection, "execution_leases"),
            tuple(
                row[0]
                for row in connection.execute(
                    "SELECT name FROM sqlite_master WHERE type = 'index' "
                    "AND name NOT LIKE 'sqlite_autoindex_%' ORDER BY name"
                )
            ),
        )

    inspected = asyncio.run(database.read(inspect))
    assert inspected == (
        2,
        "wal",
        1,
        2,
        37,
        (
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
        ),
        (
            "artifact_id",
            "kind",
            "created_at",
            "content_type",
            "byte_length",
            "metadata_json",
            "blob_path",
            "unavailable_at",
            "sha256",
        ),
        ("lease_id", "run_id", "holder", "token", "acquired_at", "expires_at"),
        ("idx_execution_leases_active", "idx_run_events_stream"),
    )

    reopened = _Database(database_path, busy_timeout_ms=37)
    assert (
        asyncio.run(
            reopened.read(
                lambda connection: connection.execute("PRAGMA user_version").fetchone()[0]
            )
        )
        == 2
    )


def test_database_migrates_legacy_event_table_without_rewriting_rows(
    database_path: Path,
) -> None:
    database_path.parent.mkdir(parents=True)
    connection = sqlite3.connect(database_path)
    connection.execute(
        """
        CREATE TABLE run_events (
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
            UNIQUE(run_id, position)
        )
        """
    )
    connection.execute(
        "INSERT INTO run_events VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        ("e1", "r1", 1, "run.created", 1, "2026-01-02T03:04:05.000Z", "system", None, None, "{}"),
    )
    connection.commit()
    connection.close()

    _Database(database_path)
    migrated = sqlite3.connect(database_path)
    try:
        assert _column_names(migrated, "run_events")[-1] == "command_id"
        assert migrated.execute(
            "SELECT event_id, payload_json, command_id FROM run_events"
        ).fetchone() == ("e1", "{}", None)
    finally:
        migrated.close()


def test_database_rejects_newer_or_invalid_schema(database_path: Path) -> None:
    database_path.parent.mkdir(parents=True)
    connection = sqlite3.connect(database_path)
    connection.execute("PRAGMA user_version = 99")
    connection.close()
    with pytest.raises(StorageIntegrityError, match="storage_schema_newer"):
        _Database(database_path)

    malformed = database_path.parent / "malformed.sqlite"
    malformed.write_bytes(b"not sqlite")
    with pytest.raises(StorageIntegrityError) as raised:
        _Database(malformed)
    assert str(malformed) not in str(raised.value)


def test_database_rejects_named_index_with_wrong_definition(database_path: Path) -> None:
    _Database(database_path)
    connection = sqlite3.connect(database_path)
    connection.execute("DROP INDEX idx_run_events_stream")
    connection.execute("CREATE INDEX idx_run_events_stream ON run_events(position)")
    connection.commit()
    connection.close()

    with pytest.raises(StorageIntegrityError, match="storage_schema_invalid"):
        _Database(database_path)


def test_database_rolls_back_fault_and_maps_bounded_busy(database_path: Path) -> None:
    database = _Database(database_path, busy_timeout_ms=10)

    def fail_after_insert(connection: sqlite3.Connection) -> None:
        connection.execute(
            "INSERT INTO execution_leases VALUES (?, ?, ?, ?, ?, ?)",
            ("l1", "r1", "worker", "token", "2026-01-02T03:04:05.000Z", "2026-01-02T03:05:05.000Z"),
        )
        raise RuntimeError("injected")

    with pytest.raises(RuntimeError, match="injected"):
        asyncio.run(database.write(fail_after_insert))
    count = asyncio.run(
        database.read(
            lambda connection: connection.execute(
                "SELECT COUNT(*) FROM execution_leases"
            ).fetchone()[0]
        )
    )
    assert count == 0

    lock = sqlite3.connect(database_path, isolation_level=None)
    lock.execute("BEGIN IMMEDIATE")
    try:
        with pytest.raises(StorageBusyError):
            asyncio.run(database.write(lambda connection: connection.execute("SELECT 1")))
    finally:
        lock.execute("ROLLBACK")
        lock.close()


@pytest.mark.parametrize("value", [True, False, 0, -1, 2_147_483_648])
def test_database_rejects_invalid_busy_timeout(database_path: Path, value: int) -> None:
    with pytest.raises(ValidationError, match="storage_busy_timeout_invalid"):
        _Database(database_path, busy_timeout_ms=value)
