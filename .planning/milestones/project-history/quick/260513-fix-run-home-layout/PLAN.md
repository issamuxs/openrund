# Fix Run Home Layout

Date: 2026-05-13

## Problem

The governed coding demo was still treating demo execution as having its own root and deriving runtime/workspace/export paths inconsistently. It also previously used a fixed demo `runID`.

## Target

Every run, including demos, gets a generated `runID` and a run home:

```text
~/.openrund/runs/<runID>/
  runtime/
  workspace/
  exports/
```

Framework helpers should derive those locations. The demo should use those helpers instead of constructing a demo root.

## Verification

- Demo output shows generated `runID`.
- Demo output shows `runtimeHome`, `workspaceRoot`, and `bundlePath` as sibling paths under one run home.
- Tests assert the layout.
- Hygiene and package checks pass.
