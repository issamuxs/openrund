---
quick_id: 260514-ht2
slug: tighten-wait-kind-taxonomy
status: planned
created: 2026-05-14
---

# Quick Task: Tighten Wait Kind Taxonomy

## Objective

Commit the user's `docs/concepts.md` edits and implement the Wait taxonomy decision:

- Keep ontology-level Wait kinds: `approval`, `interaction`, `timer`, `join`, `reconciliation`.
- Remove ontology-level Wait kinds: `external_signal`, `operational_backoff`, `operational_exhaustion`.
- Treat removed semantics as payload metadata, timer policy, interaction/approval, legality rejection, or failure semantics depending on context.

## Decision

A Wait kind must represent a fundamentally distinct reason canonical Run advancement is illegal right now. The final taxonomy is:

| Wait kind | Blocking meaning |
|---|---|
| `approval` | Authorization missing. |
| `interaction` | Participant information/input missing. |
| `timer` | Time condition missing. |
| `join` | Delegated completion condition missing. |
| `reconciliation` | Outcome certainty missing. |

## Verification

- `rg -n "external_signal|operational_backoff|operational_exhaustion" packages docs tests examples scripts --glob "!docs/archive/**"`
- `node scripts/check-ontology-canonical.mjs`
- `pnpm hygiene`
- `pnpm test -- tests/views/wait-queues.test.ts tests/runtime/timer-waits.test.ts tests/runtime/interaction-waits.test.ts tests/runtime/delegation-joins.test.ts tests/runtime/action-reconciliation.test.ts`
