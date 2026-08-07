# Quick Task Summary: CLI Receipt Identity Dedupe

## Outcome

Framework-level timeline receipt rendering no longer prints both `subject.actionID` and top-level `actionID` for the same receipt. The full single-receipt CLI output remains unchanged.

## Changes

- Removed top-level `actionID` from `renderCliResultTimeline` receipt sections.
- Added a governed-coding-run regression assertion preventing the duplicated identity block from returning.

## Verification

- `pnpm vitest run tests/examples/governed-coding-run.test.ts --reporter verbose`
- `pnpm typecheck`
- `pnpm hygiene`
