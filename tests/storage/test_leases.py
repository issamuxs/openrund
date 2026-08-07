from __future__ import annotations

import asyncio
import itertools
import sqlite3
import time
from collections.abc import Callable
from pathlib import Path

import pytest

from openrund.contracts.ids import LeaseId, RunId
from openrund.contracts.time import Timestamp
from openrund.errors import StorageBusyError, StorageIntegrityError
from openrund.ports.leases import LeaseAcquireInput, LeaseRenewInput
from openrund.storage import SqliteExecutionLeaseStore


def _timestamp(second: int) -> Timestamp:
    return Timestamp(value=f"2026-01-02T03:04:{second:02d}.000Z")


def _ids(prefix: str = "lease") -> Callable[[], LeaseId]:
    counter = itertools.count(1)
    return lambda: LeaseId(value=f"{prefix}-{next(counter)}")


def _tokens(prefix: str = "token") -> Callable[[], str]:
    counter = itertools.count(1)
    return lambda: f"{prefix}-{next(counter)}"


def _store(
    database_path: Path,
    *,
    lease_ids: Callable[[], LeaseId] | None = None,
    tokens: Callable[[], str] | None = None,
    busy_timeout_ms: int = 5_000,
) -> SqliteExecutionLeaseStore:
    return SqliteExecutionLeaseStore(
        database_path,
        lease_ids=lease_ids or _ids(),
        tokens=tokens or _tokens(),
        busy_timeout_ms=busy_timeout_ms,
    )


def _acquire(*, run: str = "run-1", owner: str = "worker-1", now: int = 5) -> LeaseAcquireInput:
    return LeaseAcquireInput(
        run_id=RunId(value=run), owner=owner, ttl_ms=2_000, now=_timestamp(now)
    )


def test_lease_store_acquires_renews_releases_and_reopens(database_path: Path) -> None:
    async def scenario() -> None:
        store = _store(database_path)
        lease = await store.acquire(_acquire())
        assert lease is not None
        assert lease.expires_at == _timestamp(7)
        assert await store.acquire(_acquire(owner="worker-2")) is None
        assert await _store(database_path).get_active(lease.run_id, _timestamp(6)) == lease

        renewed = await store.renew(
            LeaseRenewInput(
                lease_id=lease.lease_id,
                run_id=lease.run_id,
                owner=lease.owner,
                token=lease.token,
                ttl_ms=3_000,
                now=_timestamp(6),
            )
        )
        assert renewed is not None and renewed.expires_at == _timestamp(9)
        assert renewed.acquired_at == lease.acquired_at
        assert await store.release(renewed.lease_id, "stale") is False
        assert await store.release(renewed.lease_id, renewed.token) is True
        assert await store.get_active(lease.run_id, _timestamp(6)) is None

    asyncio.run(scenario())


def test_lease_expiry_is_strict_and_replacement_fences_stale_holder(
    database_path: Path,
) -> None:
    async def scenario() -> None:
        identities = iter((LeaseId(value="lease-old"), LeaseId(value="lease-new")))
        tokens = iter(("token-old", "token-new"))
        store = _store(
            database_path, lease_ids=lambda: next(identities), tokens=lambda: next(tokens)
        )
        old = await store.acquire(_acquire(now=5))
        assert old is not None
        assert await store.get_active(old.run_id, _timestamp(7)) is None

        replacement = await store.acquire(_acquire(owner="worker-2", now=7))
        assert replacement is not None
        assert replacement.lease_id != old.lease_id
        assert replacement.token != old.token
        assert await store.release(old.lease_id, old.token) is False
        stale_renew = await store.renew(
            LeaseRenewInput(
                lease_id=old.lease_id,
                run_id=old.run_id,
                owner=old.owner,
                token=old.token,
                ttl_ms=1_000,
                now=_timestamp(7),
            )
        )
        assert stale_renew is None
        assert await store.get_active(replacement.run_id, _timestamp(8)) == replacement

    asyncio.run(scenario())


@pytest.mark.parametrize("field", ["lease_id", "run_id", "owner", "token"])
def test_lease_renew_rejects_every_stale_fence(database_path: Path, field: str) -> None:
    async def scenario() -> None:
        store = _store(database_path)
        lease = await store.acquire(_acquire())
        assert lease is not None
        values = {
            "lease_id": LeaseId(value="wrong") if field == "lease_id" else lease.lease_id,
            "run_id": RunId(value="wrong") if field == "run_id" else lease.run_id,
            "owner": "wrong" if field == "owner" else lease.owner,
            "token": "wrong" if field == "token" else lease.token,
        }
        renewed = await store.renew(
            LeaseRenewInput(
                lease_id=values["lease_id"],  # type: ignore[arg-type]
                run_id=values["run_id"],  # type: ignore[arg-type]
                owner=values["owner"],  # type: ignore[arg-type]
                token=values["token"],  # type: ignore[arg-type]
                ttl_ms=1_000,
                now=_timestamp(6),
            )
        )
        assert renewed is None
        assert await store.get_active(lease.run_id, _timestamp(6)) == lease

    asyncio.run(scenario())


def test_concurrent_acquire_has_one_winner_across_adapters(database_path: Path) -> None:
    async def scenario() -> None:
        stores = (
            _store(database_path, lease_ids=lambda: LeaseId(value="left"), tokens=lambda: "left"),
            _store(database_path, lease_ids=lambda: LeaseId(value="right"), tokens=lambda: "right"),
        )
        barrier = asyncio.Barrier(2)

        async def compete(index: int) -> object:
            await barrier.wait()
            return await stores[index].acquire(_acquire(owner=f"worker-{index}"))

        outcomes = await asyncio.gather(compete(0), compete(1))
        assert sum(outcome is not None for outcome in outcomes) == 1
        active = await stores[0].get_active(RunId(value="run-1"), _timestamp(6))
        assert active is not None and active.lease_id.value in {"left", "right"}

    asyncio.run(scenario())


def test_duplicate_factory_output_rolls_back_without_second_lease(database_path: Path) -> None:
    async def scenario() -> None:
        store = _store(
            database_path,
            lease_ids=lambda: LeaseId(value="duplicate"),
            tokens=_tokens(),
        )
        assert await store.acquire(_acquire(run="run-1")) is not None
        with pytest.raises(StorageIntegrityError, match="lease_id_duplicate"):
            await store.acquire(_acquire(run="run-2"))
        assert await store.get_active(RunId(value="run-2"), _timestamp(6)) is None

    asyncio.run(scenario())


def test_reacquire_rejects_reused_fencing_token(database_path: Path) -> None:
    async def scenario() -> None:
        store = _store(database_path, lease_ids=_ids(), tokens=lambda: "reused")
        old = await store.acquire(_acquire(now=5))
        assert old is not None
        assert await store.get_active(old.run_id, _timestamp(7)) is None
        with pytest.raises(StorageIntegrityError, match="lease_token_reused"):
            await store.acquire(_acquire(owner="worker-2", now=7))
        assert await store.get_active(old.run_id, _timestamp(7)) is None

    asyncio.run(scenario())


def test_lease_busy_is_bounded_and_uses_no_internal_time(database_path: Path) -> None:
    store = _store(database_path, busy_timeout_ms=15)
    lock = sqlite3.connect(database_path, isolation_level=None)
    lock.execute("BEGIN IMMEDIATE")
    started = time.monotonic()
    try:
        with pytest.raises(StorageBusyError):
            asyncio.run(store.acquire(_acquire(now=5)))
    finally:
        lock.execute("ROLLBACK")
        lock.close()
    assert time.monotonic() - started < 1.0
