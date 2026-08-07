---
quick_id: 260806-nof
status: complete
completed: 2026-08-06
implementation_commit: 880af32
---

# Quick Task 260806-nof Summary

## Outcome

Restored workspace selection at the Python CLI host boundary while keeping
runtime custody separate from user work products.

- `openrund demo governed-coding` now proposes the generated Run's canonical
  workspace in an interactive text terminal. Enter accepts the default; a path
  selects an operator workspace.
- JSON and non-interactive execution never prompt and use the canonical per-Run
  default. `demo governed-coding WORKSPACE` remains the explicit automation
  form.
- The demo records and reports runtime home, workspace root, selection source,
  and Bundle path.
- An explicit external workspace no longer causes an unused canonical workspace
  to be materialized under the Run home.
- The implementation still uses production UUID factories, system time, local
  assembly, SQLite custody, and built-in Capability transports.

## Verification

- Focused CLI, demo, and documentation tests: 11 passed.
- Installed wheel and source-distribution tests: 6 passed.
- Complete suite: 974 passed, 3 skipped.
- Strict mypy: 224 source files passed.
- Ruff lint and format: 225 files passed.
- `uv lock --check`, `uv build`, and `git diff --check` passed.

## Commit

- `880af32 fix(cli): restore workspace selection`
