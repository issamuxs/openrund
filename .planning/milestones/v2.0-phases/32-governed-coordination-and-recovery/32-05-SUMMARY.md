---
phase: 32-governed-coordination-and-recovery
plan: "05"
subsystem: delegation
tags: [python, engine, delegation, authority, atomic-events, lineage]
requires:
  - phase: 32-governed-coordination-and-recovery
    plan: "04"
    provides: Governed recovery, Checks, and completion readiness
provides:
  - Strict child contract and Authority-subset validation
  - Explicit child Run contract metadata and delegated Authority facts
  - Atomic parent Command/Delegation and child bootstrap establishment
affects: [phase-32-delegation-lifecycle, phase-33-actions, phase-35-bundles]
tech-stack:
  added: []
  patterns: [authority subset, cross-run atomic append, explicit child contract]
key-files:
  created:
    - src/openrund/engine/_delegation.py
    - tests/engine/test_delegation.py
  modified:
    - src/openrund/engine/_legality.py
    - src/openrund/engine/_engine.py
key-decisions:
  - "Delegation is accepted only when every child grant, action, policy, budget, Artifact, and nesting fact is a current parent subset."
  - "Parent command/contract/handoff and child bootstrap/Authority facts commit through one multi-Run transaction with all result IDs in Command evidence."
requirements-completed: [DEL-01, GOV-01]
duration: 31min
completed: 2026-08-05
status: complete
---

# Phase 32 Plan 05: Atomic Delegation Establishment Summary

**Delegated Runs now begin as explicit bounded contracts and become visible only through one all-or-nothing parent/child transaction.**

## Accomplishments

- Validated child identity and lineage, parent nesting permission, worker nesting limits, Authority/action/policy subsets, parent-bounded budgets, and input Artifact custody before establishment.
- Derived child Run metadata for result kind, required Artifact kinds, known-outcome completion, cancellation, Authority drift, nesting, and late handoff.
- Narrowed inherited Capability constraints and explicitly copied only requested active policy Authority into the child stream.
- Preallocated parent Command/contract/handoff and child created/started/Authority facts, then committed both streams with one `append_many` call.
- Proved idempotent duplicate Commands, collision rejection, missing atomic custody rejection, exact causation/lineage, bounded child completion, and memory/SQLite atomic storage behavior.

## Task Commits

1. **Bounded Delegation contract validation** — `7593829`
2. **Atomic parent/child establishment** — `94a24d3`

## Deviations from Plan

None.

## Self-Check: PASSED

- Engine plus atomic storage concurrency suite: 86 passed.
- Delegation and affected View focus: 17 passed.
- Strict mypy and Ruff lint/format: passed.

## Next Plan Readiness

Ready to add explicit child terminal handoff, joins, parent cancellation, and late-result policy in Plan 32-06.
