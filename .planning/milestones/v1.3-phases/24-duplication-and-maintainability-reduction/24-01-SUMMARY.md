---
phase: "24"
plan: "24-01"
status: complete
completed_at: 2026-05-15
requirements:
  - MAINT-01
  - MAINT-02
  - MAINT-03
---

# Phase 24 Plan 24-01 Summary

## One-Liner

Centralized provider action normalization, added explicit filesystem implementation parity coverage, and preserved `RuntimeEngine` as the authority facade.

## Completed Work

- Added `packages/core/src/provider-normalization.ts` with shared helpers for provider tool-name splitting, JSON argument parsing, action operation creation, and action batch creation.
- Refactored OpenAI, Anthropic, and local OpenAI-compatible adapters to use the shared provider action normalization helpers.
- Added local OpenAI-compatible batch action normalization to match the OpenAI-compatible response shape.
- Added read-only mount posture enforcement to the built-in filesystem implementation in `@openrund/capabilities`.
- Added filesystem parity tests that run representative write/read and read-only rejection behavior against both built-in and package filesystem handlers.
- Deferred broad `RuntimeEngine` seam extraction because it would be a larger authority-boundary refactor than this phase should carry.

## Tests Added

- `tests/providers/provider-normalization.test.ts` covers dotted action names, invalid JSON fallback, single action construction, and action batch construction.
- `tests/capabilities/filesystem-parity.test.ts` covers representative write/read behavior and read-only mutation rejection for both filesystem implementations.

## Verification

- `pnpm typecheck` passed.
- Focused provider/filesystem tests passed: 6 files, 27 tests passed, 2 skipped.
- `pnpm test` passed: 58 test files, 239 tests passed, 2 skipped.
- `pnpm hygiene` passed: canonical ontology, secondary surface naming, and hygiene checks passed.

## Notes

- Provider adapters still own provider-specific HTTP shapes and response traversal; only provider-neutral model operation construction moved to core.
- Filesystem implementation consolidation by dependency inversion is deferred because `@openrund/capability-filesystem` depends on `@openrund/capabilities`; parity coverage now makes future drift visible.
- `RuntimeEngine` remains the sole authority facade in this phase.
