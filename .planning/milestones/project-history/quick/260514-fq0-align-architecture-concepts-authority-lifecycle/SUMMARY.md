---
quick_id: 260514-fq0
slug: align-architecture-concepts-authority-lifecycle
status: complete
completed: 2026-05-14
---

# Summary

Aligned `docs/architecture.md` and `docs/concepts.md` around the same authority lifecycle:

```text
Operation -> Command -> CommandDecision -> Events -> Views / Receipts / Reports
```

## Changes

- Removed implementation-only `CommandEnvelope` from public architecture lifecycle diagrams.
- Made CommandDecision explicit as the authority boundary and as an attached governance surface, not a root ontology concept.
- Strengthened Concepts wording for Commands, Actions, Waits, Delegations, Views, terminal Run mutations, and non-authority surfaces.
- Updated the banned-word rule to target exported ontology-facing semantic names.

## Verification

- `node scripts/check-ontology-canonical.mjs` — pass.
- `pnpm hygiene` — pass.
