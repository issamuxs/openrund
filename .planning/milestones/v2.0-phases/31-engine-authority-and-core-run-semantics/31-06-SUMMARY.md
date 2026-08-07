---
phase: 31-engine-authority-and-core-run-semantics
plan: "06"
subsystem: engine-trust-boundary
tags: [python, engine, proposals, providers, architecture]
requires:
  - phase: 31-engine-authority-and-core-run-semantics
    provides: Core Run and model lifecycle submit authority
provides:
  - Inert ModelProposal-to-Command adaptation
  - Model proposal submission exclusively through RuntimeEngine.submit
  - Source/API hygiene gates preventing supported authority bypasses
affects: [provider-loop, capabilities, storage, assembly]
tech-stack:
  added: []
  patterns: [proposal-as-data, construct-then-submit, architecture source gates]
key-files:
  created:
    - src/openrund/engine/_proposals.py
    - tests/engine/test_proposals.py
    - tests/engine/test_hygiene.py
  modified:
    - src/openrund/engine/__init__.py
key-decisions:
  - "Expose proposal adaptation as pure construction plus an explicit submit helper; neither calls providers nor appends Events independently."
  - "Enforce the supported architecture boundary without pretending that a host cannot directly own low-level infrastructure ports."
requirements-completed: [ENG-01, ENG-02, MSG-01]
duration: 8min
completed: 2026-08-05
status: complete
---

# Phase 31 Plan 06: Proposal and Authority Boundary Summary

**Parsed model output remains inert data until it becomes a model-origin Command and passes through the same RuntimeEngine authority as every other origin.**

## Accomplishments

- Added pure ModelProposal-to-Command adaptation preserving provider, ModelCall, response, metadata, and idempotency linkage.
- Added explicit proposal submission that delegates only to `RuntimeEngine.submit`.
- Proved accepted and rejected proposals remain distinct from provider/transport/parse failure Events.
- Added public API, dependency direction, adapter append, and no-UI/CLI/effect responsibility hygiene gates.

## Task Commits

1. **Model proposal authority routing** — `6b48836`
2. **Engine authority boundary gates** — `0857a1b`

## Deviations from Plan

None.

## Self-Check: PASSED

- Complete Engine suite: 47 passed.
- Strict mypy: passed for all Engine source and tests.
- Ruff and `git diff --check`: passed.
- All ten declared Command origins produce the same durable decision path.

## Next Plan Readiness

Ready for Plan 31-07 compatibility, documentation, installed typing, and release gates.
