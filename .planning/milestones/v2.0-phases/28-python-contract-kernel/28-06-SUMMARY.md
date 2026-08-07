---
phase: 28-python-contract-kernel
plan: "06"
subsystem: codec
tags: [python, encoding, canonical-json, unicode, compatibility-corpus]

requires:
  - phase: 28-05-strict-v1-decode-boundary
    provides: Exact typed v1 Events, decision records, aliases, and bounded JSON values
provides:
  - Exact compact v1 JSONL renderer with ECMAScript-compatible number spelling
  - Canonical Event and writer-eligible CommandDecisionRecord encoders
  - UTF-16-code-unit canonical JSON preimages matching frozen semantic hashes
affects: [28-09-corpus-matrix, bundles, event-storage, integrity-hashing]

tech-stack:
  added: []
  patterns: [explicit ordered encoding, writer eligibility, canonical UTF-16 ordering]

key-files:
  created:
    - tests/codec/test_v1_encode.py
    - tests/codec/test_v1_events.py
    - tests/codec/test_canonical_json.py
  modified:
    - src/openrund/codec/__init__.py
    - src/openrund/codec/_json.py
    - src/openrund/codec/_decisions.py
    - src/openrund/codec/_events.py

key-decisions:
  - "Render scalar and container values through a dedicated exact encoder rather than stdlib generic object dumping."
  - "Omit only semantic MISSING and canonical default-empty fields; preserve null, falsey values, required empty arrays, and explicit payload order."
  - "Reject historical payloads and superseded declaration evidence at writer entry points with stable codes."

patterns-established:
  - "Event envelopes place optional causal/correlation/Command links before payload exactly as v1 evidence records them."
  - "Canonical hashing recursively sorts object keys by UTF-16 code units, preserves arrays/code points, and emits no LF."
  - "Standalone decision writers emit no reason and share a single writer-eligibility guard with command.recorded."

requirements-completed: [SEM-01, DX-01]

coverage:
  - id: D1
    description: Exact JSONL scalar, number, decision, presence, and final-LF bytes match frozen v1 evidence
    requirement: DX-01
    verification:
      - kind: integration
        ref: "tests/codec/test_v1_encode.py"
        status: pass
      - kind: other
        ref: "strict mypy and Ruff over codec and codec tests"
        status: pass
    human_judgment: false
  - id: D2
    description: All 63 writer-eligible Events round-trip byte-identically while two legacy variants and superseded evidence fail closed
    requirement: SEM-01
    verification:
      - kind: integration
        ref: "tests/codec/test_v1_events.py"
        status: pass
      - kind: integration
        ref: "Full Python suite (390 passed)"
        status: pass
    human_judgment: false
  - id: D3
    description: Every Phase 28 semantic commitment hashes identically under recursive UTF-16 ordering without Unicode normalization
    requirement: DX-01
    verification:
      - kind: integration
        ref: "tests/codec/test_canonical_json.py (5 passed)"
        status: pass
      - kind: other
        ref: "verify artifacts and verify key-links for 28-06-PLAN.md"
        status: pass
    human_judgment: false

duration: 18m
completed: 2026-08-05
status: complete
---

# Phase 28 Plan 06: Exact v1 Encoding and Canonical Hashing Summary

**Typed Python Events and decision records now serialize to exact v1 JSONL bytes, and canonical semantic preimages reproduce every scoped frozen SHA-256 commitment.**

## Performance

- **Duration:** 18m
- **Completed:** 2026-08-05
- **Tasks:** 2
- **Files created:** 3
- **Files modified:** 4

## Accomplishments

- Added exact UTF-8 string, boolean, null, safe integer, binary64, array, and insertion-ordered object rendering with one final LF.
- Added Event and lossless decision encoders with explicit alias/order/presence policy and mechanical legacy/declaration-only writer guards.
- Added recursive canonical JSON rendering with UTF-16 key ordering, no LF, and no Unicode normalization.
- Proved all scoped Event bytes and every Phase 28 semantic hash against authenticated frozen evidence.

## Task Commits

1. **Task 1: Exact JSONL, decision, and Event encoding** — `1a6704f`
2. **Task 2: Canonical preimage and hash verification** — `dc10cc3`

## Files Created

- `tests/codec/test_v1_encode.py` — exact wire, number, decision, falsey, and writer-policy vectors.
- `tests/codec/test_v1_events.py` — complete writer-eligible Event byte identity and legacy rejection matrix.
- `tests/codec/test_canonical_json.py` — frozen semantic hashes and Unicode/order vectors.

## Files Modified

- `src/openrund/codec/_json.py` — exact scalar/container rendering and canonical preimages.
- `src/openrund/codec/_decisions.py` — semantic-to-JSON mapping and standalone decision writer.
- `src/openrund/codec/_events.py` — canonical Event and command.recorded writer.
- `src/openrund/codec/__init__.py` — complete narrow codec API exports.

## Decisions Made

- Use shortest Python binary64 spelling as the base, expand fixed notation in the v1 magnitude interval, and normalize exponent notation outside it.
- Distinguish unsafe integer and bigint rejection classifications while permitting the frozen 1e20 canonical semantic preimage.
- Preserve the canonical Event factory order explicitly, including Wait discriminator position and RunResult version-before-kind order.
- Canonicalize keys with raw UTF-16 code units rather than Python code-point order or locale-dependent sorting.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Plan Wiring] Corrected golden-test dependency direction and added link patterns**

- **Found during:** Plan closeout verification
- **Issue:** The planned hash link pointed from production rendering code directly to test fixtures and all links lacked verifier patterns.
- **Fix:** Pointed frozen hash verification from the canonical test and added exact import/hash patterns.
- **Files modified:** `28-06-PLAN.md`
- **Verification:** All three key links pass.
- **Committed in:** Plan metadata commit

---

**Total deviations:** 1 planning-link correction. **Impact:** No product or architecture change.

## Issues Encountered

- Semantic dataclass field order intentionally differs from canonical wire order in several payloads; the encoder now applies explicit v1 order without exposing aliases on the semantic classes.

## User Setup Required

None.

## Next Phase Readiness

- The final corpus matrix can now prove decode/encode/hash closure without predecessor execution.
- Durable Event storage and Bundle integrity code can consume the same exact codec boundary later.
- No generic dump API or serialized mapping has been added to semantic values.

## Self-Check: PASSED

- All seven planned files exist.
- Both task commits are present.
- Focused encoding/hash suite: 17 passed.
- Complete codec suite: 63 passed.
- Full Python suite: 390 passed.
- Strict mypy and Ruff pass over codec and tests.
- Wheel and source distribution build successfully.
- All plan artifacts and key links verify.

---
*Phase: 28-python-contract-kernel*
*Completed: 2026-08-05*
