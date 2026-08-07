---
phase: 27-frozen-compatibility-oracle
plan: "03"
subsystem: compatibility
tags: [typescript, determinism, git-provenance, runtime-events, vitest]

requires:
  - phase: 27-02-sqlite-event-command-linkage
    provides: Lossless Event command linkage and raw-versus-decoded compatibility evidence
  - phase: 27-07-decision-ledger
    provides: Frozen semantic decisions and oracle-affecting source inventory context
provides:
  - Fresh-root deterministic oracle generator shell with fixed clocks and ordered IDs for every runtime identity kind
  - Git-derived promotion provenance that rejects protected worktree drift and verifies later committed-tree equality
  - Generic Engine, Action, and reconciliation identity injection with unchanged live fallbacks and exact Event links
affects: [27-04-scenario-generation, 27-05-sqlite-corpus, 27-06-oracle-verification, 27-09-python-parity]

tech-stack:
  added: []
  patterns: [pre-execution entropy injection, protected-path Git provenance, fresh-root write boundary]

key-files:
  created:
    - scripts/compatibility/generate-v1-oracle.ts
    - tests/compatibility/oracle-regeneration.test.ts
  modified:
    - packages/runtime/src/contracts.ts
    - packages/runtime/src/runtime-engine.ts
    - packages/runtime/src/action-dispatcher.ts
    - packages/runtime/src/action-lifecycle.ts
    - packages/runtime/src/action-reconciliation-control.ts
    - tests/runtime/action-lifecycle.test.ts
    - tests/runtime/action-reconciliation.test.ts

key-decisions:
  - "Promotion provenance captures clean HEAD internally and later verifies protected committed-tree equality instead of requiring HEAD identity."
  - "Every deterministic identity is supplied before Event creation through generic optional dependencies; production callers retain live random defaults."
  - "Reconciled result Event envelopes carry the same injected commandID as their payload and command record links."

patterns-established:
  - "Oracle writes: require an explicit fresh root, reject symlinks/non-empty/corpus/home targets, and never clean or overwrite paths."
  - "Runtime determinism: inject IDs and clocks at construction boundaries rather than scrubbing serialized evidence afterward."
  - "Promotion provenance: validate protected tracked and untracked inputs before writes, then verify source commits through path-scoped committed trees."

requirements-completed: [SEM-02]

coverage:
  - id: D1
    description: Fixed entropy and fresh output contracts produce path-independent bytes in distinct roots without overwriting or home traversal
    requirement: SEM-02
    verification:
      - kind: integration
        ref: "tests/compatibility/oracle-regeneration.test.ts#fixed entropy and fresh output"
        status: pass
    human_judgment: false
  - id: D2
    description: Promotion derives clean Git provenance internally and later accepts only matching protected committed trees
    requirement: SEM-02
    verification:
      - kind: integration
        ref: "tests/compatibility/oracle-regeneration.test.ts#Git provenance"
        status: pass
    human_judgment: false
  - id: D3
    description: Engine, Action lifecycle, and reconciliation evidence uses injected IDs with exact lawful links and unchanged defaults
    requirement: SEM-02
    verification:
      - kind: integration
        ref: "pnpm exec vitest run tests/compatibility/oracle-regeneration.test.ts tests/runtime/action-lifecycle.test.ts tests/runtime/action-reconciliation.test.ts"
        status: pass
      - kind: other
        ref: "pnpm typecheck"
        status: pass
      - kind: other
        ref: "pnpm test"
        status: pass
    human_judgment: false

duration: 16min
completed: 2026-08-04
status: complete
---

# Phase 27 Plan 03: Deterministic Oracle Generator Shell Summary

**A fresh-root oracle shell now derives trusted Git provenance and creates byte-identical Engine, Action, and reconciliation evidence from fixed pre-execution entropy.**

## Performance

- **Duration:** 16 min
- **Started:** 2026-08-04T18:43:13Z
- **Completed:** 2026-08-04T18:59:15Z
- **Tasks:** 2
- **Files modified:** 9

## Accomplishments

- Added an explicit fresh-root generator boundary that rejects committed corpus, home, symlink, non-empty, and out-of-root targets without deleting or overwriting data.
- Added fixed millisecond clocks and ordered IDs for Event, Message, Artifact, Run, Checkpoint, Annotation, Command, and Wait identities, producing identical evidence across different roots.
- Established promotion provenance from the clean pre-promotion Git commit, rejecting protected tracked/untracked drift while allowing unrelated dirt and later corpus-only commits.
- Threaded generic ID dependencies through Engine, ActionDispatcher, Action lifecycle, and reconciliation paths while preserving Engine authority and existing live defaults.
- Preserved exact causation, correlation, command, Wait, unknown, reconciliation, aggregate wait, and resume links in deterministic evidence.

## TDD Cycle

- **Task 1 RED:** Eight generator contracts failed because the deterministic oracle module did not exist.
- **Task 1 GREEN:** The fresh-root generator, fixed entropy, protected source inventory, and Git provenance checks made all eight contracts pass and kept typecheck clean.
- **Task 2 RED:** Three focused contracts exposed missing Action/reconciliation ID seams and root-dependent Engine bytes.
- **Task 2 GREEN:** Generic dependency threading made all 22 focused tests pass; typecheck passed and the full suite passed 285 tests with 2 intentional skips.
- **REFACTOR:** No separate refactor commit was needed; the dependency pass-through and fallback helpers were finalized within each GREEN commit.

## Task Commits

Each TDD gate was committed atomically:

1. **Task 1 RED: failing oracle generator contracts** - `bf8422e` (test)
2. **Task 1 GREEN: deterministic oracle shell and provenance** - `18a15ed` (feat)
3. **Task 2 RED: failing runtime identity injection contracts** - `5ab03e2` (test)
4. **Task 2 GREEN: Engine and Action identity injection** - `5aac578` (feat)

## Files Created/Modified

- `scripts/compatibility/generate-v1-oracle.ts` - Defines fixed entropy, explicit protected source paths, Git provenance checks, and fresh-root generation guards.
- `tests/compatibility/oracle-regeneration.test.ts` - Covers fixed entropy, two-root equality, safe writes, forged revisions, dirty promotion, and committed-tree verification.
- `packages/runtime/src/contracts.ts` - Extends the generic runtime ID dependency contract to every oracle identity kind.
- `packages/runtime/src/runtime-engine.ts` - Selects injected Command, Event, Message, Wait, target, and reconciliation identities before evidence creation.
- `packages/runtime/src/action-dispatcher.ts` - Passes the generic ID dependency from Engine into every Action lifecycle factory.
- `packages/runtime/src/action-lifecycle.ts` - Accepts optional event-ID dependencies while retaining random defaults.
- `packages/runtime/src/action-reconciliation-control.ts` - Applies injected identities to unknown/reconciled and aggregate wait/resume evidence.
- `tests/runtime/action-lifecycle.test.ts` - Proves deterministic Action lifecycle identity and link behavior.
- `tests/runtime/action-reconciliation.test.ts` - Proves deterministic reconciliation, aggregate Wait, and exact command linkage.

## Decisions Made

- Captured promotion `sourceRevision` internally from clean `HEAD^{commit}` and prohibited caller-supplied revision text.
- Compared the protected committed source tree against `sourceRevision` during later verification, allowing HEAD to advance for corpus-only or unrelated commits.
- Kept deterministic seams generic and optional, with existing random/live fallbacks and no oracle-specific runtime export, global, or environment switch.
- Applied injected reconciliation command IDs to both payload links and result Event envelopes so the persisted causal record remains exact.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing Critical Functionality] Added ActionDispatcher identity dependency pass-through**

- **Found during:** Task 27-03-02
- **Issue:** The plan named Engine and lifecycle factories but Engine reaches those factories through `ActionDispatcher`; without an internal pass-through, injected identities could not cover normal Action execution.
- **Fix:** Added an optional generic `ids` dependency to dispatcher options and forwarded it to every lifecycle factory without changing serialized action input or public oracle APIs.
- **Files modified:** `packages/runtime/src/action-dispatcher.ts`
- **Commit:** `5aac578`

**2. [Rule 1 - Bug] Restored exact reconciliation command linkage on result Event envelopes**

- **Found during:** Task 27-03-02 GREEN verification
- **Issue:** Direct reconciliation applied the injected Command ID to payload and command records but omitted it from returned result Event envelopes.
- **Fix:** Propagated the same injected commandID onto every reconciled result Event envelope and asserted exact linkage.
- **Files modified:** `packages/runtime/src/runtime-engine.ts`, `tests/runtime/action-reconciliation.test.ts`
- **Commit:** `5aac578`

## Issues Encountered

None beyond the auto-fixed implementation gaps above.

## Known Stubs

None. Empty dependency defaults preserve production fallbacks, and the internal action-event array is populated by the Engine execution flow rather than serving as placeholder data.

## User Setup Required

None - no external service configuration or new dependency is required.

## Next Phase Readiness

- Plan 27-04 can build frozen scenario generation on a deterministic, path-independent Engine and Action substrate.
- Later promotion and verification plans can rely on internally derived source commits and the explicit oracle-affecting path inventory.
- No unresolved implementation, provenance, security, or verification blocker remains.

## Self-Check: PASSED

- All nine implementation and test artifacts plus this SUMMARY exist on disk.
- Task commits `bf8422e`, `18a15ed`, `5ab03e2`, and `5aac578` exist in RED-before-GREEN order.
- Focused tests pass 22/22, typecheck passes, the full suite passes 285 tests with 2 intentional skips, and no temporary-root or copied-home output remains.

---
*Phase: 27-frozen-compatibility-oracle*
*Completed: 2026-08-04*
