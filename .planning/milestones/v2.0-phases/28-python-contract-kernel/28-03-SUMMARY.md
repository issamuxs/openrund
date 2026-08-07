---
phase: 28-python-contract-kernel
plan: "03"
subsystem: semantic-contracts
tags: [python, dataclasses, ontology, commands, decisions, utf8]

requires:
  - phase: 28-02-primitive-semantic-kernel
    provides: Kind-safe IDs, immutable JSON/presence values, timestamps, errors, and paths
provides:
  - Frozen semantic values for every canonical run concept, five precise Wait branches, Delegation, authority, contracts, content, capabilities, Bundles, and Views
  - Precise provider operation and runtime legality-decision unions with required reason and linkage invariants
  - A separate lossless CommandDecisionRecord union for all four frozen standalone evidence branches
affects: [28-04-events, 28-05-codec, 28-07-ports, 29-runtime-engine]

tech-stack:
  added: []
  patterns: [final frozen slotted values, discriminated dataclass unions, ordinary legality results]

key-files:
  created:
    - src/openrund/contracts/content.py
    - src/openrund/contracts/capabilities.py
    - src/openrund/contracts/portable.py
    - src/openrund/contracts/runs.py
    - src/openrund/contracts/commands.py
    - tests/contracts/test_leaf_concepts.py
    - tests/contracts/test_concepts.py
    - tests/contracts/test_commands.py
  modified: []

key-decisions:
  - "Represent each closed Wait, operation, runtime decision, and standalone evidence branch as its own final frozen type rather than an all-optional payload bag."
  - "Keep runtime rejected/deferred/superseded reasons mandatory while standalone evidence records deliberately preserve their reason-free frozen shapes."
  - "Keep Capability, Action, Bundle, View, and all semantic contracts inert: no I/O, execution, reduction, Event append, or authority methods."

patterns-established:
  - "Tagged unions: branch-specific dataclasses carry exact required fields and reject cross-branch construction."
  - "Legality separation: accepted, rejected, deferred, and superseded are ordinary immutable values; infrastructure failures remain exceptions."
  - "Evidence separation: wire evidence receives a distinct lossless record contract instead of weakening runtime invariants."

requirements-completed: [SEM-01, DX-02, DX-08]

coverage:
  - id: D1
    description: Canonical content, capability, Action, Bundle, View, root run, Wait, Delegation, authority, and contract values are exact, deeply immutable, and inert
    requirement: SEM-01
    verification:
      - kind: unit
        ref: "tests/contracts/test_leaf_concepts.py and tests/contracts/test_concepts.py (28 passed)"
        status: pass
      - kind: other
        ref: "mypy --strict and Ruff over the complete contracts package"
        status: pass
    human_judgment: false
  - id: D2
    description: Content preserves exact code points and UTF-8 byte counts without normalization
    requirement: DX-02
    verification:
      - kind: unit
        ref: "tests/contracts/test_leaf_concepts.py (21 passed)"
        status: pass
    human_judgment: false
  - id: D3
    description: Runtime decisions retain required reasons and links while four standalone evidence branches preserve exact frozen fields without invented reasons
    requirement: DX-08
    verification:
      - kind: unit
        ref: "tests/contracts/test_commands.py against tests/fixtures/compatibility/v1/manifest.json"
        status: pass
      - kind: integration
        ref: "Full Python suite (306 passed)"
        status: pass
    human_judgment: false

duration: 39m
completed: 2026-08-05
status: complete
---

# Phase 28 Plan 03: Typed Ontology and Command Decisions Summary

**OpenRund now has one immutable Python ontology for run concepts and operations, with runtime legality outcomes cleanly separated from lossless frozen evidence records.**

## Performance

- **Duration:** 39m
- **Completed:** 2026-08-05T11:42:00Z
- **Tasks:** 2
- **Files created:** 8

## Accomplishments

- Added exact Content, result, mutation, capability, Action, Bundle, and View values with recursive immutability and strict UTF-8 behavior.
- Added all canonical root concepts, five precise Wait variants, Delegation contracts/join semantics, Authority, Lease, and completion requirements.
- Added precise provider operations and four runtime CommandDecision branches that return normally and retain required reasons and links.
- Added an independent CommandDecisionRecord union matching accepted, rejected, deferred, and declaration-only superseded evidence without fabricating runtime reasons.

## Task Commits

1. **Task 1: Leaf content, capability, and portable values** — `51fe933`
2. **Task 2: Root concepts, operations, and decision records** — `5b97007`

## Files Created

- `src/openrund/contracts/content.py` — Content, mutation, effects, evidence, and Run results.
- `src/openrund/contracts/capabilities.py` — Inert Capability, Action proposal, and result values.
- `src/openrund/contracts/portable.py` — Inert Bundle and View envelopes.
- `src/openrund/contracts/runs.py` — Canonical root run concepts, Waits, Delegation, authority, and contracts.
- `src/openrund/contracts/commands.py` — Operations, runtime decisions, and standalone decision records.
- `tests/contracts/test_leaf_concepts.py` — Exact UTF-8 and inert leaf-value contracts.
- `tests/contracts/test_concepts.py` — Root inventory, IDs, branch, and cross-field contracts.
- `tests/contracts/test_commands.py` — Operations, runtime decisions, and all frozen evidence branches.

## Decisions Made

- Preserve exact standalone evidence by modeling it separately; no implicit record-to-runtime conversion exists.
- Require exact ID wrapper classes and enum/literal discriminators at every constructor boundary.
- Keep semantic types data-only so later Engine and adapter layers remain the only places where authority or effects can occur.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Plan Wiring] Corrected conceptual key-link directions and patterns**

- **Found during:** Plan closeout verification
- **Issue:** The original links described semantic relationships but pointed from production modules toward tests/fixtures or omitted a checkable import pattern.
- **Fix:** Added exact import patterns and pointed behavioral evidence links from the tests that actually consume Content and the frozen manifest.
- **Files modified:** `28-03-PLAN.md`
- **Verification:** `verify key-links 28-03-PLAN.md` passes all four links.
- **Committed in:** Plan metadata commit

---

**Total deviations:** 1 auto-fixed planning-link correction. **Impact:** No architecture or runtime scope change; verification metadata now reflects actual dependency direction.

## Issues Encountered

- The earlier sequential executor did not complete within bounded retries, so this plan was recovered and executed inline in two atomic units.
- Restricted test runs could not use the external uv cache needed by installed-package subprocess tests; the full suite was rerun with the approved cache access.

## User Setup Required

None.

## Next Phase Readiness

- Event catalog types can now compose exact root values and identifiers without importing wire aliases.
- Codec work has distinct runtime and standalone command-decision contracts to preserve invariants in both directions.
- Port protocols can depend on stable immutable domain values without acquiring authority behavior.

## Self-Check: PASSED

- All eight planned source/test files exist.
- Both task commits are present.
- Contract suite: 283 passed.
- Full Python suite: 306 passed.
- Strict mypy and Ruff pass across the complete contract kernel.
- Wheel and source distribution build successfully.

---
*Phase: 28-python-contract-kernel*
*Completed: 2026-08-05*
