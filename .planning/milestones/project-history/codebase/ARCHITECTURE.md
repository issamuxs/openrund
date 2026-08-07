<!-- refreshed: 2026-05-15 -->
# Architecture

**Analysis Date:** 2026-05-15

## System Overview

```text
┌──────────────────────────────────────────────────────────────────────────────┐
│                         Public Surfaces / Assemblies                         │
├────────────────────────┬────────────────────────┬────────────────────────────┤
│ CLI commands           │ Local runtime assembly │ Governed coding demo       │
│ `packages/cli/src`     │ `packages/runtime/src` │ `examples/governed-coding-run/run.ts` │
└───────────┬────────────┴───────────┬────────────┴──────────────┬─────────────┘
            │                        │                           │
            ▼                        ▼                           ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│                           Runtime Authority Layer                            │
│ `packages/runtime/src/runtime-engine.ts`                                     │
│ `packages/runtime/src/legality-evaluator.ts`                                 │
│ `packages/runtime/src/*-control.ts`                                          │
└───────────┬────────────────────────┬───────────────────────────┬─────────────┘
            │                        │                           │
            ▼                        ▼                           ▼
┌───────────────────────┐  ┌──────────────────────┐  ┌────────────────────────┐
│ Core Contracts        │  │ Capability Boundary   │  │ Derived Views          │
│ `packages/core/src`   │  │ `packages/capabilities/src` │ `packages/views/src` │
└───────────┬───────────┘  └───────────┬──────────┘  └───────────┬────────────┘
            │                          │                         │
            ▼                          ▼                         ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│                        Persistence / Workers / Providers                     │
│ `packages/storage-sqlite/src`                                                │
│ `packages/capability-*/src`                                                  │
│ `python/openrund_documents_worker/openrund_documents_worker`                 │
│ `packages/provider-*/src`                                                    │
└──────────────────────────────────────────────────────────────────────────────┘
```

## Component Responsibilities

| Component | Responsibility | File |
|-----------|----------------|------|
| Core ontology and contracts | Define Run, Command, Event, ModelCall, Action, Wait, Delegation, Check, Checkpoint, Artifact, Authority, Lease, Bundle, View types. | `packages/core/src/run.ts`, `packages/core/src/events.ts`, `packages/core/src/model.ts`, `packages/core/src/storage.ts` |
| Runtime engine | Own all authoritative mutations, command decisions, event append calls, waits, checks, delegation handoffs, action continuation, bundle operations, and replay. | `packages/runtime/src/runtime-engine.ts` |
| Event log adapter | Wrap the configured `RunEventStore` and notify runtime subscribers after append. | `packages/runtime/src/event-log.ts` |
| Legality helpers | Construct accepted, rejected, deferred, and superseded command decisions and command envelopes. | `packages/runtime/src/legality-evaluator.ts` |
| Runtime control modules | Materialize domain-specific event drafts for bootstrap, action lifecycle, approval waits, timers, interactions, checkpoints, checks, reconciliation, and delegation. | `packages/runtime/src/bootstrap.ts`, `packages/runtime/src/action-lifecycle.ts`, `packages/runtime/src/wait-control.ts`, `packages/runtime/src/check-control.ts`, `packages/runtime/src/delegation-control.ts` |
| Capability registry and transports | Validate capability definitions and execute requested actions through transport implementations. | `packages/capabilities/src/registry.ts`, `packages/capabilities/src/dispatcher.ts`, `packages/capabilities/src/transports/in-process.ts`, `packages/capabilities/src/transports/stdio-json-rpc.ts` |
| Action dispatcher | Enforce capability policy, validate input schemas, call capability transports, materialize artifacts, and produce action lifecycle event drafts. | `packages/runtime/src/action-dispatcher.ts` |
| Local runtime assembly | Compose storage, capability registry, transports, providers, operator prompts, progress reporter, and `RuntimeEngine`. | `packages/runtime/src/local-runtime.ts` |
| Views | Rebuild non-authoritative read models, receipts, timelines, wait queues, artifact index, action status, checkpoint state, and delegation state from events. | `packages/views/src/index.ts`, `packages/views/src/run-status-view.ts` |
| SQLite storage | Persist append-only run events, artifacts, and leases in local SQLite databases and runtime artifact directories. | `packages/storage-sqlite/src/sqlite-store.ts`, `packages/storage-sqlite/src/sqlite-artifact-store.ts`, `packages/storage-sqlite/src/sqlite-lease-store.ts` |
| Storage facade | Provide the default SQLite local storage binding used by examples and CLI wiring. | `packages/storage/src/index.ts` |
| CLI | Parse operator commands, call an injected runtime, and render inspection, waits, receipts, bundles, checks, and command explanations. | `packages/cli/src/index.ts`, `packages/cli/src/bin.ts` |
| Provider adapters | Convert concrete provider APIs into OpenRund `ModelAdapter` contracts. | `packages/provider-openai/src/openai-adapter.ts`, `packages/provider-anthropic/src/anthropic-adapter.ts`, `packages/provider-local/src/local-openai-compatible-adapter.ts` |
| Capability workers | Implement domain work behind Engine-controlled Action lifecycle semantics. | `packages/capability-filesystem/src/filesystem-capability.ts`, `packages/capability-process/src/process-capability.ts`, `packages/capability-git/src/git-capability.ts`, `packages/capability-documents/src/documents-client.ts`, `python/openrund_documents_worker/openrund_documents_worker/server.py` |
| Governed demo | Exercise the authority loop with workspace roots, approval waits, capability actions, checks, unknown outcomes, receipts, and bundle export/replay. | `examples/governed-coding-run/run.ts` |

## Pattern Overview

**Overall:** Event-sourced authoritative runtime with a central Engine, rebuildable views, and capability worker boundaries.

**Key Characteristics:**
- Treat `packages/runtime/src/runtime-engine.ts` as the only code path that appends authoritative runtime events for normal operations.
- Treat provider output, CLI input, timers, capability results, operator actions, and recovery as proposals that enter the command-decision path.
- Keep durable content in artifacts and compact facts in event payloads, following `docs/events.md`.
- Derive operator-facing state from `packages/views/src/*`; do not make views decide legality.
- Add domain work as capabilities in `packages/capability-*` or `packages/capabilities/src/builtins`, then register definitions and transports through `packages/runtime/src/local-runtime.ts`.

## Layers

**Documentation Contract Layer:**
- Purpose: Defines the normative architecture, ontology, event grammar, capability contract, storage contract, provider contract, bundle contract, and delegation rules.
- Location: `docs/architecture.md`, `docs/concepts.md`, `docs/events.md`, `docs/capabilities.md`, `docs/storage.md`, `docs/providers.md`, `docs/bundles.md`, `docs/delegation.md`
- Contains: Runtime contract docs and semantic constraints.
- Depends on: Not applicable.
- Used by: All implementation packages and future code changes.

**Core Type Layer:**
- Purpose: Defines shared TypeScript contracts without owning runtime decisions.
- Location: `packages/core/src`
- Contains: Event envelopes and payloads in `packages/core/src/events.ts`, model operation and command decision types in `packages/core/src/model.ts`, run concepts in `packages/core/src/run.ts`, ID branding in `packages/core/src/ids.ts`, storage interfaces in `packages/core/src/storage.ts`, normalization helpers in `packages/core/src/normalization.ts`.
- Depends on: Standard TypeScript and Node-compatible primitives only.
- Used by: `packages/runtime/src`, `packages/views/src`, `packages/storage-sqlite/src`, `packages/capabilities/src`, provider packages, CLI, examples, and tests.

**Runtime Authority Layer:**
- Purpose: Evaluates attempted mutations, records `command.recorded`, appends accepted lifecycle events, and enforces terminal legality.
- Location: `packages/runtime/src`
- Contains: `RuntimeEngine`, command decision helpers, event drafting control modules, run contracts, wait handling, delegation handling, check handling, artifact materialization, bundle import/export/replay, and local assembly.
- Depends on: `@openrund/core`, `@openrund/capabilities`, `@openrund/views`, configured stores and transports.
- Used by: `packages/cli/src`, `examples/governed-coding-run/run.ts`, tests, and public package consumers.

**Capability Boundary Layer:**
- Purpose: Defines what can be invoked and how worker results return to the Engine.
- Location: `packages/capabilities/src`, `packages/capability-filesystem/src`, `packages/capability-documents/src`, `packages/capability-process/src`, `packages/capability-git/src`
- Contains: Capability definitions, schemas, registry validation, transports, built-in definitions, and concrete handlers/workers.
- Depends on: `@openrund/core` for IDs/effects and `@openrund/capabilities` for schemas/results.
- Used by: `ActionDispatcher` in `packages/runtime/src/action-dispatcher.ts` and local/demo assemblies.

**Provider Layer:**
- Purpose: Adapts model providers into parsed model calls and operations; provider output is proposal data only.
- Location: `packages/provider-openai/src`, `packages/provider-anthropic/src`, `packages/provider-local/src`, `packages/providers/src`
- Contains: Concrete adapters and re-export/factory surface.
- Depends on: `@openrund/core` model contracts and provider SDK packages where configured.
- Used by: `createLocalRuntime` consumers and examples.

**View Layer:**
- Purpose: Rebuild deterministic read models from canonical events and artifacts.
- Location: `packages/views/src`
- Contains: `rebuildViews`, run status, wait queues, timeline, action receipts, action reconciliation view, artifact index, checkpoint view, delegation view.
- Depends on: `@openrund/core` and event normalization.
- Used by: Runtime legality checks as cached derived facts, CLI inspection, receipts, reports, bundles, tests.

**Storage Layer:**
- Purpose: Persist append-only event history, artifacts, and leases for local runtime use.
- Location: `packages/storage-sqlite/src`, `packages/storage/src`
- Contains: SQLite migrations, `SqliteRunEventStore`, `SqliteArtifactStore`, `SqliteExecutionLeaseStore`, and default `sqlite()` binding.
- Depends on: Node `sqlite`, filesystem APIs, and `@openrund/core` storage interfaces.
- Used by: CLI process setup, examples, tests, and any local runtime assembly.

**Operator Surface Layer:**
- Purpose: Expose runtime inspection and control without deciding legality.
- Location: `packages/cli/src`, `packages/runtime/src/operator-prompts.ts`, `packages/runtime/src/runtime-progress-entries.ts`
- Contains: CLI command routing, renderers, progress entries, and console prompts.
- Depends on: Injected `RuntimeEngine`, storage binding, and views.
- Used by: `orun` CLI package bin, examples, and tests.

**Python Document Worker Layer:**
- Purpose: Provide transported Markdown document operations outside the TypeScript core runtime.
- Location: `python/openrund_documents_worker/openrund_documents_worker`
- Contains: JSON-RPC stdio server in `python/openrund_documents_worker/openrund_documents_worker/server.py`, protocol handling in `jsonrpc.py`, Markdown operations in `markdown_ops.py`.
- Depends on: Python packaging in `python/openrund_documents_worker/pyproject.toml`.
- Used by: TypeScript documents capability client in `packages/capability-documents/src/documents-client.ts` and stdio transport tests.

## Data Flow

### Primary Model-Originated Action Path

1. Provider output enters `RuntimeEngine.recordModelOutput` (`packages/runtime/src/runtime-engine.ts:148`).
2. The model call is schema/policy validated with `validateModelCall` (`packages/runtime/src/model-operation-validator.ts`).
3. For `create_action`, the runtime rebuilds current views with `rebuildViews` (`packages/views/src/index.ts:41`) and evaluates capability policy through `evaluateCapabilityPolicy` (`packages/runtime/src/capability-policy.ts`).
4. The runtime creates model-call and command-recording event drafts through `modelCallEvents` (`packages/runtime/src/runtime-engine.ts:1359`).
5. `ActionDispatcher.dispatchAction` validates the capability action and either creates approval wait events or executes the transport (`packages/runtime/src/action-dispatcher.ts:56`).
6. Capability transports execute worker code through definitions registered in `packages/capabilities/src/registry.ts` and `packages/capabilities/src/dispatcher.ts`.
7. `materializeActionResult` converts worker `CapabilityResult` inline artifacts into artifact records/events (`packages/runtime/src/artifact-materialization.ts`).
8. `RuntimeEventLog.append` persists the command/model/action events via the configured `RunEventStore` (`packages/runtime/src/event-log.ts`).
9. Views, receipts, CLI output, reports, and bundle surfaces are rebuilt from the appended events (`packages/views/src/index.ts:41`).

### Approval Wait Flow

1. A policy outcome of `requires_approval` creates `Wait(kind = approval)` event drafts in `packages/runtime/src/wait-approval-control.ts`.
2. Operator or API input calls `RuntimeEngine.resolveApproval` (`packages/runtime/src/runtime-engine.ts:890`).
3. `assertApprovedInputRevision` and `assertApprovalAuthorityUnchanged` revalidate revised input and authority in `packages/runtime/src/wait-control.ts`.
4. `RuntimeEngine.continueApprovedAction` re-enters dispatch for the approved action and records a runtime command in `packages/runtime/src/runtime-engine.ts`.
5. The action still passes through schema validation, policy checks, worker execution, and event append; approval does not bypass legality.

### Runtime/API/Timer/Capability/Operator Path

1. Runtime APIs such as delegated completion, wait resolution, timer firing, check recording, reconciliation, authority grant/revoke, and artifact unavailability methods live on `RuntimeEngine` (`packages/runtime/src/runtime-engine.ts`).
2. Each method reads canonical event history, rebuilds views when needed, and calls a focused control module such as `packages/runtime/src/timer-control.ts`, `packages/runtime/src/interaction-control.ts`, `packages/runtime/src/check-control.ts`, or `packages/runtime/src/action-reconciliation-control.ts`.
3. `runtimeCommandEvents` wraps the attempted mutation and result event drafts in a `command.recorded` event (`packages/runtime/src/runtime-engine.ts:1504`).
4. The resulting events append through the same `RuntimeEventLog` and storage path as model-originated commands.

### Delegation Flow

1. A model operation of `create_delegation` enters `recordModelOutput` (`packages/runtime/src/runtime-engine.ts:148`).
2. `createDelegationSpawnEvents` builds parent delegation events and delegated run bootstrap events (`packages/runtime/src/delegation-control.ts`).
3. The runtime appends parent spawn events, appends delegated run bootstrap events at position 0 for the delegated run, then appends the parent established event (`packages/runtime/src/runtime-engine.ts:352`).
4. Delegated terminal handoffs use `recordDelegatedRunCompleted`, `recordDelegatedRunFailed`, and `recordDelegatedRunCancelled` on `RuntimeEngine`; parent completion still requires its own legality.

### Bundle Flow

1. `RuntimeEngine.exportBundle` delegates to bundle export logic (`packages/runtime/src/runtime-engine.ts:517`, `packages/runtime/src/orun.ts`).
2. Bundle export reads event history and artifacts, emits manifest/events/artifacts/views/policy/capability/export files under a bundle path (`packages/runtime/src/orun.ts`).
3. `RuntimeEngine.verifyBundle`, `RuntimeEngine.replayBundle`, `RuntimeEngine.importBundle`, and `RuntimeEngine.assessImportedResume` delegate to `packages/runtime/src/orun.ts`.
4. Bundle replay rebuilds views from transported events; import/resume assessment checks root mappings, capabilities, providers, policy compatibility, wait kinds, and unavailable artifacts.

**State Management:**
- Canonical state is the append-only event log defined by `packages/core/src/events.ts` and stored through `RunEventStore` in `packages/core/src/storage.ts`.
- Derived state lives in rebuildable views from `packages/views/src/index.ts` and must remain disposable.
- Runtime-local assembly state is the object graph returned by `createLocalRuntime` in `packages/runtime/src/local-runtime.ts`.
- Artifact bytes live behind `ArtifactStore` and, for SQLite local runtime, under `runtimeHome/artifacts` managed by `packages/storage-sqlite/src/sqlite-artifact-store.ts`.

## Key Abstractions

**RuntimeEngine:**
- Purpose: Single authoritative boundary for run mutation.
- Examples: `packages/runtime/src/runtime-engine.ts`, tests in `tests/runtime/*.test.ts`
- Pattern: Methods create command records plus event drafts, then append through `RuntimeEventLog`.

**CommandDecision:**
- Purpose: Records whether an attempted mutation is accepted, rejected, deferred, or superseded.
- Examples: `packages/core/src/model.ts`, `packages/runtime/src/legality-evaluator.ts`, `packages/core/src/events.ts`
- Pattern: Use `acceptedDecision`, `rejectedDecision`, `deferredDecision`, or superseded decision helpers before state-changing events.

**RuntimeEvent / NewRuntimeEvent:**
- Purpose: Immutable canonical facts with run, position, type, actor, causation, correlation, command, and compact payload.
- Examples: `packages/core/src/events.ts`, `packages/runtime/src/action-lifecycle.ts`, `packages/runtime/src/bootstrap.ts`
- Pattern: Event draft helpers create `NewRuntimeEvent`; stores assign positions.

**RunEventStore:**
- Purpose: Storage interface for append/read/event-existence semantics.
- Examples: `packages/core/src/storage.ts`, `packages/storage-sqlite/src/sqlite-store.ts`
- Pattern: Append with expected position, reject conflicts, read ordered slices.

**ArtifactStore:**
- Purpose: Store immutable artifact metadata and optional blobs outside compact event payloads.
- Examples: `packages/core/src/storage.ts`, `packages/storage-sqlite/src/sqlite-artifact-store.ts`, `packages/runtime/src/artifact-materialization.ts`
- Pattern: Capability results return inline artifacts or artifact IDs; Engine materializes event references.

**CapabilityDefinition / CapabilityTransport:**
- Purpose: Describe invokable actions and execute them without granting runtime authority.
- Examples: `packages/capabilities/src/definition.ts`, `packages/capabilities/src/dispatcher.ts`, `packages/capability-filesystem/src/definition.ts`
- Pattern: Define schemas, posture, reliability, group eligibility, cancellation, artifacts, and transport metadata.

**CapabilityResult:**
- Purpose: Return worker output, preview, effects, evidence, inline artifacts, artifact IDs, and metadata to the Engine.
- Examples: `packages/capabilities/src/definition.ts`, `packages/capability-filesystem/src/filesystem-capability.ts`
- Pattern: Workers never create event envelopes; they return data for Engine materialization.

**RunViewBundle:**
- Purpose: Group all derived views needed for inspection and some legality facts.
- Examples: `packages/views/src/index.ts`, `packages/views/src/run-status-view.ts`
- Pattern: Always rebuild from complete events at a known position.

**LocalRuntimeAssembly:**
- Purpose: Compose runtime, storage, providers, registry, transports, operator, and reporter.
- Examples: `packages/runtime/src/local-runtime.ts`, `examples/governed-coding-run/run.ts`
- Pattern: Create storage first, create capability definitions and transports, then call `createLocalRuntime`.

**BundleManifest:**
- Purpose: Describe exported run history, artifacts, views, policy, capabilities, integrity, and resume needs.
- Examples: `packages/runtime/src/orun.ts`, `docs/bundles.md`
- Pattern: Treat bundles as transport artifacts for replay/resume, not authoritative mutable state.

## Entry Points

**Public package exports:**
- Location: `packages/core/src/index.ts`, `packages/runtime/src/index.ts`, `packages/capabilities/src/index.ts`, `packages/views/src/index.ts`, `packages/storage/src/index.ts`, package-specific `src/index.ts`
- Triggers: TypeScript imports from workspace packages and consumers.
- Responsibilities: Export stable public APIs and avoid leaking misleading ontology names.

**CLI binary:**
- Location: `packages/cli/src/bin.ts`
- Triggers: Package bin execution.
- Responsibilities: Call `runCliProcess(process.argv.slice(2))`, write stdout/stderr, set exit code.

**CLI command router:**
- Location: `packages/cli/src/index.ts`
- Triggers: `runCli`, `runCliProcess`, and demo calls.
- Responsibilities: Route commands such as `create`, `run`, `inspect`, `waits`, `actions`, `commands`, `runs`, and `orun` to runtime calls and render output.

**Runtime engine:**
- Location: `packages/runtime/src/runtime-engine.ts`
- Triggers: CLI, local assemblies, examples, tests, and library consumers.
- Responsibilities: Bootstrap runs, record model output, resolve waits, dispatch actions, record checks, reconcile actions, manage delegation, replay, and operate bundles.

**Local runtime assembly:**
- Location: `packages/runtime/src/local-runtime.ts`
- Triggers: Examples, tests, and local embedding.
- Responsibilities: Register capability definitions/transports/providers and construct `RuntimeEngine`.

**Storage factory:**
- Location: `packages/storage/src/index.ts`
- Triggers: CLI/demo/local runtime setup.
- Responsibilities: Create SQLite event and artifact stores rooted under `runtimeHome`.

**Governed coding demo:**
- Location: `examples/governed-coding-run/run.ts`
- Triggers: `pnpm demo:governed-coding-run` and tests.
- Responsibilities: Exercise a complete controlled coding run with local capabilities, approvals, checks, unknown outcome reconciliation, CLI rendering, and bundle export.

**Python documents worker:**
- Location: `python/openrund_documents_worker/openrund_documents_worker/server.py`
- Triggers: Stdio JSON-RPC transport from TypeScript documents capability.
- Responsibilities: Serve Markdown document operations through JSON-RPC methods.

**Tests:**
- Location: `tests`
- Triggers: `pnpm test` through Vitest.
- Responsibilities: Verify contracts, runtime flows, storage behavior, public exports, docs links, examples, providers, capabilities, and views.

## Architectural Constraints

- **Threading:** TypeScript code uses the Node async event loop. SQLite event appends use `BEGIN IMMEDIATE` in `packages/storage-sqlite/src/sqlite-store.ts` for local serialization. Python document operations run behind stdio JSON-RPC in `python/openrund_documents_worker/openrund_documents_worker/server.py`.
- **Global state:** Avoid runtime authority in module globals. `RuntimeEngine` holds dependency-injected stores/transports and a private `RuntimeEventLog` in `packages/runtime/src/runtime-engine.ts`. Capability handlers hold mount configuration in class instances such as `FilesystemCapability` in `packages/capability-filesystem/src/filesystem-capability.ts`.
- **Circular imports:** Keep dependency direction from `core` outward: `core` must not import runtime, views, storage, capabilities, CLI, examples, or provider packages. `views` must not import runtime. `capabilities` must not import runtime. `runtime` may import `core`, `views`, and `capabilities`.
- **Authority boundary:** Only `RuntimeEngine` and its delegated control helpers create authoritative command/event drafts. CLI, providers, capabilities, views, and storage must not decide legality.
- **Event position:** Append requires expected position. `SqliteRunEventStore.append` rejects mismatches with `ExpectedPositionConflictError` in `packages/storage-sqlite/src/sqlite-store.ts`.
- **Artifact discipline:** Large content and durable outputs belong in artifacts through `ArtifactStore`; event payloads should remain compact.
- **Terminal state:** Run completion, failure, and cancellation are attempted mutations. Add terminal behavior through `RuntimeEngine` methods and `check-control` contracts, not through direct event appends.
- **Workspace roots:** Filesystem and process-like capabilities operate through mounted roots and path-sandbox helpers in `packages/capability-filesystem/src/path-sandbox.ts` and related capability packages.

## Anti-Patterns

### Appending Events Outside The Engine

**What happens:** A CLI command, capability worker, provider adapter, or view directly writes `run.completed`, `action.completed`, `wait.resolved`, or another lifecycle event to a `RunEventStore`.
**Why it's wrong:** It bypasses CommandDecision, legality, policy, wait, authority, and contract checks.
**Do this instead:** Add or call a `RuntimeEngine` method in `packages/runtime/src/runtime-engine.ts` and emit event drafts through focused control helpers such as `packages/runtime/src/check-control.ts` or `packages/runtime/src/wait-control.ts`.

### Treating Model Output As Truth

**What happens:** A provider adapter or caller treats a parsed operation as accepted runtime state.
**Why it's wrong:** Provider output is a proposal. Acceptance is an Engine decision recorded on `command.recorded`.
**Do this instead:** Pass `ModelCall` values into `RuntimeEngine.recordModelOutput` in `packages/runtime/src/runtime-engine.ts:148` and inspect command decisions through views/CLI.

### Letting Views Decide Legality

**What happens:** Code adds a view reducer that decides whether a mutation is legal and appends events based on that view.
**Why it's wrong:** Views are derived, rebuildable read models. They can supply facts but not authority.
**Do this instead:** Use views as inputs inside `RuntimeEngine` legality/control paths, then record the decision through `runtimeCommandEvents` in `packages/runtime/src/runtime-engine.ts:1504`.

### Returning Event Drafts From Workers

**What happens:** A capability handler returns event envelopes or tries to grant authority, resolve waits, or complete runs.
**Why it's wrong:** Workers do domain work; the Engine owns runtime authority and lifecycle materialization.
**Do this instead:** Return `CapabilityResult` data from handlers in `packages/capability-*/src`, then let `ActionDispatcher` and `materializeActionResult` in `packages/runtime/src` produce action/artifact events.

### Adding Root Ontology Casually

**What happens:** Public APIs introduce root names like `State`, `Facts`, `Control`, `Projection`, or `Blocker` for canonical runtime semantics.
**Why it's wrong:** `docs/concepts.md` reserves root ontology and suffix conventions; misleading names create accidental authority surfaces.
**Do this instead:** Use approved secondary suffixes such as `View`, `Report`, `Receipt`, `Summary`, `Assessment`, `Manifest`, `Snapshot`, `Index`, `Entry`, or `Issue`, and place derived state under `packages/views/src`.

## Error Handling

**Strategy:** Convert validation, policy, capability, storage, and runtime conflicts into rejected/deferred command decisions or failed/unknown action lifecycle events. Throw only for programmer errors, storage conflicts, or caller-visible operation failures where no runtime command should be silently invented.

**Patterns:**
- Use `capabilityError` from `packages/capabilities/src/errors.ts` for capability registration, schema, unsupported transport, worker failure, cancelled, conflict, and unknown outcome categories.
- Use rejected command decisions for invalid model operations in `RuntimeEngine.recordModelOutput` (`packages/runtime/src/runtime-engine.ts:148`).
- Use deferred command decisions plus `Wait` events for approvals and other wait states.
- Use `action.failed`, `action.cancelled`, or `action.unknown` event drafts from `packages/runtime/src/action-lifecycle.ts` for worker execution outcomes.
- Use `ExpectedPositionConflictError` and `DuplicateEventIDError` from `packages/storage-sqlite/src/sqlite-store.ts` for local persistence conflicts.
- Use JSON-RPC errors in `python/openrund_documents_worker/openrund_documents_worker/server.py` to map document conflicts and missing files into structured worker errors.

## Cross-Cutting Concerns

**Logging:** Runtime progress is represented as events and progress entries, not ad hoc logs. Use `packages/runtime/src/runtime-progress-entries.ts` for event-derived progress reporting. The Python documents worker prints readiness to stderr in `python/openrund_documents_worker/openrund_documents_worker/server.py`.

**Validation:** Validate model operations in `packages/runtime/src/model-operation-validator.ts`, capability definitions in `packages/capabilities/src/registry.ts`, capability schemas in `packages/capabilities/src/schema.ts`, workspace/path scope in capability-specific path helpers, approval input revisions in `packages/runtime/src/wait-control.ts`, and completion legality in `packages/runtime/src/check-control.ts`.

**Authentication:** Not detected as an application auth layer. Runtime authority is modeled through `AuthorityGrant`, policy rules, capability metadata, workspace roots, delegation contracts, and command decisions in `packages/core/src/run.ts`, `packages/core/src/model.ts`, and `packages/runtime/src`.

**Authorization:** Use `AuthorityGrant` plus policy rules, capability posture/reliability, and workspace/resource checks. Do not treat capability registration as authorization.

**Persistence:** Use `RunEventStore`, `ArtifactStore`, and `ExecutionLeaseStore` interfaces in `packages/core/src/storage.ts`. The default local implementation is SQLite in `packages/storage-sqlite/src`.

**Replayability:** Keep views deterministic, use append-only events, and use bundle export/replay code in `packages/runtime/src/orun.ts` to transport run history and artifacts.

---

*Architecture analysis: 2026-05-15*
