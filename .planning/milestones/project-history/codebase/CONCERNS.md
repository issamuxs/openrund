# Codebase Concerns

**Analysis Date:** 2026-05-15

## Tech Debt

**Runtime engine owns many unrelated workflows:**
- Issue: `packages/runtime/src/runtime-engine.ts` is the central authority boundary and also owns bootstrap append, model output normalization, policy checks, action dispatch, delegation, waits, checkpoints, completion gates, bundle helpers, and reconciliation entry points.
- Files: `packages/runtime/src/runtime-engine.ts`, `packages/runtime/src/action-dispatcher.ts`, `packages/runtime/src/delegation-control.ts`, `packages/runtime/src/checkpoint-control.ts`, `packages/runtime/src/wait-control.ts`
- Impact: Changes to any runtime workflow can regress unrelated legality paths because `RuntimeEngine.recordModelOutput` branches across most operation kinds and appends events from several control modules.
- Fix approach: Keep `RuntimeEngine` as the only authority facade, but move each operation branch behind narrow command handlers with a shared append contract and focused tests per handler.

**Bundle transport logic is large and multi-purpose:**
- Issue: `packages/runtime/src/orun.ts` combines export, verification, replay, import, resume assessment, integrity hashing, audit rendering, manifest validation, and file traversal.
- Files: `packages/runtime/src/orun.ts`, `tests/runtime/orun-bundle.test.ts`, `tests/runtime/orun-replay-resume.test.ts`
- Impact: Bundle integrity and resume compatibility are security-sensitive, but unrelated edits in the same file can affect validation, rendering, or import behavior.
- Fix approach: Split by responsibility: `bundle-export`, `bundle-verify`, `bundle-import`, `bundle-manifest`, and `bundle-audit`, while keeping the public exports in `packages/runtime/src/orun.ts`.

**CLI command surface is monolithic:**
- Issue: `packages/cli/src/index.ts` contains argument parsing, runtime construction, command dispatch, render formatting, bundle commands, wait/check commands, and command-specific behavior in one file.
- Files: `packages/cli/src/index.ts`, `tests/runtime/cli-phase5.test.ts`, `tests/runtime/cli-smoke.test.ts`
- Impact: CLI additions require editing a large file and can accidentally change shared formatting or parsing paths.
- Fix approach: Keep `runCli` as the public entry point, but move command handlers and render helpers into command-specific modules under `packages/cli/src/commands/`.

**Committed build artifacts in a source directory:**
- Issue: `packages/storage-sqlite/src` contains generated `.js`, `.d.ts`, and source map files alongside TypeScript sources, while `packages/storage-sqlite/tsconfig.json` emits to `packages/storage-sqlite/dist`.
- Files: `packages/storage-sqlite/src/index.js`, `packages/storage-sqlite/src/index.d.ts`, `packages/storage-sqlite/src/migrations.js`, `packages/storage-sqlite/src/sqlite-store.js`, `packages/storage-sqlite/src/sqlite-artifact-store.js`, `packages/storage-sqlite/src/sqlite-lease-store.js`, `packages/storage-sqlite/tsconfig.json`
- Impact: Source and generated outputs can drift. Test aliases point at `src/index.ts` through `vitest.config.ts`, but consumers use `dist` from package exports, so stale `src/*.js` files create confusing review and packaging risk.
- Fix approach: Remove generated files from `packages/storage-sqlite/src`, ensure `dist/` is the only emit location, and add a hygiene check that rejects `packages/*/src/**/*.js`, `*.d.ts`, and source maps.

**Provider adapters share duplicated normalization logic:**
- Issue: OpenAI, Anthropic, and local OpenAI-compatible adapters independently parse provider tool calls, split qualified names, default invalid argument payloads, and convert text responses to model operations.
- Files: `packages/provider-openai/src/openai-adapter.ts`, `packages/provider-anthropic/src/anthropic-adapter.ts`, `packages/provider-local/src/local-openai-compatible-adapter.ts`, `tests/providers/openai.test.ts`, `tests/providers/anthropic.test.ts`, `tests/providers/local-openai-compatible.test.ts`
- Impact: Provider behavior can diverge, especially around operation batches, malformed tool arguments, fallback action IDs, and text-only messages.
- Fix approach: Introduce a provider-neutral normalization helper in `packages/providers` or `packages/core` and keep provider-specific adapters limited to HTTP shape and schema overlays.

## Known Bugs

**Policy rules use the same event type as capability grants:**
- Symptoms: Initial `policyRules` are emitted as `authority.granted` events with `ruleID` and `rule` payloads. This is currently supported by `packages/views/src/run-status-view.ts`, but it overloads the authority event shape and tests duplicate the same event-type condition.
- Files: `packages/runtime/src/bootstrap.ts`, `packages/core/src/events.ts`, `packages/views/src/run-status-view.ts`, `tests/core/bootstrap.test.ts`, `docs/events.md`
- Trigger: Bootstrap a run with both `capabilityGrants` and `policyRules` via `createBootstrapEvents`.
- Workaround: Consumers must inspect `payload.capabilityID` vs `payload.ruleID` on `authority.granted`.

**Subscriber failure can make a persisted append look failed:**
- Symptoms: `RuntimeEventLog.append` persists events first, then awaits subscribers. If a reporter/subscriber throws, the append call rejects even though the store already committed the events.
- Files: `packages/runtime/src/event-log.ts`, `packages/runtime/src/local-runtime.ts`, `tests/runtime/event-streaming.test.ts`
- Trigger: Configure `onEventsAppended` or `eventSubscribers` with a throwing async subscriber and append events.
- Workaround: Subscriber implementations must catch their own errors or risk caller retry against an already-advanced expected position.

**Artifact blob writes are not atomic with metadata writes:**
- Symptoms: `SqliteArtifactStore.put` writes artifact bytes before inserting/updating the artifact row. A crash or process kill between the filesystem write and SQLite write can leave orphan blobs; a crash after metadata write during future changes could leave missing blob references.
- Files: `packages/storage-sqlite/src/sqlite-artifact-store.ts`, `tests/storage/sqlite-artifact.test.ts`
- Trigger: Store an artifact with a blob while the process fails between `writeFileSync` and the SQLite `INSERT ... ON CONFLICT`.
- Workaround: Export and verification paths treat unavailable artifacts explicitly, but local artifact storage has no cleanup or transaction spanning filesystem and SQLite.

**Process and git capabilities can hang on large outputs:**
- Symptoms: Child process stdout/stderr are accumulated fully in memory before artifact materialization. `previewLimit` truncates previews only after all output is buffered.
- Files: `packages/capability-process/src/process-capability.ts`, `packages/capability-git/src/git-capability.ts`, `tests/capabilities/process.test.ts`, `tests/capabilities/git.test.ts`
- Trigger: Run `process.run`, `git.diff`, or other git operations that produce very large stdout/stderr.
- Workaround: Keep process commands and git diffs small; use timeouts for process execution.

## Security Considerations

**Stdio JSON-RPC transport inherits the full parent environment:**
- Risk: Spawned worker processes receive all `process.env` values by default, then overlay `options.env`.
- Files: `packages/capabilities/src/transports/stdio-json-rpc.ts`, `packages/capability-documents/src/documents-client.ts`, `tests/capabilities/documents-stdio.test.ts`
- Current mitigation: The transport is explicit and local; process capability has a separate allowlist in `packages/capability-process/src/process-capability.ts`.
- Recommendations: Default to a minimal environment for stdio workers, pass only required variables, and add tests that sensitive parent environment variables are not inherited.

**Provider HTTP errors may expose remote response bodies:**
- Risk: Provider adapters include up to 500 characters of failed response body in thrown errors. API providers usually avoid echoing secrets, but proxy/local-compatible providers can return sensitive request details.
- Files: `packages/provider-openai/src/openai-adapter.ts`, `packages/provider-anthropic/src/anthropic-adapter.ts`, `packages/provider-local/src/local-openai-compatible-adapter.ts`
- Current mitigation: Error body detail is truncated.
- Recommendations: Redact authorization-looking values and make response-body inclusion opt-in for debug mode.

**Bundle manifest paths are joined without an explicit path-boundary check:**
- Risk: `verifyBundle` reads paths from `manifest.exports.*`, `manifest.exports.actionReceiptPaths`, and `manifest.integrity.files` by joining them with `bundlePath`. The integrity hash protects honest exports, but malicious manifests should still be rejected for absolute paths or `..` segments before filesystem access.
- Files: `packages/runtime/src/orun.ts`, `tests/runtime/orun-bundle.test.ts`
- Current mitigation: Verification recomputes file hashes and bundle commitments, and exported manifests are generated by runtime code.
- Recommendations: Validate every manifest path as a normalized relative bundle path before `stat` or `readFile`, and add traversal tests.

**Filesystem mutation sandbox has symlink protection but no posture enforcement:**
- Risk: `FilesystemMount` includes `posture?: "read" | "read_write"`, but `FilesystemCapability.write`, `update`, `delete`, and `move` do not check mount posture before mutating.
- Files: `packages/capability-filesystem/src/path-sandbox.ts`, `packages/capability-filesystem/src/filesystem-capability.ts`, `tests/capabilities/filesystem.test.ts`
- Current mitigation: Runtime policy and authority grants can require approval or deny actions; symlink parents are rejected for mutation.
- Recommendations: Enforce mount posture inside the capability so a read-only mount is denied even if runtime policy is misconfigured.

## Performance Bottlenecks

**View rebuilding rereads complete event streams:**
- Problem: Several runtime operations call `eventLog.readAll` and `rebuildViews` before making a decision.
- Files: `packages/runtime/src/runtime-engine.ts`, `packages/views/src/index.ts`, `packages/views/src/run-status-view.ts`, `packages/storage-sqlite/src/sqlite-store.ts`
- Cause: Current stores expose append/read semantics, and the engine reconstructs current state from full event history.
- Improvement path: Add persisted snapshots or incremental view state for long runs while preserving replay as the source of truth.

**SQLite event reads scan full run history for every replay:**
- Problem: `SqliteRunEventStore.read` returns all events from a position and `RuntimeEventLog.readAll` calls it without a `fromPosition` argument.
- Files: `packages/storage-sqlite/src/sqlite-store.ts`, `packages/runtime/src/event-log.ts`, `packages/runtime/src/runtime-engine.ts`
- Cause: The current MVP favors simple append-only storage over cached projections.
- Improvement path: Add run status snapshots and targeted queries for common checks, keeping full replay verification available.

**Bundle hashing walks and reads the whole bundle directory:**
- Problem: Import computes `hashBundleDirectory` by recursively listing and reading all bundle files after verification already hashes manifest-declared files.
- Files: `packages/runtime/src/orun.ts`, `tests/runtime/orun-replay-resume.test.ts`
- Cause: Import records use a whole-directory hash for provenance.
- Improvement path: Reuse verified manifest integrity where possible, and reserve whole-directory hashing for debug or strict provenance modes.

## Fragile Areas

**Action lifecycle and approval replay:**
- Files: `packages/runtime/src/action-dispatcher.ts`, `packages/runtime/src/wait-control.ts`, `packages/runtime/src/wait-approval-control.ts`, `packages/runtime/src/runtime-engine.ts`, `tests/runtime/wait-approval.test.ts`, `tests/runtime/wait-approval-revision.test.ts`, `tests/runtime/action-dispatcher.test.ts`
- Why fragile: Approval waits depend on matching action IDs, original input snapshots, authority snapshots, policy snapshots, and optional approved input revisions.
- Safe modification: Change one lifecycle transition at a time and verify action, wait approval, revision, and reconciliation tests together.
- Test coverage: Good unit coverage exists, but no property tests exercise arbitrary interleavings of approval, cancellation, retry, and unknown outcomes.

**Delegation lifecycle and parent/child consistency:**
- Files: `packages/runtime/src/delegation-control.ts`, `packages/runtime/src/runtime-engine.ts`, `tests/runtime/delegation-spawn.test.ts`, `tests/runtime/delegation-joins.test.ts`, `tests/runtime/delegation-cancellation.test.ts`
- Why fragile: Creating a delegation appends to the parent, bootstraps the child run, then appends the parent establishment event. A failure between these appends leaves partially materialized delegation state.
- Safe modification: Treat multi-run append sequences as recoverable workflows; add idempotent repair or reconciliation before broadening delegation features.
- Test coverage: Lifecycle tests cover common paths, but injected append failure tests for partial parent/child writes are missing.

**Capability policy and resource scope validation:**
- Files: `packages/runtime/src/capability-policy.ts`, `packages/runtime/src/runtime-engine.ts`, `packages/capabilities/src/registry.ts`, `tests/runtime/action-dispatcher.test.ts`, `tests/runtime/model-operation-validator.test.ts`
- Why fragile: Policy allowance depends on registered metadata, authority grants, policy rule shape, resource scope checks, and action schema validation happening in the correct order.
- Safe modification: Preserve the sequence: validate model operation, check resource scope, evaluate policy, record command decision, then dispatch or create wait.
- Test coverage: Unit tests cover representative policy cases, but rule combinations and malformed rule configs need table-driven coverage.

**Filesystem capability has duplicate implementations:**
- Files: `packages/capabilities/src/builtins/filesystem.ts`, `packages/capability-filesystem/src/filesystem-capability.ts`, `tests/capabilities/filesystem.test.ts`
- Why fragile: Built-in and package-level filesystem capabilities implement similar read/write/delete/move/diff logic and can diverge in sandbox behavior, effect metadata, and bug fixes.
- Safe modification: Keep one implementation authoritative and make the other re-export or wrap it.
- Test coverage: Tests primarily target `@openrund/capability-filesystem`; duplicate built-in code requires explicit parity tests or removal.

## Scaling Limits

**Single-process SQLite is the persistence baseline:**
- Current capacity: SQLite WAL with `busy_timeout` and per-run expected-position checks supports local MVP concurrency.
- Limit: High write concurrency, multi-host workers, and long event streams will contend on `BEGIN IMMEDIATE` and full-history view rebuilds.
- Scaling path: Keep the `RunEventStore` contract stable and add a server-grade store with append transactions, leases, snapshots, and streaming reads.

**Execution leases use wall-clock timestamps only:**
- Current capacity: `SqliteExecutionLeaseStore` stores one active lease per run and prunes expired rows by ISO timestamp string.
- Limit: Clock skew across worker hosts can cause premature expiry or delayed takeover once the runtime moves beyond local single-machine execution.
- Scaling path: Use database/server time or monotonic lease fencing tokens for distributed workers.

**Artifact storage is local filesystem plus SQLite metadata:**
- Current capacity: `SqliteArtifactStore` writes blobs under `runtimeHome/artifacts` and metadata in SQLite.
- Limit: Large artifacts, remote workers, and bundle import/export flows need shared object storage or explicit artifact replication.
- Scaling path: Add an `ArtifactStore` implementation backed by content-addressed object storage and keep local filesystem storage for development.

## Dependencies at Risk

**Node 24 `node:sqlite`:**
- Risk: The storage package depends on `DatabaseSync` from `node:sqlite`, which ties runtime support to Node 24+ and a relatively new built-in SQLite API.
- Impact: Users on Node 22 LTS or hosts without the expected Node 24 build cannot use `@openrund/storage-sqlite`.
- Migration plan: Keep `RunEventStore`, `ExecutionLeaseStore`, and `ArtifactStore` interfaces provider-neutral; add an adapter for a widely deployed SQLite driver or server database when compatibility matters.

**Python documents worker dependencies are separate from pnpm install:**
- Risk: `python/openrund_documents_worker/pyproject.toml` dependencies are not installed by the root `pnpm install` flow.
- Impact: TypeScript tests that spawn the documents worker can fail in a fresh workspace unless Python packaging is set up separately.
- Migration plan: Document the Python setup in the root dev flow or add a script that provisions the worker test environment.

**Live provider tests are skipped without environment variables:**
- Risk: Provider integration behavior is guarded by `it.skipIf` when `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, or `OPENRUND_LOCAL_MODEL_URL` are missing.
- Impact: CI can pass with only normalization/source-shape tests while live provider contract drift goes unnoticed.
- Migration plan: Run scheduled provider-contract tests in a secrets-enabled CI job and keep unit tests with mocked `fetchImpl` for deterministic coverage.

## Missing Critical Features

**No durable worker runner around runtime leases:**
- Problem: Lease storage exists, and multi-process tests exercise lease acquisition, but the core local runtime does not include a durable worker loop that acquires, renews, resumes, and releases execution leases around model/provider work.
- Blocks: End-to-end long-running runs across process crashes and worker restarts.

**No persisted view snapshots:**
- Problem: Views are derived by replaying events, and snapshots are exported in bundles but not persisted as queryable runtime state.
- Blocks: Efficient inspection of large runs, low-latency wait queues, and scalable dashboards.

**No built-in redaction policy for artifacts and provider errors:**
- Problem: Artifacts can contain stdout, stderr, file contents, model context, and provider error bodies without a central redaction strategy.
- Blocks: Safe sharing of `.orun` bundles and logs in environments where runs may touch credentials or private source.

## Test Coverage Gaps

**Subscriber failure after commit:**
- What's not tested: Persisted append plus throwing subscriber behavior and retry semantics.
- Files: `packages/runtime/src/event-log.ts`, `packages/runtime/src/local-runtime.ts`, `tests/runtime/event-streaming.test.ts`
- Risk: Callers may retry a failed append and hit expected-position conflicts, or duplicate side effects around already persisted events.
- Priority: High

**Bundle manifest path traversal:**
- What's not tested: Manifest-declared paths with `..`, absolute paths, or platform-specific separators.
- Files: `packages/runtime/src/orun.ts`, `tests/runtime/orun-bundle.test.ts`
- Risk: Verifier may read outside the bundle before rejecting malformed input.
- Priority: High

**Read-only filesystem mounts:**
- What's not tested: Mutating operations against a mount declared with `posture: "read"`.
- Files: `packages/capability-filesystem/src/path-sandbox.ts`, `packages/capability-filesystem/src/filesystem-capability.ts`, `tests/capabilities/filesystem.test.ts`
- Risk: A mount-level authority constraint can be bypassed if runtime policy grants the action.
- Priority: High

**Artifact store crash consistency:**
- What's not tested: Partial failure between blob write and metadata insert/update.
- Files: `packages/storage-sqlite/src/sqlite-artifact-store.ts`, `tests/storage/sqlite-artifact.test.ts`
- Risk: Orphaned blobs or missing artifact bytes can make replay and export incomplete.
- Priority: Medium

**Partial delegation append failure:**
- What's not tested: Failure after parent spawn append and before child bootstrap or parent established append.
- Files: `packages/runtime/src/runtime-engine.ts`, `packages/runtime/src/delegation-control.ts`, `tests/runtime/delegation-spawn.test.ts`
- Risk: Parent and child run logs can disagree about delegation state after storage or process failure.
- Priority: Medium

**Provider live contract drift:**
- What's not tested: Live provider calls in default CI when required API keys or local model URL are absent.
- Files: `tests/providers/openai.test.ts`, `tests/providers/anthropic.test.ts`, `tests/providers/local-openai-compatible.test.ts`
- Risk: Provider API changes can break runtime invocation while normal test runs stay green.
- Priority: Medium

---

*Concerns audit: 2026-05-15*
