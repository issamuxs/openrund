---
phase: 32-governed-coordination-and-recovery
plan: "06"
subsystem: delegation-lifecycle
tags: [python, engine, delegation, joins, cancellation, late-handoff]
requires:
  - phase: 32-governed-coordination-and-recovery
    plan: "05"
    provides: Atomic bounded parent/child establishment
provides:
  - Explicit evidence-backed child terminal handoff Commands
  - Replay-governed all, any, and quorum join resolution
  - Atomic contract-driven parent/child cancellation and late-handoff policy
affects: [phase-32-release, phase-34-run-loop, phase-35-bundles]
tech-stack:
  added: []
  patterns: [explicit handoff, replay-derived join, contract-driven cross-run cancellation]
key-files:
  created:
    - tests/engine/test_delegation_lifecycle.py
  modified:
    - src/openrund/engine/_delegation.py
    - src/openrund/engine/_legality.py
    - src/openrund/engine/_events.py
    - src/openrund/engine/_engine.py
key-decisions:
  - "Child terminal history is evidence only; one explicit parent Command records handoff before joins can become satisfied."
  - "Only cancel-bound active children receive atomic child run.cancelled facts; detach and allow-completion contracts leave child history untouched."
requirements-completed: [DEL-01, WAIT-01, GOV-01]
duration: 35min
completed: 2026-08-05
status: complete
---

# Phase 32 Plan 06: Delegation Lifecycle Summary

**Child outcomes, join advancement, parent cancellation, and late results now remain explicit contract-governed facts with no automatic parent control flow.**

## Accomplishments

- Required an established relationship, matching identity, absent prior handoff, exact child terminal history, result kind, and required Artifact evidence for parent handoff Commands.
- Proved child completion alone leaves the parent untouched and all/any/quorum joins resolve only through a later explicit parent Command.
- Allowed late handoffs after parent termination only according to persisted `ignore`, `surface`, or `add_to_context` policy without changing terminal parent state.
- Extended parent cancellation to one atomic multi-Run append for every active cancel-bound child while leaving detach/allow-completion children running.
- Preserved complete conflict re-evaluation and cross-Run Command result evidence for cancellation batches.

## Task Commits

1. **Governed handoff, joins, cancellation, and late policy** — `4c2cbcc`
2. **Delegation lifecycle state-machine proof** — `07938e5`

## Deviations from Plan

None.

## Self-Check: PASSED

- Full Engine suite: 88 passed.
- Delegation, Wait, View, and storage focus: 29 passed.
- Strict mypy and Ruff lint/format: passed.

## Next Plan Readiness

Ready to seal Phase 32 compatibility, authority hygiene, documentation, security, and release gates in Plan 32-07.
