---
phase: 27-frozen-compatibility-oracle
plan: "07"
subsystem: compatibility
tags: [typescript, providers, bundles, determinism, security, vitest]

requires:
  - phase: 27-01-contract-inventory
    provides: Resolved provider-argument, timestamp, raw JSONL, canonical hash, and Bundle limitation decisions
provides:
  - Fail-closed provider tool argument parsing with stable safe classifications
  - Optional validated Bundle exportedAt injection for byte-deterministic evidence
  - Executable coverage for Bundle profiles, exact JSONL bytes, canonical commitments, and live defaults
affects: [27-03-deterministic-generator, 27-05-provider-and-bundle-corpus, python-providers, python-bundles]

tech-stack:
  added: []
  patterns: [safe structured boundary errors, validate entropy before file creation, raw-and-canonical byte separation]

key-files:
  created: []
  modified:
    - packages/core/src/provider-normalization.ts
    - tests/providers/provider-normalization.test.ts
    - docs/providers.md
    - packages/runtime/src/orun.ts
    - tests/runtime/orun-bundle.test.ts
    - docs/bundles.md

key-decisions:
  - "Treat only missing or empty provider argument text as empty input; malformed JSON and parsed non-objects fail with stable safe classifications."
  - "Validate an injected Bundle exportedAt as exact UTC RFC 3339 milliseconds before creating bundle files, while retaining Date.toISOString() for omitted input."
  - "Keep Bundle v1 layout, profiles, raw Event JSONL, canonical hashing, and known requiredProviders/external-Artifact limitations unchanged."

patterns-established:
  - "Provider parse boundary: distinguish absent input, malformed JSON, and parsed non-objects without copying untrusted input into errors."
  - "Deterministic writer seam: receive and validate timestamp entropy before any filesystem promotion, with live defaults remaining source-compatible."

requirements-completed: [SEM-02]

coverage:
  - id: D1
    description: Malformed and non-object provider tool arguments fail closed with stable redacted errors while absent input remains explicit
    requirement: SEM-02
    verification:
      - kind: unit
        ref: "tests/providers/provider-normalization.test.ts#provider argument matrix"
        status: pass
      - kind: integration
        ref: "pnpm exec vitest run tests/providers/provider-normalization.test.ts tests/providers/openai.test.ts tests/providers/anthropic.test.ts tests/providers/local-openai-compatible.test.ts"
        status: pass
    human_judgment: false
  - id: D2
    description: Bundle export accepts an exact validated exportedAt while omitted input retains the live timestamp default
    requirement: SEM-02
    verification:
      - kind: integration
        ref: "tests/runtime/orun-bundle.test.ts#exact supplied export time and invalid timestamp rejection"
        status: pass
    human_judgment: false
  - id: D3
    description: Complete, audit, and redacted Bundle profiles preserve exact file, Event-chain, Bundle, Artifact, and raw/canonical commitments
    requirement: SEM-02
    verification:
      - kind: integration
        ref: "tests/runtime/orun-bundle.test.ts#profile commitments and construction-order Event JSONL"
        status: pass
      - kind: other
        ref: "pnpm typecheck && pnpm build"
        status: pass
    human_judgment: false

duration: 14min
completed: 2026-08-04
status: complete
---

# Phase 27 Plan 07: Provider and Bundle Determinism Summary

**Fail-closed provider argument parsing and validated Bundle export timestamps now make predecessor evidence safe and byte-deterministic without changing authority, layout, profiles, or commitment algorithms.**

## Performance

- **Duration:** 14 min
- **Started:** 2026-08-04T18:24:32Z
- **Completed:** 2026-08-04T18:38:11Z
- **Tasks:** 2
- **Files modified:** 6

## Accomplishments

- Replaced malformed/non-object provider argument coercion with `ProviderToolArgumentsError`, stable `provider_tool_arguments_invalid` classification, and a fixed message that excludes raw bodies and secret-looking values.
- Added optional exact `BundleExportInput.exportedAt` validation before bundle filesystem creation while preserving the current live-time default for existing callers.
- Proved deterministic manifest bytes, complete/audit/redacted profile commitments, Artifact inclusion/omission metadata, construction-order Event JSONL with final LF, and recursively canonical object hashing.

## TDD Cycle

- **Task 1 RED:** The new malformed/non-object matrix failed in six cases because the shared parser returned `{}` instead of rejecting; absent, empty, valid nested, dotted-name, single-call, and batch behavior stayed green.
- **Task 1 GREEN:** A structured safe error and explicit parse classifications made all provider tests pass without changing adapter authority or live-call behavior.
- **Task 2 RED:** The Bundle suite failed exactly because supplied `exportedAt` was ignored and invalid timestamp spelling did not reject; the other 13 layout/profile/commitment cases passed.
- **Task 2 GREEN:** The optional timestamp seam and strict ISO round-trip validation made all 15 Bundle tests pass without changing schema, layout, profiles, JSONL rendering, or hashing.
- **REFACTOR:** No separate refactor was needed; both GREEN implementations were already minimal and the full gates remained clean.

## Task Commits

Each TDD gate was committed atomically:

1. **Task 1 RED: failing provider argument contracts** - `2b3cd82` (test)
2. **Task 1 GREEN: fail-closed provider argument boundary** - `2a0a673` (feat)
3. **Task 2 RED: failing deterministic Bundle time contracts** - `40160f7` (test)
4. **Task 2 GREEN: deterministic Bundle export timestamp** - `65621b5` (feat)

## Files Created/Modified

- `packages/core/src/provider-normalization.ts` - Defines the stable provider argument error and rejects malformed/non-object argument payloads.
- `tests/providers/provider-normalization.test.ts` - Covers absent, empty, nested object, malformed, array, scalar, null, redaction, dotted-name, single-call, and batch cases.
- `docs/providers.md` - Defines the parse-versus-Command rejection split and safe provider error detail policy.
- `packages/runtime/src/orun.ts` - Adds optional `exportedAt` input and validates exact millisecond UTC spelling before Bundle file creation.
- `tests/runtime/orun-bundle.test.ts` - Covers injected/default/invalid timestamps, repeated bytes, three profiles, Artifact metadata, JSONL bytes, and canonical hashes.
- `docs/bundles.md` - Freezes deterministic writer, profile, raw/canonical, known limitation, and future-version rules.

## Decisions Made

- Empty provider input is restricted to missing or zero-length argument text; whitespace-only, malformed, array, scalar, and null input are not silently legalized.
- Provider argument errors expose only stable code and classification metadata; they do not attach parser causes or untrusted provider content.
- Supplied Bundle export time is accepted only when parsing round-trips to the exact `YYYY-MM-DDTHH:mm:ss.sssZ` string, and validation occurs before reading Events or creating the Bundle tree.
- The export timestamp remains manifest evidence rather than a Bundle commitment input, preserving the frozen v1 commitment algorithm.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None. The Task 2 RED commit approval was interrupted once before staging; it was retried without any partial Git state or code change.

## Known Stubs

None. Stub-pattern matches are existing initialized accumulators and default option values that are fully populated by their production paths.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Deterministic oracle generation can now supply Bundle export time before emission and record exact reproducible manifest bytes.
- Provider corpus work can distinguish absent input from safe malformed/non-object failures without live credentials or adapter authority.
- No unresolved implementation, security, or verification blocker remains.

## Self-Check: PASSED

- All six implementation/test/documentation artifacts and this SUMMARY exist on disk.
- Task commits `2b3cd82`, `2a0a673`, `40160f7`, and `65621b5` exist in RED-before-GREEN order.
- Combined deterministic verification passed 38/38 tests with three live-provider cases disabled, followed by clean `pnpm typecheck` and `pnpm build` gates.
- Coverage metadata validates with all three deliverables automatically covered by passing evidence.

---
*Phase: 27-frozen-compatibility-oracle*
*Completed: 2026-08-04*
