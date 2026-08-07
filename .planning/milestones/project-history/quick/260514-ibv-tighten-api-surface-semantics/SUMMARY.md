---
quick_id: 260514-ibv
slug: tighten-api-surface-semantics
status: complete
completed: 2026-05-14
---

# Summary

Tightened `docs/api.md` and related public surfaces around current runtime semantics.

## Changes

- Removed stale `runRun(runID)` from API docs; no such public method exists.
- Added explicit RuntimeEngine wording that APIs submit attempted mutations into Engine-owned Command evaluation.
- Strengthened `append(...)` as a legality-bypassing escape hatch limited to bootstrap, storage integration, and controlled fixtures.
- Updated the RuntimeEngine method list to current public mutation APIs.
- Renamed CLI `.orun` resume surface from `resume-report` to `resume-assessment`.
- Updated Bundle, Quickstart, example README, CLI implementation, and tests for the renamed command.
- Clarified current `rebuildViews(...)` fields without introducing aspirational View API names.

## Verification

- `rg -n 'runRun|orun resume-report|resume-report|Command decision ->|authoritative lifecycle Events|requestInteraction\\(|scheduleTimer\\(' docs packages tests examples README.md --glob '!docs/archive/**' --glob '!node_modules' --glob '!dist'` — pass, no matches.
- `node scripts/check-ontology-canonical.mjs` — pass.
- `pnpm hygiene` — pass.
- `pnpm test -- tests/runtime/cli-phase5.test.ts tests/public-api/exports.test.ts` — pass; project script ran build plus 55 test files, 221 tests passed, 2 skipped.
- `pnpm package:check` — pass.
