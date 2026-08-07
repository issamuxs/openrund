# Quick Task 260511-gf4 Summary

**Completed:** 2026-05-11
**Status:** Complete

## Outcome

Corrected the research-brief hardening so it matches the intended OpenRund semantics:

- Developer-facing runtime state now resolves only to `~/.openrund`.
- Environment-variable runtime-home selection was removed from framework docs, example docs, example code, package surface, and recent planning records.
- Tests and embedding code still have an explicit `runtimeHome` injection seam for isolation, but this is not a user-facing local runtime-home contract.
- Runtime governance streaming now comes from reusable runtime milestone helpers and a CLI `timeline` surface, not a demo-specific event grammar.
- Reconciliation docs now distinguish runtime authority from evidence source: the runtime records, gates, validates, and unblocks; an operator or explicit deterministic reconciler supplies evidence.
- The demo now uses run-scoped parent, child, and synthetic event IDs for real durable runs so repeated executions under `~/.openrund` do not collide.

## Files Changed

- `packages/runtime/src/runtime-milestones.ts`
- `packages/runtime/src/index.ts`
- `packages/cli/src/index.ts`
- `examples/research-brief/run.ts`
- `examples/research-brief/README.md`
- `docs/storage.md`
- `docs/quickstart.md`
- `docs/runtime-semantics.md`
- `docs/api.md`
- `tests/runtime/runtime-milestones.test.ts`
- `tests/runtime/cli-phase5.test.ts`
- `.planning/quick/260511-g3v-harden-the-research-brief-demo-developer/*`

## Reconciliation Model

Default developer runs use human/operator evidence. The runtime can detect an unknown outcome, create the reconciliation blocker, reject terminal completion while unresolved, and record the final reconciled state once evidence is supplied. It must not invent evidence.

Automated reconciliation is available only through explicit automation, such as tests or `demo:research-brief:auto`, where the deterministic reconciler is the evidence provider.

