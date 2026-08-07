---
phase: quick-260807-lvk
plan: "01"
subsystem: runtime-architecture
tags: [engine, cli, filesystem, operator, typing, documentation, compatibility]
requires:
  - phase: v2.0
    provides: shipped Python authority, storage, Bundle, operator, CLI, and compatibility contracts
provides:
  - custody-free complete CLI parsing and successful help
  - one-replay Engine command attempts with cohesive immutable attempt facts
  - shared private hardened local-filesystem mechanics
  - precise typed operator success payloads with rendering-boundary serialization
  - normative authority documentation ownership and an explicit 2.x facade freeze
affects: [engine, storage, bundles, operator, cli, packaging, documentation]
tech-stack:
  added: []
  patterns:
    - immutable loaded-history and command-attempt facts
    - private OS-mechanics module with boundary-local error translation
    - generic OperatorResult with typed success payloads and adapter serialization
key-files:
  created:
    - src/openrund/_localfs.py
    - tests/test_localfs.py
  modified:
    - src/openrund/cli.py
    - src/openrund/engine/_engine.py
    - src/openrund/engine/_legality.py
    - src/openrund/operator/_model.py
    - src/openrund/operator/_render.py
    - src/openrund/operator/_service.py
    - docs/control.md
    - docs/api.md
key-decisions:
  - "Keep the exact package-root facade frozen for 2.x; contract it only through a documented major-release migration."
  - "Share low-level filesystem mechanics only; preserve domain error codes and independent trust-boundary checks in each consumer."
  - "Keep RuntimeEngine.submit(Command) unchanged and make one loaded history carry its validated replay through an attempt."
patterns-established:
  - "Parse before custody: complete CLI validation precedes LocalRuntime or SQLite construction."
  - "Typed until presentation: operator payloads remain immutable domain values until the rendering adapter converts them."
requirements-completed: [ARCH-01, ARCH-02, ARCH-03, ARCH-04, ARCH-05, ARCH-06, ARCH-07, ARCH-08]
coverage:
  - id: ARCH-01
    description: Unused RuntimeDependencies aggregate and construction-only evidence removed.
    requirement: ARCH-01
    verification:
      - kind: unit
        ref: tests/ports/test_runtime_protocols.py
        status: pass
    human_judgment: false
  - id: ARCH-02
    description: Help and invalid CLI routes complete parsing without opening runtime custody.
    requirement: ARCH-02
    verification:
      - kind: integration
        ref: tests/cli/test_commands.py#test_invalid_commands_are_fully_parsed_before_runtime_custody
        status: pass
    human_judgment: false
  - id: ARCH-03
    description: docs/control.md is the single normative authority-loop owner.
    requirement: ARCH-03
    verification:
      - kind: unit
        ref: tests/docs/test_documentation.py#test_control_has_one_normative_authority_loop_owner
        status: pass
    human_judgment: false
  - id: ARCH-04
    description: Engine attempts reuse one validated replay per loaded stream and pass cohesive attempt facts.
    requirement: ARCH-04
    verification:
      - kind: unit
        ref: tests/engine/test_engine.py#test_submit_rebuilds_each_loaded_stream_once_per_attempt
        status: pass
    human_judgment: false
  - id: ARCH-05
    description: Assembly, storage, and Bundles share hardened filesystem mechanics without merging domain policy.
    requirement: ARCH-05
    verification:
      - kind: integration
        ref: tests/test_localfs.py plus storage and Bundle adversarial suites
        status: pass
    human_judgment: false
  - id: ARCH-06
    description: Operator successes expose precise immutable payloads and render through one adapter.
    requirement: ARCH-06
    verification:
      - kind: integration
        ref: tests/operator, tests/cli, tests/demo, and tests/package/test_installed_typing.py
        status: pass
    human_judgment: false
  - id: ARCH-07
    description: The exact root facade remains frozen for 2.x and advanced types live in named subpackages.
    requirement: ARCH-07
    verification:
      - kind: unit
        ref: tests/package/test_public_api.py
        status: pass
    human_judgment: false
  - id: ARCH-08
    description: Test extra and development dependency group are locked to exact ordered parity.
    requirement: ARCH-08
    verification:
      - kind: unit
        ref: tests/package/test_py_typed.py#test_project_metadata_locks_python_and_tooling_contract
        status: pass
    human_judgment: false
duration: 4h 3m
completed: 2026-08-07
status: complete
---

# Quick Task 260807-lvk: Architecture Improvements Summary

**Authority, custody, typed operator, documentation, and release seams are deeper while all public wire and 2.x import contracts remain compatible.**

## Performance

- **Duration:** 4h 3m
- **Started:** 2026-08-07T13:45:05Z
- **Completed:** 2026-08-07T17:48:12Z
- **Tasks:** 3
- **Files modified:** 32

## Accomplishments

- Complete CLI syntax, JSON, enum, mapping, and option validation now precedes runtime/SQLite custody; help is successful and side-effect free.
- Engine history loading now validates and rebuilds each stream once per attempt, with immutable attempt facts replacing a long production keyword list.
- One private filesystem module owns lstat/no-follow/exclusive-write/bounded-read/fsync mechanics while assembly, storage, and Bundles retain their own security policy and errors.
- Every operator service success advertises a precise frozen payload type; the demo and tests use typed attributes, and rendering alone creates ordered JSON/text.
- Authority documentation has one owner, the 2.x root facade is mechanically frozen, and contributor dependency surfaces cannot drift.

## Task Commits

1. **Task 1: Dead aggregate, parse-before-custody, documentation ownership** - `2c720e9`
2. **Task 2: Engine command attempts and hardened filesystem mechanics** - `58ab89d`
3. **Task 3: Typed operator results, facade policy, dependency parity** - `1e90519`

## Verification

- Python 3.12: 991 passed, 3 expected skips.
- Python 3.13: 991 passed, 3 expected skips.
- Python 3.14: 991 passed, 3 expected skips.
- Coverage: 79%, meeting the release floor.
- Strict mypy: 229 files.
- Ruff lint/format: 230 files.
- `uv lock --check`, wheel/sdist build, installed typing, compatibility allowlist, and `git diff --check`: passed.

## Decisions Made

- Preserved all 94 root exports for the 2.x line. Named subpackages are the preferred advanced surface; contraction is explicitly a major-release decision.
- Kept `evaluate_command` pure and available for focused algorithm tests while production now supplies a single `CommandAttemptFacts` value.
- Kept Bundle and Artifact verification repeated where bytes cross distinct trust boundaries; only OS mechanics were centralized.
- Retained backwards-compatible dictionary construction for direct `OperatorResult.success` callers while production services return precise typed payloads.

## Deviations from Plan

- The GSD executor role stalled twice without producing changes or commits. Both runs were interrupted after checkpoints failed; audits confirmed a clean repository, and the approved three-task plan was executed directly with the same atomic commit boundaries.
- Python 3.13 and 3.14 were initially launched concurrently and raced over the shared `.venv`. Python 3.13 was rerun sequentially and passed; this caused no source change.
- `bundles/_importing.py` required no direct edit because it already consumes the export/verification wrappers that now delegate to the shared primitives.

## Issues Encountered

- The repository had been renamed from `openrund-py` to `openrund`, while the patch sandbox still targeted the old path. Patches were applied with the same patch helper through an approved shell rooted at the live repository.

## User Setup Required

None.

## Next Phase Readiness

- The project remains dependency-free at runtime and passes the complete release matrix.
- Future Engine or custody work can build on the deeper internal seams without changing the public mutation path.
- Root-facade contraction remains intentionally deferred to a future major release.

---
*Quick task: 260807-lvk*
*Completed: 2026-08-07*
