---
type: quick
slug: authority-loop-decision-boundary
status: complete
completed: 2026-05-13
commit: uncommitted
---

# Summary

Corrected the architecture authority loop so it explicitly names the
implementation boundary.

## Completed

- Split model-originated and non-model authority paths in `docs/architecture.md`.
- Added `CommandEnvelope -> Legality evaluation -> CommandDecision -> Event
  drafts -> append Events` as the normative loop.
- Documented accepted, rejected, deferred, and superseded outcome semantics.
- Clarified that Capability workers return data to the Engine and never author
  Commands or append Events directly.
- Updated Phase 8.8 planning/context to require the expanded authority loop.

## Verification

```bash
pnpm test -- tests/docs/docs-links.test.ts
pnpm hygiene
```

Both passed.
