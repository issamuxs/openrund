---
quick_id: 260514-i07
slug: implement-surface-taxonomy-corrections
status: complete
completed: 2026-05-14
---

# Summary

Implemented the concepts cleanup across current documentation and code.

## Changes

- Updated `docs/contributing.md` to use common secondary suffix guidance and softer authority-ambiguity wording.
- Renamed exported runtime reporting APIs from `RuntimeMilestone` terminology to `RuntimeProgressEntry` terminology.
- Changed CLI timeline output from `milestones` to `entries`.
- Renamed `reduceArtifactIndexView` to `reduceArtifactIndex` and moved the view reducer from `artifact-index-view.ts` to `artifact-index.ts`.
- Updated tests for the renamed runtime progress and artifact index surfaces.
- Added guard coverage for retired `IndexView` and runtime milestone names.

## Verification

- `node scripts/check-ontology-canonical.mjs` — pass.
- `pnpm hygiene` — pass.
- `pnpm test -- tests/runtime/runtime-progress-entries.test.ts tests/runtime/cli-phase5.test.ts tests/views/views.test.ts` — pass; project script ran build plus 55 test files, 221 tests passed, 2 skipped.
- `pnpm package:check` — pass.
