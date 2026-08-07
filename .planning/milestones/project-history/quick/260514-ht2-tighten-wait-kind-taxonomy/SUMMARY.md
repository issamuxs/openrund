---
quick_id: 260514-ht2
slug: tighten-wait-kind-taxonomy
status: complete
completed: 2026-05-14
---

# Summary

Committed the user's `docs/concepts.md` and `docs/architecture.md` edits, then implemented the Wait taxonomy decision across current code and documentation.

## Decision

Wait kinds are limited to fundamentally distinct runtime blocking semantics:

- `approval`
- `interaction`
- `timer`
- `join`
- `reconciliation`

Removed ontology-level Wait kinds:

- `external_signal`
- `operational_backoff`
- `operational_exhaustion`

Those removed meanings belong in Wait payload metadata, timer retry policy, legality evaluation, contracts, budgets, Action or Run failure semantics, or participant intervention Waits.

## Verification

- `rg -n "external_signal|operational_backoff|operational_exhaustion" packages docs tests examples scripts --glob "!docs/archive/**"` — pass, no current-surface matches.
- `node scripts/check-ontology-canonical.mjs` — pass.
- `pnpm hygiene` — pass.
- `pnpm test -- tests/views/wait-queues.test.ts tests/runtime/timer-waits.test.ts tests/runtime/interaction-waits.test.ts tests/runtime/delegation-joins.test.ts tests/runtime/action-reconciliation.test.ts` — pass; project script ran build plus 55 test files, 221 tests passed, 2 skipped.
