---
status: complete
quick_id: 260511-g3v
commit: 1bbf647
completed_at: 2026-05-11
---

# Quick Task 260511-g3v Summary

## Outcome

Hardened the research-brief demo developer surface so it now behaves like a governed runtime demo rather than an internal fixture harness.

## What Changed

- `pnpm demo:research-brief` remains the developer entrypoint, now using `~/.openrund` for runtime-owned state.
- Developer runs generate unique session IDs and session-specific `.orun` bundles under runtime home.
- Human approval is the default path; automation requires `pnpm demo:research-brief:auto`.
- Unknown-outcome reconciliation now requires explicit operator evidence by default, with deterministic reconciler evidence only for automation.
- Demo execution streams major runtime-governance events during execution.
- Runtime audit export now renders deterministic governance, delegation, uncertainty, and validation facts from replayed events.
- Fixture docs and widget code were enriched so the generated brief synthesizes approval, validation, reconciliation, and release-blocker semantics across docs and code.

## Verification

- `pnpm typecheck`
- `pnpm demo:research-brief:auto`
- `pnpm exec vitest run tests/examples/research-brief.test.ts`
- Interactive TTY run with human approval and operator reconciliation defaults.

## Notes

The sandbox blocks writes to `~/.openrund`, so default-home verification required escalated execution once. Tests continue to inject temporary runtime homes directly for isolation.
