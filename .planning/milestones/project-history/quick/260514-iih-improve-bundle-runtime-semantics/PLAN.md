# Quick Task 260514-iih: Improve Bundle Runtime Semantics

## Goal

Tighten `docs/bundles.md` so `.orun` Bundles are framed as portable governed
runtime history, not an archive format or authority source.

## Scope

- Clarify why Bundles exist.
- Separate semantic contents from concrete layout.
- Reinforce replay/import/resume legality boundaries.
- Tie Bundles to Command, CommandDecision, Wait, Action, Check, Delegation, and
  completion semantics.
- Do not rename the implemented Bundle layout unless code requires it.

## Verification

- `node scripts/check-ontology-canonical.mjs`
- `pnpm test -- tests/docs/docs-links.test.ts`
- `pnpm hygiene`
- `pnpm package:check`
