# Quick Task 260511-pd1 Summary

**Completed:** 2026-05-11
**Status:** Complete

## Outcome

Developer runs no longer place research-brief work products in OS temp folders
by default. Runtime-owned state stays in `~/.openrund`, while work products now
default to a session workspace:

```text
~/.openrund/sessions/<sessionID>/workspace
```

The runtime package exposes `defaultRuntimeHome()` and
`defaultSessionWorkspaceRoot()` so hosts can share the same local layout without
embedding their own conventions. The research-brief CLI asks for the workspace
root in interactive runs; automated/test paths use explicit injection or the
session default.

Reconciliation is now evidence-backed. The demo collects deterministic
filesystem observations for the uncertain side effect, validates them into a
candidate outcome, and then either asks the operator to approve that candidate
or uses explicit automation in tests. The operator no longer invents evidence.

## Files Changed

- `packages/runtime/src/workspace-root.ts`
- `packages/runtime/src/index.ts`
- `examples/research-brief/run.ts`
- `examples/research-brief/README.md`
- `examples/research-brief/expected/runtime-audit.json`
- `examples/research-brief/expected/runtime-audit.md`
- `docs/runtime-semantics.md`
- `docs/storage.md`
- `docs/quickstart.md`
- `docs/api.md`
- `tests/runtime/workspace-root.test.ts`
- `tests/examples/research-brief.test.ts`
