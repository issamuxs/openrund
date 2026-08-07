# Quick Task 260514-ik1 Summary

## Objective

Improve `docs/capabilities.md` so Capability semantics match the current
Engine-owned Command and CommandDecision authority model.

## Changes

- Reframed Capabilities as executable interfaces invoked through
  Engine-controlled Action lifecycle semantics.
- Updated the lifecycle from direct validation/materialization language to
  `Command -> CommandDecision -> accepted Command -> Action lifecycle Events`.
- Added explicit worker non-authority language: workers do not append Events,
  grant Authority, decide terminal Run state, or mutate Views.
- Documented Action lifecycle Events including `action.unknown` and
  `action.reconciled`, and tied unknown outcomes to reconciliation and
  completion legality.
- Explained `CapabilityAccessMode`, `CapabilityReliability`, effects, evidence,
  and how Capability output participates in completion legality.
- Simplified operation-batch language to keep batching subordinate to runtime
  legality evaluation.

## Verification

- `node scripts/check-ontology-canonical.mjs` passed.
- `pnpm test -- tests/docs/docs-links.test.ts` passed. The repo test script
  builds packages and ran the current Vitest suite: 55 files passed, 221 tests
  passed, 2 skipped.
- `pnpm hygiene` passed.
- `pnpm package:check` passed.
