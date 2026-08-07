# Quick Task 260511-po4 Summary

**Completed:** 2026-05-11
**Status:** Complete

## Outcome

Workspace selection is now part of generic session-start semantics.

- `RuntimeBootstrapInput` has a first-class `execution` field.
- `createBootstrapEvents(...)` records normalized execution metadata on
  `session.created` for every session.
- `workspaceSelectedBy` supports `operator`, `host`, `parent`, and `default`.
- The research-brief demo no longer manually embeds execution metadata; it
  passes `execution` to `runtime.bootstrap(...)`.
- Generic CLI `create` accepts `--workspace <path>` and otherwise records the
  default session workspace.

The demo still owns terminal prompting because hosts own UI, but it no longer
owns the session-start workspace contract.

