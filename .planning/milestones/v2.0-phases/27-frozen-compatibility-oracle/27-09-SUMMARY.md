---
phase: 27-frozen-compatibility-oracle
plan: "09"
subsystem: testing
tags: [compatibility, golden-corpus, provenance, deterministic-generation, tdd]

requires:
  - phase: 27-frozen-compatibility-oracle
    provides: complete v1 inventory, deterministic per-surface evidence generators, closed decision ledger, and read-only verifier
provides:
  - committed immutable v1 compatibility corpus with 286 evidence files and one manifest
  - deterministic aggregate generation with complete inventory, decision, retirement, and file bijection
  - clean pre-promotion Git provenance that remains valid after the corpus-only commit advances HEAD
affects: [phase-28-python-kernel, phase-37-python-only-cutover, cross-sdk-compatibility]

tech-stack:
  added: []
  patterns: [fresh-root-only promotion, manifest-last sealing, corpus-only commit, committed-tree provenance]

key-files:
  created:
    - tests/fixtures/compatibility/v1/manifest.json
    - tests/fixtures/compatibility/v1/evidence/
  modified:
    - scripts/compatibility/generate-v1-oracle.ts
    - scripts/check-ontology-canonical.mjs
    - tests/compatibility/oracle-manifest.test.ts
    - tests/compatibility/oracle-regeneration.test.ts
    - tests/compatibility/oracle-retirement.test.ts
    - tests/public-api/ontology-guards.test.ts

key-decisions:
  - "Promotion records the full clean pre-promotion source commit and later verifies protected committed-tree equality instead of requiring sourceRevision to equal HEAD."
  - "The committed corpus is copied once from one of two independently verified, byte-identical fresh roots, with evidence written before manifest.json."
  - "All 22 resolved ledger decisions remain represented in the manifest, including decisions not directly referenced by an inventory row."

patterns-established:
  - "Promotion recovery: if a post-promotion gate exposes protected-source drift, revert only the corpus commit, fix and commit source, then regenerate and promote into an absent root rather than overwriting corpus bytes."
  - "Ontology guards match legacy names at token boundaries so legitimate compatibility prose remains admissible."

requirements-completed: [SEM-02]

coverage:
  - id: D1
    description: "Inventory-complete deterministic aggregate generator with all evidence, 22 resolved decisions, ten retirement gates, and manifest-last sealing."
    requirement: SEM-02
    verification:
      - kind: integration
        ref: "tests/compatibility/oracle-regeneration.test.ts and tests/compatibility/oracle-manifest.test.ts — complete two-root, manifest, inventory, and provenance contract"
        status: pass
      - kind: integration
        ref: "focused compatibility gate — 5 files, 69 passed"
        status: pass
    human_judgment: false
  - id: D2
    description: "Committed v1 corpus containing 286 evidence files plus manifest.json, byte-identical to both independently generated roots and free of unsafe paths or secret material."
    requirement: SEM-02
    verification:
      - kind: other
        ref: "two fresh promotion roots and committed corpus compared with exact sorted path and byte equality — 287 total files"
        status: pass
      - kind: integration
        ref: "pnpm compatibility:verify:v1 — checkedFiles 286, issues 0"
        status: pass
    human_judgment: false
  - id: D3
    description: "Immutable source provenance records 660f42ae71139765e86838ccfbf4b45d33adfa7b and remains valid after the corpus-only commit advances HEAD."
    requirement: SEM-02
    verification:
      - kind: integration
        ref: "post-commit verifier plus Git cat-file and protected-tree equality checks"
        status: pass
      - kind: other
        ref: "read-only verification preserved corpus paths, sizes, bytes, and mtimes"
        status: pass
    human_judgment: false

duration: 30m
completed: 2026-08-04
status: complete
---

# Phase 27 Plan 09: Frozen Compatibility Corpus Promotion Summary

**A sealed 287-file v1 compatibility corpus generated twice from clean source, verified byte-for-byte, and committed with durable Git provenance to 660f42ae71139765e86838ccfbf4b45d33adfa7b**

## Performance

- **Duration:** 30 minutes
- **Started:** 2026-08-04T20:44:18Z
- **Completed:** 2026-08-04T21:14:19Z
- **Tasks:** 2
- **Files modified:** 293

## Accomplishments

- Finalized aggregate generation for every v1 Event, Command, View, provider, SQLite, Artifact, Bundle, rejection, encoding, numeric, field-policy, decision, and retirement case.
- Generated two independent fresh promotion roots, verified all 286 evidence members in each, proved exact path/byte equality, and copied one verified tree into the previously absent committed corpus with `manifest.json` last.
- Committed the corpus alone at `7f869ac`, retaining source revision `660f42ae71139765e86838ccfbf4b45d33adfa7b`; post-commit verification accepts the later HEAD because all protected source trees remain identical.
- Proved verification is read-only by comparing complete path/size/mtime state before and after verification, and passed the full TypeScript and Python suites.

## Task Commits

Task 1 followed RED/GREEN TDD, and Task 2 produced a corpus-only promotion commit:

1. **Task 27-09-01 RED: require complete promotion corpus** — `fa45cf3`
2. **Task 27-09-01 GREEN: finalize aggregate promotion source** — `d742de5`
3. **Task 27-09-01 completeness fix: include the full resolved ledger** — `0090c41`
4. **First verified corpus promotion** — `a99dad5`
5. **Safe recovery: revert only the first corpus commit** — `4d6bce1`
6. **Protected-source fix: align retirement and ontology guards** — `660f42a`
7. **Task 27-09-02 final corpus-only promotion** — `7f869ac`

## Files Created/Modified

- `tests/fixtures/compatibility/v1/manifest.json` — sealed aggregate manifest with source provenance, 22 decisions, ten retirement gates, and exact evidence metadata.
- `tests/fixtures/compatibility/v1/evidence/` — 286 immutable JSONL evidence members spanning the full compatibility inventory.
- `scripts/compatibility/generate-v1-oracle.ts` — complete aggregate generation, ledger closure, inventory/path uniqueness, fresh scratch isolation, and manifest-last output.
- `tests/compatibility/oracle-manifest.test.ts` — exact manifest shape, decision coverage, inventory, and file bijection.
- `tests/compatibility/oracle-regeneration.test.ts` — deterministic full generation, clean promotion provenance, two-root equality, and committed-corpus isolation.
- `tests/compatibility/oracle-retirement.test.ts` — retirement validation against the actual final manifest and its named Phase 37 gates.
- `scripts/check-ontology-canonical.mjs` and `tests/public-api/ontology-guards.test.ts` — token-aware legacy-name matching that permits legitimate decision-ledger prose.

## Decisions Made

- `sourceRevision` names the clean source commit immediately before corpus generation. It intentionally does not name the future corpus commit and need not equal later HEAD values.
- Promotion never writes directly through an existing corpus. Both successful promotions began with an absent root; after the first post-promotion gate failure, the corpus-only commit was safely reverted before source was fixed and a fresh promotion was performed.
- Decision manifest entries cover all 22 resolved ledger decisions, not merely the 21 directly referenced by inventory rows.
- Synthetic provider failure fixtures retain only explicit `[REDACTED]` authorization, API-key, and token values; scans found no real credentials, home/temp paths, executable members, or historical user data.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Aligned pointer metadata with JSON omission semantics**
- **Found during:** Task 27-09-01 GREEN verification
- **Issue:** Required-pointer collection included object properties whose `undefined` values are omitted from JSON bytes, producing false missing-pointer reports on aggregate verification.
- **Fix:** Pointer collection now skips undefined object members, matching actual wire serialization.
- **Files modified:** `scripts/compatibility/generate-v1-oracle.ts`
- **Verification:** Complete generated corpus verifies with 286 checked evidence files and zero issues.
- **Committed in:** `d742de5`

**2. [Rule 2 - Missing Critical] Included the complete resolved decision ledger**
- **Found during:** Task 27-09-02 pre-copy completeness audit
- **Issue:** `V1-SYNTHETIC-EVIDENCE` was resolved but omitted because it was not directly referenced by an inventory row.
- **Fix:** The generator now retains every resolved `V1-*` ledger entry while still requiring every inventory reference to resolve; tests assert the exact 22-ID set.
- **Files modified:** `scripts/compatibility/generate-v1-oracle.ts`, `tests/compatibility/oracle-manifest.test.ts`
- **Verification:** Both fresh roots contain 22 decisions and remain byte-identical.
- **Committed in:** `0090c41`

**3. [Rule 1 - Bug] Recovered from protected-source regressions without overwriting the corpus**
- **Found during:** Full-suite verification after the first corpus-only promotion
- **Issue:** The retirement test still expected the removed shell sentinel, and the ontology scanner matched the legacy term as a substring inside legitimate “supersession” ledger prose.
- **Fix:** Reverted only `a99dad5` via `4d6bce1`, restoring an absent corpus; updated retirement coverage to read final manifest gates and made the ontology pattern token-aware; committed clean source and regenerated two entirely fresh roots before the final corpus-only promotion.
- **Files modified:** `tests/compatibility/oracle-retirement.test.ts`, `scripts/check-ontology-canonical.mjs`, `tests/public-api/ontology-guards.test.ts`
- **Verification:** Focused guard tests pass 12/12; pre-promotion full suite passes 68 files / 356 tests with two credential-gated skips; final corpus verifier passes with zero issues.
- **Committed in:** `4d6bce1`, `660f42a`, `7f869ac`

---

**Total deviations:** 3 auto-fixed (2 bugs, 1 missing critical completeness rule)
**Impact on plan:** Every fix tightened correctness or preserved the no-overwrite provenance contract. No dependency, public runtime surface, network path, authority path, or mutable corpus update mechanism was added.

## TDD Gate Compliance

- RED commit `fa45cf3` failed at the intended public seams because generation still emitted only `oracle-shell.json` and no complete manifest.
- GREEN commit `d742de5` followed the RED commit and made the focused manifest/provenance tests pass.
- The later ledger and guard fixes were correctness deviations discovered by widened promotion/full-suite gates and were committed before the final clean source revision was captured.

## Verification

- Two fresh promotion roots from `660f42ae71139765e86838ccfbf4b45d33adfa7b` — 286 evidence files each, both verified with zero issues, exact sorted-path and byte equality.
- Committed corpus — 287 total files, exactly equal to both fresh roots.
- `pnpm compatibility:verify:v1` after `7f869ac` — `ok`, 286 checked files, zero issues.
- Focused compatibility gate — 5 files, 69 passed.
- Focused retirement/ontology gate — 12 passed.
- `pnpm typecheck` — passed.
- `pnpm test` — 68 files, 356 passed, 2 credential-gated skips.
- `pnpm test:python-documents` — 4 passed.
- Post-commit Git provenance — source revision exists as a commit, HEAD differs, and protected committed-tree equality passes.
- Read-only verification — complete corpus path/size/mtime digest unchanged before and after.

## Known Stubs

None. All inventory members, decision rows, retirement gates, and committed files are fully materialized and verified.

## Issues Encountered

- The first corpus promotion passed its verifier but exposed two regressions only when the entire repository suite ran. The corpus-only commit was safely reverted rather than patched, and final promotion was repeated from a new clean source revision and absent target.
- The ontology rule was correctly retained while being narrowed from substring matching to token matching, avoiding a false positive on normative supersession prose.

## User Setup Required

None — generation uses deterministic synthetic inputs and requires no external service or credentials.

## Next Phase Readiness

- Phase 28 can consume the committed v1 corpus as the frozen cross-language compatibility target.
- Phase 37 has ten machine-visible removal gates with preserved data, ledger, hashes, and Git provenance.
- No unresolved blockers remain.

## Self-Check: PASSED

- The committed manifest and all 286 evidence files exist.
- RED, GREEN, correctness-fix, recovery, source, and final corpus commits all resolve as Git commit objects.
- Source revision `660f42ae71139765e86838ccfbf4b45d33adfa7b` resolves as a commit and remains valid after corpus commit `7f869ac`.

---
*Phase: 27-frozen-compatibility-oracle*
*Completed: 2026-08-04*
