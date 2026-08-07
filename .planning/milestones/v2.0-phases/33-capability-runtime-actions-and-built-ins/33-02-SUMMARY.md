---
phase: 33-capability-runtime-actions-and-built-ins
plan: "02"
status: complete
completed: 2026-08-05
requirements: [ACT-01]
commits: [1cf3854]
---

# Plan 33-02 Summary

Added trusted start/complete/fail/cancel Action Commands, authenticated start identity and input hash, exact current-state legality, canonical Action terminal materialization, and compact produced Artifact facts. Unknown outcome now requires a durably started Action.

Added `ActionRunner`, which validates input before start, commits `action.started` before dispatch, validates worker output, stores inline Artifact bytes, then records `artifact.created` and the terminal Action outcome. Confirmed worker rejection becomes failed; interruptible confirmed cancellation becomes cancelled; timeout, transport loss, malformed post-dispatch result, and partial evidence become unknown.

The Engine retains no worker, transport, or ArtifactStore dependency. Verification passed across 626 capability, contract, Engine, storage, and View tests plus strict mypy, Ruff, and diff checks.
