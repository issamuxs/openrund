---
quick_id: 260514-i2s
slug: improve-readme-runtime-positioning
status: complete
completed: 2026-05-14
---

# Summary

Improved `README.md` first-contact positioning so it explains why OpenRund exists, states the core runtime invariants, and aligns the public lifecycle wording with `Command -> CommandDecision -> Events`.

## Changes

- Reframed OpenRund as a runtime model implemented in TypeScript.
- Added a concise explanation of runtime governance versus middleware governance.
- Added `Core Runtime Invariants`.
- Updated the core separation diagram to include `CommandDecision`.
- Renamed `Verification` to `Repository Verification` and clarified the checks.

## Verification

- `node scripts/check-ontology-canonical.mjs` — pass.
- `pnpm hygiene` — pass.
- `pnpm package:check` — pass.
