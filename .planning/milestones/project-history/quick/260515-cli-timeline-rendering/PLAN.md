---
status: in_progress
created_at: 2026-05-15
---

# Quick Task: CLI Timeline Rendering

## Goal

Modify framework-level CLI rendering so the governed coding demo output can be rendered as a chronological dependency hierarchy while preserving raw runtime fields and values.

## Scope

- Add a multi-result renderer in `@openrund/cli`.
- Keep existing single-command `renderCliResult` behavior for command-specific CLI surfaces.
- Have the demo use the framework-level multi-result renderer rather than custom demo formatting.
- Update tests for the new default demo structure.

## Verification

- `pnpm vitest run tests/examples/governed-coding-run.test.ts tests/runtime/cli-phase5.test.ts tests/runtime/cli-smoke.test.ts --reporter verbose`
- `pnpm typecheck`
