---
quick_id: 260806-nof
status: ready
description: "Restore the Python CLI workspace-selection contract"
---

# Quick Task 260806-nof Plan

Restore the Python CLI workspace-selection contract without merging user work
products into runtime custody or introducing a demo-only execution path.

## Task 1: Restore workspace selection at the CLI host boundary

- Make `demo governed-coding` accept an optional workspace.
- In an interactive text terminal, propose the generated Run's canonical
  workspace and accept Enter or an operator replacement.
- In JSON or non-interactive execution, select the canonical default without
  prompting; an explicit workspace always wins.
- Use production UUID factories, clocks, assembly, stores, and capabilities.

Verification: focused CLI and demo tests cover explicit, defaulted, and
operator-selected workspaces.

## Task 2: Align custody materialization and public documentation

- Record runtime home, selected workspace, selection source, and export path in
  Run metadata and demo output.
- Do not materialize the unused canonical workspace when the operator selects
  an external workspace.
- Update the README, quickstart, API reference, examples, and documentation
  tests to describe optional selection and non-interactive behavior.

Verification: no external-workspace run creates a second workspace; the full
test, typing, lint, format, lock, and build gates pass.
