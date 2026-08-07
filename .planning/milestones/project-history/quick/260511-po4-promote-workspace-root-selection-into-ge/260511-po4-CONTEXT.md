# Quick Task 260511-po4: Generic session-start workspace semantics - Context

**Gathered:** 2026-05-11
**Status:** Complete

<domain>
## Task Boundary

The previous correction moved workspace path helpers into runtime, but
`SessionRuntime.bootstrap(...)` did not own the session-start execution contract.
The research-brief demo still manually inserted execution metadata.

This task promotes workspace semantics into generic session-start behavior:

- Every session start records execution metadata.
- Hosts may ask the operator for a workspace root, but runtime resolves and
  records the selected/default workspace consistently.
- Child sessions can inherit by passing the parent workspace as the selected
  root with `workspaceSelectedBy: "parent"`.
- CLI create participates in the same bootstrap execution path.

</domain>

