"""Explicit configuration and context-managed local runtime assembly."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Self, final

from openrund.assembly._events import ReportingEventStore
from openrund.assembly._factories import LocalIdFactories, SystemClock
from openrund.assembly._operator import (
    NullReporter,
    OperatorInput,
    RejectingOperatorInput,
)
from openrund.capabilities import (
    ActionRunner,
    CapabilityRegistry,
    FilesystemMount,
    GitIdentity,
    ProcessBinding,
    RegisteredCapability,
)
from openrund.contracts.ids import RunId
from openrund.engine import RuntimeEngine
from openrund.errors import ResourceClosedError, ValidationError
from openrund.operator import OperatorService
from openrund.paths import PathInput, normalize_local_path
from openrund.ports.providers import ModelProvider
from openrund.ports.runtime import Clock, Reporter
from openrund.runtime import DurableRunLoop
from openrund.storage import (
    RunHome,
    SqliteArtifactStore,
    SqliteExecutionLeaseStore,
    SqliteRunEventStore,
    materialize_run_home,
    run_home,
)


@final
@dataclass(frozen=True, slots=True, kw_only=True)
class LocalAssemblyConfig:
    runtime_home: PathInput
    mounts: tuple[FilesystemMount, ...] = ()
    capabilities: tuple[RegisteredCapability, ...] = ()
    process_bindings: tuple[ProcessBinding, ...] = ()
    git_executable: PathInput | None = None
    git_identities: tuple[GitIdentity, ...] = ()
    provider: ModelProvider | None = None
    own_provider: bool = False
    clock: Clock = field(default_factory=SystemClock)
    ids: LocalIdFactories = field(default_factory=LocalIdFactories.production)
    operator_input: OperatorInput = field(default_factory=RejectingOperatorInput)
    reporter: Reporter = field(default_factory=NullReporter)
    busy_timeout_ms: int = 5_000

    def __post_init__(self) -> None:
        home = normalize_local_path(self.runtime_home)
        home_path = home.path if home.path.is_absolute() else Path.cwd() / home.path
        mounts = tuple(self.mounts)
        capabilities = tuple(self.capabilities)
        bindings = tuple(self.process_bindings)
        identities = tuple(self.git_identities)
        if any(not isinstance(item, FilesystemMount) for item in mounts):
            raise ValidationError(code="local_assembly_mounts_invalid")
        if any(not isinstance(item, RegisteredCapability) for item in capabilities):
            raise ValidationError(code="local_assembly_capabilities_invalid")
        if any(not isinstance(item, ProcessBinding) for item in bindings):
            raise ValidationError(code="local_assembly_process_bindings_invalid")
        if any(not isinstance(item, GitIdentity) for item in identities):
            raise ValidationError(code="local_assembly_git_identities_invalid")
        if (self.git_executable is None) != (not identities):
            raise ValidationError(code="local_assembly_git_configuration_incomplete")
        if self.provider is not None and not callable(getattr(self.provider, "propose", None)):
            raise ValidationError(code="local_assembly_provider_invalid")
        if not isinstance(self.own_provider, bool):
            raise ValidationError(code="local_assembly_provider_ownership_invalid")
        if not callable(getattr(self.clock, "now", None)):
            raise ValidationError(code="local_assembly_clock_invalid")
        if not isinstance(self.ids, LocalIdFactories):
            raise ValidationError(code="local_assembly_ids_invalid")
        if not callable(getattr(self.operator_input, "request", None)):
            raise ValidationError(code="local_assembly_operator_input_invalid")
        if not callable(getattr(self.reporter, "report", None)):
            raise ValidationError(code="local_assembly_reporter_invalid")
        if (
            isinstance(self.busy_timeout_ms, bool)
            or not isinstance(self.busy_timeout_ms, int)
            or not 1 <= self.busy_timeout_ms <= 300_000
        ):
            raise ValidationError(code="local_assembly_busy_timeout_invalid")
        object.__setattr__(self, "runtime_home", home_path)
        object.__setattr__(self, "mounts", mounts)
        object.__setattr__(self, "capabilities", capabilities)
        object.__setattr__(self, "process_bindings", bindings)
        object.__setattr__(self, "git_identities", identities)


@final
class LocalRuntime:
    """One explicit local resource graph; no field is an authority grant."""

    __slots__ = (
        "_closed",
        "_raw_event_store",
        "action_runner",
        "artifact_store",
        "config",
        "database_path",
        "engine",
        "event_store",
        "lease_store",
        "operator",
        "operator_input",
        "registry",
        "run_loop",
        "runtime_home",
    )

    def __init__(
        self,
        *,
        config: LocalAssemblyConfig,
        raw_event_store: SqliteRunEventStore,
        event_store: ReportingEventStore,
        artifact_store: SqliteArtifactStore,
        lease_store: SqliteExecutionLeaseStore,
        engine: RuntimeEngine,
        registry: CapabilityRegistry,
        action_runner: ActionRunner,
        operator: OperatorService,
        run_loop: DurableRunLoop | None,
    ) -> None:
        self.config = config
        self.runtime_home = Path(config.runtime_home)
        self.database_path = self.runtime_home / "runtime.sqlite"
        self._raw_event_store = raw_event_store
        self.event_store = event_store
        self.artifact_store = artifact_store
        self.lease_store = lease_store
        self.engine = engine
        self.registry = registry
        self.action_runner = action_runner
        self.operator = operator
        self.run_loop = run_loop
        self.operator_input = config.operator_input
        self._closed = False

    async def __aenter__(self) -> Self:
        if self._closed:
            raise ResourceClosedError(resource="local_runtime")
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: object | None,
    ) -> None:
        await self.aclose()

    def materialize_run_home(self, run_id: RunId, /) -> RunHome:
        if self._closed:
            raise ResourceClosedError(resource="local_runtime")
        return materialize_run_home(run_home(self.runtime_home, run_id))

    async def aclose(self) -> None:
        if self._closed:
            return
        self._closed = True
        if self.run_loop is not None:
            await self.run_loop.aclose()
        await self.engine.aclose()
        await self.lease_store.aclose()
        await self.artifact_store.aclose()
        await self._raw_event_store.aclose()
