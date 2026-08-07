---
phase: 32-governed-coordination-and-recovery
plan: "03"
subsystem: governance
tags: [python, engine, authority, actions, approval, policy]
requires:
  - phase: 32-governed-coordination-and-recovery
    plan: "02"
    provides: Exact-once Wait lifecycle and injected Wait identity
provides:
  - Ordered fail-closed governed Action legality with durable Authority
  - Policy-only approval deferral after every hard invariant passes
  - Two-Command approval resolution and current-state Action resumption
affects: [phase-32-recovery, phase-33-actions, phase-36-cli]
tech-stack:
  added: []
  patterns: [ordered legality trace, durable authority facts, approval revalidation]
key-files:
  created:
    - tests/engine/test_approval.py
  modified:
    - src/openrund/engine/_governance.py
    - src/openrund/engine/_coordination.py
    - src/openrund/engine/_legality.py
    - src/openrund/engine/_events.py
    - src/openrund/engine/_engine.py
    - tests/engine/test_governance.py
key-decisions:
  - "Approval is a deferred Command decision only after Capability, schema, Authority, scope, lineage, budget, tenant, and security facts pass."
  - "Resolving approval records validation evidence; a separate resume Command reconstructs and revalidates the Action without dispatching it."
requirements-completed: [WAIT-02, GOV-01]
duration: 38min
completed: 2026-08-05
status: complete
---

# Phase 32 Plan 03: Governed Actions and Approval Summary

**Only currently lawful Actions can enter approval, and approval creates durable work only through a separately revalidated resume Command.**

## Accomplishments

- Added operator/system/recovery-only Capability and policy Authority grant/revoke transitions with durable replay state.
- Evaluated Action proposals in a stable fail-closed order across registration, closed schema, active Authority, resource scope, Delegation lineage, budget, tenant/security constraints, and closed policy rules.
- Materialized accepted proposals as `action.created` only and policy deferrals as one approval Wait; no transport or effect execution occurs in Phase 32.
- Validated revised approved input against the registered schema and original writable-root declaration, persisted exact proof, and revalidated all current facts before resumption.
- Preserved complete proposed input and mutation evidence across approval, including idempotent replay of accepted and deferred Commands.

## Task Commits

1. **Governed Action and approval implementation** — `af9d2c8`
2. **Approval revalidation evidence** — `1e343eb`

## Deviations from Plan

None.

## Self-Check: PASSED

- Engine plus affected View suite: 84 passed.
- Strict mypy and Ruff lint/format: passed.
- Git whitespace validation: passed.

## Next Plan Readiness

Ready to implement explicit unknown Action outcomes, reconciliation, Checks, Checkpoints, and Annotations in Plan 32-04.
