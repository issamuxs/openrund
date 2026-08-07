---
phase: 32-governed-coordination-and-recovery
plan: "01"
subsystem: coordination-contracts
tags: [python, commands, governance, schema, engine]
requires:
  - phase: 31-engine-authority-and-core-run-semantics
    provides: Single authoritative Command submit path
provides:
  - Immutable Phase 32 coordination and recovery operation vocabulary
  - Trusted immutable GovernanceContext separate from Command metadata
  - Closed deterministic JSON-schema validation and exact coordination ID dependencies
affects: [phase-32-waits, phase-32-approval, phase-32-delegation, phase-33-capabilities]
tech-stack:
  added: []
  patterns: [runtime-only operations, trusted governance facts, fail-closed schema subset]
key-files:
  created:
    - src/openrund/engine/_governance.py
    - tests/engine/test_coordination_contracts.py
    - tests/engine/test_governance.py
  modified:
    - src/openrund/contracts/commands.py
    - src/openrund/engine/_model.py
    - src/openrund/engine/__init__.py
key-decisions:
  - "Keep Capability definitions, workspace roots, tenant identity, and security facts in trusted immutable Engine dependencies rather than Command metadata."
  - "Support one closed deterministic schema subset and reject unknown keywords instead of silently weakening input validation."
requirements-completed: []
duration: 18min
completed: 2026-08-05
status: complete
---

# Phase 32 Plan 01: Coordination Contracts Summary

**Every Phase 32 intent is now a typed runtime-only operation, backed by exact identity dependencies and immutable fail-closed governance facts.**

## Accomplishments

- Added validated Wait terminal, approval, Action recovery, Check, Annotation, Delegation, and Authority operation values without broadening model proposals.
- Extended Engine dependencies with typed coordination identity factories, atomic Event custody, and trusted governance context.
- Added deterministic Capability/action lookup and a closed JSON-schema validator covering object, array, scalar, required/property, enum, and bound rules.
- Kept effect execution, providers, workers, CLI, and graphical UI behavior outside the Engine foundation.

## Task Commits

1. **Coordination and governance contracts** — `8066fae`
2. **Governance context/schema evidence** — `ab80365`

## Deviations from Plan

The governance module was committed with the operation/dependency foundation because `EngineDependencies` imports its public value; its dedicated behavioral evidence remains a separate task commit.

## Self-Check: PASSED

- Engine suite: 58 passed.
- Strict mypy: 72 source/test files passed.
- Ruff: passed.

## Next Plan Readiness

Ready to implement authoritative exact-once Wait creation and terminal transitions in Plan 32-02.
