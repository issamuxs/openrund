# Quick Summary: Finalize Ontology Migration Guide

## Result

Finalized `docs/ontology-migration.md` as the refactor-control document for the
ontology code migration.

## Changes

- Split the opening migration target into model-originated and non-model
  Command paths.
- Clarified ModelCall lifecycle handling relative to Command persistence.
- Replaced single-fact normalized event shape with raw event plus
  `NormalizedFact[]`.
- Added operation kind classes, expanded ID mappings, Command decision
  semantics, payload-normalization failure rules, and `.orun` Command metadata
  guidance.
- Tightened Command Path file coverage, static-check nuance, child-wait tests,
  and documentation synchronization gate.
- Aligned `concepts.md` and `events.md` with the precise approval decision
  mapping and expanded operation taxonomy.

## Verification

- `pnpm test -- tests/docs/docs-links.test.ts tests/public-api/exports.test.ts`
  passed.
- `pnpm typecheck` passed.
- `pnpm hygiene` passed.
- Focused stale-term scan found no obsolete ModelCall/Event or approval mapping
  ambiguity.

## Commits

- Docs commit: `6bb2233`.
- Tracking commit: `450578d`.
