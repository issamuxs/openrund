# Quick Task 260514-n1e Summary

## Objective

Improve `docs/quickstart.md` so it teaches OpenRund's governed mutation loop
rather than only runtime bootstrap mechanics.

## Changes

- Reframed the opening around bootstrap, Command evaluation, derived Views, and
  replayable `.orun` Bundles.
- Replaced the low-level first runtime example with `createLocalRuntime` plus
  `sqlite(...)`.
- Added explicit `RuntimeEngine` authority boundary language.
- Added `Smallest Governed Mutation` to show parsed Operations becoming
  Commands and CommandDecisions before Event materialization.
- Strengthened replay and Bundle semantics.
- Reduced the CLI section to a minimal smoke flow and linked to `api.md` for
  the full CLI surface.
- Clarified explanation commands as runtime-governance surfaces rather than
  authority boundaries.

## Verification

- `node scripts/check-ontology-canonical.mjs` passed.
- `pnpm test -- tests/docs/docs-links.test.ts` passed. The repo test script
  builds packages and ran the current Vitest suite: 55 files passed, 221 tests
  passed, 2 skipped.
- `pnpm hygiene` passed.
- `pnpm package:check` passed.
