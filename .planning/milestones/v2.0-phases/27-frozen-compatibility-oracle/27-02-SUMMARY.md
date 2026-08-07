---
phase: 27-frozen-compatibility-oracle
plan: "02"
subsystem: storage
tags: [sqlite, migration, events, command-linkage, vitest]

requires:
  - phase: 27-01-contract-inventory
    provides: Resolved Event commandID, presence, position, and raw-versus-decoded compatibility decisions
provides:
  - Additive nullable run_events.command_id migration for fresh and legacy SQLite databases
  - Lossless Event commandID persistence and branded decoding across close/reopen
  - Raw SQL NULL, payload JSON byte, independent link, position, cursor, and rollback evidence
affects: [27-05-sqlite-corpus, python-sqlite-storage, phase-30-storage]

tech-stack:
  added: []
  patterns: [pragma-gated additive migration, raw-and-decoded evidence separation, nullable-link omission]

key-files:
  created: []
  modified:
    - packages/storage-sqlite/src/migrations.ts
    - packages/storage-sqlite/src/sqlite-store.ts
    - tests/storage/sqlite-store.test.ts
    - docs/storage.md

key-decisions:
  - "Place nullable command_id after payload_json in fresh schema creation so fresh and additively migrated legacy databases share column order."
  - "Decode SQL NULL link columns by omitting optional Event envelope properties; never fabricate commandID or materialize JSON null."

patterns-established:
  - "SQLite compatibility migration: inspect PRAGMA table_info before an additive ALTER TABLE so repeated opens remain idempotent."
  - "Persistence evidence: assert raw nullable columns and exact payload_json separately from adapter-decoded Event envelopes."

requirements-completed: [SEM-02]

coverage:
  - id: D1
    description: Current Event commandID persists as non-null SQLite linkage and round-trips exactly across close/reopen
    requirement: SEM-02
    verification:
      - kind: integration
        ref: "tests/storage/sqlite-store.test.ts#persists independent Event links and payload bytes across reopen"
        status: pass
    human_judgment: false
  - id: D2
    description: Legacy databases gain a nullable command_id column while existing SQL NULL decodes as commandID absence
    requirement: SEM-02
    verification:
      - kind: integration
        ref: "tests/storage/sqlite-store.test.ts#adds nullable command linkage to legacy rows without fabricating a value"
        status: pass
    human_judgment: false
  - id: D3
    description: Position, cursor, duplicate rollback, payload bytes, and causation/correlation/command independence remain intact
    requirement: SEM-02
    verification:
      - kind: integration
        ref: "pnpm exec vitest run tests/storage"
        status: pass
      - kind: other
        ref: "pnpm typecheck"
        status: pass
      - kind: other
        ref: "pnpm build"
        status: pass
    human_judgment: false

duration: 4min
completed: 2026-08-04
status: complete
---

# Phase 27 Plan 02: SQLite Event Command Linkage Summary

**Additive SQLite command linkage now preserves current Event command IDs losslessly while keeping legacy rows explicitly NULL and decoded as optional-field absence.**

## Performance

- **Duration:** 4 min
- **Started:** 2026-08-04T18:13:05Z
- **Completed:** 2026-08-04T18:17:18Z
- **Tasks:** 1
- **Files modified:** 4

## Accomplishments

- Added an idempotent nullable `run_events.command_id` migration whose fresh and legacy schema layouts converge without rewriting existing rows.
- Bound `EventEnvelope.commandID` on append and restored it with the `CommandID` brand on read, while omitting every optional link whose raw column is SQL `NULL`.
- Expanded the SQLite contract to prove exact raw payload JSON, independent causation/correlation/command links, reopen behavior, watermark/position/cursor semantics, duplicate rollback, and normative storage rules.

## TDD Cycle

- **RED:** Two new compatibility cases failed with `no such column: command_id`; the three pre-existing position/conflict behaviors stayed green.
- **GREEN:** The additive migration and adapter binding made all five focused tests pass; the broader storage slice passed 9/9, followed by clean typecheck and build gates.
- **REFACTOR:** No separate refactor commit was needed after the typed raw-row boundary and conditional optional-field decoding were finalized in GREEN.

## Task Commits

Each TDD gate was committed atomically:

1. **Task 1 RED: failing SQLite command-linkage contract** - `cb83004` (test)
2. **Task 1 GREEN: SQLite command-linkage migration and adapter** - `42d178c` (feat)

## Files Created/Modified

- `packages/storage-sqlite/src/migrations.ts` - Adds `command_id` to fresh schemas and uses `PRAGMA table_info` for idempotent legacy migration.
- `packages/storage-sqlite/src/sqlite-store.ts` - Binds, reads, brands, and conditionally exposes independent nullable Event links.
- `tests/storage/sqlite-store.test.ts` - Covers fresh/reopened command linkage, legacy SQL NULL, raw payload bytes, positions/cursors, and rollback.
- `docs/storage.md` - Defines canonical writer, legacy-read, raw/decoded, and position semantics.

## Decisions Made

- Kept `command_id` nullable and placed it after `payload_json` in the fresh schema, matching the physical order produced when legacy databases add the column.
- Treated SQL NULL as true optional-field omission for all three Event links rather than leaving own-properties whose value is `undefined`.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## Known Stubs

None. The conditional empty object spreads in row decoding implement optional-property omission and are not unwired data paths.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Later SQLite oracle generation can now freeze both non-null current command linkage and legacy SQL NULL without blessing silent data loss.
- Python storage work has explicit raw-row, decoded-envelope, and position/cursor behavior to reproduce.
- No unresolved implementation or verification blocker remains.

## Self-Check: PASSED

- All four implementation/test/documentation artifacts and this SUMMARY exist on disk.
- Task commits `cb83004` and `42d178c` exist in repository history in RED-before-GREEN order.
- Coverage metadata validates with all three deliverables automatically covered by passing evidence.

---
*Phase: 27-frozen-compatibility-oracle*
*Completed: 2026-08-04*
