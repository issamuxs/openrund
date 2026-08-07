---
status: completed
created_at: 2026-05-15
completed_at: 2026-05-15
---

# Quick Task: CLI Receipt Identity Dedupe

## Goal

Remove duplicated `subject.actionID` plus top-level `actionID` rendering from framework-level timeline receipt sections.

## Scope

- Change only `renderCliResultTimeline` receipt rendering behavior.
- Keep single-command `renderCliResult({ command: "actions receipt" })` unchanged so full raw receipt output remains available.
- Add a regression assertion in the governed demo test.

## Verification

- `pnpm vitest run tests/examples/governed-coding-run.test.ts --reporter verbose`
- `pnpm typecheck`
- `pnpm hygiene`
