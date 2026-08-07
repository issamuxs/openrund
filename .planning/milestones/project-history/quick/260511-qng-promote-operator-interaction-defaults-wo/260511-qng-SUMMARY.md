# Quick Task 260511-qng Summary

**Completed:** 2026-05-11
**Status:** Complete

## Outcome

Workspace selection, governed approval prompts, reconciliation prompts, and
event streaming are now framework surfaces.

- `SessionRuntime` accepts `onEventsAppended` and `eventSubscribers` callbacks.
- Runtime event subscribers receive committed canonical events after each append.
- `createNodeConsoleOperator(...)` owns local operator prompts for session
  workspace selection, governed write approval, and evidence-backed
  reconciliation.
- Manual approval and reconciliation use framework-level no-action defaults.
- The research-brief demo no longer imports `readline` or renders its own
  workspace, approval, or reconciliation prompts.
- The demo streams runtime milestones from append-time event batches instead of
  polling event history after each step.

Remaining demo-specific content is scenario code, provider selection for the
demo entrypoint, deterministic fixture inputs, and the isolated fault-injecting
transport support.
