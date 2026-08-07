---
phase: 27-frozen-compatibility-oracle
plan: "06"
subsystem: testing
tags: [compatibility, integrity, sha256, provenance, retirement, tdd]

requires:
  - phase: 27-frozen-compatibility-oracle
    provides: deterministic per-surface v1 evidence generators, independent inventory, and closed decision ledger
provides:
  - read-only fail-closed oracle verifier with structured path, byte, semantic, link, and provenance issues
  - deterministic tree diff plus explicit private generation and verification commands
  - package/public/runtime/Python boundary guards and RET-01 through RET-10 removal contract
affects: [27-09-corpus-promotion, phase-28-python-kernel, phase-37-python-only-cutover]

tech-stack:
  added: []
  patterns: [collect-all verification, lstat-before-read, exact inventory bijection, red-green task commits]

key-files:
  created:
    - scripts/compatibility/verify-v1-oracle.ts
    - tests/compatibility/oracle-rejections.test.ts
    - tests/compatibility/oracle-retirement.test.ts
  modified:
    - scripts/compatibility/generate-v1-oracle.ts
    - tests/compatibility/oracle-manifest.test.ts
    - tests/compatibility/oracle-regeneration.test.ts
    - package.json
    - .planning/phases/27-frozen-compatibility-oracle/27-VALIDATION.md

key-decisions:
  - "Verification validates committed Git trees against sourceRevision while deliberately ignoring worktree dirt; promotion alone owns cleanliness checks."
  - "Oracle tooling remains private package scripts and repository-internal source, with no package export, service, Python dependency, or authority path."
  - "Package CLIs build ignored workspace dist outputs first so they remain usable from clean checkouts without adding a runtime dependency."

patterns-established:
  - "Read-only corpus verification: validate paths, reject every symlink component, enumerate exact tree membership, then read and adjudicate bytes and meaning."
  - "Compatibility drift reports stable issue codes, JSON pointers, and first changed byte without repair or snapshot-update behavior."

requirements-completed: [SEM-02]

coverage:
  - id: D1
    description: "Fail-closed read-only verifier for unsafe paths, tree/inventory drift, byte and semantic tampering, Event policy, links, decisions, retirement gates, secrets, and Git provenance."
    requirement: SEM-02
    verification:
      - kind: integration
        ref: "tests/compatibility/oracle-rejections.test.ts and tests/compatibility/oracle-manifest.test.ts — 37 tests"
        status: pass
      - kind: integration
        ref: "pnpm exec vitest run tests/compatibility — 86 tests"
        status: pass
    human_judgment: false
  - id: D2
    description: "Deterministic added/removed/changed tree diagnostics and explicit fresh-root generation/read-only verification package commands."
    requirement: SEM-02
    verification:
      - kind: integration
        ref: "tests/compatibility/oracle-regeneration.test.ts — 23 tests"
        status: pass
      - kind: other
        ref: "two package-command generations compared byte-identically; verification preserved staging mtime and size"
        status: pass
    human_judgment: false
  - id: D3
    description: "Internal-only architecture guards and machine-visible RET-01 through RET-10 Phase 37 removal gates."
    requirement: SEM-02
    verification:
      - kind: integration
        ref: "tests/compatibility/oracle-retirement.test.ts — 8 tests"
        status: pass
      - kind: other
        ref: "pnpm test — 68 files, 353 passed, 2 credential-gated skips"
        status: pass
    human_judgment: false

duration: 24m
completed: 2026-08-04
status: complete
---

# Phase 27 Plan 06: Read-Only Verification and Retirement Summary

**Fail-closed byte-and-meaning verification with deterministic drift diagnostics, Git provenance checks, private developer commands, and an executable Phase 37 retirement contract**

## Performance

- **Duration:** 24 minutes
- **Started:** 2026-08-04T20:15:41Z
- **Completed:** 2026-08-04T20:39:23Z
- **Tasks:** 3
- **Files modified:** 8

## Accomplishments

- Added a strictly read-only recursive verifier that rejects unsafe paths and symlinks before access, proves exact manifest/tree/inventory bijections, validates byte and semantic commitments, and returns stable structured issues.
- Added strict Event envelope/payload rules, pointer/link/position checks, secret and absolute-path scans, and sourceRevision validation against committed protected source trees without consulting worktree dirt.
- Added deterministic tree diffing, explicit private generate/verify package commands, and regression coverage proving verification never rewrites corpus bytes, paths, or mtimes.
- Proved the temporary oracle is absent from package exports, production imports, services, Python runtime code, and authority surfaces while retaining all ten Phase 37 retirement gates.

## Task Commits

Each TDD task was committed atomically with a RED test commit followed by GREEN implementation:

1. **Task 27-06-01 RED: fail-closed verifier contract** — `1c1add4`
2. **Task 27-06-01 GREEN: read-only verifier** — `fc92e0d`
3. **Task 27-06-02 RED: command and drift contract** — `0e193d9`
4. **Task 27-06-02 GREEN: generation/verification commands** — `b9f6992`
5. **Task 27-06-03 RED: retirement contract** — `fc415b6`
6. **Task 27-06-03 GREEN: validation map** — `9b48152`
7. **Post-task correctness fix: clean-checkout CLI build prerequisite** — `45fe5c4`

## Files Created/Modified

- `scripts/compatibility/verify-v1-oracle.ts` — read-only verifier, tree diff, structured report, provenance checks, and CLI.
- `scripts/compatibility/generate-v1-oracle.ts` — Node-runnable workspace imports and explicit output/version CLI.
- `tests/compatibility/oracle-rejections.test.ts` — adversarial paths, symlinks, tampering, semantics, field policy, read-only, and provenance cases.
- `tests/compatibility/oracle-manifest.test.ts` — public verifier type and safe-path contract.
- `tests/compatibility/oracle-regeneration.test.ts` — two-root equality, drift diagnostics, package commands, clean-checkout, and dirty-worktree verification.
- `tests/compatibility/oracle-retirement.test.ts` — public/package/production/Python/service/authority guards and RET gate checks.
- `package.json` — private `compatibility:generate:v1` and `compatibility:verify:v1` commands.
- `.planning/phases/27-frozen-compatibility-oracle/27-VALIDATION.md` — implemented 19-task, nine-plan, eight-wave Nyquist map.

## Decisions Made

- Read-only provenance accepts a later corpus-only or unrelated commit when every protected source path still matches the recorded commit; uncommitted worktree dirt is irrelevant to verification.
- The verifier contains no filesystem write primitive and treats all manifest paths as untrusted until normalization and component-by-component `lstat` checks pass.
- The root package exposes oracle operations only as private developer scripts. No barrel, export map, runtime API, service route, or Python code receives an oracle dependency.
- Final complete staging assembly, committed-corpus equality, and promotion remain owned by Plan 27-09. The current explicit generator command exercises the reviewed fresh-root shell; full valid-corpus verification is already covered with independently assembled temporary corpora.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Made the planned generation command executable**
- **Found during:** Task 27-06-02
- **Issue:** The existing generator had no CLI, and direct Node type stripping could not resolve three repository-source `.js` imports.
- **Fix:** Added explicit `--output`, `--corpus-version`, and `--mode` parsing, rejected all revision overrides as unknown arguments before writes, and used existing workspace package outputs for runtime dependencies.
- **Files modified:** `scripts/compatibility/generate-v1-oracle.ts`, `package.json`
- **Verification:** `tests/compatibility/oracle-regeneration.test.ts` passes the real package command and confirms fresh-root output plus override rejection.
- **Committed in:** `b9f6992`

**2. [Rule 2 - Missing Critical] Made both CLI commands reliable in clean checkouts**
- **Found during:** Plan-level verification
- **Issue:** Workspace `dist` directories are ignored and may not exist immediately after install, so the advertised commands could fail before reaching their CLI.
- **Fix:** Both private package commands now run the pinned workspace build before invoking Node type stripping. Corpus verification remains read-only and still preserves corpus paths, bytes, and mtimes.
- **Files modified:** `package.json`, `tests/compatibility/oracle-regeneration.test.ts`
- **Verification:** Focused regeneration tests pass 23/23; the full suite passes 353 tests; real package commands complete from the repository root.
- **Committed in:** `45fe5c4`

---

**Total deviations:** 2 auto-fixed (1 blocking issue, 1 missing critical functionality)
**Impact on plan:** Both fixes were required to make the planned private commands truthful and usable; no dependency, public surface, service, or runtime authority path was added.

## TDD Gate Compliance

- RED commits exist for all three `tdd="true"` tasks: `1c1add4`, `0e193d9`, and `fc415b6`.
- Each RED commit failed only at its intended public behavior seam before the corresponding GREEN commit.
- GREEN commits follow each RED commit: `fc92e0d`, `b9f6992`, and `9b48152`.

## Verification

- `pnpm exec vitest run tests/compatibility` — 10 files, 86 passed.
- `pnpm typecheck` — passed.
- `pnpm test` — 68 files, 353 passed, 2 credential-gated skips.
- `pnpm test:python-documents` — 4 passed.
- Two explicit package-command generations produced byte-identical `oracle-shell.json` files.
- Read-only verification against the pre-Plan-27-09 shell-only staging tree returned the expected `manifest_missing` failure without changing its mtime or size; complete valid temporary corpora pass in `oracle-rejections.test.ts`.

## Known Stubs

None. Final manifest assembly and promotion are intentionally assigned to Plan 27-09 rather than represented by placeholder behavior here.

## Issues Encountered

- Node type stripping does not redirect TypeScript-authored `.js` source specifiers. The generator CLI now resolves existing built workspace packages, and package commands ensure those outputs exist first.

## User Setup Required

None — no external service, credential, or new dependency is required.

## Next Phase Readiness

- Plan 27-09 can finalize the aggregate manifest, verify two complete fresh staging trees through `verifyOracle()`, and promote the absent `tests/fixtures/compatibility/v1` corpus from a clean source commit.
- The verifier already accepts the later corpus-only promotion commit and rejects any committed protected-source drift.
- No blockers remain. The only expected pending validation item is final corpus assembly/promotion in Plan 27-09.

## Self-Check: PASSED

- All three created implementation/test files and this summary exist.
- All seven RED, GREEN, and correctness-fix commits resolve as Git commit objects.

---
*Phase: 27-frozen-compatibility-oracle*
*Completed: 2026-08-04*
