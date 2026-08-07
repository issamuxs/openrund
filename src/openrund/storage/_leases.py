"""Process-safe token-fenced execution Lease coordination over SQLite."""

from __future__ import annotations

import sqlite3
from collections.abc import Callable
from datetime import datetime, timedelta
from typing import Self, final

from openrund.contracts.ids import LeaseId, RunId
from openrund.contracts.runs import Lease
from openrund.contracts.time import Timestamp
from openrund.errors import (
    OpenRundError,
    ResourceClosedError,
    StorageIntegrityError,
    ValidationError,
)
from openrund.paths import PathInput
from openrund.ports.leases import LeaseAcquireInput, LeaseRenewInput
from openrund.storage._database import _Database

_LEASE_SELECT = (
    "SELECT lease_id, run_id, holder, token, acquired_at, expires_at "
    "FROM execution_leases WHERE run_id = ?"
)


def _expires_at(now: Timestamp, ttl_ms: int) -> Timestamp:
    try:
        parsed = datetime.strptime(now.value, "%Y-%m-%dT%H:%M:%S.%fZ")
        advanced = parsed + timedelta(milliseconds=ttl_ms)
        return Timestamp(value=advanced.strftime("%Y-%m-%dT%H:%M:%S.%f")[:23] + "Z")
    except (OverflowError, ValueError):
        raise ValidationError(code="lease_expiry_out_of_range") from None


def _required_text(row: sqlite3.Row, name: str) -> str:
    value = row[name]
    if not isinstance(value, str) or value == "":
        raise StorageIntegrityError(code="lease_row_invalid")
    return value


def _decode_lease(row: sqlite3.Row) -> Lease:
    try:
        return Lease(
            lease_id=LeaseId(value=_required_text(row, "lease_id")),
            run_id=RunId(value=_required_text(row, "run_id")),
            owner=_required_text(row, "holder"),
            token=_required_text(row, "token"),
            acquired_at=Timestamp(value=_required_text(row, "acquired_at")),
            expires_at=Timestamp(value=_required_text(row, "expires_at")),
        )
    except StorageIntegrityError:
        raise
    except (OpenRundError, KeyError, TypeError, ValueError):
        raise StorageIntegrityError(code="lease_row_invalid") from None


@final
class SqliteExecutionLeaseStore:
    """Strictly expiring local coordination; Leases confer no Authority."""

    def __init__(
        self,
        database_path: PathInput,
        *,
        lease_ids: Callable[[], LeaseId],
        tokens: Callable[[], str],
        busy_timeout_ms: int = 5_000,
    ) -> None:
        if not callable(lease_ids):
            raise ValidationError(code="lease_id_factory_invalid")
        if not callable(tokens):
            raise ValidationError(code="lease_token_factory_invalid")
        self._database = _Database(database_path, busy_timeout_ms=busy_timeout_ms)
        self._lease_ids = lease_ids
        self._tokens = tokens
        self._closed = False

    async def __aenter__(self) -> Self:
        if self._closed:
            raise ResourceClosedError(resource="lease_store")
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
            raise ResourceClosedError(resource="lease_store")

    def _new_identity(self) -> tuple[LeaseId, str]:
        lease_id = self._lease_ids()
        token = self._tokens()
        if not isinstance(lease_id, LeaseId):
            raise ValidationError(code="lease_id_factory_output_invalid")
        if not isinstance(token, str) or token == "":
            raise ValidationError(code="lease_token_factory_output_invalid")
        return lease_id, token

    async def acquire(self, value: LeaseAcquireInput, /) -> Lease | None:
        self._ensure_open()
        if not isinstance(value, LeaseAcquireInput):
            raise ValidationError(code="lease_acquire_input_invalid")
        expires_at = _expires_at(value.now, value.ttl_ms)

        def acquire(connection: sqlite3.Connection) -> Lease | None:
            row = connection.execute(_LEASE_SELECT, (value.run_id.value,)).fetchone()
            expired: Lease | None = None
            if row is not None:
                current = _decode_lease(row)
                if current.expires_at.value > value.now.value:
                    return None
                expired = current

            lease_id, token = self._new_identity()
            if expired is not None:
                if token == expired.token:
                    raise StorageIntegrityError(code="lease_token_reused")
                connection.execute(
                    "DELETE FROM execution_leases WHERE lease_id = ? AND token = ?",
                    (expired.lease_id.value, expired.token),
                )

            if (
                connection.execute(
                    "SELECT 1 FROM execution_leases WHERE lease_id = ? LIMIT 1",
                    (lease_id.value,),
                ).fetchone()
                is not None
            ):
                raise StorageIntegrityError(code="lease_id_duplicate")
            if (
                connection.execute(
                    "SELECT 1 FROM execution_leases WHERE token = ? LIMIT 1", (token,)
                ).fetchone()
                is not None
            ):
                raise StorageIntegrityError(code="lease_token_duplicate")
            lease = Lease(
                lease_id=lease_id,
                run_id=value.run_id,
                owner=value.owner,
                token=token,
                acquired_at=value.now,
                expires_at=expires_at,
            )
            connection.execute(
                "INSERT INTO execution_leases "
                "(lease_id, run_id, holder, token, acquired_at, expires_at) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (
                    lease.lease_id.value,
                    lease.run_id.value,
                    lease.owner,
                    lease.token,
                    lease.acquired_at.value,
                    lease.expires_at.value,
                ),
            )
            return lease

        return await self._database.write(acquire)

    async def renew(self, value: LeaseRenewInput, /) -> Lease | None:
        self._ensure_open()
        if not isinstance(value, LeaseRenewInput):
            raise ValidationError(code="lease_renew_input_invalid")
        expires_at = _expires_at(value.now, value.ttl_ms)

        def renew(connection: sqlite3.Connection) -> Lease | None:
            row = connection.execute(_LEASE_SELECT, (value.run_id.value,)).fetchone()
            if row is None:
                return None
            current = _decode_lease(row)
            if (
                current.lease_id != value.lease_id
                or current.run_id != value.run_id
                or current.owner != value.owner
                or current.token != value.token
                or current.expires_at.value <= value.now.value
            ):
                return None
            renewed = Lease(
                lease_id=current.lease_id,
                run_id=current.run_id,
                owner=current.owner,
                token=current.token,
                acquired_at=current.acquired_at,
                expires_at=expires_at,
            )
            connection.execute(
                "UPDATE execution_leases SET expires_at = ? "
                "WHERE lease_id = ? AND run_id = ? AND holder = ? AND token = ?",
                (
                    renewed.expires_at.value,
                    renewed.lease_id.value,
                    renewed.run_id.value,
                    renewed.owner,
                    renewed.token,
                ),
            )
            return renewed

        return await self._database.write(renew)

    async def release(self, lease_id: LeaseId, token: str, /) -> bool:
        self._ensure_open()
        if not isinstance(lease_id, LeaseId):
            raise ValidationError(code="lease_release_id_invalid")
        if not isinstance(token, str) or token == "":
            raise ValidationError(code="lease_release_token_invalid")

        def release(connection: sqlite3.Connection) -> bool:
            cursor = connection.execute(
                "DELETE FROM execution_leases WHERE lease_id = ? AND token = ?",
                (lease_id.value, token),
            )
            return cursor.rowcount == 1

        return await self._database.write(release)

    async def get_active(self, run_id: RunId, now: Timestamp, /) -> Lease | None:
        self._ensure_open()
        if not isinstance(run_id, RunId):
            raise ValidationError(code="lease_active_run_id_invalid")
        if not isinstance(now, Timestamp):
            raise ValidationError(code="lease_active_timestamp_invalid")

        def select(connection: sqlite3.Connection) -> Lease | None:
            row = connection.execute(_LEASE_SELECT, (run_id.value,)).fetchone()
            if row is None:
                return None
            current = _decode_lease(row)
            if current.expires_at.value > now.value:
                return current
            return None

        return await self._database.read(select)
