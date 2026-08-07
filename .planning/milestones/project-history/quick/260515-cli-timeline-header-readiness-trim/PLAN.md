---
status: completed
created_at: 2026-05-15
completed_at: 2026-05-15
---

# Quick Task: CLI Timeline Header and Readiness Trim

## Goal

Trim redundant framework-level CLI timeline/readiness fields:

- Timeline header keeps `# runID`, then only `currentPosition`, `runtimeHome`, and `workspaceRoot`.
- Completion readiness output omits `runID` and `currentPosition`.

## Scope

- Update framework CLI renderers, not demo-specific formatting.
- Preserve raw runtime-derived values; only change displayed field selection.
- Add regression assertions in the governed demo test.

## Verification

- `pnpm vitest run tests/examples/governed-coding-run.test.ts --reporter verbose`
- `pnpm typecheck`
- `pnpm hygiene`
