# Quick Task 260511-qng: Framework operator interactions and runtime streaming - Context

**Gathered:** 2026-05-11
**Status:** Complete

<domain>
## Task Boundary

The previous correction removed several demo-specific output issues, but the
research-brief script still owned important runtime surfaces:

- Workspace selection was prompted directly in the demo.
- Approval prompts and no-action defaults were demo code.
- Reconciliation prompts and evidence rendering were demo code.
- Runtime milestone reporting was implemented by polling events after each demo
  step rather than streaming append-time runtime events.

User decision:

- These surfaces must be framework-level, not demo-level.
- The demo may keep only the OpenRund TypeScript scenario script, input data,
  and the demo-local transport breaker.
- Manual approval and reconciliation must default to no action at the framework
  surface.
- Event reporting must stream from runtime append events while execution is
  happening.

</domain>
