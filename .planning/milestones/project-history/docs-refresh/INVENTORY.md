# Documentation Refresh Inventory

Generated for Phase 8.75 after the canonical ontology and secondary-surface naming cleanup.

## Public Package Entry Points

- `@openrund/core`: Events, IDs, model contracts, normalization, Run contracts, storage interfaces.
- `@openrund/runtime`: `RuntimeEngine`, local assembly, Run contract helpers, Checkpoint, Check, Wait, Delegation, Bundle, CLI-facing helpers, operator prompts.
- `@openrund/views`: `rebuildViews`, `RunStatusView`, `WaitQueueView`, `ActionStatusView`, `DelegationView`, `ArtifactIndexView`, `TimelineView`, `ActionReceipt`, Checkpoint View.
- `@openrund/capabilities`: Capability definitions, registry, policy, transports, schemas, built-in filesystem/documents definitions.
- `@openrund/storage` and `@openrund/storage-sqlite`: SQLite-backed Event and Artifact stores.
- `@openrund/providers`: OpenAI, Anthropic, and local OpenAI-compatible provider adapters.
- Built-in capability packages: filesystem, documents, git, process.
- `@openrund/cli`: `executeCli(args, dependencies)`.

## Current Script Surface

- `pnpm build`
- `pnpm typecheck`
- `pnpm test`
- `pnpm hygiene`
- `pnpm demo:governed-coding-run`
- `pnpm demo:governed-coding-run:auto`

## CLI Surface

- `create [runID] [--workspace path]`
- `run [runID] [message...]`
- `inspect [runID]`
- `waits [runID]`
- `waits show --kind approval [runID] [waitID]`
- `timeline [runID]`
- `checks export [runID]`
- `artifacts show [runID] [artifactID]`
- `orun export [runID] [bundlePath]`
- `orun verify <bundlePath>`
- `orun import <bundlePath> [root=path...]`
- `orun resume-report <bundlePath> [root=path...]`
- `orun replay <bundlePath>`

## Current Public Runtime Names

- `RuntimeEngine`
- `createLocalRuntime`
- `runContract`
- `requireOutputArtifact`
- `requireCheckBeforeCompletion`
- `requireChecks`
- `requireSourceCoverage`
- `requireKnownActionOutcomes`
- `defaultBundlePath`
- `exportBundle`
- `verifyBundle`
- `replayBundle`
- `importBundle`
- `assessImportedResume`
- `BundleManifest`
- `BundleExportResult`
- `BundleVerificationResult`
- `BundleReplayResult`
- `BundleImportResult`
- `ResumeAssessment`
- `ResumeAssessmentIssue`

## Current Documentation Problems

- `docs/README.md` links to deleted `docs/ontology-migration.md`.
- `docs/principles.md` overlaps with `docs/concepts.md` and `docs/architecture.md`.
- `docs/runtime-semantics.md` overlaps with `docs/architecture.md`, `docs/api.md`, and `docs/capabilities.md`.
- `docs/orun.md` should be renamed to Bundle vocabulary.
- Multiple docs still present migration-era language as if the codebase has not been renamed.
- Event mapping prose repeats across concepts, events, storage, architecture, and runtime-semantics.

## Final Disposition

- Keep and rewrite: `README.md`, `concepts.md`, `quickstart.md`, `architecture.md`, `events.md`, `api.md`, `capabilities.md`, `providers.md`, `storage.md`, `delegation.md`.
- Rename/rewrite: `orun.md` -> `bundles.md`.
- Add: `contributing.md`.
- Archive: `principles.md`, `runtime-semantics.md`, old `orun.md`, and old overlapping versions.
