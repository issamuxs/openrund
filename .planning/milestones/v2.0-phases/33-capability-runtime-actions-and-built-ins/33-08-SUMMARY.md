---
phase: 33-capability-runtime-actions-and-built-ins
plan: "08"
status: complete
completed: 2026-08-05
requirements: [CAP-01, ACT-01, BUILTIN-01, BUILTIN-02, BUILTIN-03]
commits: [5e42655]
---

# Plan 33-08 Summary

Sealed the Capability subsystem as one installed-package workflow. End-to-end tests register all four built-ins, dispatch them only after durable `action.started` custody, materialize immutable Artifact bytes and compact Event metadata, replay receipts, reject changed or out-of-scope input before dispatch, and reconcile ambiguous stdio outcomes through the Engine.

Architecture tests now fence concrete effects away from Engine, Event, and storage authority. Installed-wheel tests prove that the typed public capability imports and the packaged Markdown stdio worker execute outside the source tree. Documentation describes the Python registry, transports, Action runner, Artifact ordering, security boundaries, and explicit resource lifetimes without a graphical UI workflow.

The release gate passed with 827 tests, strict mypy across 152 source/test files, Ruff lint and format, lock validation, source/wheel builds, installed-wheel execution, and clean diff checks. The authenticated Python compatibility suite is included in the full test run. The frozen predecessor provenance command now rejects the intentionally expanded Python test tree covered by its historical directory-level source commitments; it remains sealed and is retired in Phase 37 rather than weakened.
