---
phase: 28-python-contract-kernel
plan: "04"
subsystem: semantic-contracts
tags: [python, events, tagged-unions, compatibility-corpus, immutability]

requires:
  - phase: 28-03-typed-ontology-and-decisions
    provides: Root concepts, IDs, content, commands, and lossless decision records
provides:
  - Exact 37-name v1 Event vocabulary and 65 unique final frozen payload classes
  - Generic immutable Event envelope with exact name/version/payload association validation
  - Explicit decode-only historical message and annotation branches distinct from canonical writer forms
affects: [28-05-codec, 28-06-encoding, 28-07-ports, 28-09-corpus-matrix]

tech-stack:
  added: []
  patterns: [manifest-bijective catalogs, typed payload associations, decode-only metadata]

key-files:
  created:
    - src/openrund/contracts/events.py
    - tests/contracts/test_event_catalog.py
  modified: []

key-decisions:
  - "Use one immutable semantic association catalog keyed by Event type, version, and frozen variant while payload classes remain the runtime discriminator."
  - "Represent every payload variant with a distinct final frozen class, including all Wait lifecycle and reconciliation branches."
  - "Mark historical content-shaped message and annotation payloads decode-only while canonical preview-shaped payloads remain writer-eligible."

patterns-established:
  - "Catalog integrity: an independent manifest-derived test proves exact 37-name and 65-variant set equality."
  - "Event admission: envelopes validate exact IDs, one-based safe positions, version 1, actor, links, and a compatible payload before construction completes."
  - "Legacy isolation: backward-read branches carry explicit decode-only catalog metadata rather than aliases or broad optional objects."

requirements-completed: [SEM-01, DX-01, DX-02]

coverage:
  - id: D1
    description: The semantic Event catalog contains exactly 37 canonical names and 65 unique payload associations matching frozen evidence
    requirement: SEM-01
    verification:
      - kind: unit
        ref: "tests/contracts/test_event_catalog.py#test_event_name_and_payload_catalog_are_manifest_bijective"
        status: pass
      - kind: other
        ref: "verify artifacts and verify key-links for 28-04-PLAN.md"
        status: pass
    human_judgment: false
  - id: D2
    description: Event construction rejects unsupported versions, unknown names, wrong payload classes, invalid positions, wrong IDs, and invalid optional links
    requirement: DX-01
    verification:
      - kind: unit
        ref: "tests/contracts/test_event_catalog.py (10 passed)"
        status: pass
      - kind: other
        ref: "mypy --strict and Ruff over events.py and catalog tests"
        status: pass
    human_judgment: false
  - id: D3
    description: All payloads are final frozen slotted annotated values and legacy read forms are mechanically distinct from canonical writers
    requirement: DX-02
    verification:
      - kind: unit
        ref: "tests/contracts/test_event_catalog.py legacy and immutability tests"
        status: pass
      - kind: integration
        ref: "Full Python suite (316 passed)"
        status: pass
    human_judgment: false

duration: 11m
completed: 2026-08-05
status: complete
---

# Phase 28 Plan 04: Exhaustive Typed Event Catalog Summary

**The Python semantic kernel now has a complete immutable v1 Event grammar: 37 names, 65 exact payload variants, and constructor-enforced associations.**

## Performance

- **Duration:** 11m
- **Completed:** 2026-08-05T11:53:00Z
- **Tasks:** 1
- **Files created:** 2

## Accomplishments

- Added the complete Event vocabulary, exact payload classes, and immutable semantic association catalog.
- Added a generic frozen Event envelope that rejects invalid IDs, versions, positions, actors, links, and payload associations before returning a value.
- Added independent manifest-bijective tests plus explicit canonical/decode-only message and annotation distinctions.

## Task Commit

1. **Task 1: Exhaustive Event and payload catalog** — `0d5e6c3`

## Files Created

- `src/openrund/contracts/events.py` — Event actors/types, 65 payload classes, association metadata, and generic Event envelope.
- `tests/contracts/test_event_catalog.py` — Independent frozen-manifest inventory, association, rejection, legacy, and immutability tests.

## Decisions Made

- Infer each association from the exact Event name and concrete payload class; the serialized variant label remains codec metadata rather than a wire-envelope field.
- Retain frozen inventory variant labels even where their historical spelling is awkward, while class behavior and decode-only metadata follow the normative writer rules.
- Keep association metadata immutable and data-only; it performs no decoding, persistence, append, or authority work.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Plan Wiring] Pointed corpus verification at the consuming test and added exact import patterns**

- **Found during:** Plan closeout key-link verification
- **Issue:** The original semantic links pointed from production code toward the frozen manifest and omitted checkable patterns.
- **Fix:** Pointed manifest verification from the independent catalog test and added the exact root-contract import pattern.
- **Files modified:** `28-04-PLAN.md`
- **Verification:** `verify key-links 28-04-PLAN.md` passes both links.
- **Committed in:** Plan metadata commit

---

**Total deviations:** 1 auto-fixed planning-link correction. **Impact:** No product or architecture change; metadata now reflects actual dependency direction.

## Issues Encountered

None.

## User Setup Required

None.

## Next Phase Readiness

- The decoder can select exact payload classes from immutable association metadata without importing predecessor code.
- The encoder can mechanically exclude decode-only branches.
- Store and runtime ports can share one exact typed Event envelope.

## Self-Check: PASSED

- Both planned files exist.
- The task commit is present.
- Event catalog suite: 10 passed.
- Contract suite: 293 passed.
- Full Python suite: 316 passed.
- Strict mypy and Ruff pass across the complete contract kernel.
- Wheel and source distribution build successfully.

---
*Phase: 28-python-contract-kernel*
*Completed: 2026-08-05*
