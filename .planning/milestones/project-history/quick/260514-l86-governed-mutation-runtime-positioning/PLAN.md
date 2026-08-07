# Quick Task 260514-l86: Governed Mutation Runtime Positioning

## Goal

Update public-facing wording in `README.md` and `docs/control.md` to use the
clearer phrase "governed mutation runtime" instead of broader harness/runtime
positioning, while preserving the exact Command/CommandDecision semantics.

## Scope

- Patch `README.md`.
- Patch `docs/control.md`.
- Do not introduce "legality-kernel" as headline wording.
- Do not change runtime code.

## Verification

- `node scripts/check-ontology-canonical.mjs`
- `pnpm test -- tests/docs/docs-links.test.ts`
- `pnpm hygiene`
- `pnpm package:check`
