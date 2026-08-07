from __future__ import annotations

import asyncio
import hashlib
import json
import sqlite3
import stat
from collections import Counter
from collections.abc import Iterator, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Final, cast

import pytest
from tests.conftest import (
    CORPUS_ROOT,
    MANIFEST_PATH,
    CorpusEntry,
    FrozenJson,
    read_corpus_entry,
)

from openrund.codec import encode_event
from openrund.contracts.ids import ArtifactId, LeaseId, RunId
from openrund.contracts.json import MISSING, JsonObject
from openrund.contracts.time import Timestamp
from openrund.ports.artifacts import ArtifactEntry
from openrund.ports.leases import LeaseAcquireInput
from openrund.storage import (
    SqliteArtifactStore,
    SqliteExecutionLeaseStore,
    SqliteRunEventStore,
)
from openrund.storage._database import _Database

_EXPECTED_KEY_COUNTS: Final = Counter({"table": 3, "column": 25, "index": 2, "constraint": 2})


@dataclass(frozen=True, slots=True)
class _Evidence:
    entry: CorpusEntry
    content: bytes
    record: Mapping[str, object]


def _mapping(value: object) -> Mapping[str, object]:
    assert isinstance(value, dict)
    assert all(isinstance(key, str) for key in value)
    return cast(Mapping[str, object], value)


def _string(value: object) -> str:
    assert isinstance(value, str)
    return value


def _integer(value: object) -> int:
    assert isinstance(value, int) and not isinstance(value, bool)
    return value


def _index_rows(database: _Database, table: str) -> tuple[sqlite3.Row, ...]:
    return database.read_sync(
        lambda connection: tuple(connection.execute(f'PRAGMA index_list("{table}")').fetchall())
    )


@pytest.fixture(scope="module")
def sqlite_entries() -> tuple[CorpusEntry, ...]:
    manifest = _mapping(json.loads(MANIFEST_PATH.read_text(encoding="utf-8")))
    raw_rows = manifest.get("sqlite")
    assert isinstance(raw_rows, list)
    entries: list[CorpusEntry] = []
    for raw in raw_rows:
        row = _mapping(raw)
        entries.append(
            CorpusEntry(
                category="sqlite",
                key=_string(row.get("key")),
                relative_path=_string(row.get("relativePath")),
                byte_length=_integer(row.get("byteLength")),
                sha256=_string(row.get("sha256")),
                decoded_meaning=cast(FrozenJson, row.get("decodedMeaning")),
                required_pointers=tuple(cast(list[str], row.get("requiredPointers"))),
                absent_pointers=tuple(cast(list[str], row.get("absentPointers"))),
                null_pointers=tuple(cast(list[str], row.get("nullPointers"))),
                manifest_entry=cast(Mapping[str, FrozenJson], row),
            )
        )
    assert len(entries) == 32
    assert len({entry.key for entry in entries}) == 32
    assert len({entry.relative_path for entry in entries}) == 32
    assert Counter(entry.key.split(":", 2)[1] for entry in entries) == _EXPECTED_KEY_COUNTS
    return tuple(entries)


def _snapshot(entries: tuple[CorpusEntry, ...]) -> tuple[tuple[str, int, int, str], ...]:
    paths = (MANIFEST_PATH, *(CORPUS_ROOT / entry.relative_path for entry in entries))
    return tuple(
        (
            path.relative_to(CORPUS_ROOT).as_posix(),
            path.lstat().st_mode,
            path.lstat().st_size,
            hashlib.sha256(path.read_bytes()).hexdigest(),
        )
        for path in paths
    )


@pytest.fixture(scope="module", autouse=True)
def frozen_sqlite_evidence_unchanged(
    sqlite_entries: tuple[CorpusEntry, ...],
) -> Iterator[None]:
    before = _snapshot(sqlite_entries)
    yield
    assert _snapshot(sqlite_entries) == before


@pytest.fixture(scope="module")
def sqlite_evidence(sqlite_entries: tuple[CorpusEntry, ...]) -> tuple[_Evidence, ...]:
    authenticated: list[_Evidence] = []
    for entry in sqlite_entries:
        content = read_corpus_entry(entry)
        parsed = _mapping(json.loads(content))
        authenticated.append(_Evidence(entry=entry, content=content, record=parsed))
    return tuple(authenticated)


def _schema(evidence: _Evidence) -> Mapping[str, object]:
    return _mapping(evidence.record.get("schema"))


def _by_key(evidence: tuple[_Evidence, ...]) -> dict[str, _Evidence]:
    return {item.entry.key: item for item in evidence}


def test_exact_sqlite_inventory_authenticates_once_and_copies_only_to_temp(
    sqlite_evidence: tuple[_Evidence, ...], tmp_path: Path
) -> None:
    copy_root = tmp_path / "evidence"
    copy_root.mkdir()
    consumed: list[str] = []
    for evidence in sqlite_evidence:
        assert len(evidence.content) == evidence.entry.byte_length
        assert hashlib.sha256(evidence.content).hexdigest() == evidence.entry.sha256
        copied = copy_root / Path(evidence.entry.relative_path).name
        copied.write_bytes(evidence.content)
        assert json.loads(copied.read_bytes()) == evidence.record
        consumed.append(evidence.entry.key)

    expected_files = {entry.entry.relative_path for entry in sqlite_evidence}
    actual_files = {
        path.relative_to(CORPUS_ROOT).as_posix()
        for path in (CORPUS_ROOT / "evidence").glob("sqlite-*.jsonl")
        if stat.S_ISREG(path.lstat().st_mode)
    }
    assert actual_files == expected_files
    assert consumed == [entry.entry.key for entry in sqlite_evidence]
    assert len(consumed) == len(set(consumed)) == 32


def test_authenticated_v1_schema_matches_with_only_nullable_digest_extension(
    sqlite_evidence: tuple[_Evidence, ...], database_path: Path
) -> None:
    database = _Database(database_path)
    indexed = _by_key(sqlite_evidence)

    def inspect(
        connection: sqlite3.Connection,
    ) -> tuple[set[str], dict[str, tuple[sqlite3.Row, ...]]]:
        tables = {
            str(row[0])
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            ).fetchall()
        }
        columns = {
            table: tuple(connection.execute(f'PRAGMA table_info("{table}")').fetchall())
            for table in ("run_events", "artifacts", "execution_leases")
        }
        return tables, columns

    tables, actual_columns = database.read_sync(inspect)
    assert tables == {"run_events", "artifacts", "execution_leases"}

    frozen_columns: dict[str, set[str]] = {
        "run_events": set(),
        "artifacts": set(),
        "execution_leases": set(),
    }
    for key, evidence in indexed.items():
        if not key.startswith("sqlite:column:"):
            continue
        _, _, table, column = key.split(":")
        frozen_columns[table].add(column)
        expected = _schema(evidence)
        actual = next(row for row in actual_columns[table] if row[1] == column)
        assert {
            "cid": actual[0],
            "name": actual[1],
            "type": actual[2],
            "notnull": actual[3],
            "dflt_value": actual[4],
            "pk": actual[5],
        } == expected

    for table, columns in actual_columns.items():
        names = {str(row[1]) for row in columns}
        extras = names - frozen_columns[table]
        assert extras == ({"sha256"} if table == "artifacts" else set())
    sha = next(row for row in actual_columns["artifacts"] if row[1] == "sha256")
    assert tuple(sha) == (8, "sha256", "TEXT", 0, None, 0)

    for key, table in (
        ("sqlite:index:idx_run_events_stream", "run_events"),
        ("sqlite:index:idx_execution_leases_active", "execution_leases"),
    ):
        expected = _schema(indexed[key])
        rows = _index_rows(database, table)
        row = next(item for item in rows if item[1] == expected["name"])
        assert {
            "seq": row[0],
            "name": row[1],
            "unique": row[2],
            "origin": row[3],
            "partial": row[4],
        } == expected

    def prove_uniques(connection: sqlite3.Connection) -> None:
        connection.execute(
            "INSERT INTO run_events VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                "e1",
                "r1",
                1,
                "run.started",
                1,
                "2026-01-02T03:04:05.000Z",
                "system",
                None,
                None,
                "{}",
                None,
            ),
        )
        with pytest.raises(sqlite3.IntegrityError):
            connection.execute(
                "INSERT INTO run_events VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    "e2",
                    "r1",
                    1,
                    "run.started",
                    1,
                    "2026-01-02T03:04:05.000Z",
                    "system",
                    None,
                    None,
                    "{}",
                    None,
                ),
            )
        connection.execute(
            "INSERT INTO execution_leases VALUES (?, ?, ?, ?, ?, ?)",
            ("l1", "r1", "worker", "token", "2026-01-02T03:04:05.000Z", "2026-01-02T03:04:06.000Z"),
        )
        with pytest.raises(sqlite3.IntegrityError):
            connection.execute(
                "INSERT INTO execution_leases VALUES (?, ?, ?, ?, ?, ?)",
                (
                    "l2",
                    "r1",
                    "other",
                    "other",
                    "2026-01-02T03:04:05.000Z",
                    "2026-01-02T03:04:06.000Z",
                ),
            )

    database.write_sync(prove_uniques)


def test_representative_event_artifact_and_lease_values_reopen_through_adapters(
    sqlite_evidence: tuple[_Evidence, ...], database_path: Path, tmp_path: Path
) -> None:
    observations = {
        json.dumps(
            _mapping(item.record.get("observations")),
            sort_keys=True,
        )
        for item in sqlite_evidence
    }
    assert len(observations) == 1
    observation = _mapping(json.loads(observations.pop()))
    raw = _mapping(observation.get("rawRow"))
    expected_event = _mapping(observation.get("decodedEvent"))
    database = _Database(database_path)

    def insert_event(connection: sqlite3.Connection) -> None:
        connection.execute(
            "INSERT INTO run_events "
            "(event_id, run_id, position, type, version, timestamp, actor, causation_id, "
            "correlation_id, payload_json, command_id) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            tuple(
                raw.get(name)
                for name in (
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
            ),
        )

    database.write_sync(insert_event)
    before = database.read_sync(
        lambda connection: tuple(connection.execute("SELECT * FROM run_events").fetchone())
    )

    async def scenario() -> None:
        events = SqliteRunEventStore(database_path)
        selected = await events.read(RunId(value=_string(raw.get("run_id"))))
        assert len(selected.events) == 1
        event = selected.events[0]
        expected_payload = dict(_mapping(expected_event.get("payload")))
        expected_payload["initialStatus"] = "created"
        normalized_expected = dict(expected_event)
        normalized_expected["payload"] = expected_payload
        assert json.loads(encode_event(event)) == normalized_expected
        assert event.causation_id is MISSING
        assert event.correlation_id is MISSING
        assert event.command_id is MISSING
        assert await SqliteRunEventStore(database_path).has_event(event.event_id) is True

        artifact = ArtifactEntry(
            artifact_id=ArtifactId(value="artifact-compatible"),
            kind="metadata",
            created_at=Timestamp(value="2026-01-02T03:04:05.000Z"),
            metadata=JsonObject(entries=(("first", 1), ("second", 2))),
        )
        artifacts = SqliteArtifactStore(database_path, tmp_path / "artifacts")
        await artifacts.put(artifact)
        assert (
            await SqliteArtifactStore(database_path, tmp_path / "artifacts").get(
                artifact.artifact_id
            )
            == artifact
        )

        leases = SqliteExecutionLeaseStore(
            database_path,
            lease_ids=lambda: LeaseId(value="lease-compatible"),
            tokens=lambda: "token-compatible",
        )
        lease = await leases.acquire(
            LeaseAcquireInput(
                run_id=RunId(value="lease-run"),
                owner="worker",
                ttl_ms=1_000,
                now=Timestamp(value="2026-01-02T03:04:05.000Z"),
            )
        )
        assert lease is not None
        reopened = SqliteExecutionLeaseStore(
            database_path,
            lease_ids=lambda: LeaseId(value="unused"),
            tokens=lambda: "unused",
        )
        assert (
            await reopened.get_active(lease.run_id, Timestamp(value="2026-01-02T03:04:05.500Z"))
            == lease
        )

    asyncio.run(scenario())
    after = database.read_sync(
        lambda connection: tuple(connection.execute("SELECT * FROM run_events").fetchone())
    )
    assert after == before
    assert after[9] == raw["payload_json"]


def test_pre_command_id_schema_migrates_additively_and_reopens_without_row_mutation(
    sqlite_evidence: tuple[_Evidence, ...], database_path: Path
) -> None:
    observation = _mapping(sqlite_evidence[0].record.get("observations"))
    raw = _mapping(observation.get("rawRow"))
    database_path.parent.mkdir(parents=True)
    connection = sqlite3.connect(database_path)
    connection.execute(
        """
        CREATE TABLE run_events (
            event_id TEXT PRIMARY KEY, run_id TEXT NOT NULL, position INTEGER NOT NULL,
            type TEXT NOT NULL, version INTEGER NOT NULL, timestamp TEXT NOT NULL,
            actor TEXT NOT NULL, causation_id TEXT, correlation_id TEXT,
            payload_json TEXT NOT NULL, UNIQUE(run_id, position)
        )
        """
    )
    connection.execute(
        "INSERT INTO run_events VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        tuple(
            raw.get(name)
            for name in (
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
            )
        ),
    )
    connection.commit()
    connection.close()

    _Database(database_path)
    migrated = sqlite3.connect(database_path)
    columns = tuple(row[1] for row in migrated.execute("PRAGMA table_info(run_events)"))
    before = migrated.execute("SELECT * FROM run_events").fetchone()
    migrated.close()
    assert columns[-1] == "command_id"
    assert before is not None and before[-1] is None

    _Database(database_path)
    reopened = sqlite3.connect(database_path)
    after = reopened.execute("SELECT * FROM run_events").fetchone()
    reopened.close()
    assert after == before
    selected = asyncio.run(
        SqliteRunEventStore(database_path).read(RunId(value=_string(raw.get("run_id"))))
    )
    assert selected.events[0].command_id is MISSING
