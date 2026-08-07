from __future__ import annotations

import ast
import json
import re
import sys
import zipfile
from pathlib import Path
from typing import Final

from tests.package._distributions import (
    BuiltDistributions,
    install_distribution,
    run_installed,
)

PROJECT_ROOT: Final = Path(__file__).resolve().parents[2]
SOURCE_ROOT: Final = PROJECT_ROOT / "src" / "openrund"


def test_installed_console_runs_governed_coding_demo(
    tmp_path: Path,
    built_distributions: BuiltDistributions,
) -> None:
    python = install_distribution(built_distributions, tmp_path).python
    runtime = tmp_path / "runtime"
    workspace = tmp_path / "workspace"
    completed = run_installed(
        str(python.parent / "openrund"),
        "--home",
        str(runtime),
        "--json",
        "demo",
        "governed-coding",
        str(workspace),
        cwd=tmp_path,
    )

    payload = json.loads(completed.stdout)
    assert payload["ok"] is True
    assert re.fullmatch(r"run_[0-9a-f]{32}", payload["data"]["run_id"])
    assert payload["data"]["status"] == "completed"
    assert payload["data"]["builtins"] == ["filesystem", "documents", "process", "git"]
    assert (workspace / "report.md").is_file()


def test_installed_source_distribution_runs_governed_coding_demo(
    tmp_path: Path,
    built_distributions: BuiltDistributions,
) -> None:
    python = install_distribution(built_distributions, tmp_path, kind="sdist").python
    runtime = tmp_path / "runtime"
    completed = run_installed(
        str(python.parent / "openrund"),
        "--home",
        str(runtime),
        "--json",
        "demo",
        "governed-coding",
        cwd=tmp_path,
    )

    payload = json.loads(completed.stdout)
    assert payload["ok"] is True
    run_id = payload["data"]["run_id"]
    assert re.fullmatch(r"run_[0-9a-f]{32}", run_id)
    assert payload["data"]["status"] == "completed"
    assert payload["data"]["builtins"] == ["filesystem", "documents", "process", "git"]
    workspace = runtime / "runs" / run_id / "workspace"
    assert payload["data"]["workspace_root"] == str(workspace)
    assert payload["data"]["workspace_selected_by"] == "default"
    assert (workspace / "report.md").is_file()


def test_installed_wheel_type_checks_representative_consumer(
    tmp_path: Path,
    built_distributions: BuiltDistributions,
) -> None:
    wheel = built_distributions.wheel
    python = install_distribution(built_distributions, tmp_path).python
    consumer = tmp_path / "consumer.py"
    consumer.write_text(
        """
from collections.abc import Awaitable, Callable
from pathlib import Path
from typing import assert_type

from openrund import (
    LocalAssemblyConfig as PublicLocalAssemblyConfig,
    OperatorResult as PublicOperatorResult,
    RuntimeEngine as PublicRuntimeEngine,
)
from openrund._testing.fakes import SeededClock, SeededIdFactory
from openrund.capabilities import (
    CapabilityRegistry,
    DocumentsCapability,
    FilesystemCapability,
    FilesystemMount,
    GitCapability,
    GitIdentity,
    ProcessBinding,
    ProcessCapability,
)
from openrund.bundles import (
    BundleCompatibility,
    BundleCommitment,
    BundleEventCommitment,
    BundleExportResult,
    BundleReplay,
    BundleVerification,
    ImportedBundle,
    ResumeAssessment,
    assess_resume,
    bundle_commitment,
    event_commitment,
    export_bundle,
    hash_bytes,
    import_bundle,
    replay_bundle,
    verify_bundle,
)
from openrund.codec import (
    canonical_content_bytes,
    canonical_content_hash,
    canonical_json_bytes,
    decode_command_decision,
    decode_event,
    decode_json_value,
    encode_command_decision,
    encode_event,
    encode_json_value,
)
from openrund.contracts.commands import (
    BootstrapRunOperation,
    CancelWaitOperation,
    Command,
    CommandDecisionRecord,
    CommandOrigin,
    CommandResult,
    CreateCheckpointOperation,
    CreateDelegationOperation,
    GrantCapabilityAuthorityOperation,
    MarkActionUnknownOperation,
    OpenTimerWaitOperation,
    ReconcileActionOperation,
    RecordAnnotationOperation,
    RecordCheckOperation,
    ResolveApprovalOperation,
    ResumeApprovedActionOperation,
)
from openrund.contracts.capabilities import ActionReliability, CapabilityAccessMode
from openrund.contracts.content import Content
from openrund.contracts.events import RuntimeEvent
from openrund.contracts.ids import (
    ActionId,
    ArtifactId,
    AuthorityId,
    CapabilityId,
    CommandId,
    EventId,
    LeaseId,
    MessageId,
    ModelCallId,
    RunId,
    WaitId,
)
from openrund.contracts.json import JsonObject, JsonValue, freeze_json
from openrund.contracts.portable import BundleProfile
from openrund.contracts.runs import CheckStatus, Lease, WaitKind
from openrund.contracts.time import Timestamp
from openrund.paths import LocalPath, PortablePath
from openrund.engine import EngineDependencies, RuntimeEngine
from openrund.ports.artifacts import ArtifactBlob, ArtifactEntry, ArtifactStore
from openrund.ports.events import AtomicEventStore, EventSlice, EventStore
from openrund.ports.leases import LeaseAcquireInput, LeaseStore
from openrund.ports.providers import ModelProvider, ModelRequest
from openrund.ports.runtime import Clock, IdFactory
from openrund.providers import (
    AnthropicMessagesProvider,
    LocalModelProfile,
    LocalOpenAICompatibleProvider,
    OpenAIResponsesProvider,
    ProviderTool,
    StdlibHttpTransport,
)
from openrund.runtime import DurableRunLoop, DurableRunLoopDependencies
from openrund.storage import (
    ArtifactRecoverySummary,
    PostCommitEventLog,
    PostCommitSubscriberFailure,
    RunHome,
    SqliteArtifactStore,
    SqliteExecutionLeaseStore,
    SqliteRunEventStore,
    default_openrund_home,
    materialize_run_home,
    run_home,
)
from openrund.views import (
    CompleteViewReplay,
    IncompleteViewReplay,
    RunViewBundle,
    rebuild_views,
)

run_id = RunId(value="run")
event_id = EventId(value="event")
value = freeze_json({"run": run_id.value})
clock: Clock = SeededClock((Timestamp(value="2026-01-02T03:04:05.000Z"),))
ids: IdFactory[EventId] = SeededIdFactory((event_id,))
message_ids: IdFactory[MessageId] = SeededIdFactory((MessageId(value="message"),))
model_call_ids: IdFactory[ModelCallId] = SeededIdFactory((ModelCallId(value="model"),))
command_ids: IdFactory[CommandId] = SeededIdFactory((CommandId(value="provider-command"),))
local = LocalPath(raw="workspace")
portable = PortablePath(value="events.jsonl")
replay = rebuild_views((), watermark=0)
mount = FilesystemMount(
    name="workspace",
    root=Path("/workspace"),
    access=CapabilityAccessMode.READ_WRITE,
)
filesystem_capability = FilesystemCapability(mounts=(mount,))
documents_capability = DocumentsCapability(mounts=(mount,))
process_binding = ProcessBinding(name="python", executable=Path("/usr/bin/python3"))
process_capability = ProcessCapability(mounts=(mount,), bindings=(process_binding,))
git_identity = GitIdentity(
    name="robot",
    author_name="OpenRund Robot",
    author_email="robot@example.rejected",
)
git_capability = GitCapability(
    mounts=(mount,),
    git_executable=Path("/usr/bin/git"),
    identities=(git_identity,),
)
capability_registry = CapabilityRegistry(
    (
        filesystem_capability.registered(),
        documents_capability.registered(),
        process_capability.registered(),
        git_capability.registered(),
    )
)

def lease_id() -> LeaseId:
    return LeaseId(value="lease")

def token() -> str:
    return "token"

event_adapter = SqliteRunEventStore("runtime.sqlite")
artifact_adapter = SqliteArtifactStore("runtime.sqlite", "artifacts")
lease_adapter = SqliteExecutionLeaseStore(
    "runtime.sqlite", lease_ids=lease_id, tokens=token
)
layout = run_home(Path("root"), run_id)
event_store: EventStore = event_adapter
atomic_event_store: AtomicEventStore = event_adapter
artifact_store: ArtifactStore = artifact_adapter
lease_store: LeaseStore = lease_adapter

async def subscriber(committed: tuple[RuntimeEvent, ...]) -> None:
    assert_type(committed, tuple[RuntimeEvent, ...])

async def failure_sink(failure: PostCommitSubscriberFailure) -> None:
    assert_type(failure, PostCommitSubscriberFailure)

event_log = PostCommitEventLog(event_store, (subscriber,), failure_sink)
engine = RuntimeEngine(
    EngineDependencies(
        event_store=event_store,
        clock=clock,
        event_ids=ids,
        message_ids=message_ids,
    )
)
provider_tool = ProviderTool(
    name="filesystem.read",
    description="Read a file",
    input_schema=JsonObject(entries=(("type", "object"),)),
)
openai_provider = OpenAIResponsesProvider(
    api_key="explicit",
    model="model",
    tools=(provider_tool,),
    stream=False,
)
anthropic_provider = AnthropicMessagesProvider(
    api_key="explicit",
    model="model",
    tools=(provider_tool,),
    stream=False,
)
local_provider = LocalOpenAICompatibleProvider(
    base_url="http://127.0.0.1:11434/v1",
    profile=LocalModelProfile.FALLBACK,
    stream=False,
)
model_provider: ModelProvider = openai_provider
model_request = ModelRequest(
    model_call_id=ModelCallId(value="model-request"),
    run_id=run_id,
    context=Content(preview="context"),
    remaining_requests=1,
)
http_transport = StdlibHttpTransport()
run_loop = DurableRunLoop(
    DurableRunLoopDependencies(
        engine=engine,
        provider=model_provider,
        clock=clock,
        model_call_ids=model_call_ids,
        command_ids=command_ids,
    )
)
command = Command(
    command_id=CommandId(value="command"),
    run_id=run_id,
    origin=CommandOrigin.SYSTEM,
    operation=BootstrapRunOperation(root_id=run_id),
)
wait_id = WaitId(value="wait")
action_id = ActionId(value="action")
authority_id = AuthorityId(value="authority")
capability_id = CapabilityId(value="capability")
approval = ResolveApprovalOperation(wait_id=wait_id, decision="approved")
resume = ResumeApprovedActionOperation(wait_id=wait_id)
unknown = MarkActionUnknownOperation(
    action_id=action_id,
    reliability=ActionReliability.TRANSPORT_LOST,
    reason="transport_lost",
)
annotation = RecordAnnotationOperation(content=Content(preview="note"))
checkpoint = CreateCheckpointOperation(from_position=1, to_position=1)
timer = OpenTimerWaitOperation(fire_at=Timestamp(value="2026-01-02T03:04:05.000Z"))
cancel_wait = CancelWaitOperation(wait_id=wait_id, wait_kind=WaitKind.TIMER)
grant = GrantCapabilityAuthorityOperation(
    capability_id=capability_id,
    authority_id=authority_id,
)

assert_type(run_id, RunId)
assert_type(value, JsonValue)
assert_type(clock.now(), Timestamp)
assert_type(ids.new_id(), EventId)
assert_type(local, LocalPath)
assert_type(portable, PortablePath)
assert_type(decode_json_value(b"null\\n"), JsonValue)
assert_type(encode_json_value(value), bytes)
assert_type(canonical_json_bytes(value), bytes)
assert_type(canonical_content_bytes(Content(preview="content")), bytes)
assert_type(canonical_content_hash(Content(preview="content")), str)
assert_type(replay, CompleteViewReplay[RunViewBundle] | IncompleteViewReplay)
assert_type(capability_registry, CapabilityRegistry)
assert_type(PublicLocalAssemblyConfig(runtime_home=Path("runtime")), PublicLocalAssemblyConfig)
assert_type(
    PublicOperatorResult.success(
        command="inspect", title="Inspection", data=JsonObject(entries=())
    ),
    PublicOperatorResult[JsonObject],
)
assert_type(PublicRuntimeEngine, type[RuntimeEngine])
assert_type(BundleCompatibility(), BundleCompatibility)
assert_type(hash_bytes(b"bundle"), str)
assert_type(event_commitment(()), BundleEventCommitment)
assert_type(
    bundle_commitment(
        profile=BundleProfile.COMPLETE,
        source_run_id=run_id,
        compatibility=BundleCompatibility(),
        events=event_commitment(()),
        files=(),
    ),
    BundleCommitment,
)
bundle_export: Awaitable[BundleExportResult] = export_bundle(
    run_id=run_id,
    output_path=Path("bundle.orun"),
    event_store=event_store,
    exported_at=Timestamp(value="2026-01-02T03:04:05.000Z"),
)
assert_type(verify_bundle(Path("bundle.orun")), BundleVerification)
assert_type(replay_bundle(Path("bundle.orun")), BundleReplay)
imported_bundle = import_bundle(
    Path("bundle.orun"),
    runtime_home=Path("runtime"),
    root_mappings={"workspace": Path("workspace")},
    imported_at=Timestamp(value="2026-01-02T03:04:05.000Z"),
)
assert_type(imported_bundle, ImportedBundle)
assert_type(assess_resume(imported_bundle), ResumeAssessment)
assert_type(documents_capability, DocumentsCapability)
assert_type(process_binding, ProcessBinding)
assert_type(git_identity, GitIdentity)
assert_type(default_openrund_home(), Path)
assert_type(layout, RunHome)
assert_type(materialize_run_home(layout), RunHome)
assert_type(event_log, PostCommitEventLog)
assert_type(engine, RuntimeEngine)
assert_type(openai_provider, OpenAIResponsesProvider)
assert_type(anthropic_provider, AnthropicMessagesProvider)
assert_type(local_provider, LocalOpenAICompatibleProvider)
assert_type(model_provider, ModelProvider)
assert_type(model_request, ModelRequest)
assert_type(http_transport, StdlibHttpTransport)
assert_type(run_loop, DurableRunLoop)
assert_type(approval, ResolveApprovalOperation)
assert_type(resume, ResumeApprovedActionOperation)
assert_type(unknown, MarkActionUnknownOperation)
assert_type(annotation, RecordAnnotationOperation)
assert_type(checkpoint, CreateCheckpointOperation)
assert_type(timer, OpenTimerWaitOperation)
assert_type(cancel_wait, CancelWaitOperation)
assert_type(grant, GrantCapabilityAuthorityOperation)
assert_type(CreateDelegationOperation, type[CreateDelegationOperation])
assert_type(ReconcileActionOperation, type[ReconcileActionOperation])
assert_type(RecordCheckOperation, type[RecordCheckOperation])

async def storage_types() -> None:
    artifact_id = ArtifactId(value="artifact")
    timestamp = Timestamp(value="2026-01-02T03:04:05.000Z")
    entry = ArtifactEntry(artifact_id=artifact_id, kind="document", created_at=timestamp)
    blob = ArtifactBlob(content=b"document")
    acquire = LeaseAcquireInput(run_id=run_id, owner="worker", ttl_ms=1_000, now=timestamp)

    assert_type(await event_adapter.read(run_id), EventSlice)
    assert_type(await event_adapter.has_event(event_id), bool)
    assert_type(await artifact_adapter.put(entry, blob=blob), None)
    assert_type(await artifact_adapter.get(artifact_id), ArtifactEntry | None)
    assert_type(await artifact_adapter.get_blob(artifact_id), ArtifactBlob | None)
    assert_type(await artifact_adapter.recover(timestamp), ArtifactRecoverySummary)
    assert_type(await lease_adapter.acquire(acquire), Lease | None)
    assert_type(await lease_adapter.get_active(run_id, timestamp), Lease | None)
    assert_type(await engine.submit(command), CommandResult)
    assert_type(await event_adapter.__aenter__(), SqliteRunEventStore)
    assert_type(await artifact_adapter.__aenter__(), SqliteArtifactStore)
    assert_type(await lease_adapter.__aenter__(), SqliteExecutionLeaseStore)
    assert_type(await engine.__aenter__(), RuntimeEngine)
    assert_type(await run_loop.__aenter__(), DurableRunLoop)
    assert_type(await event_adapter.aclose(), None)
    assert_type(await artifact_adapter.aclose(), None)
    assert_type(await lease_adapter.aclose(), None)
    assert_type(await engine.aclose(), None)
    assert_type(await run_loop.aclose(), None)

event_decoder: Callable[[bytes | str], RuntimeEvent] = decode_event
event_encoder: Callable[[RuntimeEvent], bytes] = encode_event
decision_decoder: Callable[[bytes | str], CommandDecisionRecord] = decode_command_decision
decision_encoder: Callable[[CommandDecisionRecord], bytes] = encode_command_decision
store_protocol: type[EventStore]
""".strip()
        + "\n",
        encoding="utf-8",
    )
    mypy = Path(sys.executable).with_name("mypy")
    assert mypy.is_file()

    completed = run_installed(
        str(mypy),
        "--strict",
        "--python-version",
        "3.12",
        "--python-executable",
        str(python),
        str(consumer),
        cwd=tmp_path,
    )

    assert "Success: no issues found" in completed.stdout
    with zipfile.ZipFile(wheel) as archive:
        assert archive.namelist().count("openrund/py.typed") == 1


def test_installed_import_is_isolated_from_source_tree(
    tmp_path: Path,
    built_distributions: BuiltDistributions,
) -> None:
    python = install_distribution(built_distributions, tmp_path).python
    completed = run_installed(
        str(python),
        "-I",
        "-c",
        "from pathlib import Path; import openrund; print(Path(openrund.__file__).resolve())",
        cwd=tmp_path,
    )
    installed_path = Path(completed.stdout.strip())

    assert installed_path.name == "__init__.py"
    assert not installed_path.is_relative_to(PROJECT_ROOT)


def test_installed_wheel_runs_documents_stdio_worker(
    tmp_path: Path,
    built_distributions: BuiltDistributions,
) -> None:
    python = install_distribution(built_distributions, tmp_path).python
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    content = "# Installed worker\n"
    (workspace / "report.md").write_text(content, encoding="utf-8")
    probe = tmp_path / "worker_probe.py"
    probe.write_text(
        """
import asyncio
import json
import sys
from pathlib import Path

from openrund.capabilities import (
    CapabilityRegistry,
    DocumentsCapability,
    FilesystemMount,
)
from openrund.contracts.capabilities import CapabilityAccessMode
from openrund.contracts.content import Content
from openrund.contracts.ids import ActionId, CapabilityId
from openrund.contracts.json import JsonObject
from openrund.ports.capabilities import CapabilityInvocation

root = Path(sys.argv[1]).resolve()
capability = DocumentsCapability(
    mounts=(
        FilesystemMount(
            name="workspace",
            root=root,
            access=CapabilityAccessMode.READ_WRITE,
        ),
    )
)
registry = CapabilityRegistry((capability.registered(),))
result = asyncio.run(
    registry.invoke(
        CapabilityInvocation(
            action_id=ActionId(value="installed-action"),
            capability_id=CapabilityId(value="documents"),
            action_name="read",
            input=Content(data={"mount": "workspace", "path": "report.md"}),
        )
    )
)
assert isinstance(result.output, JsonObject)
print(json.dumps({
    "text": result.output["text"],
    "artifact": result.inline_artifacts[0].kind,
    "worker_python": sys.executable,
}, sort_keys=True))
""".strip()
        + "\n",
        encoding="utf-8",
    )

    completed = run_installed(str(python), "-I", str(probe), str(workspace), cwd=tmp_path)
    observed = json.loads(completed.stdout)

    assert observed["text"] == content
    assert observed["artifact"] == "documents.markdown"
    assert Path(observed["worker_python"]).resolve() == python.resolve()


def _public_functions(tree: ast.Module) -> tuple[ast.FunctionDef | ast.AsyncFunctionDef, ...]:
    functions: list[ast.FunctionDef | ast.AsyncFunctionDef] = []
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if not node.name.startswith("_"):
                functions.append(node)
        elif isinstance(node, ast.ClassDef):
            for member in node.body:
                if isinstance(
                    member, (ast.FunctionDef, ast.AsyncFunctionDef)
                ) and not member.name.startswith("_"):
                    functions.append(member)
    return tuple(functions)


def test_all_source_public_callables_have_complete_annotations() -> None:
    for source in sorted(SOURCE_ROOT.rglob("*.py")):
        tree = ast.parse(source.read_text(encoding="utf-8"), filename=str(source))
        for function in _public_functions(tree):
            assert function.returns is not None, f"{source}:{function.lineno} return"
            arguments = (
                *function.args.posonlyargs,
                *function.args.args,
                *function.args.kwonlyargs,
            )
            for argument in arguments:
                if argument.arg not in {"self", "cls"}:
                    assert argument.annotation is not None, (
                        f"{source}:{function.lineno} parameter {argument.arg}"
                    )
            if function.args.vararg is not None:
                assert function.args.vararg.annotation is not None
            if function.args.kwarg is not None:
                assert function.args.kwarg.annotation is not None
