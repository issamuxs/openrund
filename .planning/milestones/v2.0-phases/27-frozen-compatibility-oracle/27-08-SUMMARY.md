---
phase: 27-frozen-compatibility-oracle
plan: "08"
subsystem: compatibility
tags: [typescript, artifacts, sqlite, determinism, utf8, sha256, vitest]

requires:
  - phase: 27-03-deterministic-oracle-shell
    provides: Generic RuntimeIdGenerator and fixed oracle entropy before evidence creation
provides:
  - Injected Artifact and Event identities allocated before materialization writes with exact storage, reference, and View linkage
  - SQLite Artifact identity dependency with unchanged random defaults and true optional-field absence
  - Fixed synthetic empty, ASCII, BMP, astral, composed, and decomposed UTF-8 byte/hash cases without normalization
  - Deterministic rejected-defect evidence for conflicting Artifact identity reuse
affects: [27-05-artifact-corpus, 27-06-oracle-verification, 27-09-corpus-promotion, python-artifact-storage, python-bundles]

tech-stack:
  added: []
  patterns: [pre-write identity injection, exact UTF-8 byte evidence, structural storage dependency]

key-files:
  created: []
  modified:
    - packages/runtime/src/artifact-materialization.ts
    - packages/storage-sqlite/src/sqlite-artifact-store.ts
    - scripts/compatibility/generate-v1-oracle.ts
    - tests/runtime/artifact-materialization.test.ts
    - tests/storage/sqlite-artifact.test.ts
    - tests/compatibility/oracle-regeneration.test.ts

key-decisions:
  - "Allocate both Artifact and artifact.created Event identities before the Artifact store writes metadata or blob bytes."
  - "Keep SQLite identity injection structural and core-typed so storage does not depend on the runtime package."
  - "Encode fixed Unicode inputs directly to UTF-8 without normalization and freeze literal byte lengths and SHA-256 values."
  - "Keep conflicting Artifact identity reuse exclusively in rejected-defect evidence rather than canonical writer scenarios."

patterns-established:
  - "Artifact materialization: one injected Artifact ID flows unchanged through metadata, blob path, Event payload, returned references, and derived Views."
  - "Encoding evidence: compare literal byte counts and hashes for composed and decomposed text rather than code-point or grapheme counts."
  - "Optional storage state: omit absent contentType, byteLength, and unavailableAt properties instead of materializing undefined/null values."

requirements-completed: [SEM-02]

coverage:
  - id: D1
    description: Injected Artifact and Event IDs propagate unchanged through materialization, SQLite storage, returned references, and Artifact Views
    requirement: SEM-02
    verification:
      - kind: integration
        ref: "tests/runtime/artifact-materialization.test.ts#uses supplied Artifact and Event IDs before storage, references, and Views"
        status: pass
      - kind: integration
        ref: "tests/storage/sqlite-artifact.test.ts#uses an injected Artifact identity before writing metadata and blob bytes"
        status: pass
    human_judgment: false
  - id: D2
    description: Empty, ASCII, BMP, astral, composed, and decomposed synthetic content preserves exact UTF-8 bytes, byte lengths, and SHA-256 without normalization
    requirement: SEM-02
    verification:
      - kind: integration
        ref: "tests/storage/sqlite-artifact.test.ts#persists exact UTF-8 byte lengths and hashes without Unicode normalization"
        status: pass
      - kind: unit
        ref: "tests/compatibility/oracle-regeneration.test.ts#exposes exact synthetic UTF-8 bytes, lengths, and hashes without Unicode normalization"
        status: pass
    human_judgment: false
  - id: D3
    description: Metadata-only, blob-backed, and unavailable states retain exact absence while conflicting identity reuse remains rejected-defect evidence
    requirement: SEM-02
    verification:
      - kind: integration
        ref: "tests/storage/sqlite-artifact.test.ts#preserves metadata-only, blob-backed, and unavailable absence states"
        status: pass
      - kind: unit
        ref: "tests/compatibility/oracle-regeneration.test.ts#keeps conflicting Artifact identity reuse as rejected-defect evidence"
        status: pass
      - kind: other
        ref: "pnpm test && pnpm typecheck"
        status: pass
    human_judgment: false

duration: 8min
completed: 2026-08-04
status: complete
---

# Phase 27 Plan 08: Deterministic Artifact Evidence Summary

**Injected pre-write Artifact identities and exact UTF-8 byte fixtures now produce reproducible metadata, blobs, Events, references, Views, and hashes without normalizing content or blessing overwrite behavior.**

## Performance

- **Duration:** 8 min
- **Started:** 2026-08-04T19:04:45Z
- **Completed:** 2026-08-04T19:12:53Z
- **Tasks:** 1
- **Files modified:** 6

## Accomplishments

- Added optional generic ID dependencies to Artifact materialization and SQLite creation, allocating identities before writes while preserving ordinary random/content-derived defaults.
- Proved one Artifact identity flows unchanged through SQLite metadata/blob paths, `artifact.created`, returned action references, and the Artifact View.
- Added fixed empty, ASCII, BMP, astral, composed, and decomposed inputs with exact UTF-8 byte lengths and literal SHA-256 commitments.
- Preserved metadata-only, blob-backed, and unavailable property absence, while retaining conflicting identity reuse only as a ledger-backed rejected defect.

## TDD Cycle

- **RED:** Four intended failures showed materialization and SQLite ignored supplied identities, the fixed Artifact-case factory was absent, and metadata-only results materialized optional properties instead of omitting them.
- **GREEN:** Pre-write ID selection, structural SQLite dependency injection, conditional optional fields, and fixed byte/hash cases made all 19 focused tests pass with clean typecheck.
- **REFACTOR:** No separate refactor commit was needed; the implementation remained a small extension of existing dependency/options patterns.

## Task Commits

The TDD gate and verification fix were committed atomically:

1. **Task 1 RED: failing deterministic Artifact contracts** - `1f7097b` (test)
2. **Task 1 GREEN: deterministic Artifact evidence** - `7bb0f89` (feat)
3. **Verification auto-fix: deterministic foreign provenance fixture** - `4fa2806` (fix)

## Files Created/Modified

- `packages/runtime/src/artifact-materialization.ts` - Accepts optional runtime IDs and selects Artifact/Event identities before calling the store.
- `packages/storage-sqlite/src/sqlite-artifact-store.ts` - Accepts a core-typed Artifact ID source, retains random fallback, exact blob length, content type, and absent optional fields.
- `scripts/compatibility/generate-v1-oracle.ts` - Provides fixed synthetic UTF-8 Artifact cases with byte lengths and SHA-256 commitments.
- `tests/runtime/artifact-materialization.test.ts` - Proves identity linkage across storage, Event payload, action references, and Artifact View projection.
- `tests/storage/sqlite-artifact.test.ts` - Proves injected/default IDs, exact Unicode bytes/hashes, cleanup, and metadata/blob/unavailable state distinctions.
- `tests/compatibility/oracle-regeneration.test.ts` - Proves fixed Artifact cases, rejected overwrite classification, and deterministic cross-repository provenance testing.

## Decisions Made

- Selected both the Artifact ID and its `artifact.created` Event ID before `ArtifactStore.put()` so failures cannot produce post-hoc identity rewriting.
- Used a small structural `SqliteArtifactIdGenerator` interface rather than importing runtime contracts into the storage package, preserving dependency direction.
- Derived `contentType` from explicit Artifact input or blob metadata and omitted optional record fields when absent, keeping record/blob state internally consistent.
- Kept Unicode strings byte-distinct exactly as supplied; no normalization step is permitted before byte counting or hashing.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Stabilized the foreign Git provenance test fixture**

- **Found during:** Plan-level full-suite verification
- **Issue:** The Plan 27-03 forged-revision test created a commit in a separate temporary repository but did not import that object into the repository under verification. Depending on commit timestamps, the SHA sometimes happened to match a local object and sometimes failed earlier as nonexistent.
- **Fix:** Fetched the exact foreign commit into the target temporary repository before asserting that its protected source tree differs.
- **Files modified:** `tests/compatibility/oracle-regeneration.test.ts`
- **Verification:** The focused provenance case passed, the entire regeneration file passed 11/11, and the full suite passed 291 tests with 2 intentional skips.
- **Committed in:** `4fa2806`

---

**Total deviations:** 1 auto-fixed (1 bug).
**Impact on plan:** The fix changes no frozen provenance semantics; it removes timestamp-dependent fixture behavior so the intended existing-commit/tree-mismatch contract is tested deterministically.

## Issues Encountered

- The first full-suite run exposed the provenance fixture race above; the narrow test-fixture correction resolved it without changing production behavior or the frozen contract.

## Known Stubs

None. Stub-pattern matches are initialized result arrays, a deliberate circular-metadata failure fixture, and an optional argument default that are all exercised by production/test flows.

## User Setup Required

None - no external service configuration or new dependency is required.

## Next Phase Readiness

- Artifact corpus and Bundle plans can consume stable identities, exact byte/hash cases, and explicit availability states.
- Python storage work has executable evidence for byte-count semantics, Unicode non-normalization, optional-field absence, and rejected conflicting identity reuse.
- No unresolved implementation, security, or verification blocker remains.

## Self-Check: PASSED

- All six implementation/test artifacts and this SUMMARY exist on disk.
- Commits `1f7097b`, `7bb0f89`, and `4fa2806` exist in RED-before-GREEN order with the verification fix afterward.
- Focused tests pass 19/19, regeneration passes 11/11, full verification passes 291 tests with 2 intentional skips, and typecheck passes.
- No generated Artifact input or output contains a temporary absolute path, user-home path, ambient credential, or provider body.

---
*Phase: 27-frozen-compatibility-oracle*
*Completed: 2026-08-04*
