---
phase: 29-deterministic-views-and-replay-facts
plan: "05"
subsystem: delegation-view-reducers
tags: [delegation, lineage, handoffs, joins, immutable]
requires:
  - phase: 29-01-known-history
    provides: Validated complete known-watermark input
provides:
  - Delegated Run lifecycle with full contract and lineage evidence
  - Ordered terminal handoff facts
  - all, any, and quorum join progress and satisfaction facts
affects: [run-status, engine-coordination, cli-inspection]
tech-stack:
  added: []
  patterns: [immutable lifecycle replacement, explanatory join derivation]
key-files:
  created:
    - src/openrund/views/_delegation.py
    - tests/views/test_delegation.py
  modified:
    - .planning/phases/29-deterministic-views-and-replay-facts/29-05-PLAN.md
key-decisions:
  - "Compute join satisfaction from child and terminal evidence while leaving join and parent lifecycle status unchanged until canonical Events say otherwise."
  - "Retain terminal handoffs even when their creation history is absent, without fabricating a delegated Run entry."
  - "Store the full typed Delegation creation payload so Authority, budgets, result constraints, input, and metadata remain exact."
patterns-established:
  - "Delegation mappings preserve first-appearance order and expose read-only mapping proxies."
  - "Join target subsets retain request order rather than set iteration order."
requirements-completed: []
coverage:
  - id: D1
    description: Delegated Run establishment and terminal handoffs preserve contracts, lineage, and outcomes
    requirement: VIEW-01
    verification:
      - kind: unit
        ref: "tests/views/test_delegation.py lifecycle and handoff cases"
        status: pass
    human_judgment: false
  - id: D2
    description: all, any, and quorum joins expose deterministic progress without parent authority
    requirement: VIEW-01
    verification:
      - kind: unit
        ref: "tests/views/test_delegation.py (5 passed)"
        status: pass
      - kind: other
        ref: "Wave 3 Views suite (34 passed), full suite (449 passed), strict mypy and Ruff"
        status: pass
    human_judgment: false
duration: 12m
completed: 2026-08-05
status: complete
---

# Phase 29 Plan 05: Delegation and Join Facts Summary

**Delegated Run lifecycles, handoffs, and join progress now replay as immutable facts without scheduling or advancing the parent Run.**

## Accomplishments

- Preserved parent/child identity, full Delegation contract and input, establishment lineage, and terminal handoff payloads.
- Added ordered all, any, and quorum join projections with completed, failed, cancelled, and pending child sets.
- Derived satisfaction independently from lifecycle status so observations cannot become a hidden scheduler.

## Task Commits

1. **Delegation lifecycle, handoffs, and join facts** — `d6e094c`

Both planned tasks share the same ordered reducer and test matrix, so they were committed atomically together.

## Deviations from Plan

- Corrected the plan's key-link pattern to the exact semantic class name, `DelegationContractCreatedPayload`.
- Historical join rows omit fields required by the stricter semantic contract. Tests add only those missing test-side fields before decoding; production decoding remains fail-closed.

## Self-Check: PASSED

- Focused Delegation tests: 5 passed.
- Wave 3 Views suite: 34 passed.
- Full suite: 449 passed.
- Strict mypy and Ruff: passed.
- Artifacts: 2/2; key links: 1/1.

---
*Phase: 29-deterministic-views-and-replay-facts*
*Completed: 2026-08-05*
