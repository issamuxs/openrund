# Quick Task 260514-lk1 Summary

## Objective

Improve `docs/providers.md` so Providers are clearly non-authority transport and
parsing adapters aligned with the Command/CommandDecision model.

## Changes

- Rewrote the opening to say Providers translate model output into parsed
  Operation proposals.
- Added explicit non-authority rules: Providers do not authorize execution,
  grant Authority, decide legality, resolve Waits, append Events, or determine
  completion legality.
- Clarified that the Engine converts parsed Operations into Commands, evaluates
  legality through CommandDecision semantics, and materializes Events only for
  accepted Commands.
- Clarified ModelCall as provider call plus parsed Operation proposal.
- Clarified provider-originated terminal Operations as attempted terminal
  mutations governed by accepted CommandDecisions.
- Clarified deferred CommandDecision and replay semantics.

## Verification

- `node scripts/check-ontology-canonical.mjs` passed.
- `pnpm test -- tests/docs/docs-links.test.ts` passed. The repo test script
  builds packages and ran the current Vitest suite: 55 files passed, 221 tests
  passed, 2 skipped.
- `pnpm hygiene` passed.
- `pnpm package:check` passed.
