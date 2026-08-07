---
phase: 28-python-contract-kernel
plan: "07"
subsystem: ports
tags: [python, protocols, dependency-injection, typing, authority-boundary]

requires:
  - phase: 28-04-exhaustive-typed-event-catalog
    provides: Exact domain Event and root semantic values
provides:
  - Narrow async Event, Artifact, and Lease storage protocols
  - Typed model proposal and capability result transport seams
  - Synchronous Clock and generic per-kind ID factory protocols
  - Frozen runtime dependency assembly with immutable reporting values
affects: [28-08-deterministic-fakes, 30-durable-storage, 31-engine, runtime-assembly]

tech-stack:
  added: []
  patterns: [structural protocols, domain-valued ports, per-kind generic factories]

key-files:
  created:
    - src/openrund/ports/__init__.py
    - src/openrund/ports/events.py
    - src/openrund/ports/artifacts.py
    - src/openrund/ports/leases.py
    - src/openrund/ports/providers.py
    - src/openrund/ports/capabilities.py
    - src/openrund/ports/runtime.py
    - tests/ports/test_store_protocols.py
    - tests/ports/test_runtime_protocols.py
  modified: []

key-decisions:
  - "Use static structural Protocol conformance only; no runtime_checkable decoration or adapter registration is part of the semantic kernel."
  - "Keep expected-position conflicts and transport/protocol failures as infrastructure exceptions rather than legality outcomes."
  - "Aggregate required per-kind IdFactory instances in a frozen dependency value instead of exposing a broad optional-method generator."

patterns-established:
  - "I/O seams are async and domain-valued; clocks and ID allocation remain synchronous."
  - "Provider and capability ports return proposals/results only and expose no Event append, Authority grant, or legality-decision method."
  - "Port package initialization remains documentation-only, avoiding an aggregate compatibility barrel."

requirements-completed: [DX-03, DX-08]

coverage:
  - id: D1
    description: Event, Artifact, and Lease storage contracts are exact async structural protocols over frozen domain values
    requirement: DX-03
    verification:
      - kind: unit
        ref: "tests/ports/test_store_protocols.py (5 passed)"
        status: pass
      - kind: other
        ref: "strict mypy over storage ports and conformance tests"
        status: pass
    human_judgment: false
  - id: D2
    description: Provider, capability, clock, typed ID, reporter, and dependency seams preserve their precise static types without authority methods
    requirement: DX-03
    verification:
      - kind: unit
        ref: "tests/ports/test_runtime_protocols.py (6 passed)"
        status: pass
      - kind: other
        ref: "strict mypy and Ruff over all ports and tests"
        status: pass
    human_judgment: false
  - id: D3
    description: Infrastructure concurrency remains exceptional while legality results do not enter any port contract
    requirement: DX-08
    verification:
      - kind: unit
        ref: "tests/ports/test_store_protocols.py#test_expected_position_conflict_remains_infrastructure_failure"
        status: pass
      - kind: integration
        ref: "Full Python suite (373 passed)"
        status: pass
    human_judgment: false

duration: 13m
completed: 2026-08-05
status: complete
---

# Phase 28 Plan 07: Structural Port Layer Summary

**OpenRund now exposes small typed injection seams for storage, providers, capabilities, time, identity, and reporting without leaking authority or implementation behavior.**

## Performance

- **Duration:** 13m
- **Completed:** 2026-08-05
- **Tasks:** 2
- **Files created:** 9

## Accomplishments

- Added frozen Event slice/append, Artifact blob, and Lease acquire/renew values plus narrow async storage protocols.
- Added typed model request/proposal and capability invocation/result seams that cannot create Commands or Events.
- Added synchronous clock and covariant typed ID factories, immutable report entries, and one frozen dependency assembly.
- Proved structural conformance under strict mypy without runtime protocol weakening.

## Task Commits

1. **Task 1: Domain-typed storage ports** — `e673ad6`
2. **Task 2: Runtime injection ports** — `75c00dc`

## Files Created

- `src/openrund/ports/events.py` — Event slice/append values and EventStore.
- `src/openrund/ports/artifacts.py` — immutable ArtifactBlob and ArtifactStore.
- `src/openrund/ports/leases.py` — Lease acquire/renew inputs and LeaseStore.
- `src/openrund/ports/providers.py` — ModelRequest, ModelProposal, and ModelProvider.
- `src/openrund/ports/capabilities.py` — CapabilityInvocation and CapabilityTransport.
- `src/openrund/ports/runtime.py` — Clock, IdFactory, ReportEntry, Reporter, and RuntimeDependencies.
- `src/openrund/ports/__init__.py` — narrow package documentation only.
- `tests/ports/test_store_protocols.py` — storage value and structural conformance tests.
- `tests/ports/test_runtime_protocols.py` — runtime dependency and authority-fence tests.

## Decisions Made

- Require immutable `bytes` for Artifact blobs so mutable buffers never cross the storage contract.
- Keep lease coordination input explicit with Run, owner, TTL, and canonical time while leaving token/custody mechanics to the durable adapter phase.
- Include every kind-safe ID factory as a required typed dependency; no optional mega-generator surface is retained.
- Validate proposal/invocation/report values at construction while checking protocol conformance statically.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Plan Wiring] Added exact key-link verification patterns**

- **Found during:** Plan closeout verification
- **Issue:** Descriptive links lacked the import patterns required for mechanical verification.
- **Fix:** Added exact Event-contract and runtime-port import patterns.
- **Files modified:** `28-07-PLAN.md`
- **Verification:** Both key links pass.
- **Committed in:** Plan metadata commit

---

**Total deviations:** 1 planning-metadata correction. **Impact:** No product or architecture change.

## Issues Encountered

- The test environment intentionally has no async pytest plugin; async port behavior tests use `asyncio.run` and retain deterministic standard-library-only execution.
- The sandbox initially denied uv cache access during the build; the approved build command succeeded unchanged with cache access.

## User Setup Required

None.

## Next Phase Readiness

- Plan 28-08 can implement private deterministic fakes directly against these protocols.
- Later Engine and storage phases can inject precise dependencies without changing the semantic kernel.
- No port exposes authoritative Event fabrication, legality decisions, policy grants, or concrete persistence behavior.

## Self-Check: PASSED

- All nine planned files exist.
- Both task commits are present.
- Port suite: 11 passed.
- Full Python suite: 373 passed.
- Strict mypy and Ruff pass across all ports and their tests.
- Wheel and source distribution build successfully.
- All plan artifacts and key links verify.

---
*Phase: 28-python-contract-kernel*
*Completed: 2026-08-05*
