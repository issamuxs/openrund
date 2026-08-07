---
phase: 28-python-contract-kernel
plan: "05"
subsystem: codec
tags: [python, jsonl, decoding, events, compatibility-corpus, security]

requires:
  - phase: 28-04-exhaustive-typed-event-catalog
    provides: Exact Event vocabulary, payload classes, and immutable associations
provides:
  - Bounded strict JSONL parsing into immutable JSON values
  - Exact v1 Event envelope, alias, version, and payload-variant decoding
  - Lossless four-branch CommandDecisionRecord decoding shared with command.recorded
affects: [28-06-encoding, 28-09-corpus-matrix, runtime-input-boundaries]

tech-stack:
  added: []
  patterns: [fail-closed decoding, explicit alias registries, typed variant dispatch]

key-files:
  created:
    - src/openrund/codec/__init__.py
    - src/openrund/codec/_json.py
    - src/openrund/codec/_aliases.py
    - src/openrund/codec/_decisions.py
    - src/openrund/codec/_events.py
    - tests/codec/test_json_decode.py
    - tests/codec/test_v1_decode.py
    - tests/codec/test_rejections.py
  modified: []

key-decisions:
  - "Admit exactly one LF-terminated UTF-8 JSON value only after byte, depth, collection, duplicate-key, and number-safety checks."
  - "Keep all wire aliases explicit and private to the codec; semantic constructors accept snake_case typed values only."
  - "Decode standalone and command.recorded evidence through one lossless decision-record helper without constructing reason-required runtime rejection branches."

patterns-established:
  - "Parse first, validate exact key sets and discriminators second, construct semantic values last."
  - "Use stable codes and bounded pointers only; raw hostile input never enters error details."
  - "Dispatch Event payloads through the immutable type/version/variant catalog and return only exact semantic types."

requirements-completed: [SEM-01, DX-01, DX-02, DX-08]

coverage:
  - id: D1
    description: Strict JSONL parsing rejects framing, UTF-8, duplicate, number, type, byte, nesting, and collection violations before domain construction
    requirement: DX-01
    verification:
      - kind: unit
        ref: "tests/codec/test_json_decode.py (29 passed)"
        status: pass
      - kind: other
        ref: "strict mypy and Ruff over codec and codec tests"
        status: pass
    human_judgment: false
  - id: D2
    description: Every frozen Event evidence row decodes to its exact typed catalog association with exact aliases and presence semantics
    requirement: SEM-01
    verification:
      - kind: integration
        ref: "tests/codec/test_v1_decode.py#test_every_frozen_event_decodes_to_its_exact_catalog_association"
        status: pass
      - kind: other
        ref: "verify artifacts and verify key-links for 28-05-PLAN.md"
        status: pass
    human_judgment: false
  - id: D3
    description: All four standalone decisions and command.recorded linkage preserve typed evidence without fabricated runtime reasons
    requirement: DX-08
    verification:
      - kind: integration
        ref: "tests/codec/test_v1_decode.py decision and command.recorded tests"
        status: pass
      - kind: integration
        ref: "Full Python suite (362 passed)"
        status: pass
    human_judgment: false

duration: 17m
completed: 2026-08-05
status: complete
---

# Phase 28 Plan 05: Strict v1 Decode Boundary Summary

**OpenRund now has one fail-closed Python input boundary that turns bounded v1 JSONL into exact immutable Events and decision records.**

## Performance

- **Duration:** 17m
- **Completed:** 2026-08-05T12:05:51Z
- **Tasks:** 2
- **Files created:** 8

## Accomplishments

- Added exact one-frame JSONL parsing with strict UTF-8, duplicate preservation/rejection, safe-number enforcement, and explicit resource limits.
- Added exhaustive aliases and catalog-backed Event decoding that passes all 65 authenticated frozen Event cases.
- Added lossless accepted, rejected, deferred, and superseded decision decoding plus compatible command.recorded linkage.
- Added malicious-shape coverage for versions, required/unknown fields, payload allowlists, integer confusion, null/absence distinctions, and safe error detail.

## Task Commits

1. **Task 1: Bounded strict JSONL parser** — `a4bcf81`
2. **Task 2: Exact v1 Event and decision decoder** — `c890671`

## Files Created

- `src/openrund/codec/_json.py` — bounded strict JSONL tokenizer/parser boundary.
- `src/openrund/codec/_aliases.py` — exhaustive explicit envelope and payload alias metadata.
- `src/openrund/codec/_decisions.py` — typed decision registry, semantic decoding helpers, and lossless records.
- `src/openrund/codec/_events.py` — exact Event registry, variant selection, and envelope construction.
- `src/openrund/codec/__init__.py` — narrow public decode API.
- `tests/codec/test_json_decode.py` — framing, number, duplicate, bound, and immutability tests.
- `tests/codec/test_v1_decode.py` — 65-Event and four-decision authenticated corpus tests.
- `tests/codec/test_rejections.py` — exact field, version, type-confusion, null, and safe-detail rejection tests.

## Decisions Made

- Maintain a handwritten alias registry; no generic case conversion crosses the trust boundary.
- Permit arbitrary nested keys only where a semantic field is explicitly a `JsonObject` extension container.
- Treat frozen variant labels as registry metadata and select branches from their declared payload discriminators or exact structural key.
- Preserve target, rejection, Wait, and declaration evidence in `CommandDecisionRecord`; never invent the reasons required by runtime legality decisions.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Plan Wiring] Added mechanically verifiable key-link patterns**

- **Found during:** Plan closeout verification
- **Issue:** The planned links described imports but omitted the explicit patterns required by the verifier.
- **Fix:** Added exact import patterns for Event contracts, safe errors, and shared decision decoding.
- **Files modified:** `28-05-PLAN.md`
- **Verification:** All three key links pass.
- **Committed in:** Plan metadata commit

---

**Total deviations:** 1 planning-metadata correction. **Impact:** No product or architecture change.

## Issues Encountered

- A Unicode bytes literal in the initial scalar test was invalid Python source; the test now encodes the Unicode string explicitly before decoding.

## User Setup Required

None.

## Next Phase Readiness

- Plan 28-06 can add the exact encoder against one typed decoder and immutable Event catalog.
- Plan 28-09 can reuse the authenticated corpus loop for the complete Phase 28 matrix.
- The other Wave 5 plan can define ports against typed semantic values without importing codec temporaries.

## Self-Check: PASSED

- All eight planned files exist.
- Both task commits are present.
- JSON decoder suite: 29 passed.
- Codec plus contract suites: 339 passed.
- Full Python suite: 362 passed.
- Strict mypy and Ruff pass over codec and codec tests.
- Wheel and source distribution build successfully.
- All plan artifacts and key links verify.

---
*Phase: 28-python-contract-kernel*
*Completed: 2026-08-05*
