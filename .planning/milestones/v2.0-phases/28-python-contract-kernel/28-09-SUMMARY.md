---
phase: 28-python-contract-kernel
plan: "09"
subsystem: release-gates
tags: [python, compatibility-corpus, typing, packaging, hygiene]

requires:
  - phase: 28-01-through-08
    provides: Complete typed semantic kernel, codec boundary, ports, and deterministic substitutes
provides:
  - Exact authenticated Phase 28 corpus coverage and no-mutation gate
  - Dependency-direction, codec-confinement, scope, and API-surface gates
  - Built-wheel strict consumer typing, isolated import, annotation, and py.typed gates
affects: [phase-29-views, phase-30-storage, phase-36-public-api, release-verification]

tech-stack:
  added: []
  patterns: [installed-artifact typing, authenticated corpus bijection, AST import hygiene]

key-files:
  created:
    - tests/codec/test_phase28_corpus.py
    - tests/package/test_import_hygiene.py
    - tests/package/test_installed_typing.py
    - tests/__init__.py
  modified:
    - pyproject.toml
    - tests/package/test_fixture_integrity.py
    - .planning/phases/28-python-contract-kernel/28-09-PLAN.md
    - .planning/phases/28-python-contract-kernel/28-VALIDATION.md

key-decisions:
  - "Treat the frozen Phase 28 corpus as one authenticated exact-set contract with category counts and a before/after filesystem snapshot."
  - "Prove distribution typing against an isolated installed wheel, not the source checkout."
  - "Make src-layout discovery explicit for pytest and mypy and give the test tree one module identity."

patterns-established:
  - "Final phase gates run the documented uv command unchanged: tests, strict mypy, Ruff, lock validation, wheel, and sdist."
  - "Import hygiene is enforced structurally and forbids predecessor, later-subsystem, UI, and CLI implementation drift."

requirements-completed: [SEM-01, DX-01, DX-02, DX-03, DX-05, DX-08]

coverage:
  - id: D1
    description: Every Phase 28 frozen corpus row is authenticated, selected exactly once, exercised, and left unchanged
    requirement: SEM-01
    verification:
      - kind: integration
        ref: "tests/codec/test_phase28_corpus.py"
        status: pass
    human_judgment: false
  - id: D2
    description: Package boundaries forbid predecessor, UI, CLI, later-subsystem, and serialization-surface leakage
    requirement: DX-01
    verification:
      - kind: integration
        ref: "tests/package/test_import_hygiene.py"
        status: pass
    human_judgment: false
  - id: D3
    description: The built wheel imports in isolation, contains py.typed, and strictly type-checks a representative consumer
    requirement: DX-02
    verification:
      - kind: integration
        ref: "tests/package/test_installed_typing.py"
        status: pass
      - kind: other
        ref: "Exact full release gate: 415 tests, strict mypy, Ruff, lock, wheel, and sdist"
        status: pass
    human_judgment: false

duration: 2h31m
completed: 2026-08-05
status: complete
---

# Phase 28 Plan 09: Final Contract Kernel Gates Summary

**The greenfield Python contract kernel is sealed by authenticated corpus coverage, architecture hygiene, installed-artifact typing, and one reproducible release gate.**

## Performance

- **Duration:** 2h31m
- **Completed:** 2026-08-05
- **Tasks:** 2
- **Full suite:** 415 passed

## Accomplishments

- Proved an exact bijection over 65 Events, four Command-decision records, 18 wire cases, 14 number cases, six field-policy cases, and 19 applicable rejection cases.
- Enforced codec confinement, dependency direction, minimal package root, private test substitutes, and the absence of predecessor, UI, CLI, and later-phase implementation imports.
- Built and installed the wheel into isolated environments, then verified strict consumer typing, source-independent imports, complete annotations, and `py.typed` packaging.
- Passed the exact documented pytest, mypy, Ruff, lock, wheel, and source-distribution command.

## Task Commits

1. **Task 1: Corpus and import-boundary completeness** — `bb4e308`
2. **Task 2: Installed typing and annotation gates** — `c869e61`
3. **Final-gate reproducibility fix** — `952730c`

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Removed environment-dependent virtualenv discovery**

- Replaced `uv venv --python 3.12` with the executing Python's standard `venv` module and installed the local wheel with `uv pip --no-deps`.
- This removed a long-running interpreter-discovery path while preserving an isolated installed-artifact test.

**2. [Rule 3 - Blocking] Made the documented full gate self-contained**

- Added explicit `src` discovery for pytest and mypy, made `tests` one package, and normalized the lone bare `conftest` import.
- The exact plan command now succeeds without an ambient `PYTHONPATH`.

**3. [Rule 1 - Plan Wiring] Added exact key-link verifier patterns**

- Added truthful source patterns for corpus inventory, decision decoding, and built-wheel discovery.
- All three artifacts and all three key links verify.

---

**Total deviations:** 3 auto-fixed blockers/wiring corrections. **Impact:** Reproducibility and verification only; no runtime architecture change.

## Self-Check: PASSED

- Full pytest: 415 passed.
- Strict mypy: 53 source files passed.
- Ruff lint and format: passed.
- Lockfile validation: passed.
- Wheel and source distribution: built successfully.
- Plan artifacts: 3/3 passed.
- Plan key links: 3/3 passed.
- Frozen corpus remained unchanged.

---
*Phase: 28-python-contract-kernel*
*Completed: 2026-08-05*
