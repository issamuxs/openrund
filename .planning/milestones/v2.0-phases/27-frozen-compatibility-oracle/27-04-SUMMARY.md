---
phase: 27-frozen-compatibility-oracle
plan: "04"
subsystem: compatibility-oracle
tags: [determinism, coordination, waits, delegation, bundles]

requires:
  - phase: 27-03-deterministic-oracle-shell
    provides: Fixed runtime entropy and generator shell
  - phase: 27-08-deterministic-artifact-evidence
    provides: Deterministic Artifact identity and byte evidence
provides:
  - Deterministic Check, Checkpoint, Delegation, and Wait factory evidence
  - Repeatable complete, audit, and redacted Bundle profile evidence
affects: [27-05-corpus-generation, 27-06-read-only-verification, 27-09-promotion]

tech-stack:
  added: []
  patterns:
    - optional generic identity dependency objects with unchanged live fallbacks
    - one ordered fixed entropy source allocated before Event creation
    - relative Bundle tree hashing over real SQLite-backed exports

key-files:
  created: []
  modified:
    - packages/runtime/src/check-control.ts
    - packages/runtime/src/checkpoint-control.ts
    - packages/runtime/src/delegation-control.ts
    - packages/runtime/src/interaction-control.ts
    - packages/runtime/src/timer-control.ts
    - packages/runtime/src/wait-approval-control.ts
    - packages/runtime/src/wait-control.ts
    - scripts/compatibility/generate-v1-oracle.ts
    - tests/compatibility/oracle-regeneration.test.ts

key-decisions:
  - Preserve every existing live identity fallback while allowing compatibility scenarios to inject one ordered RuntimeIdGenerator.
  - Record canonical wait.expired and reconciliation-kind evidence as contract inventory because the current runtime represents those operational transitions through resolved/cancelled and aggregate Wait Events.
  - Compare Bundle outputs only through relative paths and fixed byte commitments, with all SQLite resources closed in finally blocks.

patterns-established:
  - "Coordination determinism: inject generic IDs and clocks before Event creation while retaining live fallbacks."
  - "Bundle evidence: compare safe relative trees and fixed byte commitments from real stores closed in finally blocks."

requirements-completed: [SEM-02]

coverage:
  - id: D1
    description: Check, Checkpoint, and Delegation evidence uses fixed identities with exact parent/child, join, handoff, and cancellation links
    requirement: SEM-02
    verification:
      - kind: integration
        ref: "tests/compatibility/oracle-regeneration.test.ts#Check, Checkpoint, and Delegation regeneration"
        status: pass
      - kind: integration
        ref: "Phase 27-04 focused coordination suites"
        status: pass
    human_judgment: false
  - id: D2
    description: All Wait kinds and lifecycle outcomes preserve deterministic IDs, threshold behavior, aggregate links, and field presence distinctions
    requirement: SEM-02
    verification:
      - kind: integration
        ref: "tests/compatibility/oracle-regeneration.test.ts#Wait lifecycle regeneration"
        status: pass
      - kind: integration
        ref: "Phase 27-04 focused Wait suites"
        status: pass
    human_judgment: false
  - id: D3
    description: Complete, audit, and redacted Bundle profiles reproduce identical safe relative trees and commitments across roots
    requirement: SEM-02
    verification:
      - kind: integration
        ref: "tests/compatibility/oracle-regeneration.test.ts#Bundle profiles"
        status: pass
      - kind: other
        ref: "pnpm typecheck && pnpm test"
        status: pass
    human_judgment: false

duration: 39min
completed: 2026-08-04
status: complete
---

# Phase 27 Plan 04: Deterministic Coordination and Bundle Profiles Summary

Fixed pre-creation entropy now covers coordination topology and every Wait factory, while real SQLite-backed exports reproduce complete, audit, and redacted Bundle trees without leaking staging paths.

## Performance

- **Duration:** 39 minutes
- **Started:** 2026-08-04T19:16:52Z
- **Completed:** 2026-08-04T19:56:18Z
- **Tasks:** 3
- **Files modified:** 9

## Accomplishments

- Added optional identity dependencies to Check, Checkpoint, Delegation, interaction, timer, approval, and aggregate Wait controls without changing omitted-dependency behavior.
- Preserved exact parent spawn, child bootstrap, establishment, all/any/quorum join, handoff, cancellation, aggregate resume, and late-handoff links under fixed identities.
- Generated deterministic Wait evidence for approval, interaction, timer, join, and reconciliation paths, including one-millisecond timer thresholds and omitted/explicit/revised approval input states.
- Generated complete, audit, and redacted Bundles from identical fixed Events and Artifacts using real SQLite stores and a fixed `exportedAt`, plus distinct zero, included, missing-byte, unavailable, audit-omitted, and redacted Artifact states.
- Proved two independent output roots produce identical relative trees, Event-chain heads, and per-profile Bundle commitments with no temporary or user-home paths in returned evidence.

## Task Commits

Each task followed RED/GREEN TDD and was committed atomically:

1. **Task 27-04-01: Inject Check, Checkpoint, and Delegation identities**
   - `d3b2eec` — failing coordination identity and topology contracts
   - `6c5a6be` — fixed identity seams and deterministic coordination evidence
2. **Task 27-04-02: Inject every Wait lifecycle identity**
   - `abf5be1` — failing Wait lifecycle, threshold, and presence contracts
   - `000e882` — fixed Wait identities and real-factory lifecycle evidence
3. **Task 27-04-03: Assemble deterministic Bundle profile scenarios**
   - `f7f02a8` — failing Bundle profile reproducibility contracts
   - `77b2944` — real-store Bundle profile and Artifact-state generator

## Files Created/Modified

- `packages/runtime/src/check-control.ts` — optional fixed clock and Event identity dependency.
- `packages/runtime/src/checkpoint-control.ts` — injected Checkpoint, Annotation, and Event identities.
- `packages/runtime/src/delegation-control.ts` — injected Delegation, child Run, Wait, Annotation, and Event identities across topology and lifecycle paths.
- `packages/runtime/src/interaction-control.ts` — injected interaction Wait and Event identities.
- `packages/runtime/src/timer-control.ts` — injected timer Wait and Event identities while preserving exact threshold checks.
- `packages/runtime/src/wait-approval-control.ts` — injected approval Wait and Event identities.
- `packages/runtime/src/wait-control.ts` — injected approval resolution and aggregate resume Event identities.
- `scripts/compatibility/generate-v1-oracle.ts` — deterministic coordination, Wait, and Bundle profile evidence generators.
- `tests/compatibility/oracle-regeneration.test.ts` — byte/link, threshold, presence, tree, commitment, and path-safety contracts.

## Decisions Made

- Optional dependency objects remain internal generic seams; no public oracle export, global override, or second authority path was introduced.
- Omitted dependencies retain existing deterministic labels or live UUID/time defaults exactly, depending on the original factory behavior.
- Canonical `wait.expired` and reconciliation-kind declarations are marked `contract_inventory`; operational factory evidence remains `factory_emitted`.
- Bundle evidence contains only relative paths, hashes, byte counts, manifests, and fixed synthetic content; filesystem roots never enter the returned evidence.

## Deviations from Plan

None - plan executed exactly as written.

## Verification

- Plan slice: **67/67 tests passed**.
- Full repository suite: **60 test files passed; 297 tests passed, 2 skipped**.
- TypeScript project references: **`pnpm typecheck` passed**.
- TDD gates are present in order for all three tasks: RED test commit followed by GREEN feature commit.

## Known Stubs

None. Empty dependency objects, collections, and zero-Artifact evidence are intentional exercised states, not incomplete wiring.

## Security and Trust Boundaries

- Generator inputs are fixed synthetic values; no provider, credential, user-home state, or live external body is read.
- Bundle generation is confined to an explicit fresh output root and returns only safe relative tree paths.
- No new network endpoint, authentication path, schema trust boundary, or unplanned security surface was introduced.

## Self-Check: PASSED

- All nine modified implementation/test files exist.
- All six task commits exist in repository history.
- Focused, typecheck, complete plan-slice, and full-suite verification claims match the recorded execution results.

## Next Phase Readiness

Coordination, Wait, Artifact, and Bundle inputs now regenerate deterministically and are ready for Plan 27-05 to assemble the versioned wire, View, SQLite, Artifact, and Bundle corpus.
