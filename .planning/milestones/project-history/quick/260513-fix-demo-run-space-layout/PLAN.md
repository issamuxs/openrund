---
status: in_progress
---

# Fix Demo Run-Space Layout

## Goal

Restore the governed coding demo to runtime-owned per-Run layout:

- `runtimeHome` is runtime-owned storage root.
- workspace defaults to `<runtimeHome>/runs/<runID>/workspace`.
- Bundle exports default to `<runtimeHome>/runs/<runID>/exports/<runID>.orun`.
- demo output makes that separation explicit.

## Tasks

- Replace manual demo workspace and Bundle paths with runtime helpers.
- Update tests to assert run-space layout.
- Re-run demo and verification gates.
