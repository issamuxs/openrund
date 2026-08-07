# Quick Task 260514-lk1: Clarify Provider Boundary Semantics

## Goal

Improve `docs/providers.md` so Providers are explicitly framed as transport and
parsing adapters that produce Operation proposals but never authorize,
materialize, or decide runtime state.

## Scope

- Align Provider flow with `Command -> CommandDecision -> Events`.
- Strengthen Provider non-authority language.
- Clarify ModelCall as parsed Operation proposal, not execution.
- Clarify deferred and terminal mutation semantics.
- Clarify replay does not depend on Provider transport state.
- Keep provider APIs and event names unchanged.

## Verification

- `node scripts/check-ontology-canonical.mjs`
- `pnpm test -- tests/docs/docs-links.test.ts`
- `pnpm hygiene`
- `pnpm package:check`
