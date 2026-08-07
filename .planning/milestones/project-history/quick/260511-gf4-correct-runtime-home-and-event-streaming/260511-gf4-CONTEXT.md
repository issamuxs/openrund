# Quick Task 260511-gf4: Correct runtime-home and event-streaming semantics - Context

**Gathered:** 2026-05-11
**Status:** Ready for planning

<domain>
## Task Boundary

Correct runtime-home and event-streaming semantics after demo hardening: remove the environment-variable runtime-home override from framework/docs/examples, enforce `~/.openrund` as the only developer runtime home, clarify human/operator reconciliation versus automated test reconciliation, and move major runtime-step streaming into reusable framework/CLI surfaces instead of demo-only reporting.

</domain>

<decisions>
## Implementation Decisions

### Runtime Home
- `~/.openrund` is the only developer runtime home for local OpenRund runs.
- Do not support or document an environment-variable runtime-home override.
- Do not introduce try-directory layouts or any undocumented per-run subfolder.
- Tests may pass explicit `runtimeHome` options to isolate temp state, but user-facing framework docs/examples should not present environment-based runtime-home selection.

### Reconciliation
- The runtime owns unknown-outcome state, wait blocking, validation of reconciliation legality, and canonical `action.outcome.reconciled` recording.
- The runtime must not invent evidence.
- In developer-facing flows, evidence should come from the human/operator unless an explicit automated reconciler is selected.
- Tests and `demo:research-brief:auto` may use deterministic reconciler evidence, but that path must be clearly marked as automation.

### Streaming
- Streaming of governance/runtime milestones is a framework/CLI surface, not a demo-only capability.
- The demo may use the framework/CLI renderer, but should not define its own event grammar.
- The streaming surface should map canonical events or event batches into semantic milestones such as session start, child spawn/join/complete, approval requested/resolved, unknown outcome, reconciliation, validation, completion, and `.orun` export/verify.

</decisions>

<specifics>
## Specific Ideas

- Remove environment-variable runtime-home selection from example code and docs.
- Keep `runtimeHome` constructor/test options as an internal/test seam only.
- Add a reusable runtime or CLI helper such as `runtime-event-stream` / `renderRuntimeEventMilestone` and use it from the demo.
- Update docs to say local runtime home is `~/.openrund`; explicit runtime-home injection is for tests/embedding, not an environment variable contract.
- Update the previous quick task summary/verification if needed so project records no longer claim environment-based runtime-home support.

</specifics>

<canonical_refs>
## Canonical References

- [docs/storage.md](../../../docs/storage.md) — local runtime-home layout.
- [docs/events.md](../../../docs/events.md) — canonical event grammar.
- [docs/runtime-semantics.md](../../../docs/runtime-semantics.md) — developer-facing semantics.
- [docs/api.md](../../../docs/api.md) — runtime/CLI surface map.

</canonical_refs>
