from __future__ import annotations

import asyncio
import hashlib
import os
import shutil
import subprocess
import sys
from collections.abc import Iterator
from pathlib import Path

import pytest

from openrund._testing.memory import MemoryArtifactStore, MemoryEventStore
from openrund.capabilities import (
    ActionRunner,
    ActionRunnerDependencies,
    CapabilityRegistry,
    DocumentsCapability,
    FilesystemCapability,
    FilesystemMount,
    GitCapability,
    GitIdentity,
    ProcessBinding,
    ProcessCapability,
)
from openrund.contracts.capabilities import CapabilityAccessMode
from openrund.contracts.commands import (
    AcceptedCommandDecision,
    Command,
    CommandOrigin,
    CreateActionOperation,
    GrantCapabilityAuthorityOperation,
    ReconcileActionOperation,
    RejectedCommandDecision,
)
from openrund.contracts.content import Content
from openrund.contracts.events import (
    ActionCreatedPayload,
    CoreEventType,
    RunCreatedPayload,
    RunStartedPayload,
    RuntimeEvent,
)
from openrund.contracts.ids import (
    ActionId,
    ArtifactId,
    AuthorityId,
    CapabilityId,
    CommandId,
    EventId,
    MessageId,
    RunId,
    RuntimeId,
    WaitId,
)
from openrund.contracts.time import Timestamp
from openrund.engine import EngineDependencies, GovernanceContext, RuntimeEngine
from openrund.errors import CapabilityProtocolError
from openrund.paths import LocalPath
from openrund.ports.capabilities import CapabilityInvocation
from openrund.ports.events import AppendEventsInput
from openrund.views import CompleteViewReplay, rebuild_views
from tests.engine.conftest import runtime_event

_SOURCE_ROOT = Path(__file__).resolve().parents[2] / "src"


class _Clock:
    def now(self) -> Timestamp:
        return Timestamp(value="2026-08-05T12:00:00.000Z")


class _SequenceFactory[TId: RuntimeId]:
    def __init__(self, values: Iterator[TId]) -> None:
        self._values = values

    def new_id(self) -> TId:
        return next(self._values)


def _ids[TId: RuntimeId](factory: type[TId], prefix: str) -> Iterator[TId]:
    index = 1
    while True:
        yield factory(value=f"{prefix}-{index}")
        index += 1


def _git_executable() -> Path:
    executable = shutil.which("git")
    assert executable is not None
    return Path(executable).resolve()


def _initialize_repository(root: Path) -> None:
    environment = {
        "GIT_CONFIG_NOSYSTEM": "1",
        "GIT_CONFIG_GLOBAL": os.devnull,
        "GIT_TERMINAL_PROMPT": "0",
        "LC_ALL": "C",
    }
    subprocess.run(
        (_git_executable(), "init", "--quiet"),
        cwd=root,
        env=environment,
        check=True,
        capture_output=True,
    )
    (root / "tracked.txt").write_text("tracked\n", encoding="utf-8")
    subprocess.run(
        (_git_executable(), "add", "--", "tracked.txt"),
        cwd=root,
        env=environment,
        check=True,
        capture_output=True,
    )
    subprocess.run(
        (
            _git_executable(),
            "-c",
            "user.name=Fixture",
            "-c",
            "user.email=fixture@example.rejected",
            "commit",
            "--quiet",
            "-m",
            "initial",
        ),
        cwd=root,
        env=environment,
        check=True,
        capture_output=True,
    )


def _registry(root: Path) -> CapabilityRegistry:
    mount = FilesystemMount(
        name="workspace",
        root=root,
        access=CapabilityAccessMode.READ_WRITE,
    )
    return CapabilityRegistry(
        (
            FilesystemCapability(mounts=(mount,)).registered(),
            DocumentsCapability(mounts=(mount,)).registered(module_search_path=_SOURCE_ROOT),
            ProcessCapability(
                mounts=(mount,),
                bindings=(
                    ProcessBinding(name="python", executable=Path(sys.executable).resolve()),
                ),
            ).registered(),
            GitCapability(
                mounts=(mount,),
                git_executable=_git_executable(),
                identities=(
                    GitIdentity(
                        name="robot",
                        author_name="OpenRund Robot",
                        author_email="robot@example.rejected",
                    ),
                ),
            ).registered(),
        )
    )


def _engine(store: MemoryEventStore) -> RuntimeEngine:
    return RuntimeEngine(
        EngineDependencies(
            event_store=store,
            clock=_Clock(),
            event_ids=_SequenceFactory(_ids(EventId, "event")),
            message_ids=_SequenceFactory(_ids(MessageId, "message")),
            wait_ids=_SequenceFactory(_ids(WaitId, "wait")),
        )
    )


def _runner(
    store: MemoryEventStore,
    artifacts: MemoryArtifactStore,
    registry: CapabilityRegistry,
    engine: RuntimeEngine,
) -> ActionRunner:
    return ActionRunner(
        ActionRunnerDependencies(
            engine=engine,
            registry=registry,
            artifact_store=artifacts,
            clock=_Clock(),
            command_ids=_SequenceFactory(_ids(CommandId, "command")),
            artifact_ids=_SequenceFactory(_ids(ArtifactId, "artifact")),
        )
    )


def _invocation(
    capability: str,
    action: str,
    data: dict[str, object],
    *,
    action_id: str = "action-1",
) -> CapabilityInvocation:
    return CapabilityInvocation(
        action_id=ActionId(value=action_id),
        capability_id=CapabilityId(value=capability),
        action_name=action,
        input=Content(data=data),  # type: ignore[arg-type]
    )


def _seed(store: MemoryEventStore, run_id: RunId, invocation: CapabilityInvocation) -> None:
    asyncio.run(
        store.append(
            AppendEventsInput(
                run_id=run_id,
                expected_position=0,
                events=(
                    runtime_event(
                        CoreEventType.RUN_CREATED,
                        RunCreatedPayload(root_id=run_id, initial_status="created"),
                        1,
                        run_id=run_id,
                    ),
                    runtime_event(
                        CoreEventType.RUN_STARTED,
                        RunStartedPayload(),
                        2,
                        run_id=run_id,
                    ),
                    runtime_event(
                        CoreEventType.ACTION_CREATED,
                        ActionCreatedPayload(
                            action_id=invocation.action_id,
                            capability_id=invocation.capability_id,
                            action_name=invocation.action_name,
                            input=invocation.input,
                        ),
                        3,
                        run_id=run_id,
                    ),
                ),
            )
        )
    )


async def _events(store: MemoryEventStore, run_id: RunId) -> tuple[RuntimeEvent, ...]:
    return (await store.read(run_id, from_position=1, limit=None)).events


@pytest.mark.parametrize(
    ("capability", "action", "data", "artifact_kinds"),
    [
        (
            "filesystem",
            "read",
            {"mount": "workspace", "path": "document.md"},
            ("filesystem.file",),
        ),
        (
            "documents",
            "read",
            {"mount": "workspace", "path": "document.md"},
            ("documents.markdown",),
        ),
        (
            "process",
            "run",
            {
                "executable": "python",
                "args": ["-c", "print('governed')"],
                "cwdMount": "workspace",
            },
            ("process.stdout", "process.stderr"),
        ),
        (
            "git",
            "status",
            {"repoMount": "workspace"},
            ("git.status",),
        ),
    ],
)
def test_every_builtin_crosses_governed_action_and_artifact_custody(
    tmp_path: Path,
    capability: str,
    action: str,
    data: dict[str, object],
    artifact_kinds: tuple[str, ...],
) -> None:
    root = tmp_path / f"root-{capability}"
    root.mkdir()
    (root / "document.md").write_text("# Governed\n", encoding="utf-8")
    _initialize_repository(root)
    registry = _registry(root)
    invocation = _invocation(capability, action, data)
    run_id = RunId(value=f"run-{capability}")
    store = MemoryEventStore()
    artifacts = MemoryArtifactStore()
    engine = _engine(store)
    _seed(store, run_id, invocation)

    terminal = asyncio.run(_runner(store, artifacts, registry, engine).execute(run_id, invocation))

    assert isinstance(terminal.decision, AcceptedCommandDecision)
    events = asyncio.run(_events(store, run_id))
    assert [event.event_type for event in events[3:]] == [
        CoreEventType.COMMAND_RECORDED,
        CoreEventType.ACTION_STARTED,
        CoreEventType.COMMAND_RECORDED,
        *(CoreEventType.ARTIFACT_CREATED for _kind in artifact_kinds),
        CoreEventType.ACTION_COMPLETED,
    ]
    replay = rebuild_views(events, watermark=len(events))
    assert isinstance(replay, CompleteViewReplay)
    receipt = replay.views.action_receipts[invocation.action_id]
    assert receipt.status == "completed"
    assert receipt.result is not None
    assert tuple(reference.kind for reference in receipt.result.artifact_refs) == artifact_kinds
    for artifact_id in receipt.artifact_ids:
        entry = asyncio.run(artifacts.get(artifact_id))
        blob = asyncio.run(artifacts.get_blob(artifact_id))
        assert entry is not None and blob is not None
        assert entry.byte_length == len(blob.content)
        assert entry.sha256 == hashlib.sha256(blob.content).hexdigest()


def test_persisted_action_input_is_rejected_before_builtin_dispatch(tmp_path: Path) -> None:
    target = tmp_path / "target.txt"
    target.write_text("before", encoding="utf-8")
    registry = _registry(tmp_path)
    original = _invocation(
        "filesystem",
        "update",
        {
            "mount": "workspace",
            "path": "target.txt",
            "text": "allowed",
            "expectedSha256": hashlib.sha256(b"before").hexdigest(),
        },
    )
    changed = _invocation(
        "filesystem",
        "update",
        {
            "mount": "workspace",
            "path": "target.txt",
            "text": "changed after persistence",
            "expectedSha256": hashlib.sha256(b"before").hexdigest(),
        },
    )
    run_id = RunId(value="run-rejected")
    store = MemoryEventStore()
    artifacts = MemoryArtifactStore()
    engine = _engine(store)
    _seed(store, run_id, original)

    with pytest.raises(CapabilityProtocolError, match="action_start_rejected"):
        asyncio.run(_runner(store, artifacts, registry, engine).execute(run_id, changed))

    assert target.read_text(encoding="utf-8") == "before"
    assert not artifacts.calls
    events = asyncio.run(_events(store, run_id))
    assert not any(event.event_type is CoreEventType.ACTION_STARTED for event in events)


@pytest.mark.parametrize(
    ("capability", "action", "data"),
    [
        (
            "process",
            "run",
            {
                "executable": "python",
                "cwdMount": "workspace",
                "cwdPath": "../outside",
            },
        ),
        (
            "git",
            "status",
            {"repoMount": "workspace", "repoPath": "../outside"},
        ),
    ],
)
def test_process_and_git_paths_are_rejected_by_engine_scope_before_action_creation(
    tmp_path: Path,
    capability: str,
    action: str,
    data: dict[str, object],
) -> None:
    _initialize_repository(tmp_path)
    registry = _registry(tmp_path)
    run_id = RunId(value=f"run-scope-{capability}")
    store = MemoryEventStore()
    asyncio.run(
        store.append(
            AppendEventsInput(
                run_id=run_id,
                expected_position=0,
                events=(
                    runtime_event(
                        CoreEventType.RUN_CREATED,
                        RunCreatedPayload(root_id=run_id, initial_status="created"),
                        1,
                        run_id=run_id,
                    ),
                    runtime_event(
                        CoreEventType.RUN_STARTED,
                        RunStartedPayload(),
                        2,
                        run_id=run_id,
                    ),
                ),
            )
        )
    )
    engine = RuntimeEngine(
        EngineDependencies(
            event_store=store,
            clock=_Clock(),
            event_ids=_SequenceFactory(_ids(EventId, "scope-event")),
            message_ids=_SequenceFactory(_ids(MessageId, "scope-message")),
            wait_ids=_SequenceFactory(_ids(WaitId, "scope-wait")),
            authority_ids=_SequenceFactory(_ids(AuthorityId, "scope-authority")),
            governance=GovernanceContext(
                capabilities=registry.definitions,
                workspace_roots=(LocalPath(raw=str(tmp_path.resolve())),),
            ),
        )
    )
    granted = asyncio.run(
        engine.submit(
            Command(
                command_id=CommandId(value="scope-grant"),
                run_id=run_id,
                origin=CommandOrigin.OPERATOR,
                operation=GrantCapabilityAuthorityOperation(
                    capability_id=CapabilityId(value=capability),
                    constraints={"writableRoots": ["workspace"]},  # type: ignore[arg-type]
                ),
            )
        )
    )
    assert isinstance(granted.decision, AcceptedCommandDecision)

    rejected = asyncio.run(
        engine.submit(
            Command(
                command_id=CommandId(value="scope-create"),
                run_id=run_id,
                origin=CommandOrigin.MODEL,
                operation=CreateActionOperation(
                    action_id=ActionId(value="scope-action"),
                    capability_id=CapabilityId(value=capability),
                    action_name=action,
                    input=Content(data=data),  # type: ignore[arg-type]
                ),
            )
        )
    )

    assert isinstance(rejected.decision, RejectedCommandDecision)
    assert rejected.decision.reason == "resource_scope_escape"
    events = asyncio.run(_events(store, run_id))
    assert not any(event.event_type is CoreEventType.ACTION_CREATED for event in events)


def test_stdio_transport_ambiguity_stays_unknown_until_operator_reconciliation(
    tmp_path: Path,
) -> None:
    (tmp_path / "document.md").write_text("# Slow startup\n", encoding="utf-8")
    mount = FilesystemMount(
        name="workspace",
        root=tmp_path,
        access=CapabilityAccessMode.READ_WRITE,
    )
    registered = DocumentsCapability(mounts=(mount,)).registered(
        module_search_path=_SOURCE_ROOT,
        timeout_ms=1,
    )
    registry = CapabilityRegistry((registered,))
    invocation = _invocation("documents", "read", {"mount": "workspace", "path": "document.md"})
    run_id = RunId(value="run-unknown")
    store = MemoryEventStore()
    artifacts = MemoryArtifactStore()
    engine = _engine(store)
    _seed(store, run_id, invocation)

    result = asyncio.run(_runner(store, artifacts, registry, engine).execute(run_id, invocation))

    assert isinstance(result.decision, AcceptedCommandDecision)
    events = asyncio.run(_events(store, run_id))
    unknown_event = next(
        event for event in events if event.event_type is CoreEventType.ACTION_UNKNOWN
    )
    replay = rebuild_views(events, watermark=len(events))
    assert isinstance(replay, CompleteViewReplay)
    assert replay.views.action_receipts[invocation.action_id].status == "outcome_unknown"
    assert not artifacts.calls

    reconciled = asyncio.run(
        engine.submit(
            Command(
                command_id=CommandId(value="operator-reconcile"),
                run_id=run_id,
                origin=CommandOrigin.OPERATOR,
                operation=ReconcileActionOperation(
                    action_id=invocation.action_id,
                    unknown_event_id=unknown_event.event_id,
                    outcome="failed",
                    evidence=Content(preview="worker process was terminated and reaped"),
                    reconciled_by="operator",
                ),
            )
        )
    )
    assert isinstance(reconciled.decision, AcceptedCommandDecision)
    final_events = asyncio.run(_events(store, run_id))
    final_replay = rebuild_views(final_events, watermark=len(final_events))
    assert isinstance(final_replay, CompleteViewReplay)
    assert final_replay.views.action_receipts[invocation.action_id].status == "reconciled"
