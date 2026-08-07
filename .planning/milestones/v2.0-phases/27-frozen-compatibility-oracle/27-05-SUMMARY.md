---
phase: 27-frozen-compatibility-oracle
plan: "05"
subsystem: compatibility-oracle
tags: [events, views, providers, sqlite, artifacts, bundles]

requires:
  - phase: 27-04-deterministic-coordination
    provides: Fixed coordination, Wait, Artifact, and Bundle inputs
  - phase: 27-03-deterministic-oracle-shell
    provides: Fresh-root safety, fixed entropy, and inventory contracts
provides:
  - Exhaustive staged Event, Command, wire, number, and field-policy evidence
  - Focused streams and generated results for every material View branch
  - Offline provider, real SQLite, Artifact-state, and Bundle-profile evidence
affects: [27-06-read-only-verification, 27-09-promotion, phase-28-python-contracts]

tech-stack:
  added: []
  patterns:
    - inventory-keyed evidence files with exact byte and semantic commitments
    - focused-stream View replay at an explicit watermark
    - synthetic-only provider mocks and fresh-root real-store generation

key-files:
  created:
    - tests/compatibility/oracle-wire.test.ts
    - tests/compatibility/oracle-views.test.ts
    - tests/compatibility/oracle-providers.test.ts
    - tests/compatibility/oracle-sqlite.test.ts
    - tests/compatibility/oracle-artifacts.test.ts
    - tests/compatibility/oracle-bundles.test.ts
  modified:
    - scripts/compatibility/generate-v1-oracle.ts

key-decisions:
  - Keep every generated record inventory-keyed and data-only, with provenance, JSON-pointer presence metadata, exact staged bytes, and separate semantic hashes.
  - Generate provider outcomes exclusively from fixed response bodies and injected fetch functions; never read credentials or make a live request.
  - Record the current Artifact overwrite behavior truthfully as a rejected defect rather than treating replacement as portable v1 behavior.

patterns-established:
  - "Evidence entry: inventory provenance plus staged bytes, byte hash, canonical semantic hash, presence pointers, and decoded meaning."
  - "View evidence: one focused Event stream per adjudicated branch, replayed through rebuildViews at its exact watermark."

requirements-completed: [SEM-02]

coverage:
  - id: D1
    description: Every Event, Command outcome, wire escape, Unicode form, number boundary, and field-policy decision has exact staged bytes and decoded evidence
    requirement: SEM-02
    verification:
      - kind: integration
        ref: "tests/compatibility/oracle-wire.test.ts#generated Event, Command, and wire evidence"
        status: pass
    human_judgment: false
  - id: D2
    description: Every material branch of all nine derived Views has an independently inventoried focused stream and exact replay result at a recorded watermark
    requirement: SEM-02
    verification:
      - kind: integration
        ref: "tests/compatibility/oracle-views.test.ts#generated View evidence"
        status: pass
    human_judgment: false
  - id: D3
    description: OpenAI, Anthropic, and local adapters have deterministic offline evidence for all ten normalized outcome and safe-failure variants
    requirement: SEM-02
    verification:
      - kind: integration
        ref: "tests/compatibility/oracle-providers.test.ts#generated provider evidence"
        status: pass
    human_judgment: false
  - id: D4
    description: Real SQLite schemas, rows, null states, payload bytes, constraints, Artifact states, and Bundle profile trees are frozen as staged evidence
    requirement: SEM-02
    verification:
      - kind: integration
        ref: "tests/compatibility/oracle-sqlite.test.ts; tests/compatibility/oracle-artifacts.test.ts; tests/compatibility/oracle-bundles.test.ts"
        status: pass
      - kind: other
        ref: "pnpm typecheck && pnpm test"
        status: pass
    human_judgment: false

duration: 12min
completed: 2026-08-04
status: complete
---

# Phase 27 Plan 05: Generated Compatibility Surface Evidence Summary

Inventory-keyed staged evidence now freezes Event wire bytes, View branch results, provider normalization, SQLite persistence, Artifact states, and complete/audit/redacted Bundle trees without writing the committed corpus.

## Performance

- **Duration:** 12 minutes
- **Started:** 2026-08-04T19:59:40Z
- **Completed:** 2026-08-04T20:12:05Z
- **Tasks:** 2
- **Files modified:** 7

## Accomplishments

- Generated exact JSONL bytes, byte hashes, canonical semantic hashes, normalized facts, ordered positions, presence pointers, provenance, and link classifications for every Event, Command, wire, number, and field-policy inventory key.
- Generated one focused Event stream for every declared branch across all nine Views and proved exact `rebuildViews` reproduction at each stream watermark.
- Generated the full 3-provider × 10-outcome matrix from fixed offline responses, including supplied/fallback IDs, dotted actions, malformed/non-object arguments, and redacted failures without live traffic.
- Interrogated real migrated SQLite databases for every table, column, index, and constraint; preserved raw SQL nulls, construction-order payload bytes, decoded absence, and stable conflict classifications.
- Persisted exact empty/ASCII/BMP/astral/composed/decomposed Artifact bytes, froze all Artifact states, exported complete/audit/redacted Bundle trees, and exercised actual zero/single/multiple Artifact boundaries.
- Proved every completed surface produces identical relative evidence paths and bytes across two fresh staging roots.

## Task Commits

Each task followed RED/GREEN TDD and was committed atomically:

1. **Task 27-05-01: Generate Event, Command, View, wire, and provider evidence**
   - `3cccf15` — failing exhaustive surface and provider contracts
   - `d29ac2f` — staged wire/View/provider evidence generators
2. **Task 27-05-02: Generate SQLite, Artifact, and Bundle evidence**
   - `ad3ec78` — failing storage, Artifact, and Bundle contracts
   - `45547de` — real-store evidence generators and profile exports
   - `8bc5980` — explicit all-surface two-fresh-root determinism gate

## Files Created/Modified

- `scripts/compatibility/generate-v1-oracle.ts` — inventory-driven evidence writer and surface generators.
- `tests/compatibility/oracle-wire.test.ts` — Event, Command, wire, number, and field-policy contracts.
- `tests/compatibility/oracle-views.test.ts` — exhaustive focused-stream branch and watermark replay contracts.
- `tests/compatibility/oracle-providers.test.ts` — offline provider matrix, safe error, and determinism contracts.
- `tests/compatibility/oracle-sqlite.test.ts` — schema, row, null/absence, payload byte, and conflict contracts.
- `tests/compatibility/oracle-artifacts.test.ts` — state matrix, exact UTF-8 bytes, and overwrite-defect contracts.
- `tests/compatibility/oracle-bundles.test.ts` — profile trees, cardinality boundaries, and all-surface repeatability contracts.

## Decisions Made

- Evidence files contain data only and are written exclusively beneath an explicit fresh staging root; Plan 27-05 does not promote or mutate `tests/fixtures/compatibility/v1/`.
- Command `superseded` and external Artifact behavior remain explicitly declaration-only where no predecessor emission path exists.
- SQLite binary files are generation inputs, not portable compatibility artifacts; the frozen contract is schema/row/decoded evidence and stable rejection behavior.
- Existing Artifact overwrite is recorded as `artifact_overwrite_not_rejected`, a rejected defect that must not be imported as lawful Python behavior.

## Deviations from Plan

None - plan executed exactly as written.

## Verification

- Six focused compatibility suites: **6 files passed; 18 tests passed**.
- Explicit two-fresh-root generation compares every completed surface path and byte hash: **passed**.
- Full repository suite: **66 files passed; 314 tests passed, 2 skipped**.
- TypeScript project references: **`pnpm typecheck` passed**.
- Transported-document evidence was not included, so `pnpm test:python-documents` was not applicable.
- TDD gates are present in order for both tasks: RED test commits followed by GREEN feature commits.

## Known Stubs

None. Empty collections and nulls in the generated records are deliberate boundary and presence-state evidence, not incomplete wiring.

## Security and Trust Boundaries

- All providers use fixed response bodies or injected fetch functions; no live endpoint, API key, environment credential, or raw secret-bearing body enters evidence.
- All SQLite, Artifact, and Bundle generation stays within caller-provided fresh roots and closes stores in `finally` blocks.
- Evidence manifests contain relative paths only, and normal generation cannot target the committed corpus or OpenRund user-home state.
- No new network endpoint, authentication path, database schema, or external trust boundary was introduced.

## Self-Check: PASSED

- All seven implementation/test files exist.
- All five task and verification commits exist in repository history.
- Focused, deterministic-regeneration, typecheck, and full-suite claims match the recorded command results.

## Next Phase Readiness

The staged compatibility surface is complete and ready for Plan 27-06 to implement read-only corpus verification, including strict rejection and integrity checks, without relying on executable fixtures.
