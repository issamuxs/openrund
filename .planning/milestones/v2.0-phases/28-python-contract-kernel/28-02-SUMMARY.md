---
phase: 28-python-contract-kernel
plan: "02"
subsystem: semantic-contracts
tags: [python, dataclasses, immutable-values, identifiers, paths, rfc3339]

requires:
  - phase: 28-01-python-package-and-corpus-boundary
    provides: Locked Python 3.12 package, strict tooling, and authenticated frozen evidence
provides:
  - Seventeen runtime-distinct immutable identifier classes and a safe semantic exception hierarchy
  - Deeply immutable ordered JSON values with exact omission/null/value semantics and canonical timestamps
  - Separate local PathLike normalization and exact relative portable-path validation
affects: [28-03-concepts, 28-04-events, 28-05-codec, 28-07-ports]

tech-stack:
  added: []
  patterns: [final frozen slotted values, validation-before-construction, lexical path separation]

key-files:
  created:
    - src/openrund/contracts/__init__.py
    - src/openrund/contracts/ids.py
    - src/openrund/contracts/json.py
    - src/openrund/contracts/time.py
    - src/openrund/errors.py
    - src/openrund/paths.py
    - tests/contracts/test_ids.py
    - tests/contracts/test_errors.py
    - tests/contracts/test_values.py
    - tests/contracts/test_paths.py
  modified:
    - .gitignore

key-decisions:
  - "Use final frozen slotted dataclass wrappers rather than aliases or NewType so every identifier remains kind-safe at runtime."
  - "Represent ordered JSON with recursively frozen tuple-backed values and one identity-only MISSING singleton; semantic types expose no serialization methods."
  - "Retain exact local path spelling beside an unresolved pathlib.Path while portable paths remain exact relative POSIX lexical values; containment belongs to later filesystem adapters."

patterns-established:
  - "Boundary validation: check runtime kinds before coercion and preserve exact string code points without normalization."
  - "Presence: MISSING is omission, None is explicit JSON null, and falsey/empty values remain present."
  - "Path safety: local ergonomics and portable wire-path constraints use distinct final runtime types."

requirements-completed: [SEM-01, DX-02, DX-05, DX-08]

coverage:
  - id: D1
    description: Seventeen immutable ID kinds and safe classifiable exceptions reject invalid input and redact sensitive detail
    requirement: SEM-01
    verification:
      - kind: unit
        ref: "tests/contracts/test_ids.py and tests/contracts/test_errors.py (194 passed)"
        status: pass
      - kind: other
        ref: "mypy --strict on errors, IDs, and focused tests"
        status: pass
    human_judgment: false
  - id: D2
    description: Ordered JSON, omission/null/value presence, exact Unicode and signed zero, and canonical UTC timestamps are deeply immutable
    requirement: DX-02
    verification:
      - kind: unit
        ref: "tests/contracts/test_values.py (23 passed)"
        status: pass
      - kind: other
        ref: "mypy --strict and Ruff on JSON/time modules"
        status: pass
    human_judgment: false
  - id: D3
    description: Local PathLike inputs and portable POSIX paths preserve exact spellings while unsafe and ambiguous inputs fail closed
    requirement: DX-05
    verification:
      - kind: unit
        ref: "tests/contracts/test_paths.py (31 passed)"
        status: pass
      - kind: other
        ref: "mypy --strict and Ruff on path contracts"
        status: pass
    human_judgment: false

duration: 1h 19m
completed: 2026-08-05
status: complete
---

# Phase 28 Plan 02: Primitive Semantic Kernel Summary

**Runtime-distinct IDs, safe semantic exceptions, immutable ordered JSON/presence values, canonical timestamps, and separate local/portable path contracts now form the dependency-free Python semantic foundation.**

## Performance

- **Duration:** 1h 19m (including stalled-executor recovery and permission waits)
- **Started:** 2026-08-05T09:44:00Z
- **Completed:** 2026-08-05T11:03:07Z
- **Tasks:** 3
- **Files modified:** 11

## Accomplishments

- Added seventeen final, frozen, runtime-distinct ID wrappers and a bounded/redacting exception hierarchy with stable codes.
- Added tuple-backed immutable JSON values, exact presence semantics, Unicode/signed-zero preservation, and strict RFC 3339 millisecond UTC timestamps.
- Added one-call PathLike normalization plus exact relative portable paths without filesystem I/O or false containment claims.

## Task Commits

1. **Task 1: Safe exceptions and kind-safe identities** — `021a24b`
2. **Task 2: Immutable JSON, presence, and timestamps** — `fd3f2a2`
3. **Task 3: Local and portable path boundaries** — `dabbaea`

Additional scoped deviation: `2f20dd4` — ignore Python bytecode and tool caches.

## Files Created/Modified

- `src/openrund/errors.py` — Stable safe exception hierarchy with bounded/redacted detail.
- `src/openrund/contracts/ids.py` — Seventeen final runtime-distinct ID wrappers and closed `RuntimeId` union.
- `src/openrund/contracts/json.py` — Deeply immutable ordered JSON values and identity-only omission marker.
- `src/openrund/contracts/time.py` — Exact UTC RFC 3339 millisecond timestamp value.
- `src/openrund/paths.py` — Distinct local and portable path values and one-call normalization.
- `tests/contracts/` — 248 focused semantic-boundary tests across the four contract modules.
- `.gitignore` — Python bytecode, virtual-environment, build, and tool-cache hygiene.

## Decisions Made

- Preserve exact caller strings at semantic boundaries and defer all wire aliases/serialization to the codec package.
- Keep local lexical path spelling and its unresolved `Path` together; require later adapters to perform root/symlink containment checks.
- Make portable paths string-only relative POSIX values so local and wire path types cannot be interchanged accidentally.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Added Python cache and build ignores**

- **Found during:** Plan-level full-suite verification
- **Issue:** Python test, type, and lint runs left bytecode/cache directories visible as untracked files, making each later autonomous wave dirty.
- **Fix:** Added standard Python bytecode, virtual-environment, build, pytest, mypy, and Ruff cache patterns to `.gitignore`.
- **Files modified:** `.gitignore`
- **Verification:** `git status --short` reports no generated Python cache paths.
- **Committed in:** `2f20dd4`

**2. [Rule 1 - Plan Wiring] Corrected a conceptual sibling-module key link**

- **Found during:** Plan closeout key-link verification
- **Issue:** The plan modeled `json.py` as directly linking to `time.py`, although both are intentionally independent semantic leaves and importing one from the other would create a false dependency.
- **Fix:** Pointed the key link at `test_values.py`, whose `Timestamp` integration coverage exercises both leaf contracts.
- **Files modified:** `28-02-PLAN.md`
- **Verification:** `verify.key-links 28-02-PLAN.md` reports both links verified.
- **Committed in:** Plan metadata commit

---

**Total deviations:** 2 auto-fixed (1 blocking workflow issue, 1 planning-link correction). **Impact:** No architecture or runtime scope change; later Python waves retain clean git state and truthful dependency metadata.

## Issues Encountered

- The first sequential executor became unresponsive before producing a commit. Its partial RED tests were preserved; after a bounded retry also stalled, execution switched inline and completed all tasks atomically.
- Restricted runs could not access the external uv cache. Focused verification used the locked workspace environment, and the full suite was rerun with the required cache permission; 271 tests passed.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Plan 28-03 can build the canonical concept ontology on validated immutable primitives.
- Codec and port plans have stable ID, JSON, time, error, and path types without importing predecessor runtime code.

## Self-Check: PASSED

- All ten planned source/test files exist.
- Four scoped commits are present for Plan 28-02.
- Focused contract suite: 248 passed.
- Full Python suite: 271 passed.
- Strict mypy and Ruff checks pass for every Plan 28-02 module and test.

---
*Phase: 28-python-contract-kernel*
*Completed: 2026-08-05*
