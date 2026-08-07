from __future__ import annotations

import asyncio
import os
import sys
from collections.abc import Iterator
from pathlib import Path

import pytest

from openrund._testing.memory import MemoryEventStore
from openrund.capabilities import StdioJsonRpcConfig, StdioJsonRpcTransport
from openrund.contracts.commands import BootstrapRunOperation, Command, CommandOrigin
from openrund.contracts.content import Content
from openrund.contracts.ids import (
    ActionId,
    ArtifactId,
    CapabilityId,
    CommandId,
    EventId,
    LeaseId,
    MessageId,
    RunId,
    RuntimeId,
)
from openrund.contracts.time import Timestamp
from openrund.engine import EngineDependencies, RuntimeEngine
from openrund.errors import ResourceClosedError
from openrund.ports.capabilities import CapabilityInvocation
from openrund.storage import (
    SqliteArtifactStore,
    SqliteExecutionLeaseStore,
    SqliteRunEventStore,
)


class _Clock:
    def now(self) -> Timestamp:
        return Timestamp(value="2026-08-06T11:00:00.000Z")


class _Factory[TId: RuntimeId]:
    def __init__(self, values: Iterator[TId]) -> None:
        self._values = values

    def new_id(self) -> TId:
        return next(self._values)


def _ids[TId: RuntimeId](kind: type[TId], prefix: str) -> Iterator[TId]:
    index = 1
    while True:
        yield kind(value=f"{prefix}-{index}")
        index += 1


def _engine() -> RuntimeEngine:
    return RuntimeEngine(
        EngineDependencies(
            event_store=MemoryEventStore(),
            clock=_Clock(),
            event_ids=_Factory(_ids(EventId, "event")),
            message_ids=_Factory(_ids(MessageId, "message")),
        )
    )


def _bootstrap() -> Command:
    run_id = RunId(value="run-lifetime")
    return Command(
        command_id=CommandId(value="bootstrap-lifetime"),
        run_id=run_id,
        origin=CommandOrigin.SYSTEM,
        operation=BootstrapRunOperation(root_id=run_id),
    )


def _invocation() -> CapabilityInvocation:
    return CapabilityInvocation(
        action_id=ActionId(value="action-lifetime"),
        capability_id=CapabilityId(value="documents"),
        action_name="read",
        input=Content(data={"mount": "workspace", "path": "README.md"}),  # type: ignore[arg-type]
    )


def test_engine_async_context_rejects_use_after_close() -> None:
    async def scenario() -> None:
        engine = _engine()
        async with engine as entered:
            assert entered is engine
            await engine.submit(_bootstrap())
        await engine.aclose()
        with pytest.raises(ResourceClosedError) as raised:
            await engine.submit(_bootstrap())
        assert raised.value.resource == "engine"

    asyncio.run(scenario())


def test_sqlite_stores_have_idempotent_explicit_lifetimes(tmp_path: Path) -> None:
    async def scenario() -> None:
        database = tmp_path / "runtime.sqlite"
        event_store = SqliteRunEventStore(database)
        artifact_store = SqliteArtifactStore(database, tmp_path / "artifacts")
        lease_store = SqliteExecutionLeaseStore(
            database,
            lease_ids=lambda: LeaseId(value="lease-lifetime"),
            tokens=lambda: "token-lifetime",
        )
        async with event_store as entered_events:
            assert entered_events is event_store
            await event_store.read(RunId(value="missing"))
        async with artifact_store as entered_artifacts:
            assert entered_artifacts is artifact_store
        async with lease_store as entered_leases:
            assert entered_leases is lease_store
        await event_store.aclose()
        await artifact_store.aclose()
        await lease_store.aclose()

        for resource, operation in (
            ("event_store", event_store.read(RunId(value="missing"))),
            ("artifact_store", artifact_store.get(ArtifactId(value="missing"))),
            (
                "lease_store",
                lease_store.get_active(
                    RunId(value="missing"),
                    Timestamp(value="2026-08-06T11:00:00.000Z"),
                ),
            ),
        ):
            with pytest.raises(ResourceClosedError) as raised:
                await operation
            assert raised.value.resource == resource

    asyncio.run(scenario())


def test_stdio_context_exit_reaps_active_worker_and_rejects_reuse(tmp_path: Path) -> None:
    worker = tmp_path / "worker.py"
    pid_file = tmp_path / "worker.pid"
    worker.write_text(
        "import os, pathlib, sys, time\n"
        "sys.stdin.readline()\n"
        "pathlib.Path(sys.argv[1]).write_text(str(os.getpid()))\n"
        "time.sleep(30)\n",
        encoding="utf-8",
    )

    async def scenario() -> None:
        transport = StdioJsonRpcTransport(
            StdioJsonRpcConfig(
                command=(sys.executable, str(worker), str(pid_file)),
                timeout_ms=60_000,
            )
        )
        task = asyncio.create_task(transport.invoke(_invocation()))
        for _attempt in range(100):
            if pid_file.exists():
                break
            await asyncio.sleep(0.01)
        assert pid_file.exists()
        process_id = int(pid_file.read_text(encoding="utf-8"))

        await transport.aclose()
        result = await asyncio.gather(task, return_exceptions=True)

        assert isinstance(result[0], BaseException)
        with pytest.raises(ProcessLookupError):
            os.kill(process_id, 0)
        with pytest.raises(ResourceClosedError) as raised:
            await transport.invoke(_invocation())
        assert raised.value.resource == "stdio_transport"

    asyncio.run(scenario())
