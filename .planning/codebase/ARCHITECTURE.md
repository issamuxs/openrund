# Architecture

**Analysis Date:** 2026-08-06

## Pattern Overview

**Overall:** Event-sourced Python runtime with hexagonal ports, deterministic replay, and a single command authority.

**Key Characteristics:**

- `openrund.engine.RuntimeEngine` is the only supported lifecycle mutation boundary.
- Durable state is an append-only per-run Event stream; Views are deterministic, non-authoritative projections.
- Model providers and Capabilities produce proposals or outcomes, but all lifecycle changes re-enter the Engine as Commands.
- Protocols in `src/openrund/ports/` separate core semantics from SQLite, HTTP, subprocess, and local filesystem adapters.
- The default assembly is a single-process local runtime backed by SQLite and immutable Artifact references.
- The installed product is a library plus the `openrund` CLI; there is no server or UI layer.

## System Overview

```text
CLI / Python host
        |
        v
OperatorService / DurableRunLoop / ActionRunner
        |                 |              |
        |            ModelProvider   CapabilityRegistry -> transport/worker
        |                 |              |
        +-----------------+--------------+
                          |
                       Command
                          v
                    RuntimeEngine
             read -> replay -> evaluate
                          |
                 atomic Event append
                    /             \
                   v               v
          SQLite Event store   Artifact store
                   |
                   v
          deterministic Views -> inspection / Bundles
```

The authoritative direction is inward toward `RuntimeEngine.submit()` in
`src/openrund/engine/_engine.py`. Outbound adapters may perform work, but they cannot
directly manufacture accepted lifecycle state.

## Layers

**Contract Kernel:**

- Purpose: Define immutable domain values, Commands, Events, run state, Content, IDs, and portable Bundle types.
- Location: `src/openrund/contracts/`, with shared errors in `src/openrund/errors.py` and path values in `src/openrund/paths.py`.
- Depends on: Python standard library and other contract modules only.
- Used by: Every runtime layer.
- Boundary rule: Constructors validate eagerly; missing, null, and concrete values remain distinct through `MISSING` in `src/openrund/contracts/json.py`.

**Wire Codec:**

- Purpose: Encode and decode canonical JSON, Event envelopes, decision records, and Content hashes.
- Location: `src/openrund/codec/`.
- Depends on: Contract values and errors.
- Used by: Storage, Bundles, providers, Capability transports, and compatibility tests.
- Boundary rule: `src/openrund/codec/_events.py` is the serialized Event input boundary and rejects unsupported or ambiguous wire forms.

**Deterministic Views:**

- Purpose: Validate a complete known-watermark history and reduce it into run status, waits, actions, artifacts, delegation, reports, checkpoints, and timeline facts.
- Location: `src/openrund/views/`.
- Depends on: Contracts only.
- Used by: Engine legality, operator inspection, Bundle export/verification, and callers of the public replay API.
- Boundary rule: `src/openrund/views/_history.py` fails closed with `IncompleteViewReplay`; reducers only receive `KnownHistory`.

**Authority Engine:**

- Purpose: Replay the complete stream, evaluate Command legality and governance, materialize Events, and append them atomically.
- Location: `src/openrund/engine/`.
- Depends on: Contracts, codecs, Event-store ports, and complete View facts.
- Used by: Run loop, Action runner, Operator service, host applications, and local assembly.
- Boundary rule: Accepted Commands append `command.recorded` plus target Events; rejected and superseded Commands record decisions without target lifecycle Events; deferred Commands create or reference durable Waits.

**Coordination Runtime:**

- Purpose: Coordinate external work while preserving durable lifecycle ordering.
- Location: `src/openrund/runtime/_loop.py` for model calls and `src/openrund/capabilities/_runner.py` for actions.
- Depends on: Engine, contracts, provider/Artifact ports, and Capability registry.
- Used by: Local assembly and host applications.
- Boundary rule: The durable start is accepted before dispatch; completion, failure, cancellation, or unknown outcome is submitted back through the Engine.

**Ports:**

- Purpose: Define structural protocols and transport-neutral records for Events, Artifacts, leases, providers, Capabilities, clocks, IDs, and reporting.
- Location: `src/openrund/ports/`.
- Depends on: Contracts and errors.
- Used by: Engine and coordinators as dependency interfaces; adapters implement them.
- Boundary rule: Ports grant no authority by themselves.

**Adapters:**

- Purpose: Implement persistence, providers, Capability execution, and portable Bundle I/O.
- Location: `src/openrund/storage/`, `src/openrund/providers/`, `src/openrund/capabilities/`, and `src/openrund/bundles/`.
- Depends on: Ports, contracts, codecs, and selected View surfaces.
- Used by: Assembly, CLI, and external Python hosts.
- Boundary rule: Filesystem, process, Git, HTTP, SQLite, and Bundle inputs are validated at their trust boundary.

**Application and Composition:**

- Purpose: Compose concrete local adapters, expose operator workflows, route CLI commands, and prove the complete offline lifecycle.
- Location: `src/openrund/assembly/`, `src/openrund/operator/`, `src/openrund/cli.py`, and `src/openrund/demo.py`.
- Depends on: All lower layers.
- Used by: `src/openrund/__main__.py`, the `openrund` console script, examples, and library clients.
- Boundary rule: Assembly configures authority; it does not infer or synthesize grants.

## Dependency Direction

The intended dependency direction is:

```text
contracts <- codec/views/ports <- engine <- runtime coordinators
                                  ^              |
                                  |              v
                         concrete adapters <- assembly/operator/CLI
```

Most packages follow this direction. Two current seams are tighter than the public
package boundaries suggest:

- Engine modules import private View implementation types from
  `src/openrund/views/_model.py`, `src/openrund/views/_run_status.py`,
  `src/openrund/views/_waits.py`, and `src/openrund/views/_delegation.py`.
- `src/openrund/operator/_service.py` imports private View models directly rather than
  using only `src/openrund/views/__init__.py`.

These imports do not violate the runtime authority rule, but they make private View file
layout part of Engine and Operator maintenance.

## Data Flow

**Command Submission:**

1. A host creates a typed `Command`, or a model `ModelProposal` is converted by `src/openrund/engine/_proposals.py`.
2. `RuntimeEngine.submit()` in `src/openrund/engine/_engine.py` reads the full run stream from the `EventStore` port.
3. `rebuild_views()` in `src/openrund/views/_rebuild.py` proves complete history at the current watermark and builds all View facts.
4. The Engine detects an existing command ID or idempotency-key owner before evaluating new work.
5. `evaluate_command()` in `src/openrund/engine/_legality.py` checks lifecycle, origin, governance, waits, completion readiness, delegation, and evidence requirements.
6. Event intents are materialized by `src/openrund/engine/_events.py`; the command decision is encoded by `src/openrund/engine/_records.py`.
7. The Engine atomically appends the `command.recorded` Event and any accepted target Events at the expected position.
8. An expected-position conflict causes a bounded reread/replay/evaluate retry; the Engine never appends against stale state.
9. Callers receive a typed `CommandResult`; subsequent reads reconstruct state from the committed Events.

**Durable Model Call:**

1. `DurableRunLoop.step()` in `src/openrund/runtime/_loop.py` submits `StartModelCallOperation` through the Engine.
2. Only after the start is accepted does the configured `ModelProvider` receive a `ModelRequest`.
3. `src/openrund/providers/openai.py` or `src/openrund/providers/anthropic.py` performs HTTP and normalizes untrusted responses through `src/openrund/providers/_normalization.py`.
4. The loop records completion or classified failure through the Engine.
5. The inert proposal is submitted as a separate model-origin Command; the provider never mutates state directly.

**Durable Capability Action:**

1. A previously accepted action request is represented by a `CapabilityInvocation`.
2. `ActionRunner.execute()` in `src/openrund/capabilities/_runner.py` resolves the registered action and validates its input schema.
3. The runner durably records `action.started` through the Engine.
4. An in-process or strict stdio JSON-RPC transport in `src/openrund/capabilities/_transports.py` performs the external work.
5. Inline Artifact bytes are hashed and stored before their immutable references are included in a terminal Command.
6. The Engine records completed, failed, cancelled, or outcome-unknown state. Unknown outcomes require explicit reconciliation rather than implicit retry.

**Inspection and Bundle Flow:**

1. `OperatorService` in `src/openrund/operator/_service.py` reads canonical Events and rebuilds complete Views.
2. Read-only operations render status, readiness, waits, receipts, checks, Artifacts, and command explanations.
3. `src/openrund/bundles/_export.py` stages a `.orun` directory, writes canonical Events and derived evidence, fsyncs it, and publishes by rename.
4. `src/openrund/bundles/_verify.py` rejects symlinks, special files, oversized inputs, unexpected tree entries, commitment mismatches, and semantic replay mismatches.
5. Import and resume assessment remain separate from verification in `src/openrund/bundles/_importing.py` and `src/openrund/bundles/_resume.py`.

**State Management:**

- Authoritative state: Ordered Events in SQLite `run_events`, one position sequence per Run.
- Derived state: Immutable View bundles rebuilt from complete Event history; no persistent View cache is authoritative.
- Artifact custody: Metadata in SQLite `artifacts`, bytes under the configured Artifact root, references in Events and Content.
- Concurrency: Expected stream positions plus `BEGIN IMMEDIATE` SQLite transactions; multi-run delegation uses atomic append batches.
- Coordination: SQLite execution leases are advisory coordination records, not lifecycle authority.
- Local layout: Runtime database and Artifact storage live under the configured runtime home; per-run custody paths are built by `src/openrund/storage/_layout.py`.

## Key Abstractions

**Command / Operation / CommandDecision:**

- Purpose: Represent every requested mutation and its durable legality result.
- Examples: `Command`, `CreateActionOperation`, `DeferredCommandDecision` in `src/openrund/contracts/commands.py`.
- Pattern: Validated immutable dataclasses and discriminated unions.

**RuntimeEvent:**

- Purpose: Represent the ordered evidence from which all run state is reconstructed.
- Examples: Event and payload types in `src/openrund/contracts/events.py`.
- Pattern: Append-only event sourcing with explicit causation and command identity.

**CompleteViewReplay / RunViewBundle:**

- Purpose: Prove the Event sequence is complete at an exact watermark before exposing derived facts.
- Examples: `src/openrund/views/_model.py` and the aggregator in `src/openrund/views/_rebuild.py`.
- Pattern: Fail-closed deterministic projection.

**RuntimeEngine:**

- Purpose: Own the replay/evaluate/append transaction and all core lifecycle authority.
- Example: `src/openrund/engine/_engine.py`.
- Pattern: Application service with injected ports and optimistic concurrency.

**Port Protocols:**

- Purpose: Invert dependencies for storage, providers, Capabilities, clocks, IDs, and reporting.
- Examples: `EventStore` in `src/openrund/ports/events.py`, `ArtifactStore` in `src/openrund/ports/artifacts.py`, and `ModelProvider` in `src/openrund/ports/providers.py`.
- Pattern: Python structural `Protocol` interfaces.

**Capability / RegisteredCapability / CapabilityRoute:**

- Purpose: Separate declared actions and schemas from concrete execution transports.
- Examples: `src/openrund/contracts/capabilities.py` and `src/openrund/capabilities/_registry.py`.
- Pattern: Registry with validated bindings and explicit transport kinds.

**Content / ArtifactReference:**

- Purpose: Carry compact previews and structured data while keeping large outputs in immutable Artifact custody.
- Example: `src/openrund/contracts/content.py`.
- Pattern: Value object with optional inline metadata and stable Artifact IDs.

**LocalRuntime:**

- Purpose: Own the lifetime of one explicit local dependency graph.
- Examples: `LocalAssemblyConfig` and `LocalRuntime` in `src/openrund/assembly/_model.py`, constructed by `src/openrund/assembly/_factory.py`.
- Pattern: Composition root plus async context manager.

## Entry Points

**Installed CLI:**

- Location: `src/openrund/__main__.py` and the `openrund = openrund.__main__:main` script in `pyproject.toml`.
- Triggers: `openrund ...` or `python -m openrund`.
- Responsibilities: Start the async CLI process and return a stable exit code.

**CLI Router:**

- Location: `src/openrund/cli.py`.
- Triggers: Parsed command-line arguments.
- Responsibilities: Parse global options, construct the local runtime, route operator commands, sanitize failures, and render text or JSON.

**Python Library:**

- Location: Public facade in `src/openrund/__init__.py` and narrower package facades such as `src/openrund/engine/__init__.py`.
- Triggers: Host imports.
- Responsibilities: Expose the supported typed API while private modules retain implementation details.

**Capability Worker:**

- Location: `src/openrund/capabilities/documents_worker.py`.
- Triggers: The stdio transport registered by `DocumentsCapability` in `src/openrund/capabilities/documents.py`.
- Responsibilities: Decode one JSON-RPC invocation, perform the bounded document operation, and emit one strict response.

**Offline Demonstration:**

- Location: `run_governed_coding_demo()` in `src/openrund/demo.py`, wrapped by `examples/governed_coding.py` and routed by `src/openrund/cli.py`.
- Triggers: `openrund demo governed-coding` or the example script.
- Responsibilities: Exercise production assembly, governance, delegation, Capabilities, unknown-outcome reconciliation, checks, and completion without network access.

## Error Handling

**Strategy:** Typed, code-bearing exceptions fail closed inside the runtime; the CLI converts them to stable sanitized operator results at the outer boundary.

**Patterns:**

- `src/openrund/errors.py` defines the error taxonomy; callers key on codes rather than exception text.
- Contract constructors raise `ValidationError` before invalid values enter core logic.
- Provider and Capability adapters separate transport, protocol, response, and execution failures.
- SQLite exceptions are translated in `src/openrund/storage/_database.py`; transactions roll back before translated errors escape.
- Replay integrity defects produce `IncompleteViewReplay` or `StorageIntegrityError`, never a partial authoritative View.
- Capability ambiguity after dispatch becomes an explicit unknown action outcome.
- CLI exception handling in `src/openrund/cli.py` returns usage, integrity, unavailable, or internal exit classes without exposing unsafe details.
- Post-commit subscriber failures in `src/openrund/storage/_event_log.py` are advisory and isolated after durable append.

## Cross-Cutting Concerns

**Validation:**

- Immutable dataclass constructors validate domain invariants.
- Canonical codecs reject duplicate keys, non-finite numbers, unsafe integer forms, unknown fields, and unsupported Event versions.
- Provider and Capability schemas are checked before untrusted data becomes a proposal or result.

**Authority and Security:**

- There is no authentication subsystem because OpenRund is a local embedded runtime, not a network service.
- Authorization is durable runtime governance: authority grants, policy rules, Capability declarations, workspace roots, and Command-origin checks.
- `src/openrund/capabilities/_sandbox.py` validates named mounts and containment; built-ins do not accept ambient unrestricted paths.
- Bundle and run-home code rejects symlink redirection and unexpected filesystem objects.
- Provider credentials are explicit constructor inputs and are not stored in runtime Events.

**Determinism and Compatibility:**

- Canonical JSON and exact JSONL framing are implemented in `src/openrund/codec/`.
- Compatibility behavior is frozen by `tests/fixtures/compatibility/v1/manifest.json` and the evidence corpus under `tests/fixtures/compatibility/v1/evidence/`.
- View reducers are pure over validated history; Bundle commitments cover canonical bytes and semantic evidence.

**Observability:**

- Events are the audit log; Views, command explanations, action receipts, reports, and Bundles are derived inspection surfaces.
- Reporting is injected through `Reporter` and wrapped by `src/openrund/assembly/_events.py`; the core has no ambient logger singleton.

**Resource Lifetime:**

- Providers, runtime loops, SQLite stores, and `LocalRuntime` support explicit async closure.
- The run loop tracks active tasks and shields durable terminal recording from cancellation.

## Structural Friction and Safe Simplifications

The following are evidence-backed structural opportunities, not permission to remove
runtime behavior:

1. **Publish the Engine-facing replay facts instead of importing private View modules.**
   `src/openrund/engine/_engine.py`, `src/openrund/engine/_legality.py`,
   `src/openrund/engine/_coordination.py`, `src/openrund/engine/_delegation.py`,
   `src/openrund/engine/_events.py`, and `src/openrund/engine/_governance.py` import
   `openrund.views._*`. A low-risk first step is to export the required immutable types
   through `src/openrund/views/__init__.py` and switch these imports to that public seam.
   Keep replay semantics and all Engine/View compatibility tests unchanged.

2. **Remove Operator dependence on View file layout.**
   `src/openrund/operator/_service.py` imports `ActionReceipt`, `ArtifactIndexEntry`,
   `RunViewBundle`, `ReadinessBlocker`, and related types from private modules. Exporting
   the supported inspection types from `src/openrund/views/__init__.py` would make the
   dependency explicit without adding a new layer or changing data flow.

3. **Move provider-neutral HTTP helpers out of the OpenAI adapter.**
   `src/openrund/providers/anthropic.py` imports `_content_context`, `_decode_object`,
   `_text`, and `_wire` from `src/openrund/providers/openai.py`. These helpers serve both
   adapters and can move to `src/openrund/providers/_normalization.py` or a focused
   private wire module. This removes concrete-adapter-to-concrete-adapter coupling while
   preserving public APIs and provider behavior.

4. **Clarify the two assembly factory module names.**
   `src/openrund/assembly/_factory.py` composes the runtime graph, while
   `src/openrund/assembly/_factories.py` contains clocks and ID factories. Renaming the
   latter to an intent-revealing private name such as `_ids.py` would reduce navigation
   ambiguity. Re-export names from `src/openrund/assembly/__init__.py` to avoid a public
   API change.

5. **Do not centralize all repeated validators.**
   Small `_text`, `_required_text`, and `_optional_text` helpers appear in contracts,
   codecs, storage, providers, Capabilities, and Bundles. They look duplicated, but most
   encode boundary-specific error codes and accepted value shapes. A shared catch-all
   utility would add coupling and erase error precision; consolidate only helpers with
   identical trust boundaries, such as the provider-neutral functions above.

6. **Keep similarly named path modules separate.**
   `src/openrund/paths.py`, `src/openrund/capabilities/_sandbox.py`,
   `src/openrund/storage/_layout.py`, and `src/openrund/bundles/_paths.py` are not duplicate
   path utilities: they respectively model lexical values, enforce Capability mounts,
   materialize run custody, and validate hostile Bundle trees. Combining them would blur
   trust boundaries.

## Architectural Constraints

- Preserve `RuntimeEngine` as the only supported core mutation authority.
- Keep Event payloads compact and Artifact bytes out of lifecycle Events.
- Never treat a partial or unknown-watermark history as authoritative.
- Preserve accepted/rejected/deferred/superseded decision evidence and idempotent retries.
- Keep provider output and Capability output inert until the Engine accepts a Command.
- Maintain stdlib-only runtime dependencies declared in `pyproject.toml`.
- Treat `docs/architecture.md`, `docs/concepts.md`, `docs/events.md`,
  `docs/capabilities.md`, `docs/providers.md`, `docs/storage.md`,
  `docs/delegation.md`, and `docs/bundles.md` as normative contracts.
- Changes to codecs, Event schemas, Views, SQLite layout, provider normalization, or
  Bundle bytes must remain compatible with `tests/fixtures/compatibility/v1/`.

---

*Architecture analysis: 2026-08-06*
*Update when major patterns change*
