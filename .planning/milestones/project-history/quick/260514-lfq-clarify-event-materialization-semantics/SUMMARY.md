# Quick Task 260514-lfq Summary

## Objective

Improve `docs/events.md` so Events are described as canonical immutable
materializations of Engine-evaluated runtime transitions.

## Changes

- Added explicit CommandDecision materialization semantics.
- Clarified rejected, deferred, and superseded Command effects.
- Explained `command.recorded` as the persisted attempted mutation, origin,
  CommandDecision, trace, result Event, Wait, and replacement linkage.
- Added provenance semantics for `causationID` and `correlationID`.
- Clarified approval Wait resolution and post-approval Command revalidation.
- Added explicit unknown/reconciliation semantics.
- Clarified Delegation, Authority, Lease, Bundle, and replay relationships.

## Verification

- `node scripts/check-ontology-canonical.mjs` passed after replacing
  `supersession linkage` with `replacement linkage` to avoid the banned
  `Session` substring.
- `pnpm test -- tests/docs/docs-links.test.ts` passed. The repo test script
  builds packages and ran the current Vitest suite: 55 files passed, 221 tests
  passed, 2 skipped.
- `pnpm hygiene` passed.
- `pnpm package:check` passed.
