# Quick Task 260514-ld4: Improve Delegation Legality Semantics

## Goal

Improve `docs/delegation.md` so Delegation reads as governed bounded sub-work
with explicit Authority, Command, join, completion, and replay semantics rather
than generic parent/child orchestration.

## Scope

- Rewrite the opening around governed sub-work.
- Add Command/CommandDecision mutation semantics.
- Add explicit delegated Authority attenuation.
- Clarify join and completion legality.
- Clarify unknown outcome and replay implications.
- Keep event names and implementation behavior unchanged.

## Verification

- `node scripts/check-ontology-canonical.mjs`
- `pnpm test -- tests/docs/docs-links.test.ts`
- `pnpm hygiene`
- `pnpm package:check`
