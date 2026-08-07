---
status: complete
mode: quick-discuss
must_haves:
  truths:
    - "SessionRuntime supports append-time event subscribers for true runtime event streaming."
    - "Framework operator prompts own workspace selection, governed write approval, and evidence-backed reconciliation."
    - "Manual governed writes and reconciliation default to no action at framework level."
    - "The research-brief demo no longer imports readline or owns prompt rendering."
    - "The demo streams milestones from runtime event subscribers instead of polling after each step."
  artifacts:
    - "packages/runtime/src/event-log.ts"
    - "packages/runtime/src/run-session.ts"
    - "packages/runtime/src/operator-prompts.ts"
    - "examples/research-brief/run.ts"
    - "tests/runtime/event-streaming.test.ts"
    - "tests/runtime/operator-prompts.test.ts"
---

# Quick Task 260511-qng Plan

1. Add runtime event subscriber support to `SessionRuntime` and `RuntimeEventLog`.
2. Add framework-owned Node console operator prompts for workspace, governed
   write approval, and evidence-backed reconciliation.
3. Move no-action approval/reconciliation defaults into the framework operator
   surface.
4. Refactor the research-brief script to use the framework operator and
   append-time event streaming.
5. Add tests for event streaming and framework operator defaults.
6. Update docs and the example README to describe the framework-level surfaces.
