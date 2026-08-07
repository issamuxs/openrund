from __future__ import annotations

import asyncio
from pathlib import Path

import pytest

from openrund.assembly import LocalAssemblyConfig, create_local_runtime
from openrund.capabilities import FilesystemMount, ProcessBinding
from openrund.contracts.capabilities import CapabilityAccessMode
from openrund.contracts.commands import (
    AcceptedCommandDecision,
    BootstrapRunOperation,
    Command,
    CommandOrigin,
)
from openrund.contracts.events import CoreEventType
from openrund.contracts.ids import CommandId, RunId
from openrund.errors import ResourceClosedError, StorageError, ValidationError
from openrund.ports.runtime import ReportEntry


class RecordingReporter:
    def __init__(self) -> None:
        self.entries: list[ReportEntry] = []

    async def report(self, entry: ReportEntry, /) -> None:
        self.entries.append(entry)


class FailingReporter:
    async def report(self, entry: ReportEntry, /) -> None:
        raise RuntimeError("advisory reporter failed")


def _bootstrap(run_id: RunId) -> Command:
    return Command(
        command_id=CommandId(value="cmd_bootstrap"),
        run_id=run_id,
        origin=CommandOrigin.SYSTEM,
        operation=BootstrapRunOperation(root_id=run_id),
    )


def test_empty_default_assembly_grants_no_root_capability_or_authority(tmp_path: Path) -> None:
    runtime = create_local_runtime(LocalAssemblyConfig(runtime_home=tmp_path / "runtime"))
    run_id = RunId(value="run_empty")

    async def scenario() -> None:
        async with runtime:
            result = await runtime.engine.submit(_bootstrap(run_id))
            assert isinstance(result.decision, AcceptedCommandDecision)
            assert runtime.registry.definitions == ()
            history = await runtime.event_store.read(run_id)
            assert not any(
                event.event_type
                in (CoreEventType.AUTHORITY_GRANTED, CoreEventType.AUTHORITY_REVOKED)
                for event in history.events
            )

    asyncio.run(scenario())
    assert runtime.database_path.is_file()
    with pytest.raises(ResourceClosedError, match="local_runtime"):
        runtime.materialize_run_home(run_id)


def test_explicit_mount_wires_only_eligible_builtins_and_run_home(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    mount = FilesystemMount(
        name="workspace",
        root=workspace,
        access=CapabilityAccessMode.READ_WRITE,
    )
    runtime = create_local_runtime(
        LocalAssemblyConfig(
            runtime_home=tmp_path / "runtime",
            mounts=(mount,),
            process_bindings=(ProcessBinding(name="python", executable=Path("/usr/bin/python3")),),
        )
    )

    assert tuple(item.capability_id.value for item in runtime.registry.definitions) == (
        "filesystem",
        "documents",
        "process",
    )
    layout = runtime.materialize_run_home(RunId(value="run_layout"))
    assert layout.workspace.is_dir()
    assert layout.exports.is_dir()
    asyncio.run(runtime.aclose())


def test_reporting_is_post_commit_and_failure_is_advisory(tmp_path: Path) -> None:
    recorder = RecordingReporter()
    first = create_local_runtime(
        LocalAssemblyConfig(runtime_home=tmp_path / "recording", reporter=recorder)
    )
    second = create_local_runtime(
        LocalAssemblyConfig(runtime_home=tmp_path / "failing", reporter=FailingReporter())
    )

    async def scenario() -> None:
        await first.engine.submit(_bootstrap(RunId(value="run_reported")))
        await second.engine.submit(_bootstrap(RunId(value="run_advisory_failure")))
        await first.aclose()
        await second.aclose()

    asyncio.run(scenario())
    assert len(recorder.entries) == 3
    assert {entry.category for entry in recorder.entries} == {"event.committed"}


def test_assembly_rejects_partial_git_configuration_and_symlink_home(tmp_path: Path) -> None:
    with pytest.raises(ValidationError, match="local_assembly_git_configuration_incomplete"):
        LocalAssemblyConfig(runtime_home=tmp_path, git_executable=Path("/usr/bin/git"))

    target = tmp_path / "target"
    target.mkdir()
    linked = tmp_path / "linked"
    linked.symlink_to(target, target_is_directory=True)
    with pytest.raises(StorageError, match="local_runtime_home_invalid"):
        create_local_runtime(LocalAssemblyConfig(runtime_home=linked / "runtime"))
