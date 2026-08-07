# Quick Task 260514-n1e: Improve Quickstart Governed Mutation Loop

## Goal

Improve `docs/quickstart.md` so the first-contact flow teaches OpenRund's
actual wedge: attempted mutation enters Command evaluation, produces a
CommandDecision, and only accepted Commands materialize Events.

## Scope

- Reframe opening around the smallest governed runtime loop.
- Prefer `createLocalRuntime` for the first runtime assembly example.
- Add a smallest governed mutation section.
- Strengthen replay and Bundle semantics.
- Reduce the CLI list to a smoke flow and point to `api.md` for full CLI.
- Keep code illustrative and avoid runtime API changes.

## Verification

- `node scripts/check-ontology-canonical.mjs`
- `pnpm test -- tests/docs/docs-links.test.ts`
- `pnpm hygiene`
- `pnpm package:check`
