---
quick_id: 260512-r3h
slug: finalize-concepts-md-ontology-cleanup
status: complete
completed: 2026-05-12T19:31:29+02:00
commit: 9e463dc
---

# Summary: Finalize `docs/concepts.md` Ontology Cleanup

## Completed

- Added `external` to canonical Command origins.
- Clarified that Events are Run-scoped in the minimal ontology, including
  Artifact, Authority, and Lease Events.
- Removed `status` from the Action payload and made Action status derived by
  ActionStatusView.
- Clarified that Delegation terminal Events are produced by parent-Run Commands
  after observing child terminal results.
- Clarified that Authority is a global concept while Authority Events remain
  Run-scoped unless a future global log migration is introduced.

## Verification

- `pnpm test -- tests/docs/docs-links.test.ts tests/public-api/exports.test.ts`
- `pnpm typecheck`
- `pnpm hygiene`
