# Quick Task Summary: CLI Timeline Header and Readiness Trim

## Outcome

Framework-level CLI rendering now removes redundant status/identity rows from the timeline summary shape:

- Timeline header shows `# runID`, then `currentPosition`, `runtimeHome`, and `workspaceRoot`.
- Completion readiness output omits `runID` and `currentPosition`.

## Changes

- Updated `renderCliResultTimeline` header rendering.
- Updated timeline completion readiness rendering.
- Updated standalone `runs readiness` rendering to match the readiness field trim.
- Added governed demo regression assertions for the revised output shape.

## Verification

- `pnpm vitest run tests/examples/governed-coding-run.test.ts --reporter verbose`
- `pnpm typecheck`
- `pnpm hygiene`
