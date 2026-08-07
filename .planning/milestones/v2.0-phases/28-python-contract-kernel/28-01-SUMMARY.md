---
phase: 28-python-contract-kernel
plan: "01"
subsystem: python-foundation
tags: [python, uv, hatchling, pytest, mypy, ruff, pep-561, compatibility-corpus]

requires:
  - phase: 27-frozen-compatibility-oracle
    provides: source-revision-pinned v1 manifest and 286 inert evidence files with exact byte and semantic commitments
provides:
  - Locked Python 3.12+ src-layout distribution with strict pytest, mypy, and Ruff tooling
  - PEP 561 marker verified in wheel and sdist plus an isolated installed-wheel import proof
  - Read-only Phase 28 corpus selection with contained regular-file and hash-before-meaning enforcement
affects: [28-02-contract-foundations, 28-05-codec-decode, 28-06-codec-encode, 28-09-release-gates]

tech-stack:
  added: [Python 3.12, uv, Hatchling, pytest, mypy, Ruff]
  patterns: [src-layout package, dependency groups, narrow package root, authenticated inert fixtures]

key-files:
  created:
    - pyproject.toml
    - uv.lock
    - src/openrund/__init__.py
    - src/openrund/py.typed
    - tests/conftest.py
    - tests/package/test_py_typed.py
    - tests/package/test_fixture_integrity.py
  modified: []

key-decisions:
  - "Keep the openrund root to a package docstring with no public names until Phase 36 curates the installed API."
  - "Select Phase 28 corpus rows through an explicit category and rejection allowlist, excluding later subsystem and oracle-promotion evidence."
  - "Authenticate every evidence path through lexical containment, component lstat checks, regular-file enforcement, byte length, and SHA-256 before returning bytes."

patterns-established:
  - "Package proof: validate typing metadata and import hygiene from built artifacts in an isolated uv environment, not from the source tree."
  - "Corpus proof: freeze manifest rows, preserve manifest order, and expose evidence bytes only after path, file-kind, length, and digest checks pass."

requirements-completed: [DX-01, DX-02]

coverage:
  - id: D1
    description: Locked Python 3.12+ distribution builds wheel and sdist, ships one py.typed marker, and imports with a deliberately narrow root
    requirement: DX-02
    verification:
      - kind: integration
        ref: "uv lock --check && uv build && uv run --python 3.12 pytest tests/package/test_py_typed.py -q"
        status: pass
      - kind: other
        ref: "uv run --python 3.12 mypy --strict src/openrund tests && uv run ruff check src tests"
        status: pass
    human_judgment: false
  - id: D2
    description: Phase 28 receives only explicitly scoped Event, Command-decision, wire, number, field-policy, and rejection evidence through one authenticated fixture boundary
    requirement: DX-01
    verification:
      - kind: integration
        ref: "tests/package/test_fixture_integrity.py#test_phase28_selection_has_required_categories_only"
        status: pass
      - kind: integration
        ref: "tests/package/test_fixture_integrity.py#test_every_selected_entry_authenticates_before_use"
        status: pass
    human_judgment: false
  - id: D3
    description: Absolute, traversal, ambiguous, symlink, non-regular, length-mismatched, and hash-mismatched corpus entries fail closed without corpus mutation
    requirement: DX-02
    verification:
      - kind: unit
        ref: "uv run --python 3.12 pytest tests/package/test_fixture_integrity.py -q"
        status: pass
    human_judgment: false

duration: 9min
completed: 2026-08-05
status: complete
---

# Phase 28 Plan 01: Python Package and Trusted Corpus Boundary Summary

**A locked, strictly typed Python 3.12+ package now builds and imports from its wheel while Phase 28 compatibility evidence crosses one contained, regular-file, SHA-256-authenticated read-only boundary.**

## Performance

- **Duration:** 9 min
- **Started:** 2026-08-05T09:31:29Z
- **Completed:** 2026-08-05T09:41:11Z
- **Tasks:** 2
- **Files modified:** 7

## Accomplishments

- Established the root `openrund` src-layout distribution with no runtime dependencies, an exact uv lock, Hatchling builds, strict pytest/mypy/Ruff configuration, and no broad root exports.
- Proved the wheel and sdist each ship exactly one `openrund/py.typed` marker and that an isolated Python 3.12 wheel import cannot leak through the repository source path.
- Added a frozen Phase 28 manifest selection and authenticated reader covering 65 Events, four Command decisions, 18 encoding vectors, 14 number vectors, six field-policy vectors, and 19 relevant rejection records while excluding later subsystems.
- Added adversarial path, symlink, file-kind, length, hash, and mutation tests; the combined package gate passes 23 tests plus strict mypy and Ruff.

## Task Commits

Each task was committed atomically:

1. **Task 28-01-01: Create the locked typed Python package** - `af4d0a4` (chore)
2. **Task 28-01-02: Build the inert frozen-corpus fixture boundary** - `8429f09` (test)

## Files Created/Modified

- `pyproject.toml` - Python 3.12+, Hatchling, uv dependency group, pytest, mypy, Ruff, and package selection contract.
- `uv.lock` - Exact build and development dependency resolution.
- `src/openrund/__init__.py` - Deliberately narrow package root containing only its docstring.
- `src/openrund/py.typed` - PEP 561 typed-package marker.
- `tests/conftest.py` - Frozen manifest rows, scoped Phase 28 selection, and fail-closed authenticated evidence reader.
- `tests/package/test_py_typed.py` - Built wheel/sdist marker and isolated-import verification.
- `tests/package/test_fixture_integrity.py` - Corpus selection, containment, symlink, file-kind, integrity-order, read-only, and import-hygiene tests.

## Decisions Made

- Package no runtime dependency and no top-level semantic names; Phase 36 remains the sole owner of final root API curation.
- Preserve manifest order but select Phase 28 evidence through explicit categories and rejection keys, so adding a later-subsystem manifest row cannot silently expand this phase's test surface.
- Treat the manifest path as untrusted input: reject absolute, drive, NUL, backslash, empty, dot, parent, symlink, and non-regular paths before reading, then verify byte length and SHA-256 before returning evidence.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## Known Stubs

None. Empty runtime dependencies, package-root public-name assertions, and local test accumulators are intentional completed contracts rather than unwired behavior.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Plan 28-02 can add semantic errors, kind-safe IDs, immutable values, canonical time, and path boundaries on a locked strict Python foundation.
- All later Phase 28 corpus tests can consume authenticated inert bytes through the shared fixture boundary without invoking predecessor code.
- No UI, UI-SPEC, CLI, TypeScript runtime implementation, or later-phase subsystem surface was introduced.

## Self-Check: PASSED

- All seven planned package and test artifacts exist.
- Task commits `af4d0a4` and `8429f09` exist in repository history.
- `uv lock --check`, wheel/sdist build, 23 package tests, strict mypy, Ruff lint, and Ruff format checks passed.
- The committed `tests/fixtures/compatibility/v1/` tree remains unchanged.

---
*Phase: 28-python-contract-kernel*
*Completed: 2026-08-05*
