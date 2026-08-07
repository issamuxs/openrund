---
phase: 28-python-contract-kernel
plan: "08"
subsystem: testing-contracts
tags: [python, deterministic-fakes, memory-stores, testing, protocols]

requires:
  - phase: 28-07-structural-port-layer
    provides: Domain-valued structural protocols for all runtime dependencies
provides:
  - Private insertion-ordered in-memory Event, Artifact, and Lease port substitutes
  - Seeded clock and kind-preserving ID factories with deterministic exhaustion
  - Fake provider, capability transport, and recording reporter with immutable call logs
affects: [phase-tests, engine-tests, storage-contract-tests, provider-tests]

tech-stack:
  added: []
  patterns: [seeded substitution, immutable observation logs, authority-neutral fakes]

key-files:
  created:
    - src/openrund/_testing/__init__.py
    - src/openrund/_testing/memory.py
    - src/openrund/_testing/fakes.py
    - tests/ports/test_memory_stores.py
    - tests/ports/test_deterministic_fakes.py
  modified: []

key-decisions:
  - "Keep all deterministic substitutes private under openrund._testing and absent from package-root exports."
  - "Return caller-supplied domain values or explicit coordination values only; never fabricate authoritative lifecycle Events."
  - "Expose observations as newly allocated immutable tuples and classify exhaustion with stable safe errors."

patterns-established:
  - "Memory stores model observable port contracts only and explicitly make no durability, transaction, recovery, or filesystem-custody claim."
  - "Seed sequences are consumed exactly once in insertion order; exhausted or mismatched calls fail with stable non-echoing codes."
  - "Provider and capability fakes record frozen requests and return typed proposals/results without legality or Authority methods."

requirements-completed: [DX-03, DX-08]

coverage:
  - id: D1
    description: Memory Event, Artifact, and Lease stores structurally conform, preserve order, isolate blob bytes, and classify conflicts
    requirement: DX-03
    verification:
      - kind: unit
        ref: "tests/ports/test_memory_stores.py (5 passed)"
        status: pass
      - kind: other
        ref: "strict mypy over private testing implementations and port tests"
        status: pass
    human_judgment: false
  - id: D2
    description: Seeded dependency fakes preserve typed order, immutable logs, and deterministic exhaustion without authority methods
    requirement: DX-03
    verification:
      - kind: unit
        ref: "tests/ports/test_deterministic_fakes.py (6 passed)"
        status: pass
      - kind: other
        ref: "Ruff lint and format over _testing, ports, and port tests"
        status: pass
    human_judgment: false
  - id: D3
    description: Store conflicts and fake transport/protocol exhaustion retain infrastructure exception classifications
    requirement: DX-08
    verification:
      - kind: integration
        ref: "Full Python suite (401 passed)"
        status: pass
      - kind: other
        ref: "verify artifacts and verify key-links for 28-08-PLAN.md"
        status: pass
    human_judgment: false

duration: 12m
completed: 2026-08-05
status: complete
---

# Phase 28 Plan 08: Private Deterministic Contract Fakes Summary

**Every Phase 28 port now has a deterministic private substitute with exact typed results, immutable observations, and no alternate authority path.**

## Performance

- **Duration:** 12m
- **Completed:** 2026-08-05
- **Tasks:** 2
- **Files created:** 5

## Accomplishments

- Added deterministic memory Event, Artifact, and Lease stores that model only observable port behavior.
- Added seeded clocks and generic ID factories with exact order, type preservation, and safe exhaustion.
- Added fake model/capability seams and a recording reporter with copied frozen inputs and immutable tuple logs.
- Added structural, conflict, ordering, isolation, exhaustion, and authority-surface tests.

## Task Commits

1. **Task 1: Deterministic memory stores** — `1884d6d`
2. **Task 2: Seeded runtime fakes** — `904961e`

## Files Created

- `src/openrund/_testing/memory.py` — MemoryEventStore, MemoryArtifactStore, and MemoryLeaseStore.
- `src/openrund/_testing/fakes.py` — SeededClock, SeededIdFactory, FakeModelProvider, FakeCapabilityTransport, and RecordingReporter.
- `src/openrund/_testing/__init__.py` — private package documentation only.
- `tests/ports/test_memory_stores.py` — store contract, order, conflict, and no-durability tests.
- `tests/ports/test_deterministic_fakes.py` — seed, call-log, exhaustion, conformance, and authority-fence tests.

## Decisions Made

- Treat immutable semantic inputs as safe retained values and copy top-level calls/results so fake observations never alias mutable containers.
- Use deterministic private Lease IDs solely for the coordination-value contract; no lifecycle Event or authoritative history is synthesized.
- Keep provider call-ID mismatches separate from seed exhaustion and never echo request content in either error.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Plan Wiring] Added exact structural import patterns**

- **Found during:** Plan closeout verification
- **Issue:** Descriptive links to port and contract directories lacked verifier patterns.
- **Fix:** Added exact Event-port and Capability-contract import patterns.
- **Files modified:** `28-08-PLAN.md`
- **Verification:** Both key links pass.
- **Committed in:** Plan metadata commit

---

**Total deviations:** 1 planning-metadata correction. **Impact:** No product or architecture change.

## Issues Encountered

- The first sandboxed full-suite run could not let nested package tests access the uv cache; the identical approved command passed with cache access.

## User Setup Required

None.

## Next Phase Readiness

- The final Phase 28 matrix can test every port and private substitute together.
- Later subsystem tests can inject deterministic dependencies without expanding public API or weakening authority boundaries.
- No fake claims production durability, crash recovery, policy evaluation, or Event authorship.

## Self-Check: PASSED

- All five planned files exist.
- Both task commits are present.
- Memory-store suite: 5 passed.
- Deterministic-fakes suite: 6 passed.
- Full Python suite: 401 passed.
- Strict mypy and Ruff pass across `_testing`, ports, and port tests.
- All plan artifacts and key links verify.

---
*Phase: 28-python-contract-kernel*
*Completed: 2026-08-05*
