# Fix Run Home Layout

Date: 2026-05-13

## Outcome

The demo and framework helpers now follow the run-home rule:

```text
~/.openrund/runs/<runID>/
  runtime/
  workspace/
  exports/
```

Each demo invocation generates a `runID`. The demo no longer invents a separate demo root and no longer nests exports under runtime storage.

## Changes

- Added `defaultRunHome(...)` and `defaultRunRuntimeHome(...)` to the runtime helper surface.
- Updated `defaultRunWorkspaceRoot(...)` and `defaultBundlePath(...)` to derive from the canonical run home.
- Updated `examples/governed-coding-run/run.ts` so default paths are:
  - `runtimeHome = ~/.openrund/runs/<runID>/runtime`
  - `workspaceRoot = ~/.openrund/runs/<runID>/workspace`
  - `bundlePath = ~/.openrund/runs/<runID>/exports/<runID>.orun`
- Updated tests and docs to lock the run-home structure.

## Verification

- `pnpm demo:governed-coding-run`
- `pnpm test -- tests/examples/governed-coding-run.test.ts tests/runtime/workspace-root.test.ts`
- `pnpm hygiene`
- `pnpm package:check`
