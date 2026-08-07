---
phase: 27-frozen-compatibility-oracle
plan: "01"
subsystem: compatibility
tags: [typescript, vitest, events, wire-format, golden-oracle]

requires:
  - phase: v1.3-runtime
    provides: predecessor Event factories, reducers, SQLite schema, provider normalization, Artifact storage, and Bundle behavior
provides:
  - Independent duplicate-safe inventory for the complete Event, View, provider, SQLite, Artifact, Bundle, rejection, and retirement surface
  - Machine-checked v1 ambiguity ledger with resolved writer, backward-read, declaration-only, and rejected-defect classifications
  - Event v1 payload declarations and normative wire documentation aligned to emitted and reducer-consumed shapes
affects: [27-02-oracle-harness, 27-03-event-corpus, 27-04-view-corpus, python-compatibility]

tech-stack:
  added: []
  patterns: [independent expected inventory, ledger-gated corpus promotion, named Event payload variants]

key-files:
  created:
    - scripts/compatibility/oracle-inventory.ts
    - tests/compatibility/oracle-manifest.test.ts
    - docs/archive/compatibility-v1-decisions.md
  modified:
    - packages/core/src/events.ts
    - tests/core/event-normalization.test.ts
    - docs/events.md
    - packages/views/src/checkpoint-view.ts

key-decisions:
  - "Freeze JavaScript JSON.stringify bytes without Unicode normalization; canonical hashes sort object keys but preserve arrays and string code points."
  - "Treat emitted reducer-consumed Event shapes as canonical writer forms, keeping legacy shapes only as explicit backward-read variants."
  - "Allow payload extensions only at Event/version-manifest pointers while rejecting unknown envelope and payload fields with distinct stable codes."
  - "Generate v1 evidence from fixed synthetic inputs and require clean Git-derived promotion provenance before corpus writes."

patterns-established:
  - "Independent inventory: expected keys are authored separately from future generator scenarios and checked bidirectionally."
  - "Variant identity: repeated Event types use unique type:version:variant array entries rather than overwrite-prone object keys."
  - "Ledger gate: every inventory decision reference must resolve before evidence promotion."

requirements-completed: [SEM-02]

coverage:
  - id: D1
    description: Independent exact-set compatibility inventory with duplicate detection and reducer-branch granularity
    requirement: SEM-02
    verification:
      - kind: unit
        ref: "tests/compatibility/oracle-manifest.test.ts#inventory"
        status: pass
    human_judgment: false
  - id: D2
    description: Closed v1 ambiguity ledger covering wire bytes, decoded meaning, writer policy, backward reads, and promotion provenance
    requirement: SEM-02
    verification:
      - kind: unit
        ref: "tests/compatibility/oracle-manifest.test.ts#decision ledger"
        status: pass
    human_judgment: false
  - id: D3
    description: Event v1 declarations, normalization variants, and normative wire documentation aligned with runtime emissions and reducers
    requirement: SEM-02
    verification:
      - kind: integration
        ref: "pnpm exec vitest run tests/compatibility/oracle-manifest.test.ts tests/core/event-normalization.test.ts"
        status: pass
      - kind: other
        ref: "pnpm typecheck"
        status: pass
    human_judgment: false

duration: 21min
completed: 2026-08-04
status: complete
---

# Phase 27 Plan 01: Contract Inventory and Adjudication Summary

**Independent exact-set oracle inventory, closed v1 decision ledger, and named Event payload variants now freeze the predecessor's byte and decoded-meaning contract before corpus generation.**

## Performance

- **Duration:** 21 min
- **Started:** 2026-08-04T17:42:36Z
- **Completed:** 2026-08-04T18:03:57Z
- **Tasks:** 3
- **Files modified:** 7

## Accomplishments

- Defined a duplicate-safe inventory covering all 37 Event names and material variants, four Command outcomes, nine View surfaces at branch granularity, provider/SQLite/Artifact/Bundle surfaces, rejection cases, and RET-01 through RET-10.
- Closed 22 machine-readable v1 decisions covering canonical writers, backward reads, declaration-only states, rejected predecessor defects, exact JavaScript wire bytes, safe numbers, strict fields, synthetic evidence, and Git provenance.
- Replaced overwrite-prone normalization fixtures with unique Event variant cases and aligned TypeScript payload declarations plus normative Event documentation to current factory and reducer behavior.

## Task Commits

Each task was committed atomically:

1. **Task 1 RED: failing independent inventory contract** - `911bbcd` (test)
2. **Task 1 GREEN: independent compatibility inventory** - `6d23df6` (feat)
3. **Task 2: resolved v1 ambiguity ledger** - `689d300` (docs)
4. **Task 3 RED: failing Event variant contracts** - `28bda64` (test)
5. **Task 3 GREEN: Event declarations and wire contract** - `ba4c26b` (feat)

## Files Created/Modified

- `scripts/compatibility/oracle-inventory.ts` - Independent exact expected sets, evidence requirements, variant metadata, and duplicate/mismatch assertions.
- `tests/compatibility/oracle-manifest.test.ts` - Inventory and ledger closure contracts with actionable missing/extra/duplicate diagnostics.
- `docs/archive/compatibility-v1-decisions.md` - Resolved v1 byte-and-meaning ambiguity ledger.
- `packages/core/src/events.ts` - Named canonical, backward-read, aggregate, and concrete payload declarations.
- `tests/core/event-normalization.test.ts` - Unique `type:version:variant` normalization fixtures and declaration/documentation contracts.
- `docs/events.md` - Normative envelope, presence, position, timestamp, wire encoding, number, extension, and writer rules.
- `packages/views/src/checkpoint-view.ts` - Type-safe optional legacy range fallback beside canonical flat positions.

## Decisions Made

- JavaScript `JSON.stringify` defines raw finite-number and string escaping bytes; canonical semantic hashes recursively sort keys without normalizing Unicode.
- Event envelope fields are exact and payload extensions are accepted only at manifest-allowlisted pointers for the Event name and version.
- Current emitted reducer-consumed shapes are canonical; historical content shapes remain backward-read-only and non-emitted states require explicit declaration-only justification.
- Oracle evidence is synthetic-only, and promotion must derive its source commit from a clean protected tree.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Corrected two self-test assertions in the new inventory suite**
- **Found during:** Task 1 (independent inventory GREEN)
- **Issue:** One expected numeric-case list used numeric rather than lexicographic key order, and the no-snapshot guard matched its own regular-expression literal.
- **Fix:** Aligned the exact expected order with deterministic string sorting and narrowed the guard so it checks executable update behavior without self-matching.
- **Files modified:** `tests/compatibility/oracle-manifest.test.ts`
- **Verification:** The focused inventory suite passed.
- **Committed in:** `6d23df6`

**2. [Rule 3 - Blocking] Kept legacy checkpoint range reads type-safe after declaration alignment**
- **Found during:** Task 3 (Event declarations GREEN)
- **Issue:** Making canonical flat checkpoint positions explicit exposed the reducer's untyped empty-object fallback for legacy nested ranges during full typecheck.
- **Fix:** Switched the backward-read fallback to optional chaining while preserving canonical `fromPosition`/`toPosition` precedence.
- **Files modified:** `packages/views/src/checkpoint-view.ts`
- **Verification:** `pnpm typecheck` and 11 focused runtime/View checkpoint tests passed.
- **Committed in:** `ba4c26b`

---

**Total deviations:** 2 auto-fixed (1 bug, 1 blocking issue)
**Impact on plan:** Both fixes were limited to correctness of the planned tests and backward-read compatibility; no public API, dependency, endpoint, or authority path was added.

## Issues Encountered

None beyond the auto-fixed issues above.

## Known Stubs

None. Stub-pattern matches were local initialized accumulators in tests/View reduction, not unwired behavior.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Plan 27-02 can build the deterministic oracle harness against an independently checked inventory and a closed decision ledger.
- No unresolved byte-or-meaning decision or implementation blocker remains.

## Self-Check: PASSED

- All seven created/modified implementation artifacts exist.
- Task commits `911bbcd`, `6d23df6`, `689d300`, `28bda64`, and `ba4c26b` exist in repository history.
- Focused compatibility tests passed 21/21, checkpoint regression tests passed 11/11, and `pnpm typecheck` passed.

---
*Phase: 27-frozen-compatibility-oracle*
*Completed: 2026-08-04*
