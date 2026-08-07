# Quick Task 260511-pjv Summary

**Completed:** 2026-05-11
**Status:** Complete

## Outcome

Workspace selection is no longer defined by the research-brief demo. The demo
still acts as a host and asks the operator for a workspace root, but generic
runtime helpers now own the path semantics:

- `defaultRuntimeHome()`
- `defaultSessionWorkspaceRoot(...)`
- `resolveSessionWorkspaceRoot(...)`
- `sessionExecutionMetadata(...)`

Runtime execution state remains under `~/.openrund`. Work products go to the
selected session workspace. If no workspace is selected, the default is still:

```text
~/.openrund/sessions/<sessionID>/workspace
```

The research-brief bootstrap metadata now records runtime home, workspace root,
default workspace root, whether the workspace defaulted, and whether selection
came from the host, operator, or default.

## Files Changed

- `packages/runtime/src/workspace-root.ts`
- `examples/research-brief/run.ts`
- `docs/api.md`
- `docs/quickstart.md`
- `docs/storage.md`
- `examples/research-brief/README.md`
- `tests/runtime/workspace-root.test.ts`

