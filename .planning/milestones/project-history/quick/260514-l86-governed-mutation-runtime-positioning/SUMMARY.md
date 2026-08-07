# Quick Task 260514-l86 Summary

## Objective

Align public positioning with the differentiation exploration by using
"governed mutation runtime" as the external-facing phrase and avoiding
"legality-kernel" as headline vocabulary.

## Changes

- Updated `README.md` opening and positioning language.
- Updated `docs/control.md` positioning to state that harness primitives are
  support features, not the differentiator.
- Added the exact technical center:
  `Operation -> Command -> CommandDecision -> Events`.

## Verification

- `node scripts/check-ontology-canonical.mjs` passed.
- `pnpm test -- tests/docs/docs-links.test.ts` passed. The repo test script
  builds packages and ran the current Vitest suite: 55 files passed, 221 tests
  passed, 2 skipped.
- `pnpm hygiene` passed.
- `pnpm package:check` passed.
