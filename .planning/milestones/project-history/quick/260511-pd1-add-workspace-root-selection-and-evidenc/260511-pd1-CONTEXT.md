# Quick Task 260511-pd1: Workspace root selection and evidence-backed reconciliation - Context

**Gathered:** 2026-05-11
**Status:** Ready for execution

<domain>
## Task Boundary

Fix two developer-surface issues exposed by the real demo trace:

- Work products should not be created in OS temp folders for developer runs.
- Reconciliation should approve collected evidence, not ask the operator to invent evidence.

</domain>

<decisions>
## Implementation Decisions

### Workspace Roots

- Runtime-owned state remains in `~/.openrund`.
- Developer-facing work products need a declared workspace root.
- The host/CLI asks the operator for the workspace root because terminal I/O is not a runtime responsibility.
- The runtime package should expose a deterministic default session workspace helper so hosts do not invent layouts independently.
- Default workspace root is session-scoped under `~/.openrund/sessions/<sessionID>/workspace`.
- Tests may still inject temporary workspace roots directly.

### Relocation

- Normal governed writes stay inside the selected workspace root.
- Local developer UX may let the operator choose the workspace at session start without predeclaring roots in application code.
- Stricter policy can later constrain allowed workspaces.

### Reconciliation Evidence

- Unknown outcomes create a reconciliation blocker.
- The model or runtime may choose evidence-gathering actions, but the model cannot decide final truth.
- Capabilities collect deterministic observations.
- A validator derives a candidate outcome from observations.
- Default developer flow asks the operator to approve the evidence-backed candidate.
- Explicit automation may approve the candidate when policy/test mode allows it.

</decisions>

<canonical_refs>
## Canonical References

- [examples/research-brief/run.ts](../../../examples/research-brief/run.ts)
- [docs/runtime-semantics.md](../../../docs/runtime-semantics.md)
- [docs/storage.md](../../../docs/storage.md)
- [docs/quickstart.md](../../../docs/quickstart.md)

</canonical_refs>

