"""Construct the explicit default local runtime graph."""

from __future__ import annotations

from pathlib import Path

from openrund._localfs import LocalFilesystemError, secure_directory_tree
from openrund.assembly._events import ReportingEventStore
from openrund.assembly._model import LocalAssemblyConfig, LocalRuntime
from openrund.capabilities import (
    ActionRunner,
    ActionRunnerDependencies,
    CapabilityRegistry,
    DocumentsCapability,
    FilesystemCapability,
    GitCapability,
    ProcessCapability,
)
from openrund.engine import EngineDependencies, GovernanceContext, RuntimeEngine
from openrund.errors import StorageError
from openrund.operator import OperatorService, OperatorServiceDependencies
from openrund.paths import LocalPath
from openrund.runtime import DurableRunLoop, DurableRunLoopDependencies
from openrund.storage import (
    SqliteArtifactStore,
    SqliteExecutionLeaseStore,
    SqliteRunEventStore,
)

_PACKAGE_SEARCH_ROOT = Path(__file__).resolve().parents[2]


def _secure_runtime_home(path: Path) -> Path:
    try:
        return secure_directory_tree(path, create=True)
    except LocalFilesystemError as error:
        if error.reason == "create":
            raise StorageError(code="local_runtime_home_create_failed") from None
        if error.reason == "inspect":
            raise StorageError(code="local_runtime_home_inspection_failed") from None
        raise StorageError(code="local_runtime_home_invalid") from None


def create_local_runtime(config: LocalAssemblyConfig) -> LocalRuntime:
    """Build one local runtime from explicit configuration.

    An empty mount set produces no built-in Capability and no workspace root.
    Authority remains durable Engine state and is never synthesized here.
    """

    if not isinstance(config, LocalAssemblyConfig):
        raise TypeError("local_assembly_config_invalid")
    home = _secure_runtime_home(Path(config.runtime_home))
    database = home / "runtime.sqlite"
    artifact_root = home / "artifacts"
    registered = list(config.capabilities)
    if config.mounts:
        registered.append(FilesystemCapability(mounts=config.mounts).registered())
        registered.append(
            DocumentsCapability(mounts=config.mounts).registered(
                module_search_path=_PACKAGE_SEARCH_ROOT
            )
        )
        if config.process_bindings:
            registered.append(
                ProcessCapability(
                    mounts=config.mounts,
                    bindings=config.process_bindings,
                ).registered()
            )
        if config.git_executable is not None:
            registered.append(
                GitCapability(
                    mounts=config.mounts,
                    git_executable=config.git_executable,
                    identities=config.git_identities,
                ).registered()
            )
    registry = CapabilityRegistry(tuple(registered))
    raw_events = SqliteRunEventStore(database, busy_timeout_ms=config.busy_timeout_ms)
    events = ReportingEventStore(raw_events, config.reporter)
    artifacts = SqliteArtifactStore(
        database,
        artifact_root,
        busy_timeout_ms=config.busy_timeout_ms,
    )
    leases = SqliteExecutionLeaseStore(
        database,
        lease_ids=config.ids.lease_ids.new_id,
        tokens=config.ids.lease_tokens,
        busy_timeout_ms=config.busy_timeout_ms,
    )
    governance = GovernanceContext(
        capabilities=registry.definitions,
        workspace_roots=tuple(LocalPath(raw=str(item.resolved_root)) for item in config.mounts),
    )
    engine = RuntimeEngine(
        EngineDependencies(
            event_store=events,
            atomic_event_store=events,
            clock=config.clock,
            event_ids=config.ids.event_ids,
            message_ids=config.ids.message_ids,
            run_ids=config.ids.run_ids,
            wait_ids=config.ids.wait_ids,
            delegation_ids=config.ids.delegation_ids,
            check_ids=config.ids.check_ids,
            checkpoint_ids=config.ids.checkpoint_ids,
            annotation_ids=config.ids.annotation_ids,
            authority_ids=config.ids.authority_ids,
            governance=governance,
        )
    )
    action_runner = ActionRunner(
        ActionRunnerDependencies(
            engine=engine,
            registry=registry,
            artifact_store=artifacts,
            clock=config.clock,
            command_ids=config.ids.command_ids,
            artifact_ids=config.ids.artifact_ids,
        )
    )
    operator = OperatorService(
        OperatorServiceDependencies(
            event_store=events,
            artifact_store=artifacts,
            engine=engine,
            clock=config.clock,
            command_ids=config.ids.command_ids,
            runtime_home=home,
            required_root_mappings=tuple(item.name for item in config.mounts),
            available_capabilities=tuple(item.capability_id.value for item in registry.definitions),
            available_providers=(
                ()
                if config.provider is None
                else (str(getattr(config.provider, "provider", type(config.provider).__name__)),)
            ),
        )
    )
    run_loop = (
        None
        if config.provider is None
        else DurableRunLoop(
            DurableRunLoopDependencies(
                engine=engine,
                provider=config.provider,
                clock=config.clock,
                model_call_ids=config.ids.model_call_ids,
                command_ids=config.ids.command_ids,
                own_provider=config.own_provider,
            )
        )
    )
    return LocalRuntime(
        config=config,
        raw_event_store=raw_events,
        event_store=events,
        artifact_store=artifacts,
        lease_store=leases,
        engine=engine,
        registry=registry,
        action_runner=action_runner,
        operator=operator,
        run_loop=run_loop,
    )
