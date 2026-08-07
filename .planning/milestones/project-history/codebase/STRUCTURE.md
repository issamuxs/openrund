# Codebase Structure

**Analysis Date:** 2026-05-15

## Directory Layout

```text
openrund/
├── AGENTS.md                         # Repository instructions and GSD workflow notes
├── README.md                         # Public project overview and quick orientation
├── package.json                      # Root pnpm workspace scripts and dependencies
├── pnpm-workspace.yaml               # Workspace package membership
├── pnpm-lock.yaml                    # Locked pnpm dependency graph
├── tsconfig.base.json                # Shared TypeScript compiler options
├── vitest.config.ts                  # Vitest configuration
├── docs/                             # Normative architecture, ontology, event, storage, provider, and capability docs
├── examples/
│   └── governed-coding-run/          # End-to-end controlled coding demo
├── packages/
│   ├── core/                         # Canonical types, events, IDs, model contracts, storage interfaces
│   ├── runtime/                      # Engine, legality, controls, local assembly, bundles, waits, delegation
│   ├── views/                        # Rebuildable read models, receipts, indexes, timelines, queues
│   ├── capabilities/                 # Capability definitions, registry, schemas, transports, built-in definitions
│   ├── capability-filesystem/        # Filesystem capability handlers and path sandbox
│   ├── capability-documents/         # Documents capability definition and TypeScript client
│   ├── capability-process/           # Process capability definition and handlers
│   ├── capability-git/               # Git capability definition, handlers, receipts
│   ├── storage-sqlite/               # SQLite event, artifact, lease stores and migrations
│   ├── storage/                      # Default storage facade over SQLite stores
│   ├── provider-openai/              # OpenAI provider adapter
│   ├── provider-anthropic/           # Anthropic provider adapter
│   ├── provider-local/               # Local OpenAI-compatible provider adapter
│   ├── providers/                    # Provider re-export/factory package
│   └── cli/                          # CLI command router, process wrapper, renderers
├── python/
│   └── openrund_documents_worker/    # Python stdio JSON-RPC documents worker
├── scripts/                          # Hygiene, ontology, package content, and naming checks
├── tests/                            # Vitest test suites grouped by package/domain
└── .planning/                        # GSD planning, mapping, phase, quick, and research artifacts
```

## Directory Purposes

**`docs`:**
- Purpose: Holds the normative runtime contract and public design documentation.
- Contains: `docs/architecture.md`, `docs/concepts.md`, `docs/events.md`, `docs/capabilities.md`, `docs/storage.md`, `docs/providers.md`, `docs/delegation.md`, `docs/bundles.md`, `docs/control.md`, `docs/api.md`, `docs/quickstart.md`, `docs/contributing.md`.
- Key files: `docs/architecture.md`, `docs/concepts.md`, `docs/events.md`, `docs/capabilities.md`.

**`packages/core`:**
- Purpose: Shared canonical contracts with minimal dependencies.
- Contains: TypeScript source in `packages/core/src`, package metadata in `packages/core/package.json`, compiler config in `packages/core/tsconfig.json`, build output in `packages/core/dist`.
- Key files: `packages/core/src/events.ts`, `packages/core/src/model.ts`, `packages/core/src/run.ts`, `packages/core/src/storage.ts`, `packages/core/src/ids.ts`, `packages/core/src/index.ts`.

**`packages/runtime`:**
- Purpose: Central runtime authority and local runtime assembly.
- Contains: Engine, event log, command decisions, action lifecycle, waits, timers, interactions, delegation, checks, checkpoints, bundles, model validation, local assembly, workspace root helpers, progress entries.
- Key files: `packages/runtime/src/runtime-engine.ts`, `packages/runtime/src/local-runtime.ts`, `packages/runtime/src/action-dispatcher.ts`, `packages/runtime/src/legality-evaluator.ts`, `packages/runtime/src/orun.ts`, `packages/runtime/src/index.ts`.

**`packages/views`:**
- Purpose: Rebuildable, non-authoritative read models.
- Contains: View reducers for run status, wait queues, timeline, action status, action reconciliation, action receipts, artifact index, checkpoints, delegation.
- Key files: `packages/views/src/index.ts`, `packages/views/src/run-status-view.ts`, `packages/views/src/wait-queues.ts`, `packages/views/src/action-receipts.ts`.

**`packages/capabilities`:**
- Purpose: Capability definition system, schemas, registry validation, policy outcomes, errors, and generic transports.
- Contains: `packages/capabilities/src/definition.ts`, `dispatcher.ts`, `registry.ts`, `schema.ts`, `tool-schema.ts`, `policy.ts`, transport implementations, and built-in definitions.
- Key files: `packages/capabilities/src/definition.ts`, `packages/capabilities/src/registry.ts`, `packages/capabilities/src/transports/in-process.ts`, `packages/capabilities/src/transports/stdio-json-rpc.ts`.

**`packages/capability-filesystem`:**
- Purpose: Workspace-scoped filesystem capability implementation.
- Contains: Capability definition, handlers, path sandboxing, package exports.
- Key files: `packages/capability-filesystem/src/filesystem-capability.ts`, `packages/capability-filesystem/src/path-sandbox.ts`, `packages/capability-filesystem/src/definition.ts`.

**`packages/capability-documents`:**
- Purpose: Documents capability definition and TypeScript client for transported document workers.
- Contains: Capability definition, documents client, package exports.
- Key files: `packages/capability-documents/src/definition.ts`, `packages/capability-documents/src/documents-client.ts`, `packages/capability-documents/src/index.ts`.

**`packages/capability-process`:**
- Purpose: Process execution capability implementation behind mounted workspace roots.
- Contains: Capability definition, process handlers, package exports.
- Key files: `packages/capability-process/src/process-capability.ts`, `packages/capability-process/src/definition.ts`.

**`packages/capability-git`:**
- Purpose: Git inspection/mutation capability implementation and receipts.
- Contains: Capability definition, Git handlers, Git receipt helpers.
- Key files: `packages/capability-git/src/git-capability.ts`, `packages/capability-git/src/git-receipts.ts`, `packages/capability-git/src/definition.ts`.

**`packages/storage-sqlite`:**
- Purpose: Local SQLite implementation of event, artifact, and lease stores.
- Contains: SQLite migrations, event store, artifact store, lease store, package exports.
- Key files: `packages/storage-sqlite/src/sqlite-store.ts`, `packages/storage-sqlite/src/sqlite-artifact-store.ts`, `packages/storage-sqlite/src/sqlite-lease-store.ts`, `packages/storage-sqlite/src/migrations.ts`.

**`packages/storage`:**
- Purpose: Public storage facade for creating default local SQLite-backed runtime storage.
- Contains: `sqlite()` binding and re-exports from `@openrund/storage-sqlite`.
- Key files: `packages/storage/src/index.ts`.

**`packages/provider-openai`:**
- Purpose: OpenAI provider adapter.
- Contains: OpenAI adapter and package exports.
- Key files: `packages/provider-openai/src/openai-adapter.ts`, `packages/provider-openai/src/index.ts`.

**`packages/provider-anthropic`:**
- Purpose: Anthropic provider adapter.
- Contains: Anthropic adapter and package exports.
- Key files: `packages/provider-anthropic/src/anthropic-adapter.ts`, `packages/provider-anthropic/src/index.ts`.

**`packages/provider-local`:**
- Purpose: Local OpenAI-compatible provider adapter.
- Contains: Local compatible adapter and package exports.
- Key files: `packages/provider-local/src/local-openai-compatible-adapter.ts`, `packages/provider-local/src/index.ts`.

**`packages/providers`:**
- Purpose: Provider aggregate package.
- Contains: Re-export surface for provider adapters/factories.
- Key files: `packages/providers/src/index.ts`.

**`packages/cli`:**
- Purpose: Operator-facing command surface over an injected runtime.
- Contains: CLI command router, result renderer, process entrypoint, bin wrapper.
- Key files: `packages/cli/src/index.ts`, `packages/cli/src/bin.ts`.

**`examples/governed-coding-run`:**
- Purpose: End-to-end demonstration of the controlled runtime loop.
- Contains: Demo script, fixture project, expected outputs, README.
- Key files: `examples/governed-coding-run/run.ts`, `examples/governed-coding-run/fixtures/project/src/math.mjs`, `examples/governed-coding-run/fixtures/model-fixture.json`.

**`python/openrund_documents_worker`:**
- Purpose: Python package for transported documents worker.
- Contains: Python package metadata, JSON-RPC server, Markdown operations, Python tests.
- Key files: `python/openrund_documents_worker/pyproject.toml`, `python/openrund_documents_worker/openrund_documents_worker/server.py`, `python/openrund_documents_worker/openrund_documents_worker/jsonrpc.py`, `python/openrund_documents_worker/openrund_documents_worker/markdown_ops.py`.

**`tests`:**
- Purpose: Vitest and pytest-style verification by domain.
- Contains: TypeScript tests under `tests/capabilities`, `tests/core`, `tests/runtime`, `tests/storage`, `tests/views`, `tests/providers`, `tests/public-api`, `tests/examples`, `tests/docs`; Python tests under `python/openrund_documents_worker/tests`.
- Key files: `tests/runtime/local-runtime.test.ts`, `tests/runtime/orun-replay-resume.test.ts`, `tests/public-api/exports.test.ts`, `tests/examples/governed-coding-run.test.ts`.

**`scripts`:**
- Purpose: Repository hygiene and semantic checks.
- Contains: Node scripts for package content, ontology canonicality, secondary surface names, and hygiene.
- Key files: `scripts/check-hygiene.mjs`, `scripts/check-ontology-canonical.mjs`, `scripts/check-package-content.mjs`, `scripts/check-secondary-surface-names.mjs`.

**`.planning`:**
- Purpose: GSD planning state and generated planning artifacts.
- Contains: Codebase maps in `.planning/codebase`, phase plans in `.planning/phases`, quick tasks in `.planning/quick`, milestone state in `.planning/milestones`, research artifacts in `.planning/research`.
- Key files: `.planning/codebase/ARCHITECTURE.md`, `.planning/codebase/STRUCTURE.md`.

## Key File Locations

**Entry Points:**
- `packages/cli/src/bin.ts`: Node executable wrapper.
- `packages/cli/src/index.ts`: CLI command routing and rendering.
- `packages/runtime/src/runtime-engine.ts`: Main runtime API and authority boundary.
- `packages/runtime/src/local-runtime.ts`: Local runtime assembly factory.
- `packages/storage/src/index.ts`: Default SQLite storage binding.
- `examples/governed-coding-run/run.ts`: Demo entry point.
- `python/openrund_documents_worker/openrund_documents_worker/server.py`: Python documents worker entry point.

**Configuration:**
- `package.json`: Root scripts, Node/pnpm engine constraints, workspace dependencies.
- `pnpm-workspace.yaml`: pnpm workspace package selection.
- `pnpm-lock.yaml`: Dependency lockfile.
- `tsconfig.base.json`: Shared TypeScript compiler options.
- `vitest.config.ts`: Test runner configuration.
- `packages/*/package.json`: Package names, exports, dependencies, scripts.
- `packages/*/tsconfig.json`: Per-package TypeScript project configs.
- `python/openrund_documents_worker/pyproject.toml`: Python worker package and test config.

**Core Logic:**
- `packages/core/src/events.ts`: Event catalog, event envelope, payload types.
- `packages/core/src/model.ts`: Provider/runtime operation types, command decisions, model context.
- `packages/core/src/run.ts`: Run, wait, authority, delegation, result, and contract types.
- `packages/core/src/storage.ts`: Store interfaces.
- `packages/runtime/src/runtime-engine.ts`: Runtime mutation methods.
- `packages/runtime/src/action-dispatcher.ts`: Capability action dispatch and worker result materialization.
- `packages/runtime/src/check-control.ts`: Completion checks and run contract enforcement.
- `packages/runtime/src/wait-control.ts`: Wait resolution and approval validation.
- `packages/runtime/src/delegation-control.ts`: Delegation spawn/join/handoff events.
- `packages/runtime/src/orun.ts`: Bundle export/import/verify/replay/resume assessment.
- `packages/views/src/index.ts`: View bundle rebuild entry point.

**Capability Logic:**
- `packages/capabilities/src/definition.ts`: CapabilityDefinition and CapabilityResult contracts.
- `packages/capabilities/src/registry.ts`: Capability registry validation and lookup.
- `packages/capabilities/src/dispatcher.ts`: CapabilityTransport and handler contracts.
- `packages/capability-filesystem/src/filesystem-capability.ts`: Filesystem handlers.
- `packages/capability-filesystem/src/path-sandbox.ts`: Mount and path safety.
- `packages/capability-process/src/process-capability.ts`: Process handlers.
- `packages/capability-git/src/git-capability.ts`: Git handlers.
- `packages/capability-documents/src/documents-client.ts`: Documents worker client.

**Persistence:**
- `packages/storage-sqlite/src/migrations.ts`: SQLite schema and database opening.
- `packages/storage-sqlite/src/sqlite-store.ts`: Run event store.
- `packages/storage-sqlite/src/sqlite-artifact-store.ts`: Artifact metadata and blob store.
- `packages/storage-sqlite/src/sqlite-lease-store.ts`: Execution lease store.

**Testing:**
- `tests/core`: Core type/contract and normalization tests.
- `tests/runtime`: Engine, waits, actions, checks, delegation, bundles, CLI smoke, replay/resume tests.
- `tests/capabilities`: Capability registry, filesystem, documents stdio, process, git, tool schema tests.
- `tests/storage`: SQLite store/artifact/lease tests.
- `tests/views`: View reducer tests.
- `tests/providers`: Provider adapter tests.
- `tests/public-api`: Export and ontology guard tests.
- `tests/examples`: Demo tests.
- `python/openrund_documents_worker/tests`: Python documents worker tests.

## Naming Conventions

**Files:**
- Use kebab-case for most TypeScript module filenames: `runtime-engine.ts`, `action-dispatcher.ts`, `run-status-view.ts`, `sqlite-artifact-store.ts`.
- Use `index.ts` as package public export barrels: `packages/runtime/src/index.ts`, `packages/views/src/index.ts`, `packages/storage/src/index.ts`.
- Use capability package names with `capability-*` directories and action implementation filenames ending in `-capability.ts`: `packages/capability-filesystem/src/filesystem-capability.ts`.
- Use provider implementation filenames ending in `-adapter.ts`: `packages/provider-openai/src/openai-adapter.ts`.
- Use tests named `*.test.ts` under `tests/<domain>`: `tests/runtime/action-dispatcher.test.ts`.
- Use Python snake_case modules under the Python worker: `jsonrpc.py`, `markdown_ops.py`.

**Directories:**
- Put workspace packages under `packages/<package-name>`.
- Put package source under `packages/<package-name>/src`.
- Put package build output under `packages/<package-name>/dist`; treat `dist` as generated.
- Put tests under top-level `tests/<domain>` for TypeScript and under the Python package for Python worker tests.
- Put examples under `examples/<example-name>`.
- Put normative docs under `docs`.
- Put planning artifacts under `.planning`.

## Where to Add New Code

**New Runtime Mutation:**
- Primary code: `packages/runtime/src/runtime-engine.ts`
- Event draft helper: `packages/runtime/src/<domain>-control.ts`
- Shared operation/decision types: `packages/core/src/model.ts`
- Event payload types/catalog: `packages/core/src/events.ts`
- Views: `packages/views/src/<domain>-view.ts` and `packages/views/src/index.ts`
- Tests: `tests/runtime/<domain>.test.ts`, plus view tests in `tests/views/<domain>.test.ts` when derived state changes.

**New Core Concept Or Event:**
- Primary code: `packages/core/src/run.ts`, `packages/core/src/events.ts`, `packages/core/src/model.ts`
- Documentation: `docs/concepts.md`, `docs/events.md`, and related docs under `docs`
- Runtime handling: `packages/runtime/src`
- Derived state: `packages/views/src`
- Tests: `tests/core/*.test.ts`, `tests/public-api/ontology-guards.test.ts`, `tests/runtime/*.test.ts`, `tests/views/*.test.ts`

**New Capability Package:**
- Implementation: `packages/capability-<name>/src/definition.ts`, `packages/capability-<name>/src/<name>-capability.ts`, `packages/capability-<name>/src/index.ts`
- Package metadata: `packages/capability-<name>/package.json`, `packages/capability-<name>/tsconfig.json`
- Shared capability infrastructure: `packages/capabilities/src` only when the generic contract changes.
- Assembly registration: local/demo setup such as `examples/governed-coding-run/run.ts` or caller-specific `createLocalRuntime` usage.
- Tests: `tests/capabilities/<name>.test.ts`

**New Capability Action In Existing Package:**
- Definition: `packages/capability-<name>/src/definition.ts`
- Handler: `packages/capability-<name>/src/<name>-capability.ts`
- Schema validation: use `packages/capabilities/src/schema.ts` compatible JSON schemas.
- Tests: `tests/capabilities/<name>.test.ts`

**New Transport:**
- Implementation: `packages/capabilities/src/transports/<transport>.ts`
- Contract type changes: `packages/capabilities/src/dispatcher.ts`, `packages/capabilities/src/definition.ts`
- Exports: `packages/capabilities/src/index.ts`
- Tests: `tests/capabilities/<transport>.test.ts`

**New Provider Adapter:**
- Implementation: `packages/provider-<name>/src/<name>-adapter.ts`, `packages/provider-<name>/src/index.ts`
- Aggregate exports: `packages/providers/src/index.ts`
- Tests: `tests/providers/<name>.test.ts`

**New View:**
- Implementation: `packages/views/src/<domain>-view.ts`
- Export/rebuild wiring: `packages/views/src/index.ts`
- Tests: `tests/views/<domain>.test.ts`
- Rule: Keep it deterministic and derived only from events/artifacts.

**New CLI Command:**
- Routing and implementation: `packages/cli/src/index.ts`
- Rendering: `renderCliResult` in `packages/cli/src/index.ts`
- Runtime call: prefer existing `RuntimeEngine` method or add one in `packages/runtime/src/runtime-engine.ts`
- Tests: `tests/runtime/cli-*.test.ts` or a focused CLI test under `tests/runtime`.

**New Storage Backend:**
- Interfaces: keep `packages/core/src/storage.ts` stable unless the storage contract changes.
- Implementation: create a new package under `packages/storage-<backend>/src`.
- Facade exports: update or add binding package under `packages/storage/src`.
- Tests: `tests/storage/<backend>-*.test.ts`.

**New Bundle Feature:**
- Primary code: `packages/runtime/src/orun.ts`
- Runtime method surface: `packages/runtime/src/runtime-engine.ts`
- Docs: `docs/bundles.md`
- Tests: `tests/runtime/orun-*.test.ts`

**New Demo Flow:**
- Implementation: `examples/<demo-name>/run.ts`
- Fixtures: `examples/<demo-name>/fixtures`
- Expected output: `examples/<demo-name>/expected`
- Tests: `tests/examples/<demo-name>.test.ts`

**Utilities:**
- Runtime-specific helpers: `packages/runtime/src/<helper>.ts`
- Core shared helpers: `packages/core/src/<helper>.ts`
- Capability generic helpers: `packages/capabilities/src/<helper>.ts`
- Repository scripts: `scripts/<task>.mjs`

## Special Directories

**`packages/*/dist`:**
- Purpose: TypeScript build output for each package.
- Generated: Yes
- Committed: Present in workspace; do not edit by hand.

**`packages/*/node_modules`:**
- Purpose: pnpm-linked package dependencies.
- Generated: Yes
- Committed: No.

**`node_modules`:**
- Purpose: Root dependency install location.
- Generated: Yes
- Committed: No.

**`.pnpm-store`:**
- Purpose: Local pnpm package store.
- Generated: Yes
- Committed: No.

**`.planning`:**
- Purpose: GSD project state, phase artifacts, quick tasks, research, and codebase maps.
- Generated: Mixed; managed by GSD workflow and mapper agents.
- Committed: Project-specific planning artifacts may be committed by orchestrator; mapper agents should only edit their assigned files.

**`docs/archive`:**
- Purpose: Archived documentation snapshots.
- Generated: No
- Committed: Yes.

**`examples/governed-coding-run/fixtures`:**
- Purpose: Source fixture project copied into runtime workspaces by the demo.
- Generated: No
- Committed: Yes.

**`examples/governed-coding-run/expected`:**
- Purpose: Expected demo outputs.
- Generated: No
- Committed: Yes.

**`python/openrund_documents_worker/openrund_documents_worker.egg-info`:**
- Purpose: Python packaging metadata.
- Generated: Yes
- Committed: Present in workspace; do not edit for runtime TypeScript changes.

**`python/openrund_documents_worker/.pytest_cache`:**
- Purpose: Python test cache.
- Generated: Yes
- Committed: No.

---

*Structure analysis: 2026-05-15*
