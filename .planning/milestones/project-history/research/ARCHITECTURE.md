# Architecture Research

**Domain:** Complete Python implementation of an event-sourced governed mutation runtime
**Researched:** 2026-08-04
**Confidence:** HIGH for preserved runtime semantics; MEDIUM for the new Python API and module organization

## Recommendation

Ship one distribution named `openrund` with one `src/openrund/` import package. Organize it by semantic responsibility rather than translating TypeScript packages or files one for one. Keep `RuntimeEngine` as the only authoritative mutation facade, but make it a deep facade over narrow command handlers, one private append gate, deterministic reducers, and injected ports. Providers, capability workers, Views, stores, Bundle code, CLI handlers, and plugin discovery remain outside the authority boundary.

The primary API should be async. Network providers, subprocess workers, cancellation, timers, and durable execution are naturally asynchronous, and the existing runtime contract is already promise-based. A synchronous client may wrap the async Engine, but it must contain no separate legality or event-materialization logic. This prevents two implementations from drifting.

Before implementation, freeze the serialized compatibility surface as executable fixtures. The existing documentation and source agree on the authority model but contain details that need adjudication rather than accidental copying: the TypeScript `EventEnvelope` includes `actor` and optional `commandID`, the event documentation omits them from its envelope list, and the SQLite adapter does not currently round-trip envelope `commandID`. Likewise, policy rules are represented through an overloaded `authority.granted` payload. Python must read existing data, but any change to what new Python code writes should be an explicit versioned compatibility decision.

## Fixed Contracts vs Python-Native Organization

### Behavioral and serialized contracts that remain fixed

| Contract | Required preservation |
|---|---|
| Authority | Only the Engine evaluates Commands and appends authoritative Events. All model, API, timer, capability-result, operator, Delegation, and recovery mutation paths enter this boundary. |
| CommandDecision | Preserve `accepted`, `rejected`, `deferred`, and `superseded`, including reasons, trace entries, result Event references, Wait linkage, and replacement linkage. Rejected and superseded Commands produce no target lifecycle Events. |
| Event grammar | Preserve canonical event names and versions, including Run, Command, Message, ModelCall, Action, Wait, Delegation, Check, Checkpoint, Annotation, Artifact, Authority, and Lease events. |
| Event ordering | Initial expected position is `0`; the first persisted Event is position `1`; expected position means the last committed position. Check and append must be atomic. Do not reproduce the ambiguous TypeScript name `nextPosition` internally; return `current_position` in the Python API. |
| Event and payload JSON | Preserve camelCase wire keys, enum strings, optional-field behavior, compact payload discipline, causation/correlation identity, and existing version fields. Missing and explicit `null` must not be conflated. |
| Wait semantics | Preserve the five kinds: `approval`, `interaction`, `timer`, `join`, and `reconciliation`. Wait remains the only canonical blocker concept. |
| Capability boundary | Preserve `CapabilityExecutionRequest` and `CapabilityResult` meaning. Workers return output, effects, evidence, Artifact material, and metadata; they never return Events or decide legality. |
| Provider boundary | Preserve ModelCall and parsed Operation meaning. Provider output is an untrusted proposal, not a Command or accepted transition. |
| Views | Preserve deterministic replay from ordered Events and Artifacts. A cached View is usable only at a known complete watermark and remains disposable. |
| Storage | Preserve expected-position conflict behavior, per-Run strict ordering, immutable Artifact identity, and Lease-as-coordination-only semantics. |
| Delegation | Preserve bounded contracts, explicit child Authority, separate parent/child lifecycles, join semantics, and the rule that a child terminal Event never becomes a parent terminal Event. |
| Terminal legality | Completion, failure, and cancellation are attempted mutations. Only accepted Commands can create terminal Run Events. Unknown Action outcomes and required Checks/Artifacts/Waits participate in completion legality. |
| `.orun` | Preserve schema version, directory layout, manifest fields, JSONL Events, canonical JSON hashing, Event hash chain, Artifact integrity, verification behavior, replay behavior, and ResumeAssessment issue vocabulary. |

### Python-native choices that should change

| Concern | Python-native design |
|---|---|
| Distribution | One publishable distribution and one import package, with optional dependency extras for provider SDKs. Do not recreate the TypeScript workspace as many Python distributions. |
| Naming | `snake_case` methods and attributes, `PascalCase` classes, `Path` for paths, context managers for owned resources. CamelCase exists only in wire codecs. |
| Domain values | Immutable typed value objects for Events, Commands, decisions, IDs, and definitions. Keep raw `dict[str, Any]` at untrusted parsing seams, not throughout the Engine. |
| Interfaces | `typing.Protocol` ports for storage, providers, transports, clocks, IDs, and subscribers. Structural typing is a static contract; plugin registration still performs explicit metadata and schema validation. |
| Public exports | A small curated `openrund.__init__`/`openrund.api` surface. Internal command handlers and append helpers are not re-exported. |
| Errors | Typed exceptions for caller/storage conflicts and structured result objects for runtime decisions. External failures become ModelCall or Action lifecycle data at the Engine boundary. |
| Composition | One explicit local composition root creates stores, registries, transports, providers, Bundle services, and the Engine. No import-time global registry. |
| Testing | `tests/` mirrors behavioral domains, not module files. Compatibility fixtures contain predecessor-produced JSON and `.orun` samples, not a second live implementation. |

## Standard Architecture

### System Overview

```text
 Hosts / CLI / synchronous client
              |
              v
 +-------------------------------------------------------------------+
 | Local assembly and public API                                     |
 | creates stores, registries, provider adapters, transports, Engine  |
 +-------------------------------+-----------------------------------+
                                 |
                                 v
 +-------------------------------------------------------------------+
 | RuntimeEngine — sole authority facade                             |
 | ingest -> load -> evaluate -> CommandDecision -> private append    |
 |              |                  |                    |              |
 |        command handlers     execution intent      Event log         |
 +--------------+------------------+--------------------+--------------+
                |                  |                    |
                |                  v                    v
                |        Capability/Provider ports   Store ports
                |          return untrusted data     persist only
                v
        Deterministic Views
        facts in, no decisions

 Bundle services read canonical Events/Artifacts and derive transport files.
 They verify, replay, import, and assess; they never authorize resume.
```

### Component Responsibilities and Existing-System Mapping

| Python component | Responsibility | Existing components absorbed |
|---|---|---|
| `contracts` | Canonical ontology, IDs, Event envelopes/payloads, Commands, Operations, decisions, contracts, wire codecs, normalization. No I/O. | `packages/core/src/events.ts`, `model.ts`, `run.ts`, IDs and normalization modules |
| `ports` | Minimal async Protocols for Event, Artifact, and Lease stores; model adapters; capability transports; clock/ID providers; post-commit subscribers. | `packages/core/src/storage.ts`, `ModelAdapter`, `CapabilityTransport` |
| `views` | Pure reducers for Run status/readiness, timeline, Actions, reconciliation, receipts, Artifacts, Checkpoints, Delegation, and Wait queues. | `packages/views/src/*` |
| `engine` | Command ingress, legality evaluation, terminal gates, focused transition handlers, Action/provider coordination, private authoritative append, replay facade. | `runtime-engine.ts`, legality evaluator, action dispatcher, `*-control.ts`, event log |
| `capabilities` | Definitions, schemas, registry validation, transports, discovery, and one implementation of each built-in Capability. | `packages/capabilities`, all `capability-*` packages |
| `providers` | Provider-neutral normalization plus OpenAI, Anthropic, and local OpenAI-compatible adapters. Returns ModelCalls only. | `providers` and all `provider-*` packages |
| `storage.sqlite` | SQLite migrations and Event, Artifact, and Lease store adapters behind ports. | `storage-sqlite` and storage facade |
| `bundles` | Manifest/codec, canonical hashing, export, verify, replay, import, audit output, and resume assessment. | `runtime/src/orun.ts` |
| `assembly` | Default paths, plugin loading, local runtime construction, lifecycle/close ownership. | `local-runtime.ts`, workspace-root helpers, storage factory |
| `cli` | Argument parsing, command handlers, deterministic rendering, process exit behavior. Calls injected Engine/query services only. | `packages/cli/src/index.ts` and bin |
| `workers.documents` | Markdown operations and stdio JSON-RPC server installed by the same distribution. | `openrund_documents_worker` |
| `docs` | Normative semantic contract. Changes to ontology or wire data start here and require compatibility tests. | Current `docs/` set |

## Recommended Project Structure

```text
pyproject.toml
src/
└── openrund/
    ├── __init__.py                 # curated public exports only
    ├── api.py                      # stable public types/factories
    ├── sync.py                     # thin synchronous client over async Engine
    ├── py.typed
    ├── contracts/
    │   ├── ids.py                  # typed ID constructors and validation
    │   ├── events.py               # Event envelope, catalog, payload models
    │   ├── commands.py             # Operations, Command, CommandDecision, traces
    │   ├── runs.py                 # Run, Wait, Authority, Delegation, contracts
    │   ├── artifacts.py            # Artifact references and immutable metadata
    │   ├── content.py              # compact Content/effect/evidence value types
    │   ├── codec.py                # camelCase JSON decode/encode and aliases
    │   └── canonical_json.py       # stable JSON for hashes and IDs
    ├── ports/
    │   ├── events.py               # RunEventStore, atomic multi-Run extension
    │   ├── artifacts.py            # ArtifactStore
    │   ├── leases.py               # ExecutionLeaseStore
    │   ├── capabilities.py         # CapabilityTransport
    │   ├── providers.py            # ModelAdapter
    │   └── runtime.py              # Clock, ID provider, post-commit subscriber
    ├── views/
    │   ├── rebuild.py              # one rebuild_views entry point
    │   ├── run_status.py
    │   ├── actions.py
    │   ├── waits.py
    │   ├── delegation.py
    │   ├── artifacts.py
    │   ├── checkpoints.py
    │   ├── timeline.py
    │   └── receipts.py
    ├── engine/
    │   ├── runtime_engine.py       # sole public mutation facade
    │   ├── command_bus.py          # common command processing pipeline
    │   ├── decisions.py            # accepted/rejected/deferred/superseded builders
    │   ├── plans.py                # internal CommandPlan and execution intent
    │   ├── append_gate.py          # only normal EventStore.append caller
    │   ├── event_log.py            # read + post-commit notifications
    │   ├── legality.py             # invariant/policy/contract evaluation
    │   ├── completion.py           # terminal readiness and contracts
    │   ├── execution/
    │   │   ├── actions.py          # durable dispatch/result submission
    │   │   └── models.py           # provider invocation/result submission
    │   └── handlers/
    │       ├── bootstrap.py
    │       ├── messages.py
    │       ├── model_calls.py
    │       ├── actions.py
    │       ├── waits.py
    │       ├── checks.py
    │       ├── checkpoints.py
    │       ├── delegation.py
    │       ├── authority.py
    │       ├── artifacts.py
    │       └── terminal.py
    ├── capabilities/
    │   ├── definitions.py
    │   ├── registry.py
    │   ├── schema.py
    │   ├── discovery.py
    │   ├── transports/
    │   │   ├── in_process.py
    │   │   └── stdio_json_rpc.py
    │   └── builtins/
    │       ├── filesystem/
    │       ├── documents/
    │       ├── process/
    │       └── git/
    ├── providers/
    │   ├── normalization.py
    │   ├── registry.py
    │   ├── discovery.py
    │   ├── openai.py
    │   ├── anthropic.py
    │   └── local_openai.py
    ├── storage/
    │   └── sqlite/
    │       ├── database.py
    │       ├── migrations.py
    │       ├── event_store.py
    │       ├── artifact_store.py
    │       └── lease_store.py
    ├── bundles/
    │   ├── models.py
    │   ├── codec.py
    │   ├── integrity.py
    │   ├── export.py
    │   ├── verify.py
    │   ├── replay.py
    │   ├── import_.py
    │   ├── audit.py
    │   └── resume.py
    ├── assembly/
    │   ├── local.py
    │   ├── paths.py
    │   └── plugins.py
    ├── cli/
    │   ├── main.py
    │   ├── render.py
    │   └── commands/
    │       ├── runs.py
    │       ├── waits.py
    │       ├── actions.py
    │       ├── checks.py
    │       └── bundles.py
    └── workers/
        └── documents/
            ├── __main__.py
            ├── server.py
            └── markdown.py
tests/
├── compatibility/                  # frozen JSON/Event/Bundle fixtures
├── contracts/
├── views/
├── engine/
├── capabilities/
├── providers/
├── storage/
├── bundles/
├── cli/
└── e2e/
```

### Structure Rationale

- `contracts` is the stable semantic center and has no infrastructure dependencies. It owns wire aliases so camelCase compatibility cannot leak into ordinary Python code.
- `ports` defines what the Engine needs, not what a specific adapter happens to offer. Protocols return domain values and never expose SQLite connections, HTTP responses, subprocess handles, or Event-authoring callbacks.
- `engine` is one authority package with many private handlers. Splitting handlers deepens the single facade; it does not create multiple authorities.
- `capabilities.builtins` contains exactly one implementation of filesystem, documents, process, and git behavior. Do not preserve the current duplicate filesystem implementations.
- `bundles` is split by operation because verification and import are security-sensitive and should not share a 1,500-line module with rendering and export.
- `cli.commands` separates parsing/routing from deterministic rendering and keeps storage construction in `assembly`, not command handlers.
- `workers.documents` remains a transported worker even though both sides are Python. This proves the worker boundary and failure semantics without requiring a second distribution or another language runtime.

## Allowed Dependency Directions

```text
contracts
   ^
   ├── ports
   ├── views
   ├── capabilities framework + built-ins
   ├── providers
   └── storage adapters

contracts + ports + views + capabilities framework
   ^
   └── engine

contracts + ports + views
   ^
   └── bundles

engine + bundles + concrete adapters
   ^
   └── assembly
        ^
        ├── cli
        └── examples/host applications
```

Hard rules:

1. `contracts`, `ports`, and `views` never import `engine`.
2. Capability and provider modules never import `RuntimeEngine`, Event stores, Bundle writers, CLI code, or concrete storage.
3. Storage imports contracts and store Protocols only. It validates persistence invariants but never evaluates legality.
4. Command handlers may build internal Event drafts but cannot append. Only `engine.append_gate` receives the Event store dependency.
5. Bundle replay may call View reducers; Bundle import may stage verified files. Neither path calls command handlers or appends canonical Run Events.
6. CLI mutation commands call `RuntimeEngine`; CLI query commands call Engine/query services. They never call a store directly.
7. `assembly` is the only layer allowed to know concrete stores, provider adapters, Capability transports, and plugin discovery simultaneously.

## Core Protocols

The protocols should be small and async at the Engine-facing edge:

```python
class RunEventStore(Protocol):
    async def append(self, batch: AppendEvents) -> AppendResult: ...
    async def read(self, run_id: RunID, from_position: int = 1) -> EventSlice: ...
    async def has_event(self, event_id: EventID) -> bool: ...

class AtomicRunEventStore(RunEventStore, Protocol):
    async def append_many(self, batches: Sequence[AppendEvents]) -> Sequence[AppendResult]: ...

class ArtifactStore(Protocol):
    async def put(self, entry: ArtifactEntry, blob: ArtifactBlob | None = None) -> None: ...
    async def get(self, artifact_id: ArtifactID) -> ArtifactEntry | None: ...
    async def get_blob(self, artifact_id: ArtifactID) -> ArtifactBlob | None: ...
    async def mark_unavailable(self, artifact_id: ArtifactID, at: datetime) -> None: ...

class CapabilityTransport(Protocol):
    kind: str
    async def execute(self, request: CapabilityExecutionRequest) -> CapabilityResult: ...

class ModelAdapter(Protocol):
    provider: str
    async def invoke(self, context: ModelContext) -> ModelCall: ...
```

Use Protocols primarily for static structural typing. Do not treat `@runtime_checkable` as plugin validation: Python only checks member presence, not signatures or semantic compatibility. Registries must validate IDs, versions, duplicate names, schemas, action posture, reliability, batching eligibility, and transport declarations before a plugin becomes reachable.

The base Event store stays small. Cross-Run Delegation creation additionally requires `AtomicRunEventStore.append_many` in the local SQLite assembly so the parent spawn, child bootstrap, and parent establishment cannot partially commit. A future backend that cannot provide a multi-stream transaction must implement an explicit idempotent recovery workflow; silent sequential appends are not acceptable.

## RuntimeEngine as a Deep Authority Module

`RuntimeEngine` should expose one generic mutation entry plus ergonomic helpers:

```python
await engine.submit(command, expected_position=watermark)
await engine.record_model_output(...)
await engine.resolve_approval(...)
await engine.fire_timer(...)
await engine.record_check_result(...)
await engine.reconcile_action_outcome(...)
await engine.complete_run(...)
```

Every helper constructs a Command and delegates to the same `submit` pipeline. There is no public `RuntimeEngine.append`. Bootstrap uses an internal handler and the same append gate. Tests that need arbitrary history use a private fixture builder or an in-memory store directly; production adapters, examples, plugins, and CLI code cannot obtain an Event-authoring shortcut from the Engine.

The processing pipeline is:

1. Validate the Command envelope and operation schema.
2. Read canonical Events through the requested expected position.
3. Rebuild deterministic Views and derive legality facts at that watermark.
4. Route to one handler. The handler returns a `CommandPlan`: CommandDecision, decision trace, Event drafts, Wait linkage, and optionally an internal execution intent.
5. The Engine binds IDs/timestamps, produces `command.recorded`, and sends the complete append batch through the private append gate.
6. Only after the enabling Events are durable may an execution coordinator invoke a provider or Capability worker.
7. Provider output or worker result re-enters the Engine as data on another Command. The Engine alone materializes ModelCall, Action outcome, Artifact, Wait, Check, Delegation, or terminal Events.
8. Post-commit subscribers receive persisted Events. Subscriber failure is isolated and cannot turn a successful append into an apparent failure.

Handlers are pure with respect to persistence and external effects. They may use current Views, policy definitions, Capability metadata, clocks, and ID providers supplied in their input. They cannot call transports or stores. This makes legality tables directly testable and prevents the Engine facade from becoming another monolith.

### Durable Action execution

The Action path should use two authoritative turns:

```text
create_action Command
  -> legality/Authority/policy/schema/resource checks
  -> rejected, deferred Wait, or accepted action.created/action.started
  -> durable append
  -> CapabilityTransport.execute
  -> CapabilityResult or classified transport failure
  -> capability-origin result Command
  -> action.completed / failed / cancelled / unknown + Artifact Events
```

This ordering ensures a crash after dispatch has a durable Action identity and reliability class that recovery can reconcile. Timeouts or transport loss after dispatch are not ordinary failures; consequential effects may have occurred, so the result Command must produce `action.unknown` and normally a reconciliation Wait. Automatic retries are allowed only when the Capability reliability and idempotency contract make them legal.

### Durable ModelCall execution

The default run loop similarly records `model_call.started` through the Engine before invoking a provider, then submits provider completion/failure and the parsed Operation back through Engine Commands. `record_model_output` may remain as a host-integration helper for an already completed external call, but it must still create the audited ModelCall/Command sequence and never treat the Operation as accepted state. Provider retries use ModelCall identity and budget policy; they do not replay already accepted Operations.

### Optimistic concurrency

The SQLite expected-position check and Event inserts occur in one immediate write transaction. A process-local per-Run lock may reduce avoidable conflicts, but the database watermark is authoritative. On conflict, reload the winning history and re-evaluate. Never blindly rerun a Capability side effect after an append conflict; use durable Action identity and idempotency/reconciliation semantics.

## Sync and Async Stance

The canonical `RuntimeEngine` API and all Engine-facing ports are async.

- Provider HTTP, timers, stdio JSON-RPC, subprocess cancellation, and Action execution remain awaitable end to end.
- Blocking filesystem and SQLite work must not run on the event-loop thread. The SQLite adapter should confine its connection and transactions to one dedicated worker thread (or an equivalent vetted async SQLite adapter). A connection is never shared concurrently across arbitrary threads.
- Built-in blocking handlers adapt through `asyncio.to_thread()` or a transport-owned executor. The Engine does not guess whether user code is blocking.
- The CLI is a top-level owner and may call `asyncio.run(main())` once.
- Library code never calls `asyncio.run()` internally and never nests an event loop.

`openrund.sync.SyncRuntime` is an optional convenience client, not another Engine. It owns one `asyncio.Runner` and one async `RuntimeEngine` for its context-managed lifetime, delegates every method, and closes owned resources deterministically. It rejects use from a thread already running an event loop with a clear instruction to use the async Engine. Do not expose parallel `sync_*` store, legality, or handler implementations, and do not share one Engine instance between the sync wrapper and an unrelated event loop.

## Capability and Provider Integration

### Built-ins and transports

Capability definitions are inert metadata. A registry validates definitions at assembly time, while transports execute only after the Engine has accepted an Action.

- `in_process` adapts first-party filesystem, process, and git handlers.
- `stdio_json_rpc` launches the packaged documents worker with a minimal allowlisted environment, bounded message size, startup handshake, timeout, cancellation, stderr diagnostics, and structured error mapping.
- The documents worker provides Markdown read/write, frontmatter, section, and patch operations. It returns `CapabilityResult`; the server package imports no Engine or Event types.
- Filesystem mount posture and symlink/path containment are enforced inside the Capability as defense in depth in addition to Engine Authority and policy checks.
- Process and git output is streamed or bounded before Artifact materialization; preview truncation must not occur only after unbounded buffering.

### Optional plugins

Use `importlib.metadata.entry_points()` only in `assembly.plugins`, with namespaced groups:

- `openrund.providers`
- `openrund.capabilities`

An entry point loads a factory, not a global singleton. A provider factory returns a `ModelAdapter` plus version/compatibility metadata. A Capability factory returns definitions and transport factories. The composition root then applies an explicit allowlist and registry validation. Duplicate IDs fail closed.

Plugin discovery is opt-in for embedded runtimes and explicit in CLI configuration. Loading an installed entry point executes third-party Python code, so discovery itself is not a security sandbox. The architectural safeguard is least authority: factories receive configuration and narrow ports only, never `RuntimeEngine`, Event stores, append callbacks, Bundle custody, or mutable Views. A malicious Capability can still perform effects when invoked; Engine legality, sandboxing, process isolation, and deployment trust remain necessary.

### Provider normalization

Keep provider-neutral Operation normalization in one module. Concrete adapters translate provider HTTP/tool-call shapes into that intermediate representation and preserve raw response references as Artifacts when configured. They do not:

- choose CommandDecision;
- grant Authority;
- resolve Waits;
- create Event envelopes;
- retain independent Run execution state;
- treat a text completion as terminal legality.

Provider transport/parse failures become ModelCall failure input to the Engine. A syntactically parsed but unsupported or illegal Operation becomes a rejected Command instead.

## Data Flows

### Model-originated mutation

```text
Host -> RuntimeEngine start_model_call Command -> durable model_call.started
     -> provider adapter -> ModelCall(Operation proposal) or provider failure
     -> RuntimeEngine result/Operation Commands
     -> read Events -> rebuild Views -> legality + CommandDecision
     -> command.recorded + ModelCall/target Event drafts
     -> expected-position append
     -> optional durable Action execution
     -> worker CapabilityResult
     -> RuntimeEngine.submit(result Command)
     -> outcome/Artifact Events
     -> replayed Views / Receipts / CLI output
```

### Operator, timer, capability-result, and recovery mutation

```text
External input -> typed RuntimeEngine helper -> Command -> same pipeline
```

Approval resolution records the exact Wait decision and any revised input, then the continuation is revalidated against current Authority, schema, resource scope, and policy. Approval never converts an illegal input into a legal one.

### Read and replay

```text
RunEventStore.read -> wire decode -> ordered Event values -> pure reducers
                   -> RunViewBundle / Receipts / Reports
```

Views do not call stores themselves. The caller supplies the complete ordered slice and watermark. Persisted snapshots, if introduced later, are caches that include the source watermark and can always be discarded.

### Delegation

The Engine evaluates the parent Command, validates bounded child Authority and contract, and atomically appends parent and child bootstrap batches in SQLite. Child terminal handoff later enters the parent as a new Command. Join satisfaction may resolve a join Wait, but it does not directly complete the parent.

### Bundle

```text
Events + Artifacts -> export -> manifest/files/hash commitments
Bundle path -> path validation -> schema validation -> integrity -> Event grammar
            -> verify -> replay Views OR stage import -> ResumeAssessment
```

Verification is side-effect free and validates every manifest-derived path before filesystem access. Replay reads only Bundle contents. Import stages verified content under runtime custody but does not append Run Events or authorize resume. ResumeAssessment is deterministic diagnostics; actual resume must enter Engine legality.

## SQLite and Artifact Boundaries

The SQLite implementation should preserve three independent ports while sharing one database lifecycle in the local assembly:

- Event append: one immediate transaction contains current-position read, duplicate Event-ID checks, all Event inserts, and commit/rollback.
- Multi-Run append: all parent/child Delegation batches and expected-position checks share one transaction.
- Lease operations: acquisition/renewal/release use conditional writes and fencing tokens. A Lease coordinates workers but never proves Authority or Command legality.
- Artifact storage: immutable metadata and content identity. Blob writes use staged temporary files plus atomic rename where possible, with explicit recovery for orphan/missing bytes. Event payloads reference Artifact IDs; they do not embed large content.

The adapter owns transaction mode, WAL/busy timeout, connection/thread confinement, migrations, and JSON encoding. Protocol callers see domain results and typed `ExpectedPositionConflict`, never `sqlite3.Connection` or SQL exceptions.

## Bundle Compatibility Boundary

Centralize all Bundle constants and wire models in `bundles.models`/`bundles.codec`. Compatibility tests must cover:

- `manifest.json` critical fields and exact layout;
- `events.jsonl` envelope/payload round trips;
- canonical key ordering and treatment of omitted optional fields;
- SHA-256 file commitments and `sha256-chain-v1` Event head;
- Artifact inclusion/omission categories;
- export profiles;
- fail-closed path normalization across POSIX and Windows separators;
- replayed Views from an existing Bundle;
- import provenance and every ResumeAssessment issue kind.

Do not serialize internal dataclasses with a generic `asdict()` or model dump. The dedicated codec is the compatibility seam and must use golden predecessor-generated fixtures. Python may expose richer typed objects while writing the same wire format.

## Scaling Considerations

| Scale | Architecture response |
|---|---|
| Local development and tens of active Runs | One process, SQLite WAL, expected positions, full replay, local Artifact files. This is the milestone target. |
| Hundreds to low thousands of long Runs | Add watermark-keyed View snapshots, bounded Artifact streaming, a durable lease-driven runner, and targeted Event reads. Preserve full replay verification. |
| Multi-host/high write concurrency | Add a server-grade `RunEventStore`, object Artifact store, database-time leases with fencing, and transactional multi-stream append. Do not split Engine semantics into services first. |

The first bottleneck is repeated full-history replay, followed by SQLite write contention and local Artifact custody. These are adapter/cache concerns; none justify weakening expected-position ordering or moving legality into storage.

## Dependency-Ordered Implementation Sequence

1. **Freeze compatibility evidence.** Generate representative Event JSON, Command decisions, View results, SQLite conflict cases, and `.orun` Bundles once from the current implementation. Check them in as inert fixtures with a contract decision log for documentation/code mismatches. Stop feature development in the predecessor.
2. **Create the Python distribution and contract kernel.** Implement IDs, immutable domain values, enum vocabularies, wire codecs, canonical JSON, and compatibility tests. This establishes the only serialization layer.
3. **Implement pure Views.** Port reducers by behavior, not file shape. Replay golden streams and compare every Run/Action/Wait/Delegation/Check/Artifact surface before adding authority code.
4. **Implement ports and storage.** Add in-memory test stores, SQLite Event/Artifact/Lease adapters, expected-position transactions, atomic multi-Run append, and crash-consistency tests. Engine work can then target stable ports.
5. **Implement the Engine command kernel.** Add private append gate, `command.recorded`, decision traces, bootstrap, messages, Authority/policy, lifecycle invariants, and terminal gates. Every path uses `submit` from the start.
6. **Implement Wait, Check, Checkpoint, uncertainty, and Delegation handlers.** Build completion legality on stable Views; test approval revision, one-shot Wait resolution, reconciliation, join modes, cancellation policy, and injected multi-Run append failures.
7. **Implement Capability infrastructure and built-ins.** Registry/schema validation first, then transports, durable Action execution, Artifact materialization, and exactly one filesystem/documents/process/git implementation. Add fault injection before provider work.
8. **Implement provider adapters and the durable run loop.** Build shared normalization, deterministic mocked adapters, ModelCall lifecycle, cancellation/timeouts, and lease-owned resume. Provider plugins remain optional adapters.
9. **Implement Bundles.** With Events, Views, Artifacts, capabilities, policy, and providers stable, implement export/verify/replay/import/resume assessment against golden Bundles and malicious-path fixtures.
10. **Implement local assembly, sync client, CLI, and flagship demo.** These become thin consumers of the finished contracts. The end-to-end demo proves rejected mutation, approval, execution, unknown reconciliation, Checks, Delegation, completion, and Bundle portability.
11. **Cut over once.** Rewrite live docs/examples for Python, run full parity/security tests, remove TypeScript/Node tooling and generated outputs, and publish only the Python distribution. Do not ship a compatibility bridge that keeps two runtimes alive.

This order avoids building adapters against unstable contracts, avoids duplicating logic in sync and async APIs, and makes the predecessor useful only as a fixture oracle. Each completed layer becomes the sole implementation for the Python path; no new feature should be implemented twice.

## Anti-Patterns

### Mechanical file-for-file translation

**What people do:** Recreate every TypeScript package, barrel, class, and helper as a Python module.
**Why it fails:** It preserves monoliths, duplicate filesystem implementations, provider normalization drift, and JavaScript-specific API shapes.
**Instead:** Preserve behavior and wire data while grouping Python code into deep semantic modules behind a small public API.

### A public raw append escape hatch

**What people do:** Expose `RuntimeEngine.append` for convenience, then use it from CLI, workers, tests, or imports.
**Why it fails:** It makes Engine authority conventional rather than structural.
**Instead:** Keep append private; give fixtures direct in-memory-store helpers that are not public runtime APIs.

### Two Engine implementations for sync and async

**What people do:** Maintain synchronous and asynchronous stores, handlers, legality evaluators, and runtimes separately.
**Why it fails:** Decisions and Event sequences drift.
**Instead:** One async Engine; a thin context-managed synchronous client delegates to it.

### Plugin access to Engine or storage

**What people do:** Pass the Engine, Event store, or append callback into provider and Capability factories.
**Why it fails:** A plugin can author history or resolve lifecycle state outside Command evaluation.
**Instead:** Pass configuration and narrow execution/context values only; results return through typed ports.

### Views as hidden authority

**What people do:** Put `can_complete()` or policy decisions inside reducers and trust cached state without a watermark.
**Why it fails:** Derived data becomes canonical and stale caches change legality.
**Instead:** Views supply deterministic facts; Engine legality interprets them against contracts and policy.

### Worker-authored Events

**What people do:** Let a handler return `action.completed` or `artifact.created` envelopes.
**Why it fails:** Workers choose history, IDs, causation, and lifecycle.
**Instead:** Workers return `CapabilityResult`; Engine-owned handlers materialize Events.

### Implicit serialization

**What people do:** Dump Python models directly to JSON and assume aliases/defaults match predecessor data.
**Why it fails:** `None`, missing fields, datetimes, bytes, enum values, and key casing change hashes and Bundle compatibility.
**Instead:** Use one explicit versioned wire codec and golden fixtures.

### Long-lived dual runtimes

**What people do:** Keep TypeScript and Python both active, patch both during migration, or ship one calling the other.
**Why it fails:** Semantics, tests, and docs become permanently ambiguous.
**Instead:** Freeze the predecessor, extract fixtures once, complete the Python dependency chain, then remove the predecessor in a single cutover.

### Sequential parent/child Delegation appends

**What people do:** Append parent spawn, child bootstrap, and parent establishment independently.
**Why it fails:** A crash leaves incompatible Run histories.
**Instead:** Use atomic multi-Run append in SQLite or a formally modeled idempotent recovery workflow.

## Phase-Specific Research Flags

| Phase topic | Research needed | Reason |
|---|---|---|
| Compatibility kernel | HIGH | Adjudicate Event `actor`/`commandID`, optional field encoding, policy-on-Authority payloads, ID/hash generation, and exact existing Bundle fixtures before code. |
| Durable Action runner | HIGH | Define crash points around `action.started`, worker dispatch, timeout, lease loss, unknown outcome, and safe retry by reliability class. |
| Delegation | HIGH | Specify atomic multi-stream append and recovery behavior for partial legacy histories. |
| Bundle codec/verification | HIGH | Byte-level canonicalization and hostile path handling are security and portability seams. |
| SQLite/Event/Artifact transactions | MEDIUM | Choose connection confinement and staged Artifact write recovery while preserving expected-position semantics. |
| Provider adapters | MEDIUM | Verify current SDK response/tool-call contracts and keep live contract tests separate from deterministic tests. |
| Pure Views and CLI rendering | LOW | Existing reducers and command outputs provide strong local behavioral references. |

## Confidence Assessment

| Area | Confidence | Basis |
|---|---|---|
| Authority and component boundaries | HIGH | Normative docs and implemented runtime paths agree on the Engine-only authority rule. |
| Serialized compatibility requirements | HIGH | Event, model, storage, and Bundle source define the current shapes; noted discrepancies require explicit phase-0 decisions. |
| Python module decomposition | MEDIUM | Derived from current cohesion problems and standard Python packaging/interface patterns. |
| Async-first stance | MEDIUM | Matches the runtime I/O model and official `asyncio` guidance, but the exact SQLite adapter library belongs to stack selection. |
| Plugin discovery | MEDIUM | Official entry-point APIs are stable; OpenRund-specific allowlisting and compatibility metadata still need implementation design. |
| Phase ordering | HIGH | Follows direct dependency direction from contracts to Views/storage, Engine, adapters, Bundles, and surfaces. |

## Sources

Primary project sources:

- `.planning/PROJECT.md`
- `docs/concepts.md`, `docs/control.md`, `docs/architecture.md`, `docs/events.md`
- `docs/capabilities.md`, `docs/providers.md`, `docs/storage.md`, `docs/bundles.md`, `docs/delegation.md`
- `docs/api.md`, `docs/quickstart.md`
- `.planning/codebase/ARCHITECTURE.md`, `STRUCTURE.md`, `CONVENTIONS.md`, `CONCERNS.md`
- `packages/core/src/events.ts`, `model.ts`, `run.ts`, `storage.ts`
- `packages/runtime/src/runtime-engine.ts`, `local-runtime.ts`, `event-log.ts`, `orun.ts`
- `packages/capabilities/src/definition.ts`, `registry.ts`, `dispatcher.ts`
- `packages/views/src/index.ts`
- `packages/storage-sqlite/src/sqlite-store.ts`
- `packages/cli/src/index.ts`
- `python/openrund_documents_worker/openrund_documents_worker/server.py`

Official Python references:

- [Python 3.12 typing.Protocol and runtime_checkable](https://docs.python.org/3.12/library/typing.html#typing.Protocol) — MEDIUM confidence via documentation-search seam; supports structural Protocols and the warning that runtime checks validate presence, not signatures.
- [Python 3.12 asyncio running blocking I/O in threads](https://docs.python.org/3.12/library/asyncio-task.html#running-in-threads) — MEDIUM confidence via documentation-search seam; supports an async Engine with explicit blocking-I/O adapters.
- [Python 3.12 importlib.metadata entry points](https://docs.python.org/3.12/library/importlib.metadata.html#entry-points) — MEDIUM confidence via documentation-search seam; supports optional provider/Capability discovery at the composition root.
- [Python sqlite3 connection and transaction control](https://docs.python.org/3/library/sqlite3.html#transaction-control) — MEDIUM confidence via documentation-search seam; supports explicit transaction ownership and serialized connection use.

---
*Architecture research for: OpenRund v2.0 Python implementation*
*Researched: 2026-08-04*
