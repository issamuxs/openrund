---
quick_id: 260514-fq0
slug: align-architecture-concepts-authority-lifecycle
status: planned
created: 2026-05-14
---

# Quick Task: Align Architecture And Concepts Authority Lifecycle

## Objective

Converge `docs/architecture.md` and `docs/concepts.md` on one public semantic model:

```text
Operation -> Command -> CommandDecision -> Events -> Views / Receipts / Reports
```

## Scope

- Remove implementation-only `CommandEnvelope` wording from public architecture diagrams.
- Make `CommandDecision` explicit as a canonical governance surface attached to Commands, not a new root ontology concept.
- Strengthen Concepts wording for Command, Action, Wait, Delegation, View, terminal Run mutations, and non-authority surfaces.
- Soften the banned-word rule from exported production names to exported ontology-facing semantic names.

## Verification

- `node scripts/check-ontology-canonical.mjs`
- `pnpm hygiene`
