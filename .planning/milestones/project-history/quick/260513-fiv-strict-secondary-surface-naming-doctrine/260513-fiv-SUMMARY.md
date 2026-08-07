---
status: complete
completed: 2026-05-13
task: Strict secondary-surface naming doctrine and production renaming pass for Phase 8.75
---

# Summary

Implemented a naming-control pass for secondary surfaces:

- Added `docs/secondary-surfaces.md` with the locked suffix doctrine.
- Renamed exported View reducers from `project*` to `reduce*`.
- Replaced secondary-surface names using State/Facts/Boundary/Blocker/Record
  shapes with StatusView, ReadinessView, Checkpoint, Issue, and Entry names.
- Renamed `.orun` View schema naming away from projection wording.
- Removed old CLI aliases for approval and check export paths; target commands
  are `waits show --kind approval` and `checks export`.
- Added `scripts/check-secondary-surface-names.mjs` and wired it into hygiene.

## Verification

- `pnpm typecheck`
- `pnpm test`
- `pnpm hygiene`

All passed.
