---
quick_id: 260514-ieh
slug: api-coherence-sweep
status: complete
completed: 2026-05-14
---

# Summary

Swept the repository for stale names and surfaces after the `docs/api.md` update.

## Changes

- Removed stale ignored `dist` outputs for retired modules:
  - `packages/runtime/dist/runtime-milestones.*`
  - `packages/views/dist/artifact-index-view.*`
- Updated archived pre-refresh docs so they no longer read as current references to retired API names.
- Confirmed no current source, docs, examples, tests, or archive docs contain retired names such as `runRun`, `resume-report`, `runtimeMilestones*`, `RuntimeMilestone`, `ArtifactIndexView`, or `artifact-index-view`, excluding guard-script literals that intentionally block regressions.

## Verification

- repo-wide stale-name sweep — pass.
- generated-output stale file sweep — pass.
- `node scripts/check-ontology-canonical.mjs` — pass.
- `pnpm hygiene` — pass.
- `pnpm test` — pass: 55 files, 221 tests passed, 2 skipped.
- `pnpm package:check` — pass.
