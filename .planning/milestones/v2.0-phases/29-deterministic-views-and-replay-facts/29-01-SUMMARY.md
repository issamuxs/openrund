---
phase: 29-deterministic-views-and-replay-facts
plan: "01"
subsystem: views-replay-boundary
tags: [python, views, replay, watermark, frozen-corpus]
requires:
  - phase: 28-python-contract-kernel
    provides: Typed RuntimeEvent, Artifact, IDs, codec, and authenticated corpus primitives
provides:
  - Typed complete/incomplete replay result contracts
  - Fail-closed exact known-watermark history validation
  - Authenticated exact 71-row View fixture harness
affects: [phase-29-reducers, engine-replay, bundle-replay]
tech-stack:
  added: []
  patterns: [known-watermark boundary, fail-closed result union, authenticated fixture bijection]
key-files:
  created:
    - src/openrund/views/__init__.py
    - src/openrund/views/_model.py
    - src/openrund/views/_history.py
    - tests/views/__init__.py
    - tests/views/conftest.py
    - tests/views/test_history.py
    - tests/views/test_fixture_integrity.py
  modified:
    - tests/package/test_import_hygiene.py
key-decisions:
  - "Return ordered safe incomplete issues with no View bundle whenever exact source completeness is unproven."
  - "Treat an empty history as complete only at watermark zero and preserve no invented Run identity."
  - "Deduplicate identical Artifact inputs but reject conflicting identity reuse before reduction."
patterns-established:
  - "All reducers receive only private KnownHistory values produced by prepare_history."
  - "View fixtures reuse the existing containment/hash boundary and add an exact 71-row surface bijection."
requirements-completed: []
coverage:
  - id: D1
    description: Unknown, invalid, gapped, duplicate, reordered, mixed-Run, and over-watermark histories fail closed
    requirement: VIEW-01
    verification:
      - kind: unit
        ref: "tests/views/test_history.py (9 passed)"
        status: pass
    human_judgment: false
  - id: D2
    description: Exactly 71 frozen View rows authenticate before semantic use and remain unchanged
    requirement: VIEW-01
    verification:
      - kind: integration
        ref: "tests/views/test_fixture_integrity.py (3 passed)"
        status: pass
      - kind: other
        ref: "Plan artifacts 3/3 and key links 2/2"
        status: pass
    human_judgment: false
duration: 5m
completed: 2026-08-05
status: complete
---

# Phase 29 Plan 01: Replay Boundary and View Corpus Summary

**Reducers now have one immutable fail-closed known-watermark input, backed by an authenticated exact inventory of all 71 frozen View cases.**

## Accomplishments

- Added precise complete/incomplete replay contracts with stable safe issue codes.
- Rejected unknown or invalid watermarks, incomplete/gapped/duplicate/reordered histories, mixed Runs, events beyond the declaration, and conflicting Artifact identities before reduction.
- Added exact per-surface View inventory, file containment, byte-length, SHA-256, semantic-shape, orphan, and no-mutation gates.
- Kept `openrund` package-root exports unchanged and evolved import hygiene to permit only the new semantic Views layer.

## Task Commits

1. **Known-watermark replay boundary** — `6a1ed88`
2. **Authenticated View corpus** — `f3e8f44`
3. **Test-package/import-hygiene integration** — `cf028d4`

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Assigned the View test tree one import identity**

- Added `tests/views/__init__.py` to prevent pytest basename collision with the package fixture-integrity test.

**2. [Rule 3 - Blocking] Advanced the Phase 28 import fence to the Phase 29 dependency graph**

- Permitted `openrund.views` as a current subsystem while adding a Views-specific ban on codec, ports, private fakes, and all later layers.

## Self-Check: PASSED

- Focused tests: 12 passed.
- Full suite: 427 passed.
- Strict mypy: 60 source files passed.
- Ruff lint/format: passed.
- Artifacts: 3/3; key links: 2/2.

---
*Phase: 29-deterministic-views-and-replay-facts*
*Completed: 2026-08-05*
